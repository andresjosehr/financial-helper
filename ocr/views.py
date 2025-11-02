import asyncio
import base64
import json
import logging
from io import BytesIO
from django.utils import timezone

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from PIL import Image

# Configurar logging
logger = logging.getLogger(__name__)

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
    Endpoint para extraer texto de una imagen usando Google Gemini o generar texto sin imagen.
    
    Requiere:
    - telegram_user: Username de Telegram del usuario
    
    Opcional:
    - image: Archivo de imagen (si quieres OCR)
    - image_base64: Imagen en base64 (alternativa a 'image')
    - prompt: Prompt personalizado (si no se envía, usa el por defecto)
    - model: Modelo de Gemini a usar (si no se envía, usa el preferido del usuario)
    
    Nota: Si no envías imagen, puedes usar esto para chat de texto con Gemini.
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
        
        # Opción 2: Imagen enviada como base64 en JSON (OPCIONAL)
        elif request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
                image_base64 = body.get('image_base64', '')
                
                if image_base64:
                    # Remover el prefijo data:image si existe
                    if ',' in image_base64:
                        image_base64 = image_base64.split(',')[1]
                    
                    image_data = base64.b64decode(image_base64)
                
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Error al decodificar: {str(e)}'}, status=400)
        
        # Validar imagen solo si se proporcionó
        if image_data:
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
            psid=user_config.gemini_psid,
            psidts=user_config.gemini_psidts,
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
            'message': 'Texto generado exitosamente' if not image_data else 'Texto extraído exitosamente',
            'user': user_config.user.username,
            'telegram_user': user_config.telegram_user,
            'model_used': model,
            'has_image': bool(image_data)
        }
        
        # Agregar info de formato si fue convertido
        if original_format:
            response_data['image_format'] = original_format
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar: {str(e)}'
        }, status=500)


def extract_text_from_gemini_response(response_text: str) -> str:
    """
    Parsea manualmente la respuesta RAW de Gemini para extraer el texto.
    La librería gemini-webapi falla al parsear, así que lo hacemos manual.
    """
    import re
    
    # Buscar el patrón ["rc_XXXXX",["TEXTO AQUI"
    # El texto puede contener \n, \", etc. Usar DOTALL para capturar todo
    pattern = r'\["rc_[a-f0-9]+",\["(.+?)"\]\]'
    
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        # Tomar el texto más largo (suele ser la respuesta principal)
        text = max(matches, key=len)
        # Decodificar secuencias de escape
        text = text.replace('\\n', '\n')
        text = text.replace('\\t', '\t')
        text = text.replace('\\"', '"')
        text = text.replace('\\\\', '\\')
        text = text.replace('\\u003e', '>')
        text = text.replace('\\u003d', '=')
        text = text.replace('\\u003c', '<')
        return text
    
    return None


async def process_image_with_gemini(image_data: bytes = None, psid: str = None, psidts: str = None, proxy: str = None, custom_prompt: str = None, model: str = None):
    """
    Procesa una imagen con Google Gemini y extrae el texto (o genera texto sin imagen).
    
    Args:
        image_data: Datos binarios de la imagen (OPCIONAL - si no se pasa, es chat sin imagen)
        psid: Cookie __Secure-1PSID
        psidts: Cookie __Secure-1PSIDTS
        proxy: Proxy opcional
        custom_prompt: Prompt personalizado opcional
        model: Modelo de Gemini a usar
    """
    import tempfile
    import os
    import httpx
    
    # Inicializar cliente con cookies individuales según documentación oficial
    client = GeminiClient(psid, psidts, proxy=proxy)
    await client.init(timeout=300, auto_close=False, auto_refresh=True)
    
    # Interceptar el httpx client para capturar la respuesta RAW
    original_post = client.client.post
    raw_response_text = None
    
    async def intercept_post(*args, **kwargs):
        nonlocal raw_response_text
        response = await original_post(*args, **kwargs)
        raw_response_text = response.text
        return response
    
    client.client.post = intercept_post
    
    temp_file = None
    try:
        # Prompt por defecto o personalizado
        if custom_prompt:
            prompt = custom_prompt
        else:
            if image_data:
                # Prompt por defecto para OCR
                prompt = """Extrae TODO el texto de esta imagen de manera estructurada.
Si es un recibo o factura, incluye:
- Nombre del establecimiento
- Fecha y hora
- Número de factura/recibo
- Items con precios
- Subtotales, impuestos y totales
- Método de pago
Mantén el formato original. Responde SOLO con el texto extraído."""
            else:
                # Si no hay imagen y no hay prompt, error
                raise Exception("Debes proporcionar una imagen o un prompt de texto")
        
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
        
        print(f"[OCR] Iniciando request a Gemini con modelo: {model_to_use or 'default'}", flush=True)
        print(f"[OCR] Tiene imagen: {bool(image_data)}", flush=True)
        
        # Generar contenido con o sin imagen
        try:
            if image_data:
                # Guardar imagen temporalmente (gemini-webapi requiere rutas de archivo)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                temp_file.write(image_data)
                temp_file.close()
                
                print(f"[OCR] Imagen temporal guardada en: {temp_file.name}", flush=True)
                
                if model_to_use:
                    response = await client.generate_content(prompt, files=[temp_file.name], model=model_to_use)
                else:
                    response = await client.generate_content(prompt, files=[temp_file.name])
            else:
                # Sin imagen, solo texto
                if model_to_use:
                    response = await client.generate_content(prompt, model=model_to_use)
                else:
                    response = await client.generate_content(prompt)
        except Exception as e:
            print(f"[OCR ERROR] Excepción al llamar generate_content: {e}", flush=True)
            print(f"[OCR ERROR] Tipo de excepción: {type(e)}", flush=True)
            
            # Si tenemos la respuesta RAW, intentar parsearla manualmente
            if raw_response_text and 'Failed to parse response body' in str(e):
                print(f"[OCR] Intentando parseo manual de respuesta RAW...", flush=True)
                print(f"[OCR] Longitud de respuesta RAW: {len(raw_response_text)}", flush=True)
                
                extracted_text = extract_text_from_gemini_response(raw_response_text)
                if extracted_text:
                    print(f"[OCR] ✓ SUCCESS - Texto extraído manualmente (longitud: {len(extracted_text)})", flush=True)
                    return extracted_text
                else:
                    print(f"[OCR ERROR] No se pudo extraer texto del parseo manual", flush=True)
                    print(f"[OCR] Primeros 1000 chars de respuesta:", flush=True)
                    print(raw_response_text[:1000], flush=True)
            
            import traceback
            traceback.print_exc()
            raise Exception(f"Error al llamar a Gemini: {str(e)}")
        
        print("=" * 80, flush=True)
        print("[OCR] RESPUESTA COMPLETA DE GEMINI", flush=True)
        print(f"[OCR] Tipo de respuesta: {type(response)}", flush=True)
        print(f"[OCR] Response es None: {response is None}", flush=True)
        print(f"[OCR] Response bool: {bool(response)}", flush=True)
        
        if response is None:
            print("[OCR ERROR] Response es None!", flush=True)
            raise Exception("Gemini retornó None - posible error de parseo en la librería")
        
        print(f"[OCR] Response tiene atributo 'text': {hasattr(response, 'text')}", flush=True)
        print(f"[OCR] Response tiene atributo 'rcid': {hasattr(response, 'rcid')}", flush=True)
        print(f"[OCR] Response tiene atributo 'candidates': {hasattr(response, 'candidates')}", flush=True)
        print(f"[OCR] Response tiene atributo 'content': {hasattr(response, 'content')}", flush=True)
        print(f"[OCR] Dir completo de respuesta:", flush=True)
        print(dir(response), flush=True)
        
        # Intentar acceder a text y ver qué pasa
        try:
            text_value = response.text
            print(f"[OCR] response.text = {text_value}", flush=True)
            print(f"[OCR] response.text es None: {text_value is None}", flush=True)
            print(f"[OCR] response.text bool: {bool(text_value)}", flush=True)
            if text_value:
                print(f"[OCR] ✓ SUCCESS - Texto tiene longitud: {len(str(text_value))}", flush=True)
                print("=" * 80, flush=True)
                return text_value
            else:
                print(f"[OCR ERROR] response.text existe pero está vacío o es None", flush=True)
        except AttributeError as e:
            print(f"[OCR ERROR] No existe response.text: {e}", flush=True)
        except Exception as e:
            print(f"[OCR ERROR] Error al acceder response.text: {e}", flush=True)
        
        # Intentar con rcid/candidates
        try:
            if hasattr(response, 'rcid'):
                print(f"[OCR] ✓ Objeto tiene rcid: {response.rcid}", flush=True)
                if hasattr(response, 'candidates') and response.candidates:
                    print(f"[OCR] Candidates encontrados: {len(response.candidates)}", flush=True)
                    first_candidate = response.candidates[0]
                    print(f"[OCR] Candidate[0] type: {type(first_candidate)}", flush=True)
                    print(f"[OCR] Candidate[0] dir: {dir(first_candidate)}", flush=True)
                    if hasattr(first_candidate, 'text'):
                        print(f"[OCR] ✓ Usando candidate[0].text", flush=True)
                        print("=" * 80, flush=True)
                        return first_candidate.text
        except Exception as e:
            print(f"[OCR ERROR] Error con rcid/candidates: {e}", flush=True)
        
        # Intentar convertir a string y buscar patrón
        print(f"[OCR] Último intento: convertir a string", flush=True)
        response_str = str(response)
        print(f"[OCR] Response como string (primeros 1000 chars):", flush=True)
        print(response_str[:1000], flush=True)
        print("=" * 80, flush=True)
        
        raise Exception(f"No se pudo extraer texto. Response type: {type(response)}, tiene text: {hasattr(response, 'text')}")
            
    except Exception as e:
        raise Exception(f"Error Gemini: {str(e)}")
    
    finally:
        # Limpiar archivo temporal
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except:
                pass
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
