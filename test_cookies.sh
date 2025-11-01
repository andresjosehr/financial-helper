#!/bin/bash
# Script para verificar que las cookies funcionan

echo "🧪 VERIFICANDO COOKIES DE GEMINI"
echo "================================="
echo ""

cd /var/www/financial-helper

# Test 1: Verificar cookies en BD
echo "1️⃣ Verificando cookies en base de datos..."
docker compose exec -T web python manage.py shell << 'PYEOF'
from ocr.models import UserGeminiConfig

config = UserGeminiConfig.objects.get(telegram_user='andresjosehr')
print(f"   Usuario: {config.user.username}")
print(f"   Telegram: @{config.telegram_user}")
print(f"   PSID length: {len(config.gemini_psid)}")
print(f"   PSIDTS length: {len(config.gemini_psidts)}")
print(f"   Activo: {config.is_active}")
PYEOF

echo ""
echo "2️⃣ Probando cliente Gemini con texto simple..."
docker compose exec -T web bash << 'BASHEOF'
export DJANGO_SETTINGS_MODULE=config.settings
python << 'PYEOF'
import django
import asyncio
django.setup()

from gemini_webapi import GeminiClient
from ocr.models import UserGeminiConfig

config = UserGeminiConfig.objects.get(telegram_user='andresjosehr')

async def test():
    client = GeminiClient(cookies=config.cookies_string, auto_close=False, auto_refresh=True)
    try:
        response = await client.generate_content("Responde solo: OK")
        print(f"   ✅ COOKIES FUNCIONANDO!")
        print(f"   Respuesta: {response.text[:50]}")
        return True
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)[:100]}")
        return False
    finally:
        await client.close()

result = asyncio.run(test())
exit(0 if result else 1)
PYEOF
BASHEOF

if [ $? -eq 0 ]; then
    echo ""
    echo "3️⃣ Probando con imagen de prueba..."
    
    # Crear imagen de prueba simple
    docker compose exec -T web python << 'PYEOF'
from PIL import Image, ImageDraw, ImageFont
import io

# Crear imagen simple con texto
img = Image.new('RGB', (400, 200), color='white')
draw = ImageDraw.Draw(img)
draw.text((50, 80), "RECIBO TEST", fill='black')
draw.text((50, 120), "TOTAL: $100.00", fill='black')

# Guardar
img.save('/tmp/test_receipt.jpg', 'JPEG')
print("   Imagen de prueba creada: /tmp/test_receipt.jpg")
PYEOF

    # Test con imagen
    docker compose exec -T web bash << 'BASHEOF'
export DJANGO_SETTINGS_MODULE=config.settings
python << 'PYEOF'
import django
import asyncio
django.setup()

from gemini_webapi import GeminiClient
from ocr.models import UserGeminiConfig

config = UserGeminiConfig.objects.get(telegram_user='andresjosehr')

async def test_image():
    with open('/tmp/test_receipt.jpg', 'rb') as f:
        image_data = f.read()
    
    client = GeminiClient(cookies=config.cookies_string, auto_close=False, auto_refresh=True)
    try:
        response = await client.generate_content(
            "Extrae el texto de esta imagen", 
            image=image_data
        )
        print(f"   ✅ OCR FUNCIONANDO!")
        print(f"   Texto extraído: {response.text[:100]}")
        return True
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)[:100]}")
        return False
    finally:
        await client.close()

result = asyncio.run(test_image())
exit(0 if result else 1)
PYEOF
BASHEOF

    if [ $? -eq 0 ]; then
        echo ""
        echo "=" * 50
        echo "✅ ¡TODO FUNCIONA CORRECTAMENTE!"
        echo ""
        echo "Ahora puedes usar el endpoint desde n8n:"
        echo "  URL: https://financial-helper.andresjosehr.com/api/ocr/extract-text/"
        echo "  Método: POST"
        echo "  Parámetros:"
        echo "    - telegram_user: andresjosehr"
        echo "    - image: [tu imagen]"
        echo ""
    else
        echo ""
        echo "⚠️  Las cookies funcionan para texto pero fallan con imágenes."
        echo "Intenta actualizarlas nuevamente."
    fi
else
    echo ""
    echo "=" * 50
    echo "❌ LAS COOKIES SIGUEN SIN FUNCIONAR"
    echo ""
    echo "Por favor:"
    echo "1. Ve a https://gemini.google.com/"
    echo "2. CIERRA SESIÓN completamente"
    echo "3. Inicia sesión nuevamente"
    echo "4. Haz una pregunta para activar la sesión"
    echo "5. Abre DevTools (F12)"
    echo "6. Copia las cookies FRESCAS"
    echo "7. Actualiza en el admin"
    echo "8. Corre este script de nuevo"
    echo ""
fi
