# OCR API con Google Gemini 🔍

API para extracción de texto desde imágenes usando Google Gemini.

## 📋 Configuración

### 1. Obtener Cookies de Gemini

Para usar esta API, necesitas obtener las cookies de tu sesión de Google Gemini:

1. Inicia sesión en https://gemini.google.com/
2. Abre las Herramientas de Desarrollador (F12)
3. Ve a la pestaña **Application** (Chrome) o **Storage** (Firefox)
4. Busca **Cookies** en el árbol izquierdo
5. Haz clic en `https://gemini.google.com`
6. Copia los valores de las siguientes cookies importantes:
   - `__Secure-1PSID`
   - `__Secure-1PSIDTS`
   - `__Secure-1PAPISID`

### 2. Configurar Variables de Entorno

Agrega las cookies al archivo `.env`:

```env
GEMINI_COOKIES="__Secure-1PSID=valor1; __Secure-1PSIDTS=valor2; __Secure-1PAPISID=valor3"
```

O el string completo de cookies:

```env
GEMINI_COOKIES="cookie_completa_aqui"
```

### 3. Reiniciar el Contenedor

```bash
docker-compose restart web
```

## 🚀 Uso de la API

### Endpoint de Estado

Verifica si la API está configurada:

```bash
curl http://localhost:8000/api/ocr/status/
```

Respuesta:
```json
{
  "success": true,
  "service": "OCR API with Google Gemini",
  "version": "1.0.0",
  "gemini_configured": true,
  "endpoints": {
    "extract_text": "/api/ocr/extract-text/",
    "status": "/api/ocr/status/"
  },
  "supported_formats": ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"],
  "max_file_size": "10MB"
}
```

### Endpoint de Extracción de Texto

**POST** `/api/ocr/extract-text/`

#### Opción 1: Enviar Imagen como Archivo (multipart/form-data)

```bash
curl -X POST http://localhost:8000/api/ocr/extract-text/ \
     -F "image=@/ruta/a/tu/imagen.jpg"
```

Con prompt personalizado:

```bash
curl -X POST http://localhost:8000/api/ocr/extract-text/ \
     -F "image=@/ruta/a/tu/recibo.jpg" \
     -F "prompt=Extrae solo los precios y productos de este recibo"
```

#### Opción 2: Enviar Imagen en Base64 (application/json)

```bash
curl -X POST http://localhost:8000/api/ocr/extract-text/ \
     -H "Content-Type: application/json" \
     -d '{
       "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
       "prompt": "Extrae el texto de esta imagen"
     }'
```

O sin el prefijo `data:image/jpeg;base64,`:

```bash
curl -X POST http://localhost:8000/api/ocr/extract-text/ \
     -H "Content-Type: application/json" \
     -d '{
       "image_base64": "/9j/4AAQSkZJRg..."
     }'
```

### Respuesta Exitosa

```json
{
  "success": true,
  "text": "SUPERMERCADO XYZ\nCalle Principal #123\nFecha: 01/11/2024\n...",
  "message": "Texto extraído exitosamente"
}
```

### Respuesta de Error

```json
{
  "success": false,
  "error": "Descripción del error"
}
```

## 📝 Ejemplos con Python

### Usando requests

```python
import requests

# Con archivo
with open('recibo.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/ocr/extract-text/',
        files={'image': f}
    )
    
print(response.json()['text'])
```

### Con base64

```python
import requests
import base64

# Leer y codificar imagen
with open('recibo.jpg', 'rb') as f:
    image_base64 = base64.b64encode(f.read()).decode()

# Enviar
response = requests.post(
    'http://localhost:8000/api/ocr/extract-text/',
    json={
        'image_base64': image_base64,
        'prompt': 'Extrae solo la información de productos y precios'
    }
)

print(response.json()['text'])
```

## 🎯 Casos de Uso

### 1. Extracción de Recibos de Compra

El prompt por defecto está optimizado para recibos y facturas:

```bash
curl -X POST http://localhost:8000/api/ocr/extract-text/ \
     -F "image=@recibo.jpg"
```

### 2. Extracción de Texto General

Con prompt personalizado:

```bash
curl -X POST http://localhost:8000/api/ocr/extract-text/ \
     -F "image=@documento.jpg" \
     -F "prompt=Extrae todo el texto visible en esta imagen"
```

### 3. Extracción Estructurada

```bash
curl -X POST http://localhost:8000/api/ocr/extract-text/ \
     -F "image=@factura.jpg" \
     -F "prompt=Extrae la información en formato JSON con los campos: establecimiento, fecha, items (array con nombre y precio), total"
```

## ⚙️ Configuración Avanzada

### Usar Proxy (Opcional)

Si necesitas usar un proxy para conectarte a Gemini:

```env
GEMINI_PROXY="http://proxy.ejemplo.com:8080"
```

O con autenticación:

```env
GEMINI_PROXY="http://usuario:password@proxy.ejemplo.com:8080"
```

## 🔒 Seguridad

- Las cookies de Gemini son sensibles, **nunca las compartas públicamente**
- Mantén el archivo `.env` fuera del control de versiones (ya está en `.gitignore`)
- Las cookies pueden expirar, si recibes errores de autenticación, obtén nuevas cookies
- Limita el acceso a este endpoint en producción

## 📊 Limitaciones

- **Tamaño máximo de imagen:** 10MB
- **Formatos soportados:** JPEG, JPG, PNG, WebP, GIF
- **Rate limiting:** Depende de los límites de Google Gemini
- Las cookies de sesión pueden expirar y necesitar renovación

## 🐛 Troubleshooting

### Error: "Gemini API no configurada"

```json
{"success": false, "error": "Gemini API no configurada"}
```

**Solución:** Configura `GEMINI_COOKIES` en el archivo `.env`

### Error: "Error al comunicarse con Gemini"

Posibles causas:
1. Cookies expiradas → Obtén nuevas cookies
2. Problemas de red → Verifica conectividad
3. Límite de uso alcanzado → Espera unos minutos

### Error: "Tipo de archivo no soportado"

**Solución:** Usa solo imágenes en formato JPEG, PNG, WebP o GIF

### Error: "Archivo muy grande"

**Solución:** Reduce el tamaño de la imagen a menos de 10MB

## 📚 Documentación Adicional

- [Gemini WebAPI Library](https://pypi.org/project/gemini-webapi/)
- [Google Gemini](https://gemini.google.com/)
- [Django Documentation](https://docs.djangoproject.com/)

## 🤝 Integración con Financial Helper

Esta API está diseñada para integrarse con el sistema Financial Helper, permitiendo:

1. **Escanear recibos de compra** y extraer automáticamente la información
2. **Pre-llenar formularios** de compras con los datos extraídos
3. **Reducir errores** de entrada manual de datos
4. **Acelerar el proceso** de registro de compras

### Flujo Sugerido

1. Usuario captura foto del recibo
2. Se envía al endpoint `/api/ocr/extract-text/`
3. Gemini extrae el texto estructurado
4. Se parsea el texto y se pre-llena el formulario de `Purchase`
5. Usuario revisa y confirma los datos
6. Se guarda la compra en la base de datos

---

**Nota:** Esta implementación usa la librería `gemini-webapi` que es un wrapper no oficial de Google Gemini. Para uso en producción, considera usar la API oficial de Google Gemini cuando esté disponible.
