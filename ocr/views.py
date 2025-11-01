import asyncio
import base64
import json
from io import BytesIO
from django.utils import timezone

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:
    HEIF_SUPPORTED = False

from gemini_webapi import GeminiClient
from gemini_webapi.constants import Model
from .models import UserGeminiConfig


@csrf_exempt
@require_http_methods(["POST"])
def extract_text_from_image(request):
    """
    Endpoint para extraer texto de una imagen usando Google Gemini.
    Requiere el parámetro 'telegram_user' para identificar al usuario.
    """
    
    try:
        # Obtener telegram_user del request
        telegram_user = None
        if request.POST.get('telegram_user'):
            telegram_user = request.POST.get('telegram_user')
        elif request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
                telegram_user = body.get('telegram_user')
            except:
                pass
        
        if not telegram_user:
            return JsonResponse({
                'success': False,
                'error': 'Parámetro "telegram_user" es requerido. Envía tu username de Telegram.'
            }, status=400)
        
        # Limpiar el telegram_user (remover @ si existe)
        telegram_user = telegram_user.lstrip('@').strip()
        
        # Buscar la configuración del usuario
        try:
            user_config = UserGeminiConfig.objects.select_related('user').get(
                telegram_user=telegram_user,
                is_active=True
            )
        except UserGeminiConfig.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Usuario de Telegram "@{telegram_user}" no encontrado o no tiene configuración de Gemini activa. Por favor configura tus cookies en el panel de administración.'
            }, status=404)
        
        # Validar que tenga las cookies necesarias
        if not user_config.gemini_psid or not user_config.gemini_psidts:
            return JsonResponse({
                'success': False,
                'error': f'Configuración incompleta para el usuario "@{telegram_user}". Por favor configura las cookies de Gemini en el panel de administración.'
            }, status=500)
        
        image_data = None
        original_format = None
        
        # Opción 1: Imagen enviada como archivo
        if request.FILES.get('image'):
            image_file = request.FILES['image']
            original_format = image_file.content_type
            
            # Tipos permitidos (ahora incluye HEIC si está instalado pillow-heif)
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']
            if HEIF_SUPPORTED:
                allowed_types.extend(['image/heic', 'image/heif'])
            
            if image_file.content_type not in allowed_types:
                error_msg = f'Tipo no soportado: {image_file.content_type}. Tipos permitidos: {", ".join(allowed_types)}'
                if not HEIF_SUPPORTED and image_file.content_type in ['image/heic', 'image/heif']:
                    error_msg += '. HEIC detectado pero no soportado en el servidor. Envía la imagen en formato JPEG o PNG.'
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)
            
            # Validar tamaño (máximo 10MB)
            max_size = 10 * 1024 * 1024
            if image_file.size > max_size:
                return JsonResponse({
                    'success': False,
                    'error': f'Archivo muy grande (max 10MB). Tamaño: {image_file.size / 1024 / 1024:.2f}MB'
                }, status=400)
            
            # Leer imagen
            image_data = image_file.read()
            
            # Si es HEIC/HEIF, convertir a JPEG automáticamente
            if image_file.content_type in ['image/heic', 'image/heif']:
                try:
                    img = Image.open(BytesIO(image_data))
                    # Convertir a RGB si es necesario
                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    # Guardar como JPEG con buena calidad
                    output = BytesIO()
                    img.save(output, format='JPEG', quality=90, optimize=True)
                    image_data = output.getvalue()
                    original_format = f"{original_format} (convertido a JPEG)"
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'error': f'Error al convertir HEIC a JPEG: {str(e)}'
                    }, status=400)
        
        # Opción 2: Imagen enviada como base64 en JSON
        elif request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
                image_base64 = body.get('image_base64', '')
                
                if not image_base64:
                    return JsonResponse({
                        'success': False,
                        'error': 'Campo "image_base64" no encontrado en el JSON'
                    }, status=400)
                
                # Remover el prefijo data:image si existe
                if ',' in image_base64:
                    image_base64 = image_base64.split(',')[1]
                
                image_data = base64.b64decode(image_base64)
                
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Error al decodificar: {str(e)}'}, status=400)
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Enviar imagen como archivo (multipart/form-data) o base64 (application/json)'
            }, status=400)
        
        if not image_data:
            return JsonResponse({'success': False, 'error': 'No se pudo leer imagen'}, status=400)
        
        # Validar que sea una imagen válida usando PIL
        try:
            img = Image.open(BytesIO(image_data))
            img.verify()
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Imagen inválida: {str(e)}'}, status=400)
        
        # Obtener prompt personalizado si se proporciona
        prompt = None
        if request.POST.get('prompt'):
            prompt = request.POST.get('prompt')
        elif request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
                prompt = body.get('prompt')
            except:
                pass
        
        # Obtener modelo si se proporciona (opcional, sino usa el del usuario)
        model = None
        if request.POST.get('model'):
            model = request.POST.get('model')
        elif request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
                model = body.get('model')
            except:
                pass
        
        # Si no se especificó modelo en el request, usar el preferido del usuario
        if not model:
            model = user_config.preferred_model
        
        # Procesar con Gemini usando las cookies del usuario
        extracted_text = asyncio.run(process_image_with_gemini(
            image_data=image_data,
            cookies=user_config.cookies_string,
            proxy=user_config.proxy,
            custom_prompt=prompt,
            model=model
        ))
        
        # Actualizar last_used
        user_config.last_used = timezone.now()
        user_config.save(update_fields=['last_used'])
        
        response_data = {
            'success': True,
            'text': extracted_text,
            'message': 'Texto extraído exitosamente',
            'user': user_config.user.username,
            'telegram_user': user_config.telegram_user,
            'model_used': model
        }
        
        # Agregar info de formato si fue convertido
        if original_format:
            response_data['image_format'] = original_format
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la imagen: {str(e)}'
        }, status=500)


async def process_image_with_gemini(image_data: bytes, cookies: str, proxy: str = None, custom_prompt: str = None, model: str = None):
    """
    Procesa una imagen con Google Gemini y extrae el texto.
    """
    client = GeminiClient(cookies=cookies, proxies=proxy, auto_close=False, auto_refresh=True)
    
    try:
        # Prompt por defecto
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = """Extrae TODO el texto de esta imagen de manera estructurada.
Si es un recibo o factura, incluye:
- Nombre del establecimiento
- Fecha y hora
- Número de factura/recibo
- Items con precios
- Subtotales, impuestos y totales
- Método de pago
Mantén el formato original. Responde SOLO con el texto extraído."""
        
        # Determinar el modelo a usar
        model_to_use = None
        if model and model != 'unspecified':
            model_map = {
                'gemini-2.5-flash': Model.G_2_5_FLASH,
                'gemini-2.5-pro': Model.G_2_5_PRO,
                'gemini-2.0-flash': 'gemini-2.0-flash',
                'gemini-2.0-flash-thinking': 'gemini-2.0-flash-thinking',
            }
            model_to_use = model_map.get(model.lower(), model)
        
        # Generar contenido con o sin modelo especificado
        if model_to_use:
            response = await client.generate_content(prompt, image=image_data, model=model_to_use)
        else:
            response = await client.generate_content(prompt, image=image_data)
        
        if response:
            return response.text
        else:
            raise Exception("No se recibió respuesta de Gemini")
            
    except Exception as e:
        raise Exception(f"Error Gemini: {str(e)}")
    
    finally:
        await client.close()


@require_http_methods(["GET"])
def api_status(request):
    """
    Endpoint para verificar el estado de la API de OCR.
    """
    # Contar usuarios configurados
    total_users = UserGeminiConfig.objects.count()
    active_users = UserGeminiConfig.objects.filter(is_active=True).count()
    
    # Si se proporciona telegram_user, verificar su configuración
    telegram_user = request.GET.get('telegram_user')
    user_status = None
    
    if telegram_user:
        telegram_user = telegram_user.lstrip('@').strip()
        try:
            user_config = UserGeminiConfig.objects.get(telegram_user=telegram_user)
            user_status = {
                'telegram_user': user_config.telegram_user,
                'username': user_config.user.username,
                'is_active': user_config.is_active,
                'is_configured': bool(user_config.gemini_psid and user_config.gemini_psidts),
                'preferred_model': user_config.preferred_model,
                'model_display': user_config.get_preferred_model_display(),
                'last_used': user_config.last_used.isoformat() if user_config.last_used else None
            }
        except UserGeminiConfig.DoesNotExist:
            user_status = {
                'telegram_user': telegram_user,
                'error': 'Usuario no encontrado'
            }
    
    # Verificar soporte HEIC
    supported_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']
    if HEIF_SUPPORTED:
        supported_formats.extend(['image/heic', 'image/heif'])
    
    return JsonResponse({
        'success': True,
        'service': 'OCR API with Google Gemini (Multi-User)',
        'version': '2.2.0',
        'authentication': 'telegram_user',
        'total_users_configured': total_users,
        'active_users': active_users,
        'user_status': user_status,
        'endpoints': {
            'extract_text': '/api/ocr/extract-text/',
            'status': '/api/ocr/status/'
        },
        'supported_formats': supported_formats,
        'heic_support': HEIF_SUPPORTED,
        'max_file_size': '10MB',
        'required_parameters': {
            'telegram_user': 'Username de Telegram del usuario (sin @)',
            'image': 'Archivo de imagen o image_base64'
        },
        'optional_parameters': {
            'prompt': 'Prompt personalizado (sobrescribe el prompt por defecto)',
            'model': 'Modelo de Gemini (sobrescribe el modelo preferido del usuario)'
        },
        'available_models': [
            {
                'value': 'gemini-2.5-flash',
                'name': 'Gemini 2.5 Flash',
                'description': 'Rápido y eficiente - Ideal para uso general',
                'icon': '⚡'
            },
            {
                'value': 'gemini-2.5-pro',
                'name': 'Gemini 2.5 Pro',
                'description': 'Más potente y preciso - Límite diario',
                'icon': '🧠'
            },
            {
                'value': 'gemini-2.0-flash',
                'name': 'Gemini 2.0 Flash',
                'description': 'Versión anterior',
                'icon': '📦'
            },
            {
                'value': 'gemini-2.0-flash-thinking',
                'name': 'Gemini 2.0 Flash Thinking',
                'description': 'Incluye proceso de razonamiento',
                'icon': '💭'
            },
            {
                'value': 'unspecified',
                'name': 'Sin especificar',
                'description': 'Usa modelo por defecto de Gemini',
                'icon': '❓'
            }
        ],
        'note': 'Si no se especifica "model" en el request, se usará el modelo preferido configurado por el usuario en el admin'
    })
