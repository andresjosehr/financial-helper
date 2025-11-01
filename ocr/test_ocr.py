#!/usr/bin/env python3
"""
Script de prueba para el API de OCR con Gemini.
Ejecutar: python ocr/test_ocr.py
"""
import base64
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests no está instalado")
    print("Instala con: pip install requests")
    sys.exit(1)


def test_status():
    """Prueba el endpoint de estado"""
    print("🔍 Probando endpoint de estado...")
    response = requests.get('http://localhost:8000/api/ocr/status/')
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Endpoint de estado funcionando")
        print(f"   Gemini configurado: {data.get('gemini_configured')}")
        print(f"   Versión: {data.get('version')}")
        return data.get('gemini_configured', False)
    else:
        print(f"❌ Error: {response.status_code}")
        return False


def test_extract_with_file(image_path):
    """Prueba extracción con archivo"""
    print(f"\n📸 Probando extracción con archivo: {image_path}")
    
    if not Path(image_path).exists():
        print(f"❌ Archivo no encontrado: {image_path}")
        return False
    
    with open(image_path, 'rb') as f:
        files = {'image': f}
        response = requests.post(
            'http://localhost:8000/api/ocr/extract-text/',
            files=files
        )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Texto extraído exitosamente")
            print(f"\n--- TEXTO EXTRAÍDO ---")
            print(data.get('text', '')[:500])  # Primeros 500 caracteres
            if len(data.get('text', '')) > 500:
                print("...")
            print("--- FIN ---\n")
            return True
        else:
            print(f"❌ Error: {data.get('error')}")
            return False
    else:
        print(f"❌ Error HTTP: {response.status_code}")
        try:
            print(f"   {response.json()}")
        except:
            print(f"   {response.text}")
        return False


def test_extract_with_base64(image_path):
    """Prueba extracción con base64"""
    print(f"\n📸 Probando extracción con base64: {image_path}")
    
    if not Path(image_path).exists():
        print(f"❌ Archivo no encontrado: {image_path}")
        return False
    
    with open(image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    response = requests.post(
        'http://localhost:8000/api/ocr/extract-text/',
        json={'image_base64': image_base64},
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Texto extraído exitosamente con base64")
            return True
        else:
            print(f"❌ Error: {data.get('error')}")
            return False
    else:
        print(f"❌ Error HTTP: {response.status_code}")
        return False


def main():
    print("=" * 60)
    print("  PRUEBAS DE OCR API CON GOOGLE GEMINI")
    print("=" * 60)
    
    # Test 1: Status
    gemini_configured = test_status()
    
    if not gemini_configured:
        print("\n⚠️  GEMINI NO ESTÁ CONFIGURADO")
        print("   Para configurarlo:")
        print("   1. Obtén las cookies de https://gemini.google.com/")
        print("   2. Agrégalas al archivo .env:")
        print('      GEMINI_COOKIES="__Secure-1PSID=xxx; ..."')
        print("   3. Reinicia el contenedor: docker-compose restart web")
        return
    
    # Test 2: Extracción con archivo
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        test_extract_with_file(image_path)
        test_extract_with_base64(image_path)
    else:
        print("\n💡 Para probar la extracción de texto:")
        print("   python ocr/test_ocr.py /ruta/a/imagen.jpg")
    
    print("\n" + "=" * 60)
    print("  PRUEBAS COMPLETADAS")
    print("=" * 60)


if __name__ == '__main__':
    main()
