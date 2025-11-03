from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from PIL import Image, ImageEnhance, ImageFilter
import io
import numpy as np
import base64
import cv2
from scipy import ndimage


def test_page(request):
    """Página HTML para probar el procesamiento de imágenes"""
    return render(request, 'image_processor/test.html')


@csrf_exempt
@require_http_methods(["POST"])
def process_invoice_image(request):
    """
    Endpoint para procesar imágenes de facturas:
    1. Detecta y recorta el rectángulo blanco de la factura
    2. Convierte a blanco y negro
    3. Aumenta el contraste para mejor legibilidad

    Acepta: multipart/form-data con campo 'image'
    Retorna: imagen procesada en base64 o como archivo
    """
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No se proporcionó una imagen'}, status=400)

        image_file = request.FILES['image']

        # Abrir imagen con PIL
        image = Image.open(image_file)

        # Convertir a RGB si es necesario
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Paso 1: Preprocesar - eliminar ruido agresivamente
        preprocessed = preprocess_image_aggressive(image)

        # Paso 2: Detectar y recortar la factura con mejor algoritmo
        cropped_image = detect_and_crop_invoice_improved(preprocessed)

        # Paso 3: Convertir a escala de grises
        gray_image = cropped_image.convert('L')

        # Paso 4: Limpiar ruido residual con filtros múltiples
        cleaned = clean_noise_aggressive(gray_image)

        # Paso 5: Aumentar contraste
        enhanced_image = enhance_contrast(cleaned)

        # Paso 6: Aplicar umbral adaptativo para mejor legibilidad
        processed_image = apply_adaptive_threshold_improved(enhanced_image)
        
        # Paso 7: Limpieza morfológica final para eliminar ruido sal y pimienta
        final_image = final_noise_removal(processed_image)

        # Determinar formato de respuesta
        return_format = request.POST.get('format', 'base64')

        if return_format == 'file':
            # Retornar como archivo de imagen
            buffer = io.BytesIO()
            final_image.save(buffer, format='PNG')
            buffer.seek(0)

            response = HttpResponse(buffer.getvalue(), content_type='image/png')
            response['Content-Disposition'] = 'attachment; filename="processed_invoice.png"'
            return response
        else:
            # Retornar como base64
            buffer = io.BytesIO()
            final_image.save(buffer, format='PNG')
            buffer.seek(0)

            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            return JsonResponse({
                'success': True,
                'image': f'data:image/png;base64,{img_base64}',
                'original_size': f'{image.width}x{image.height}',
                'processed_size': f'{final_image.width}x{final_image.height}'
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


def preprocess_image_aggressive(image):
    """
    Preprocesamiento agresivo para imágenes con mucho ruido
    """
    # Convertir a numpy array
    img_array = np.array(image)
    
    # Convertir a escala de grises
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # 1. Filtro de mediana grande para eliminar ruido sal y pimienta
    denoised = cv2.medianBlur(gray, 5)
    
    # 2. Filtro bilateral para suavizar preservando bordes
    bilateral = cv2.bilateralFilter(denoised, 9, 75, 75)
    
    # 3. Filtro morfológico para cerrar pequeños agujeros
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    morph = cv2.morphologyEx(bilateral, cv2.MORPH_CLOSE, kernel)
    
    # 4. CLAHE para ecualizar histograma
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    equalized = clahe.apply(morph)
    
    # Convertir de vuelta a PIL RGB
    result_rgb = cv2.cvtColor(equalized, cv2.COLOR_GRAY2RGB)
    result = Image.fromarray(result_rgb)
    
    return result


def detect_and_crop_invoice_improved(image):
    """
    Detecta y recorta la factura usando múltiples estrategias de detección
    """
    # Convertir PIL a numpy
    img_array = np.array(image)

    # Convertir a escala de grises
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    h, w = gray.shape

    print(f"[DEBUG] Imagen original: {w}x{h}")

    # ESTRATEGIA 1: Detección por bordes Canny
    def strategy_canny():
        """Detecta el documento usando detección de bordes Canny"""
        # Aplicar blur para reducir ruido
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Detección de bordes Canny
        edges = cv2.Canny(blurred, 50, 150)

        # Dilatar para conectar bordes fragmentados
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # Encontrar contornos
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) == 0:
            return None

        # Buscar el contorno rectangular más grande
        min_area = (w * h) * 0.10  # Al menos 10% del área
        max_area = (w * h) * 0.98  # Máximo 98%

        best = None
        best_score = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area < area < max_area:
                # Aproximar el contorno a un polígono
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect_ratio = cw / float(ch) if ch > 0 else 0

                # Rechazar si es toda la imagen
                is_full = (x <= 10 and y <= 10 and cw >= w-20 and ch >= h-20)

                # Preferir rectángulos (4 esquinas) con aspect ratio razonable
                # Facturas pueden ser verticales (0.4) o apaisadas (2.5)
                if not is_full and 0.3 < aspect_ratio < 3.0:
                    # Scoring: priorizar área y número de vértices cercano a 4
                    vertices_score = 1.0 if len(approx) == 4 else 0.7
                    score = area * vertices_score

                    if score > best_score:
                        best_score = score
                        best = (x, y, cw, ch, area)

        return best

    # ESTRATEGIA 2: Detección por umbralización Otsu (algoritmo original mejorado)
    def strategy_otsu():
        """Detecta usando umbralización Otsu en ambas polaridades"""
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        results = []

        for polarity_name, binary_img in [("normal", thresh), ("invertida", cv2.bitwise_not(thresh))]:
            # Operaciones morfológicas
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
            morph = cv2.morphologyEx(binary_img, cv2.MORPH_CLOSE, kernel, iterations=3)
            morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel, iterations=1)

            contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if len(contours) == 0:
                continue

            min_area = (w * h) * 0.10
            max_area = (w * h) * 0.98

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if min_area < area < max_area:
                    x, y, cw, ch = cv2.boundingRect(cnt)
                    aspect_ratio = cw / float(ch) if ch > 0 else 0

                    is_full = (x <= 10 and y <= 10 and cw >= w-20 and ch >= h-20)

                    if not is_full and 0.3 < aspect_ratio < 3.0:
                        results.append((area, x, y, cw, ch))

        if results:
            results.sort(reverse=True)
            area, x, y, cw, ch = results[0]
            return (x, y, cw, ch, area)
        return None

    # ESTRATEGIA 3: Detección por análisis de brillo (encontrar región clara/oscura)
    def strategy_brightness():
        """Detecta documento buscando regiones con brillo diferente al fondo"""
        # Calcular brillo promedio global
        mean_brightness = np.mean(gray)

        # Umbralizar basado en si el documento es más claro o más oscuro que el fondo
        if mean_brightness < 128:  # Fondo oscuro, documento claro
            _, thresh = cv2.threshold(gray, mean_brightness + 20, 255, cv2.THRESH_BINARY)
        else:  # Fondo claro, documento oscuro
            _, thresh = cv2.threshold(gray, mean_brightness - 20, 255, cv2.THRESH_BINARY_INV)

        # Limpiar ruido
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) == 0:
            return None

        min_area = (w * h) * 0.10
        max_area = (w * h) * 0.98

        best = None
        best_area = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area < area < max_area and area > best_area:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect_ratio = cw / float(ch) if ch > 0 else 0
                is_full = (x <= 10 and y <= 10 and cw >= w-20 and ch >= h-20)

                if not is_full and 0.3 < aspect_ratio < 3.0:
                    best_area = area
                    best = (x, y, cw, ch, area)

        return best

    # Ejecutar todas las estrategias
    results = []

    result1 = strategy_canny()
    if result1:
        results.append(("Canny", result1))
        print(f"[DEBUG] Estrategia Canny: encontró {result1[2]}x{result1[3]} (área: {result1[4]/(w*h)*100:.1f}%)")

    result2 = strategy_otsu()
    if result2:
        results.append(("Otsu", result2))
        print(f"[DEBUG] Estrategia Otsu: encontró {result2[2]}x{result2[3]} (área: {result2[4]/(w*h)*100:.1f}%)")

    result3 = strategy_brightness()
    if result3:
        results.append(("Brillo", result3))
        print(f"[DEBUG] Estrategia Brillo: encontró {result3[2]}x{result3[3]} (área: {result3[4]/(w*h)*100:.1f}%)")

    # Si no se encontró nada, retornar imagen original
    if not results:
        print("[DEBUG] ⚠️  Ninguna estrategia detectó la factura - retornando imagen original")
        return image

    # Elegir el mejor resultado: el que tenga mayor área pero no sea toda la imagen
    results.sort(key=lambda x: x[1][4], reverse=True)

    best_name, (x, y, cw, ch, area) = results[0]
    print(f"[DEBUG] ✅ Usando resultado de estrategia '{best_name}'")
    print(f"[DEBUG] Recorte: x={x}, y={y}, w={cw}, h={ch}")

    # Añadir margen proporcional (3% en cada lado)
    margin_x = int(cw * 0.03)
    margin_y = int(ch * 0.03)

    x = max(0, x - margin_x)
    y = max(0, y - margin_y)
    cw = min(w - x, cw + 2*margin_x)
    ch = min(h - y, ch + 2*margin_y)

    print(f"[DEBUG] Recorte final (con margen): x={x}, y={y}, w={cw}, h={ch}")

    # Recortar imagen original
    cropped = image.crop((x, y, x + cw, y + ch))

    return cropped


def clean_noise_aggressive(image):
    """
    Limpieza agresiva de ruido en escala de grises
    """
    # Convertir a numpy
    img_array = np.array(image)
    
    # 1. Filtro de mediana más grande
    step1 = cv2.medianBlur(img_array, 5)
    
    # 2. Filtro gaussiano
    step2 = cv2.GaussianBlur(step1, (3, 3), 0)
    
    # 3. Filtro bilateral
    step3 = cv2.bilateralFilter(step2, 9, 50, 50)
    
    # Convertir de vuelta a PIL
    result = Image.fromarray(step3, mode='L')
    
    return result


def enhance_contrast(image):
    """
    Aumenta el contraste de la imagen en escala de grises
    """
    # Convertir a numpy
    img_array = np.array(image)
    
    # CLAHE para contraste adaptativo más agresivo
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
    enhanced = clahe.apply(img_array)
    
    # Convertir a PIL
    result = Image.fromarray(enhanced, mode='L')
    
    # Aumentar nitidez adicional
    sharpener = ImageEnhance.Sharpness(result)
    sharpened = sharpener.enhance(1.5)
    
    return sharpened


def apply_adaptive_threshold_improved(image):
    """
    Aplica umbralización adaptativa mejorada
    """
    # Convertir a numpy
    img_array = np.array(image)
    
    # Umbralización adaptativa de OpenCV con parámetros ajustados
    binary = cv2.adaptiveThreshold(
        img_array, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 15  # Ventana más grande y offset mayor
    )
    
    # Convertir de vuelta a PIL
    result = Image.fromarray(binary, mode='L')
    
    return result


def final_noise_removal(image):
    """
    Limpieza final morfológica para eliminar ruido sal y pimienta
    """
    # Convertir a numpy
    img_array = np.array(image)
    
    # 1. Opening para eliminar puntos blancos pequeños (ruido blanco)
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    opened = cv2.morphologyEx(img_array, cv2.MORPH_OPEN, kernel_open)
    
    # 2. Closing para eliminar puntos negros pequeños (ruido negro)
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_close)
    
    # 3. Filtro de mediana final muy suave
    final = cv2.medianBlur(closed, 3)
    
    # Convertir de vuelta a PIL
    result = Image.fromarray(final, mode='L')
    
    return result


# Funciones antiguas mantenidas por compatibilidad
def preprocess_image(image):
    """DEPRECATED: Usa preprocess_image_aggressive"""
    return preprocess_image_aggressive(image)


def clean_noise(image):
    """DEPRECATED: Usa clean_noise_aggressive"""
    return clean_noise_aggressive(image)


def detect_and_crop_invoice(image):
    """DEPRECATED: Usa detect_and_crop_invoice_improved"""
    return detect_and_crop_invoice_improved(image)


def crop_by_edges(image):
    """DEPRECATED: Usa detect_and_crop_invoice_improved"""
    return image


def apply_adaptive_threshold(image):
    """DEPRECATED: Usa apply_adaptive_threshold_improved"""
    return apply_adaptive_threshold_improved(image)


def calculate_otsu_threshold(image_array):
    """DEPRECATED: Usa cv2.threshold con OTSU"""
    _, threshold = cv2.threshold(image_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return threshold


@csrf_exempt
@require_http_methods(["POST"])
def process_with_params(request):
    """
    Endpoint para procesar imágenes con parámetros personalizables

    Parámetros de formato de respuesta:
    - response_format=binary (por defecto): Devuelve la imagen como binario PNG
    - response_format=base64: Devuelve JSON con la imagen en base64
    """
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No se proporcionó una imagen'}, status=400)

        image_file = request.FILES['image']

        # Obtener parámetros (con valores por defecto)
        params = {
            'median_blur': int(request.POST.get('median_blur', 1)),
            'bilateral_d': int(request.POST.get('bilateral_d', 14)),
            'bilateral_sigma': int(request.POST.get('bilateral_sigma', 100)),
            'clahe_clip': float(request.POST.get('clahe_clip', 0)),
            'clahe_grid': int(request.POST.get('clahe_grid', 4)),
            'adaptive_block': int(request.POST.get('adaptive_block', 17)),
            'adaptive_c': int(request.POST.get('adaptive_c', 2)),
            'gaussian_blur': int(request.POST.get('gaussian_blur', 6)),
            'morph_open': int(request.POST.get('morph_open', 0)),
            'morph_close': int(request.POST.get('morph_close', 0)),
            'sharpness': float(request.POST.get('sharpness', 0)),
            'skip_crop': request.POST.get('skip_crop', 'false') == 'true'
        }

        # Formato de respuesta: binary (por defecto) o base64
        response_format = request.POST.get('response_format', 'binary').lower()

        # Abrir imagen
        image = Image.open(image_file)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Procesar con parámetros personalizados
        result = process_with_custom_params(image, params)

        # Preparar buffer con la imagen procesada
        buffer = io.BytesIO()
        result.save(buffer, format='PNG')
        buffer.seek(0)

        # Retornar según el formato solicitado
        if response_format == 'base64':
            # Respuesta JSON con base64
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return JsonResponse({
                'success': True,
                'image': f'data:image/png;base64,{img_base64}',
                'original_size': f'{image.width}x{image.height}',
                'processed_size': f'{result.width}x{result.height}',
                'params': params
            })
        else:
            # Respuesta binaria (por defecto)
            response = HttpResponse(buffer.getvalue(), content_type='image/png')
            response['Content-Disposition'] = 'inline; filename="processed_invoice.png"'
            response['Content-Type'] = 'image/png'
            response['X-Content-Type-Options'] = 'nosniff'
            return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


def process_with_custom_params(image, params):
    """
    Procesa imagen con parámetros personalizados
    """
    # Validar y ajustar parámetros (deben ser impares)
    if params["median_blur"] % 2 == 0:
        params["median_blur"] += 1
    
    if params["gaussian_blur"] > 0 and params["gaussian_blur"] % 2 == 0:
        params["gaussian_blur"] += 1
    
    if params["adaptive_block"] % 2 == 0:
        params["adaptive_block"] += 1
    
    # PASO 0: Recortar factura PRIMERO (antes de cualquier procesamiento)
    if not params['skip_crop']:
        image = detect_and_crop_invoice_improved(image)
    
    # Convertir a numpy y escala de grises
    img_array = np.array(image)
    
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # 1. Preprocesamiento
    if params['median_blur'] > 1:
        gray = cv2.medianBlur(gray, params['median_blur'])
    
    if params['bilateral_d'] > 0:
        gray = cv2.bilateralFilter(gray, params['bilateral_d'], 
                                   params['bilateral_sigma'], 
                                   params['bilateral_sigma'])
    
    if params['clahe_clip'] > 0:
        clahe = cv2.createCLAHE(clipLimit=params['clahe_clip'], 
                               tileGridSize=(params['clahe_grid'], params['clahe_grid']))
        gray = clahe.apply(gray)

    # 2. Desenfoque gaussiano
    if params['gaussian_blur'] > 0:
        gray = cv2.GaussianBlur(gray, (params['gaussian_blur'], params['gaussian_blur']), 0)

    # 3. Aumentar nitidez
    if params['sharpness'] != 1.0:
        pil_img = Image.fromarray(gray, mode='L')
        sharpener = ImageEnhance.Sharpness(pil_img)
        pil_img = sharpener.enhance(params['sharpness'])
        gray = np.array(pil_img)

    # 4. Umbralización adaptativa
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        params['adaptive_block'], 
        params['adaptive_c']
    )

    # 5. Operaciones morfológicas
    if params['morph_open'] > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                          (params['morph_open'], params['morph_open']))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    if params['morph_close'] > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                          (params['morph_close'], params['morph_close']))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Convertir a PIL
    result = Image.fromarray(binary, mode='L')
    return result


def tuning_page(request):
    """Página de ajuste de parámetros"""
    return render(request, 'image_processor/tuning.html')


# Actualizar endpoint principal para usar configuración óptima
@csrf_exempt
@require_http_methods(["POST"])
def process_invoice_optimal(request):
    """
    Endpoint optimizado para procesar facturas con la mejor configuración encontrada

    Parámetros opcionales:
    - response_format=binary (por defecto): Devuelve la imagen como binario PNG
    - response_format=base64: Devuelve JSON con la imagen en base64
    - skip_crop=true/false: Omitir el recorte automático (por defecto: false)
    """
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No se proporcionó una imagen'}, status=400)

        image_file = request.FILES['image']

        # Parámetros óptimos predefinidos
        optimal_params = {
            'median_blur': 1,
            'bilateral_d': 14,
            'bilateral_sigma': 100,
            'clahe_clip': 0,
            'clahe_grid': 4,
            'adaptive_block': 17,
            'adaptive_c': 2,
            'gaussian_blur': 6,
            'morph_open': 0,
            'morph_close': 0,
            'sharpness': 0,
            'skip_crop': request.POST.get('skip_crop', 'false').lower() == 'true'
        }

        # Formato de respuesta: binary (por defecto) o base64
        response_format = request.POST.get('response_format', 'binary').lower()

        # Abrir imagen
        image = Image.open(image_file)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Procesar con parámetros óptimos
        result = process_with_custom_params(image, optimal_params)

        # Preparar buffer con la imagen procesada
        buffer = io.BytesIO()
        result.save(buffer, format='PNG')
        buffer.seek(0)

        # Retornar según el formato solicitado
        if response_format == 'base64':
            # Respuesta JSON con base64
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return JsonResponse({
                'success': True,
                'image': f'data:image/png;base64,{img_base64}',
                'original_size': f'{image.width}x{image.height}',
                'processed_size': f'{result.width}x{result.height}'
            })
        else:
            # Respuesta binaria (por defecto)
            response = HttpResponse(buffer.getvalue(), content_type='image/png')
            response['Content-Disposition'] = 'inline; filename="processed_invoice.png"'
            response['Content-Type'] = 'image/png'
            response['X-Content-Type-Options'] = 'nosniff'
            return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
