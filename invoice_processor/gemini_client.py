"""
Cliente para interactuar con Google Gemini API.
"""
import json
import logging
import re
from typing import Dict, Any, Optional
from django.conf import settings
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiClient:
    """Cliente para procesar datos con Google Gemini API."""

    def __init__(self):
        """Inicializa el cliente de Gemini."""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada en el entorno")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    def transcribe_audio(self, audio_binary: bytes, mime_type: str = 'audio/ogg') -> str:
        """
        Transcribe un audio usando Gemini.

        Args:
            audio_binary: Bytes del archivo de audio
            mime_type: Tipo MIME del audio

        Returns:
            Texto transcrito
        """
        try:
            logger.info(f"Transcribiendo audio ({len(audio_binary)} bytes)")

            # Crear el objeto de audio para Gemini
            audio_part = {
                'mime_type': mime_type,
                'data': audio_binary
            }

            response = self.model.generate_content([
                audio_part,
                "Transcribe el audio a texto. Responde únicamente con el texto transcrito, sin agregar explicaciones adicionales."
            ])

            transcription = response.text.strip()
            logger.info(f"Audio transcrito exitosamente ({len(transcription)} caracteres)")

            return transcription

        except Exception as e:
            logger.error(f"Error al transcribir audio: {str(e)}")
            raise

    def analyze_image(self, image_binary: bytes, mime_type: str = 'image/png') -> Dict[str, Any]:
        """
        Analiza una imagen de factura con Gemini.

        Args:
            image_binary: Bytes de la imagen
            mime_type: Tipo MIME de la imagen

        Returns:
            Diccionario con datos extraídos
        """
        try:
            logger.info(f"Analizando imagen ({len(image_binary)} bytes)")

            # Crear el objeto de imagen para Gemini
            image_part = {
                'mime_type': mime_type,
                'data': image_binary
            }

            prompt = """Analiza la siguiente imagen de una factura y extrae la información en formato JSON.

ESTRUCTURA JSON REQUERIDA:
{
  "purchase": {
    "purchase_date": "YYYY-MM-DD",
    "purchase_time": "HH:MM" o null,
    "subtotal_ves": número,
    "total_ves": número,
    "tax_ves": número,
    "tax_type": "IVA" o null,
    "tax_percentage": 16.00 o null,
    "notes": string o null,
    "establishment": {
      "name": "string",
      "legal_name": string o null,
      "tax_id": "J-XXXXXXX" o null,
      "address": string o null,
      "city": string o null,
      "state": string o null,
      "postal_code": string o null,
      "country": null (siempre null),
      "phone": string o null,
      "email": string o null,
      "website": string o null
    },
    "purchase_items": [
      {
        "product_code": string o null,
        "description": "string",
        "quantity": número,
        "unit_type": string o null,
        "total_ves": número,
        "notes": null
      }
    ]
  }
}

INSTRUCCIONES CRÍTICAS:
1. purchase_items DEBE ser un ARRAY de objetos
2. Cada producto es un objeto SEPARADO con llaves {}
3. Convierte montos correctamente: "Bs8.935,57" → 8935.57
4. Fechas en formato YYYY-MM-DD
5. SIEMPRE deja bcv_rate, binance_rate, total_usd_bcv, total_usd_binance en null
6. El impuesto SIEMPRE es 16%

REGLAS PARA LEER LA FACTURA (MUY IMPORTANTE):

**PASO 1: Analiza primero la estructura de la tabla de productos**
- Identifica qué columnas tiene la factura mirando los encabezados o el patrón de datos
- Formatos comunes:
  * CÓDIGO | DESCRIPCIÓN | TOTAL (sin cantidad explícita)
  * CÓDIGO | DESCRIPCIÓN | CANT | PRECIO | TOTAL
  * DESCRIPCIÓN | CANTIDAD | PRECIO UNIT | TOTAL
  * Otros formatos similares

**PASO 2: Identifica la columna de CANTIDAD (si existe)**
- La columna de CANTIDAD contiene números como: 1, 2, 3, 0.5, 1.250, 2.5, etc.
- Está usualmente entre la descripción y el precio/total
- NO es el código del producto (suelen ser números largos: 111197799, 111262157, etc.)
- NO es el número de línea/ítem (1, 2, 3, 4... en secuencia perfecta)
- NO son letras o códigos como "(G)", "(E)", "G", "E" (significan Gravable/Exento)
- Si hay varias columnas de números, la cantidad es la que varía por producto y representa la medida comprada

**PASO 3: Extrae la cantidad correctamente**
- Si identificaste una columna de cantidad → úsala
- Si NO hay columna de cantidad pero la descripción incluye multiplicadores como "2x", "3x", etc. → extrae la cantidad
  * Ejemplo: "Kit Viajero 2x" → quantity = 2.0, description = "Kit Viajero"
  * Ejemplo: "Toallas Desmaquilladoras 2x" → quantity = 2.0, description = "Toallas Desmaquilladoras"
- Si NO hay columna de cantidad y NO hay multiplicador en descripción → usa quantity = 1.0
- La cantidad puede tener decimales (0.5 kg, 1.250 kg, 2.5 litros, etc.)
- Para productos por peso/volumen, la cantidad puede ser fraccionaria

**EJEMPLOS DE ANÁLISIS:**

Ejemplo 1 - Farmatodo (SIN columna cantidad):
```
111197799 Gel Fijador Rolda Blanco 25 (G)    Bs 541,38
```
Estructura: CÓDIGO | DESCRIPCIÓN (G/E) | TOTAL
→ quantity = 1.0 (no hay columna de cantidad)

Ejemplo 2 - Supermercado (CON columna cantidad):
```
12345  Tomate  0.500  Bs 8.50/kg  Bs 4.25
```
Estructura: CÓDIGO | DESCRIPCIÓN | CANTIDAD | PRECIO_UNIT | TOTAL
→ quantity = 0.5 (hay columna explícita)

Ejemplo 3 - Con cantidad de unidades:
```
567  Pan Campesino  3  Bs 2.00  Bs 6.00
```
Estructura: CÓDIGO | DESCRIPCIÓN | CANTIDAD | PRECIO_UNIT | TOTAL
→ quantity = 3.0 (hay columna explícita)

Ejemplo 4 - Multiplicador en descripción (SIN columna cantidad):
```
111262157 Kit Viajero Iceberg 2x (G)    Bs 1.000,40
```
Estructura: CÓDIGO | DESCRIPCIÓN (G/E) | TOTAL
→ quantity = 2.0 (extraído del "2x" en descripción)
→ description = "Kit Viajero Iceberg" (sin el "2x")

REGLAS PARA unit_type:
- unit_type DEBE ser la palabra completa en español, NO abreviaturas
- Para productos de charcutería, verdurería, frutería o cualquier producto vendido por peso: usa "Kilogramo" o "Gramo" según corresponda
- Para productos líquidos vendidos por volumen: usa "Litro" o "Mililitro" según corresponda
- Para productos vendidos por unidad individual: usa "Unidad"
- Ejemplos correctos: "Kilogramo", "Gramo", "Litro", "Mililitro", "Unidad"
- Ejemplos INCORRECTOS: "Kg", "G", "L", "ML", "U", "Un"

EJEMPLO DE ARRAY CORRECTO:
"purchase_items": [
  {"product_code": "12345", "description": "Tomate", "quantity": 0.5, "unit_type": "Kilogramo", "total_ves": 100.50, "notes": null},
  {"product_code": "67890", "description": "Agua Mineral", "quantity": 2.0, "unit_type": "Litro", "total_ves": 50.00, "notes": null},
  {"product_code": null, "description": "Pan", "quantity": 1.0, "unit_type": "Unidad", "total_ves": 200.75, "notes": null},
  {"product_code": null, "description": "Kit Viajero", "quantity": 2.0, "unit_type": "Unidad", "total_ves": 1000.40, "notes": null}
]

IMPORTANTE: Si la descripción dice "2x", "3x", etc., extrae ese número como quantity y remuévelo de la descripción.

Responde ÚNICAMENTE con el JSON válido, sin explicaciones adicionales."""

            response = self.model.generate_content([image_part, prompt])

            # Log COMPLETO de la respuesta de Gemini
            logger.info("="*80)
            logger.info("RESPUESTA COMPLETA DE GEMINI (analyze_image):")
            logger.info("="*80)
            logger.info(response.text)
            logger.info("="*80)
            logger.info(f"Longitud de respuesta: {len(response.text)} caracteres")
            logger.info("="*80)

            # Parsear la respuesta
            json_data = self._parse_json_response(response.text)
            logger.info("Imagen analizada exitosamente")

            return json_data

        except Exception as e:
            logger.error(f"Error al analizar imagen: {str(e)}")
            raise

    def extract_invoice_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extrae datos de factura desde texto (transcripción de audio).

        Args:
            text: Texto transcrito

        Returns:
            Diccionario con datos extraídos
        """
        try:
            logger.info(f"Extrayendo datos de factura desde texto ({len(text)} caracteres)")

            prompt = f"""Tengo un texto que extraje de un audio. Formatea la respuesta con este esquema JSON:

{{
  "factura": {{
    "metadata": {{
      "tipo_documento": "string",
      "numero": "string",
      "fecha": "string",
      "hora": "string",
      "establecimiento": {{
        "nombre": "string",
        "razon_social": "string",
        "rif": "string",
        "direccion": "string",
        "ciudad": "string",
        "estado": "string",
        "codigo_postal": "string",
        "pais": "string",
        "telefono": "string",
        "email": "string",
        "sitio_web": "string"
      }},
      "cliente": {{
        "nombre": "string",
        "rif": "string",
        "direccion": "string",
        "telefono": "string",
        "email": "string"
      }}
    }},
    "items": [
      {{
        "codigo_producto": "string",
        "descripcion": "string",
        "cantidad": number,
        "unidad": "string",
        "precio_unitario": number,
        "descuento": number,
        "impuesto": number,
        "subtotal": number,
        "categoria": "string",
        "notas": "string"
      }}
    ],
    "totales": {{
      "subtotal": number,
      "descuentos": number,
      "impuestos": [
        {{
          "tipo": "string",
          "porcentaje": number,
          "base_imponible": number,
          "monto": number
        }}
      ],
      "propina": number,
      "cargos_adicionales": [
        {{
          "concepto": "string",
          "monto": number
        }}
      ],
      "total": number,
      "moneda": "string"
    }},
    "metodo_pago": {{
      "tipo": "string",
      "ultimos_digitos": "string",
      "referencia": "string",
      "banco": "string",
      "monto_pagado": number,
      "cambio": number
    }},
    "informacion_adicional": {{
      "vendedor": "string",
      "cajero": "string",
      "caja": "string",
      "orden_compra": "string",
      "condiciones_pago": "string",
      "notas": ["string"]
    }}
  }}
}}

INSTRUCCIONES:
1. Extrae SOLO la información visible
2. Si un campo no está presente, usa null
3. Valores numéricos deben ser números, no strings
4. Fechas en formato YYYY-MM-DD
5. Convierte montos correctamente (Ej: "Bs8.935,57" → 8935.57)
6. Presta especial atención a los montos totales

REGLAS PARA EL CAMPO "unidad":
- El campo "unidad" DEBE ser la palabra completa en español, NO abreviaturas
- Para productos de charcutería, verdurería, frutería o cualquier producto vendido por peso: usa "Kilogramo" o "Gramo" según corresponda
- Para productos líquidos vendidos por volumen: usa "Litro" o "Mililitro" según corresponda
- Para productos vendidos por unidad individual: usa "Unidad"
- Ejemplos correctos: "Kilogramo", "Gramo", "Litro", "Mililitro", "Unidad"
- Ejemplos INCORRECTOS: "Kg", "G", "L", "ML", "U", "Un"

Responde ÚNICAMENTE con el JSON válido, sin explicaciones adicionales.

El texto es el siguiente: {text}"""

            response = self.model.generate_content(prompt)

            # Log COMPLETO de la respuesta de Gemini
            logger.info("="*80)
            logger.info("RESPUESTA COMPLETA DE GEMINI (extract_invoice_from_text):")
            logger.info("="*80)
            logger.info(response.text)
            logger.info("="*80)
            logger.info(f"Longitud de respuesta: {len(response.text)} caracteres")
            logger.info("="*80)

            # Parsear la respuesta
            json_data = self._parse_json_response(response.text)
            logger.info("Datos extraídos exitosamente desde texto")

            return json_data

        except Exception as e:
            logger.error(f"Error al extraer datos desde texto: {str(e)}")
            raise

    def categorize_products(self, items: list, categories: list) -> Dict[str, Any]:
        """
        Asigna categorías padre e hija a los items de compra.

        Args:
            items: Lista de items de compra
            categories: Lista de categorías disponibles

        Returns:
            JSON con items categorizados
        """
        try:
            logger.info(f"Categorizando {len(items)} productos")

            prompt = f"""Necesito que le asignes una categorias padre de manera obligatoria y una categoria hija a todos los productos obligatoria tambien. Las categorias son las siguientes: {json.dumps(categories)}

Y los productos a los que les tiene que asignar las categorias son los siguientes:

{json.dumps(items)}

Respondeme solamente con el json con las categorias adjuntadas con las nuevas propiedades para cada producto (category_1, category_2). Me tienes que devolver el json completo con todas las propiedades, no omitas ninguna"""

            response = self.model.generate_content(prompt)

            # Log COMPLETO de la respuesta de Gemini
            logger.info("="*80)
            logger.info("RESPUESTA COMPLETA DE GEMINI (categorize_products):")
            logger.info("="*80)
            logger.info(response.text)
            logger.info("="*80)
            logger.info(f"Longitud de respuesta: {len(response.text)} caracteres")
            logger.info("="*80)

            # Parsear la respuesta
            json_data = self._parse_json_response(response.text)
            logger.info("Productos categorizados exitosamente")

            return json_data

        except Exception as e:
            logger.error(f"Error al categorizar productos: {str(e)}")
            raise

    def normalize_products(self, items: list, existing_products: list) -> Dict[str, Any]:
        """
        Normaliza productos extrayendo nombre genérico, marca y variantes.

        Args:
            items: Lista de items de compra
            existing_products: Lista de productos existentes en BD

        Returns:
            JSON con items normalizados
        """
        try:
            logger.info(f"Normalizando {len(items)} productos")

            prompt = f"""Asigna un producto normalizado a cada ítem de compra, incluyendo marcas y variantes específicas.

Si no existe un producto adecuado en la lista, crea uno nuevo que sea reutilizable.
Si la lista `productos` está vacía o es `null`, define tú mismo los productos basándote en el ítem.

## Reglas importantes:

1. **Nombre del producto**: DEBE ser genérico, sin marcas, pesos, cantidades ni variantes.
   - ✅ Correcto: "Mantequilla", "Camisa", "Leche", "Refresco"
   - ❌ Incorrecto: "Mantequilla Mavesa", "Mantequilla 200gm", "Camisa Roja", "Leche Descremada"

2. **Marca (brand)**: Extraer del nombre del ítem si está presente.
   - Si no hay marca explícita, usa `null`
   - Solo UNA marca por ítem (la marca específica del producto comprado)

3. **Variantes (variants)**: Identificar TODAS las características del producto comprado:
   - **Tipos válidos**: "size" (tamaño/peso), "flavor" (sabor), "color", "version" (light/diet/descremado), "material", "package" (empaque)
   - Cada variante es un objeto: {{"type": "size", "value": "200gm"}}
   - Extraer del nombre del ítem

## Estructura de salida para cada ítem:

```json
{{
  "producto": {{
    "name": "string",              // Nombre genérico (SIN marca, SIN variantes)
    "brand": "string | null",      // Marca específica o null
    "variants": [                  // Array de variantes (puede estar vacío [])
      {{
        "type": "size",
        "value": "200gm"
      }}
    ]
  }}
}}
```

Ejemplos de extracción:

Ejemplo 1: "Mantequilla Mavesa 200gm"
{{
  "producto": {{
    "name": "Mantequilla",
    "brand": "Mavesa",
    "variants": [
      {{"type": "size", "value": "200gm"}}
    ]
  }}
}}

Ejemplo 2: "Coca-Cola Zero 2L Botella"
{{
  "producto": {{
    "name": "Coca-Cola",
    "brand": "Coca-Cola",
    "variants": [
      {{"type": "version", "value": "Zero"}},
      {{"type": "size", "value": "2L"}},
      {{"type": "package", "value": "Botella"}}
    ]
  }}
}}

Ejemplo 3: "Camisa Nike Roja Talla XL"
{{
  "producto": {{
    "name": "Camisa",
    "brand": "Nike",
    "variants": [
      {{"type": "color", "value": "Rojo"}},
      {{"type": "size", "value": "XL"}}
    ]
  }}
}}

Ejemplo 4: "Tomate" (sin marca ni variantes específicas)
{{
  "producto": {{
    "name": "Tomate",
    "brand": null,
    "variants": []
  }}
}}

Datos disponibles:

Productos existentes (para reutilizar):
{json.dumps(existing_products)}

Ítems de compra a procesar:
{json.dumps(items)}

Instrucciones finales:

1. Reutiliza productos existentes cuando el name coincida (ignora marca y variantes al comparar)
2. Si reutilizas un producto, asegúrate de extraer la marca y variantes específicas del ítem actual
3. Devuélveme únicamente el JSON completo original con la propiedad producto añadida a cada ítem
4. NO omitas propiedades existentes en los ítems
5. NO agregues explicaciones ni texto adicional, solo el JSON final
6. El campo brand debe ser un string (una sola marca) o null, NO un array"""

            response = self.model.generate_content(prompt)

            # Log COMPLETO de la respuesta de Gemini
            logger.info("="*80)
            logger.info("RESPUESTA COMPLETA DE GEMINI (normalize_products):")
            logger.info("="*80)
            logger.info(response.text)
            logger.info("="*80)
            logger.info(f"Longitud de respuesta: {len(response.text)} caracteres")
            logger.info("="*80)

            # Parsear la respuesta
            json_data = self._parse_json_response(response.text)
            logger.info("Productos normalizados exitosamente")

            return json_data

        except Exception as e:
            logger.error(f"Error al normalizar productos: {str(e)}")
            raise

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        Parsea respuesta JSON de Gemini, manejando code fences y formato loose.

        Args:
            text: Texto de respuesta de Gemini

        Returns:
            Diccionario parseado
        """
        # Log de la respuesta original (primeros 500 chars)
        logger.debug(f"Respuesta Gemini (primeros 500 chars): {text[:500]}")

        # Normalizar y quitar code fences
        s = text.strip()
        s = re.sub(r'^```[a-zA-Z]*\s*', '', s)
        s = re.sub(r'\s*```$', '', s).strip()

        # Extraer primer bloque JSON válido
        first_bracket = s.find('[')
        first_brace = s.find('{')

        if first_bracket != -1 and (first_bracket < first_brace or first_brace == -1):
            # Es un array
            start_idx = first_bracket
            end_idx = s.rfind(']')
        elif first_brace != -1:
            # Es un objeto
            start_idx = first_brace
            end_idx = s.rfind('}')
        else:
            logger.error(f"No se encontró JSON válido. Texto: {s[:200]}")
            raise ValueError("No se encontró JSON válido en la respuesta")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            s = s[start_idx:end_idx + 1]

        # IMPORTANTE: Eliminar caracteres de control inválidos ANTES de parsear
        # Esto incluye saltos de línea literales dentro de strings
        # Los reemplazamos con espacios para no romper el JSON
        s = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', ' ', s)

        # Eliminar espacios múltiples
        s = re.sub(r'\s+', ' ', s)

        # Eliminar comas finales
        s = re.sub(r',(\s*[}\]])', r'\1', s)

        # Intentar parsear
        try:
            return json.loads(s)
        except json.JSONDecodeError as e1:
            logger.warning(f"Intento 1 fallido: {e1}. Probando alternativa...")

            # Intentar con escape de comillas
            s2 = s.replace('\\"', '"')
            try:
                return json.loads(s2)
            except json.JSONDecodeError as e2:
                logger.warning(f"Intento 2 fallido: {e2}. Probando alternativa...")

                # Último intento: quitar comillas envolventes
                s3 = s2.strip()
                if (s3.startswith('"') and s3.endswith('"')) or (s3.startswith("'") and s3.endswith("'")):
                    s3 = s3[1:-1].replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
                    s3 = re.sub(r',(\s*[}\]])', r'\1', s3)
                    try:
                        return json.loads(s3)
                    except json.JSONDecodeError as e3:
                        logger.error(f"Todos los intentos fallaron. JSON problemático (primeros 300 chars): {s[:300]}")
                        raise ValueError(f"No se pudo parsear JSON después de varios intentos: {e1}, {e2}, {e3}")

                logger.error(f"JSON problemático (primeros 300 chars): {s2[:300]}")
                raise ValueError(f"No se pudo parsear JSON: {e1}, {e2}")
