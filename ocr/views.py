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

from gemini_webapi import GeminiClient
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
        
        # Opción 1: Imagen enviada como archivo
        if request.FILES.get('image'):
            image_file = request.FILES['image']
            
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']
            if image_file.content_type not in allowed_types:
                return JsonResponse({
                    'success': False,
                    'error': f'Tipo no soportado: {image_file.content_type}. Tipos permitidos: {", ".join(allowed_types)}'
                }, status=400)
            
            # Validar tamaño (máximo 10MB)
            max_size = 10 * 1024 * 1024
            if image_file.size > max_size:
                return JsonResponse({
                    'success': False,
                    'error': f'Archivo muy grande (max 10MB). Tamaño: {image_file.size / 1024 / 1024:.2f}MB'
                }, status=400)
            
            image_data = image_file.read()
        
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
        
        # Procesar con Gemini usando las cookies del usuario
        extracted_text = asyncio.run(process_image_with_gemini(
            image_data=image_data,
            cookies=user_config.cookies_string,
            proxy=user_config.proxy,
            custom_prompt=prompt
        ))
        
        # Actualizar last_used
        user_config.last_used = timezone.now()
        user_config.save(update_fields=['last_used'])
        
        return JsonResponse({
            'success': True,
            'text': extracted_text,
            'message': 'Texto extraído exitosamente',
            'user': user_config.user.username,
            'telegram_user': user_config.telegram_user
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la imagen: {str(e)}'
        }, status=500)


async def process_image_with_gemini(image_data: bytes, cookies: str, proxy: str = None, custom_prompt: str = None):
    """
    Procesa una imagen con Google Gemini y extrae el texto.
    """
    client = GeminiClient(cookies=cookies, proxies=proxy, auto_close=False, auto_refresh=True)
    
    try:
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
                'last_used': user_config.last_used.isoformat() if user_config.last_used else None
            }
        except UserGeminiConfig.DoesNotExist:
            user_status = {
                'telegram_user': telegram_user,
                'error': 'Usuario no encontrado'
            }
    
    return JsonResponse({
        'success': True,
        'service': 'OCR API with Google Gemini (Multi-User)',
        'version': '2.0.0',
        'authentication': 'telegram_user',
        'total_users_configured': total_users,
        'active_users': active_users,
        'user_status': user_status,
        'endpoints': {
            'extract_text': '/api/ocr/extract-text/',
            'status': '/api/ocr/status/'
        },
        'supported_formats': ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif'],
        'max_file_size': '10MB',
        'required_parameters': {
            'telegram_user': 'Username de Telegram del usuario (sin @)',
            'image': 'Archivo de imagen o image_base64',
            'prompt': 'Prompt personalizado (opcional)'
        }
    })
