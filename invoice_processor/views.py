"""
Vistas para el procesamiento de facturas desde n8n.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User

from .services import InvoiceProcessorService
from users.models import UserProfile

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def process_invoice_from_n8n(request):
    """
    Endpoint principal para procesar facturas desde n8n.

    Acepta:
        - Archivo (audio o imagen) en request.FILES['file']
        - Tipo de archivo en request.POST['file_type'] ('audio' o 'image')
        - MIME type en request.POST['mime_type'] (opcional)
        - Usuario de Telegram en request.POST['telegram_user'] (requerido)

    Retorna:
        JSON con:
        - purchase_id: UUID del Purchase creado
        - summary: Texto formateado para enviar a Telegram
    """
    try:
        # Log de debugging: ver qué llega en el request
        logger.info("=== INICIO REQUEST DEBUG ===")
        logger.info(f"request.FILES.keys(): {list(request.FILES.keys())}")
        logger.info(f"request.POST.keys(): {list(request.POST.keys())}")
        logger.info(f"request.POST items: {dict(request.POST.items())}")

        # Validar que se envió un archivo
        if 'file' not in request.FILES:
            logger.error(f"No se encontró 'file' en FILES. FILES disponibles: {list(request.FILES.keys())}")
            return JsonResponse({
                'error': 'No se envió ningún archivo. Debe incluir "file" en el request.'
            }, status=400)

        # Obtener archivo
        uploaded_file = request.FILES['file']
        logger.info(f"Archivo recibido - Name: {uploaded_file.name}, Size: {uploaded_file.size}, Content-Type: {uploaded_file.content_type}")
        file_binary = uploaded_file.read()

        # Obtener tipo de archivo
        file_type = request.POST.get('file_type', '').lower()
        logger.info(f"file_type recibido: '{file_type}' (type: {type(file_type)})")

        # Si file_type no es válido, intentar detectar automáticamente
        if file_type not in ['audio', 'image']:
            logger.warning(f"file_type inválido: '{file_type}'. Intentando detectar automáticamente...")

            # Detectar por MIME type
            mime = uploaded_file.content_type.lower()
            extension = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''

            logger.info(f"Auto-detección - MIME: {mime}, Extension: {extension}")

            if mime.startswith('image/') or extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                file_type = 'image'
                logger.info(f"Auto-detectado como IMAGE")
            elif mime.startswith('audio/') or extension in ['ogg', 'mp3', 'wav', 'oga', 'opus', 'm4a']:
                file_type = 'audio'
                logger.info(f"Auto-detectado como AUDIO")
            else:
                logger.error(f"No se pudo auto-detectar el tipo. MIME: {mime}, Extension: {extension}")
                return JsonResponse({
                    'error': f'file_type debe ser "audio" o "image". Recibido: "{file_type}". MIME: "{mime}", Extension: "{extension}"'
                }, status=400)

        # Obtener MIME type
        mime_type = request.POST.get('mime_type') or uploaded_file.content_type

        # Determinar MIME type por defecto según tipo
        if not mime_type:
            if file_type == 'audio':
                mime_type = 'audio/ogg'  # Telegram usa OGG para notas de voz
            else:
                mime_type = 'image/jpeg'

        # Obtener telegram_user (requerido)
        telegram_user = request.POST.get('telegram_user', '').strip()
        if not telegram_user:
            logger.error("telegram_user no fue enviado")
            return JsonResponse({
                'error': 'Se requiere el campo "telegram_user" con el username de Telegram'
            }, status=400)

        # Limpiar @ si viene incluido
        telegram_user = telegram_user.lstrip('@')
        logger.info(f"Buscando usuario con telegram_user: {telegram_user}")

        # Buscar o crear User por telegram_user
        try:
            # Intentar buscar por UserProfile.telegram_user
            user_profile = UserProfile.objects.select_related('user').filter(telegram_user=telegram_user).first()

            if user_profile:
                user = user_profile.user
                logger.info(f"✓ Usuario ENCONTRADO: {user.username} (ID: {user.id})")
            else:
                # Crear nuevo User y UserProfile
                logger.info(f"Usuario no existe. Creando nuevo User para telegram_user: {telegram_user}")

                # Username será el telegram_user (debe ser único)
                username = telegram_user
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{telegram_user}_{counter}"
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@telegram.user",  # Email placeholder
                    password=User.objects.make_random_password()  # Password aleatorio (no se usará)
                )

                # Crear UserProfile asociado
                UserProfile.objects.create(
                    user=user,
                    telegram_user=telegram_user
                )

                logger.info(f"✓ Usuario CREADO: {user.username} (ID: {user.id}) con telegram_user: {telegram_user}")

        except Exception as e:
            logger.error(f"Error al buscar/crear usuario: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': f'Error al procesar usuario: {str(e)}'
            }, status=500)

        logger.info(f"Procesando {file_type} ({mime_type}, {len(file_binary)} bytes)")

        # Procesar factura
        service = InvoiceProcessorService()
        result = service.process_invoice(
            file_type=file_type,
            file_binary=file_binary,
            mime_type=mime_type,
            user=user
        )

        return JsonResponse({
            'success': True,
            'purchase_id': result['purchase_id'],
            'summary': result['summary']
        }, status=200)

    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}")
        return JsonResponse({
            'error': f'Error de validación: {str(e)}'
        }, status=400)

    except Exception as e:
        logger.error(f"Error interno al procesar factura: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)
