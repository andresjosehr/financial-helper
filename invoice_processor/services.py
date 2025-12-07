"""
Servicios para procesamiento de facturas.
"""
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from django.db import transaction
from django.contrib.auth.models import User

from .gemini_client import GeminiClient
from image_processor.views import process_invoice_optimal
from exchange_rates.models import ExchangeRate
from products.models import ProductCategory, ProductBrand, Product, ProductVariant, ProductVariantAssignment
from establishments.models import Establishment
from purchases.models import Purchase, PurchaseItem

logger = logging.getLogger(__name__)


class InvoiceProcessorService:
    """Servicio principal para procesar facturas desde n8n."""

    def __init__(self):
        """Inicializa el servicio con el cliente de Gemini."""
        self.gemini = GeminiClient()

    def process_invoice(
        self,
        file_type: str,
        file_binary: bytes,
        mime_type: str,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Procesa una factura (audio o imagen) y retorna resumen.

        Args:
            file_type: 'audio' o 'image'
            file_binary: Bytes del archivo
            mime_type: Tipo MIME del archivo
            user: Usuario que realizó la compra (opcional)

        Returns:
            Diccionario con purchase_id y summary para Telegram
        """
        try:
            logger.info(f"Iniciando procesamiento de factura ({file_type})")

            # Paso 1: Extraer datos según el tipo
            if file_type == 'audio':
                extracted_data = self._process_audio(file_binary, mime_type)
            elif file_type == 'image':
                extracted_data = self._process_image(file_binary, mime_type)
            else:
                raise ValueError(f"Tipo de archivo no soportado: {file_type}")

            # Paso 2: Obtener tasas de cambio actuales
            rates = self._get_exchange_rates()
            bcv_rate = rates['bcv']
            binance_rate = rates['binance_sell']

            # Paso 3: Calcular valores USD usando las tasas
            extracted_data = self._calculate_usd_values(extracted_data, bcv_rate, binance_rate)

            # Paso 4: Obtener categorías de BD
            categories = self._get_categories()

            # Paso 5: Categorizar productos con Gemini
            categorized_items = self.gemini.categorize_products(
                extracted_data['purchase']['purchase_items'],
                categories
            )

            # Paso 6: Obtener productos existentes filtrados por categorías
            existing_products = self._get_products_by_categories(categorized_items)

            # Paso 7: Normalizar productos con Gemini
            normalized_items = self.gemini.normalize_products(
                categorized_items if isinstance(categorized_items, list) else categorized_items['purchase']['purchase_items'],
                existing_products
            )

            # Reconstruir la estructura completa con items normalizados
            normalized_data = {
                'purchase': {
                    **extracted_data['purchase'],
                    'purchase_items': normalized_items if isinstance(normalized_items, list) else normalized_items['purchase']['purchase_items']
                }
            }

            # Paso 8: Guardar en BD
            purchase = self._save_to_database(
                normalized_data,
                bcv_rate,
                binance_rate,
                user
            )

            # Paso 9: Generar resumen para Telegram
            summary = self._generate_summary(purchase)

            logger.info(f"Factura procesada exitosamente: {purchase.id}")

            return {
                'purchase_id': str(purchase.id),
                'summary': summary
            }

        except Exception as e:
            logger.error(f"Error al procesar factura: {str(e)}", exc_info=True)
            raise

    def _process_audio(self, audio_binary: bytes, mime_type: str) -> Dict[str, Any]:
        """
        Procesa audio: transcribe y extrae datos.

        Args:
            audio_binary: Bytes del audio
            mime_type: Tipo MIME

        Returns:
            Diccionario con datos extraídos
        """
        logger.info("Procesando audio")

        # Transcribir
        transcription = self.gemini.transcribe_audio(audio_binary, mime_type)
        logger.debug(f"Transcripción: {transcription[:200]}...")

        # Extraer datos estructurados
        extracted_data = self.gemini.extract_invoice_from_text(transcription)

        # Convertir formato de audio a formato de imagen (normalizar estructura)
        return self._normalize_audio_format(extracted_data)

    def _process_image(self, image_binary: bytes, mime_type: str) -> Dict[str, Any]:
        """
        Procesa imagen: optimiza y analiza con Gemini.

        Args:
            image_binary: Bytes de la imagen
            mime_type: Tipo MIME

        Returns:
            Diccionario con datos extraídos
        """
        logger.info("Procesando imagen")

        # Optimizar imagen usando el pipeline existente
        from io import BytesIO
        from PIL import Image
        import cv2
        import numpy as np
        from image_processor.views import process_with_custom_params

        # Convertir bytes a imagen PIL
        img_pil = Image.open(BytesIO(image_binary))
        if img_pil.mode != 'RGB':
            img_pil = img_pil.convert('RGB')

        # Aplicar el pipeline de procesamiento con parámetros óptimos
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
            'skip_crop': False
        }

        processed_img_pil = process_with_custom_params(img_pil, optimal_params)

        # Convertir imagen procesada a bytes
        buffer = BytesIO()
        processed_img_pil.save(buffer, format='PNG')
        processed_binary = buffer.getvalue()

        # Analizar con Gemini
        extracted_data = self.gemini.analyze_image(processed_binary, 'image/png')

        return extracted_data

    def _normalize_audio_format(self, audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte el formato de datos de audio al formato de imagen.

        Args:
            audio_data: Datos extraídos del audio

        Returns:
            Datos en formato normalizado
        """
        factura = audio_data.get('factura', {})
        metadata = factura.get('metadata', {})
        establecimiento = metadata.get('establecimiento', {})
        totales = factura.get('totales', {})
        items = factura.get('items', [])

        # Calcular tax_ves y tax_percentage
        impuestos = totales.get('impuestos', [])
        tax_ves = sum(imp.get('monto', 0) for imp in impuestos) if impuestos else 0
        tax_percentage = impuestos[0].get('porcentaje', 16) if impuestos else 16

        # Construir estructura normalizada
        normalized = {
            'purchase': {
                'purchase_date': metadata.get('fecha'),
                'purchase_time': metadata.get('hora'),
                'subtotal_ves': totales.get('subtotal', 0),
                'total_ves': totales.get('total', 0),
                'bcv_rate': None,  # Se llenará después
                'binance_rate': None,  # Se llenará después
                'total_usd_bcv': None,  # Se calculará después
                'total_usd_binance': None,  # Se calculará después
                'tax_ves': tax_ves,
                'tax_type': impuestos[0].get('tipo') if impuestos else None,
                'tax_percentage': tax_percentage,
                'notes': '; '.join(factura.get('informacion_adicional', {}).get('notas', [])),
                'raw_json': audio_data,
                'establishment': {
                    'name': establecimiento.get('nombre', 'Desconocido'),
                    'legal_name': establecimiento.get('razon_social'),
                    'tax_id': establecimiento.get('rif'),
                    'address': establecimiento.get('direccion'),
                    'city': establecimiento.get('ciudad'),
                    'state': establecimiento.get('estado'),
                    'postal_code': establecimiento.get('codigo_postal'),
                    'country': establecimiento.get('pais', 'Venezuela'),
                    'phone': establecimiento.get('telefono'),
                    'email': establecimiento.get('email'),
                    'website': establecimiento.get('sitio_web')
                },
                'purchase_items': []
            }
        }

        # Convertir items
        for item in items:
            normalized['purchase']['purchase_items'].append({
                'product_code': item.get('codigo_producto'),
                'description': item.get('descripcion', 'Sin descripción'),
                'quantity': item.get('cantidad', 1),
                'unit_type': item.get('unidad'),
                'notes': item.get('notas'),
                'total_usd_bcv': None,  # Se calculará después
                'total_usd_binance': None,  # Se calculará después
                'total_ves': item.get('subtotal', 0)  # En audio se guarda como subtotal
            })

        return normalized

    def _get_exchange_rates(self) -> Dict[str, Decimal]:
        """
        Obtiene las tasas de cambio más recientes de la BD.

        Returns:
            Diccionario con tasas BCV y Binance
        """
        logger.info("Obteniendo tasas de cambio")

        rates = ExchangeRate.get_latest_rates()

        bcv_rate = rates.get('BCV')
        binance_sell_rate = rates.get('BINANCE_SELL')

        if not bcv_rate or not binance_sell_rate:
            raise ValueError("No se encontraron tasas de cambio en la BD")

        logger.info(f"Tasas obtenidas - BCV: {bcv_rate}, Binance Sell: {binance_sell_rate}")

        return {
            'bcv': bcv_rate,
            'binance_sell': binance_sell_rate
        }

    def _calculate_usd_values(
        self,
        data: Dict[str, Any],
        bcv_rate: Decimal,
        binance_rate: Decimal
    ) -> Dict[str, Any]:
        """
        Calcula valores en USD para purchase e items.

        Args:
            data: Datos extraídos
            bcv_rate: Tasa BCV
            binance_rate: Tasa Binance

        Returns:
            Datos con valores USD calculados
        """
        logger.info("Calculando valores USD")

        purchase = data['purchase']

        # Asignar tasas
        purchase['bcv_rate'] = float(bcv_rate)
        purchase['binance_rate'] = float(binance_rate)

        # Calcular totales USD
        if purchase.get('total_ves'):
            purchase['total_usd_bcv'] = round(purchase['total_ves'] / float(bcv_rate), 2)
            purchase['total_usd_binance'] = round(purchase['total_ves'] / float(binance_rate), 2)

        if purchase.get('subtotal_ves'):
            purchase['subtotal_usd_bcv'] = round(purchase['subtotal_ves'] / float(bcv_rate), 2)
            purchase['subtotal_usd_binance'] = round(purchase['subtotal_ves'] / float(binance_rate), 2)

        # Calcular items USD
        for item in purchase.get('purchase_items', []):
            if item.get('total_ves'):
                item['total_usd_bcv'] = round(item['total_ves'] / float(bcv_rate), 2)
                item['total_usd_binance'] = round(item['total_ves'] / float(binance_rate), 2)

        return data

    def _get_categories(self) -> list:
        """
        Obtiene todas las categorías de productos desde la BD.

        Returns:
            Lista de categorías con estructura jerárquica
        """
        logger.info("Obteniendo categorías de productos")

        # Obtener categorías padre (sin parent)
        parent_categories = ProductCategory.objects.filter(parent__isnull=True)

        categories = []
        for parent in parent_categories:
            # Obtener hijos
            children = ProductCategory.objects.filter(parent=parent)
            children_names = ', '.join(child.name for child in children)

            categories.append({
                'name': parent.name,
                'children': children_names
            })

        logger.info(f"Se encontraron {len(categories)} categorías padre")

        return categories

    def _get_products_by_categories(self, categorized_data: Dict[str, Any]) -> list:
        """
        Obtiene productos existentes filtrados por las categorías asignadas.

        Args:
            categorized_data: Datos con categorías asignadas

        Returns:
            Lista de productos con marca y variantes
        """
        logger.info("Obteniendo productos por categorías")

        # Extraer categorías únicas (category_2)
        # Gemini puede devolver array directo o objeto anidado
        if isinstance(categorized_data, list):
            items = categorized_data
        else:
            items = categorized_data.get('purchase', {}).get('purchase_items', [])

        category_names = set()

        for item in items:
            cat2 = item.get('category_2')
            if cat2:
                category_names.add(cat2)

        if not category_names:
            logger.warning("No se encontraron categorías asignadas")
            return []

        # Buscar categorías en BD
        categories = ProductCategory.objects.filter(name__in=category_names)

        # Buscar productos de esas categorías
        # Nota: brands es ManyToManyField, usar prefetch_related
        products = Product.objects.filter(category__in=categories).select_related('category').prefetch_related('brands')

        result = []
        for product in products:
            # Obtener variantes
            variant_assignments = ProductVariantAssignment.objects.filter(
                product=product
            ).select_related('variant')

            variants = []
            for assignment in variant_assignments:
                variant = assignment.variant
                variants.append({
                    'type': variant.type,
                    'value': variant.value
                })

            # Obtener marcas (es M2M, puede tener múltiples)
            brands_list = list(product.brands.all())
            brand_name = brands_list[0].name if brands_list else None

            result.append({
                'id': str(product.id),
                'name': product.name,
                'brand': brand_name,
                'variants': variants
            })

        logger.info(f"Se encontraron {len(result)} productos")

        return result

    @transaction.atomic
    def _save_to_database(
        self,
        normalized_data: Dict[str, Any],
        bcv_rate: Decimal,
        binance_rate: Decimal,
        user: Optional[User]
    ) -> Purchase:
        """
        Guarda la factura procesada en la BD.

        Proceso:
        1. Get or create Establishment
        2. Para cada item:
           - Get or create ProductBrand (si tiene)
           - Get or create ProductVariants
           - Get or create Product (solo por name)
           - Asociar brands y variants al product
        3. Create Purchase
        4. Create PurchaseItems

        Args:
            normalized_data: Datos normalizados con productos
            bcv_rate: Tasa BCV
            binance_rate: Tasa Binance
            user: Usuario (opcional)

        Returns:
            Objeto Purchase creado
        """
        logger.info("Guardando factura en BD")

        purchase_data = normalized_data.get('purchase', {})
        establishment_data = purchase_data.get('establishment', {})
        items_data = purchase_data.get('purchase_items', [])

        # Crear o buscar establecimiento
        establishment = None
        if establishment_data.get('name'):
            # FORZAR country a Venezuela si viene null o vacío
            country = establishment_data.get('country')
            if not country or country.strip() == '':
                country = 'Venezuela'

            establishment, created = Establishment.objects.get_or_create(
                name=establishment_data['name'],
                defaults={
                    'legal_name': establishment_data.get('legal_name'),
                    'tax_id': establishment_data.get('tax_id'),
                    'address': establishment_data.get('address'),
                    'city': establishment_data.get('city'),
                    'state': establishment_data.get('state'),
                    'postal_code': establishment_data.get('postal_code'),
                    'country': country,
                    'phone': establishment_data.get('phone'),
                    'email': establishment_data.get('email'),
                    'website': establishment_data.get('website')
                }
            )
            if created:
                logger.info(f"✓ Establecimiento CREADO: {establishment.name} ({country})")
            else:
                logger.debug(f"Establecimiento ya existe: {establishment.name}")

        # Parsear fecha y hora
        purchase_date = self._parse_date(purchase_data.get('purchase_date'))
        purchase_time = self._parse_time(purchase_data.get('purchase_time'))

        # Preparar valores del Purchase
        total_ves = Decimal(str(purchase_data.get('total_ves', 0)))
        subtotal_ves = Decimal(str(purchase_data.get('subtotal_ves', 0)))
        tax_ves = Decimal(str(purchase_data.get('tax_ves', 0)))
        tax_percentage = Decimal(str(purchase_data.get('tax_percentage', 16)))

        # Calcular USD usando las tasas
        total_usd_bcv = total_ves / bcv_rate if bcv_rate else None
        total_usd_binance = total_ves / binance_rate if binance_rate else None

        # Crear Purchase
        purchase = Purchase.objects.create(
            user=user,
            establishment=establishment,
            purchase_date=purchase_date,
            purchase_time=purchase_time,
            subtotal_ves=subtotal_ves,
            total_ves=total_ves,
            bcv_rate=bcv_rate,
            binance_rate=binance_rate,
            total_usd_bcv=total_usd_bcv,
            total_usd_binance=total_usd_binance,
            tax_ves=tax_ves,
            tax_type=purchase_data.get('tax_type'),
            tax_percentage=tax_percentage,
            notes=purchase_data.get('notes'),
            raw_json=normalized_data
        )

        logger.info(f"Purchase creado: {purchase.id}")

        # Crear PurchaseItems
        uncategorized_category = self._get_or_create_uncategorized_category()

        for item_data in items_data:
            # Buscar o crear producto
            product = self._get_or_create_product(item_data, uncategorized_category)

            # Calcular USD para el item
            item_total_ves = Decimal(str(item_data.get('total_ves', 0)))
            item_total_usd_bcv = item_total_ves / bcv_rate if bcv_rate else None
            item_total_usd_binance = item_total_ves / binance_rate if binance_rate else None

            PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                description=item_data.get('description', 'Sin descripción'),
                quantity=Decimal(str(item_data.get('quantity', 1))),
                unit_type=item_data.get('unit_type'),
                total_ves=item_total_ves,
                total_usd_bcv=item_total_usd_bcv,
                total_usd_binance=item_total_usd_binance,
                notes=item_data.get('notes')
            )

        logger.info(f"Se crearon {len(items_data)} items")

        return purchase

    def _get_or_create_uncategorized_category(self) -> ProductCategory:
        """
        Obtiene o crea la categoría 'Sin Clasificar'.

        Returns:
            ProductCategory
        """
        category, created = ProductCategory.objects.get_or_create(
            name='Sin Clasificar',
            defaults={
                'description': 'Productos sin categoría asignada'
            }
        )
        if created:
            logger.info("Categoría 'Sin Clasificar' creada")

        return category

    def _get_or_create_product(
        self,
        item_data: Dict[str, Any],
        uncategorized_category: ProductCategory
    ) -> Optional[Product]:
        """
        Busca o crea producto con marca y variantes.

        Lógica:
        - El PRODUCTO se identifica SOLO por el NAME (único)
        - Un mismo producto puede tener MÚLTIPLES MARCAS (M2M)
        - Un mismo producto puede tener MÚLTIPLES VARIANTES (M2M)
        - Si el producto YA EXISTE, agrega la marca y variantes si no las tiene
        - Si el producto NO EXISTE, lo crea y agrega marca y variantes

        Args:
            item_data: Datos del item con producto normalizado
            uncategorized_category: Categoría por defecto

        Returns:
            Product o None
        """
        producto_data = item_data.get('producto')
        if not producto_data:
            logger.warning("Item sin datos de producto")
            return None

        product_name = producto_data.get('name')
        if not product_name:
            logger.warning("Producto sin nombre")
            return None

        brand_name = producto_data.get('brand')
        variants_data = producto_data.get('variants', [])

        # Buscar categoría asignada (de category_2)
        category = uncategorized_category
        category_name = item_data.get('category_2')
        if category_name:
            try:
                category = ProductCategory.objects.get(name=category_name)
                logger.debug(f"Categoría encontrada: {category_name}")
            except ProductCategory.DoesNotExist:
                logger.warning(f"Categoría no encontrada: {category_name}, usando 'Sin Clasificar'")

        # 1. BUSCAR O CREAR PRODUCTO (solo por name)
        product, product_created = Product.objects.get_or_create(
            name=product_name,
            defaults={
                'category': category
            }
        )

        if product_created:
            logger.info(f"✓ Producto CREADO: {product_name} (categoría: {category.name})")
        else:
            logger.debug(f"Producto ya existe: {product_name}")

        # 2. AGREGAR MARCA (si tiene y no está ya asociada)
        if brand_name:
            brand, brand_created = ProductBrand.objects.get_or_create(name=brand_name)

            if brand_created:
                logger.info(f"✓ Marca CREADA: {brand_name}")

            # Verificar si la marca ya está asociada al producto
            if not product.brands.filter(id=brand.id).exists():
                product.brands.add(brand)
                logger.info(f"✓ Marca '{brand_name}' asociada a producto '{product_name}'")
            else:
                logger.debug(f"Marca '{brand_name}' ya asociada a '{product_name}'")

        # 3. AGREGAR VARIANTES (si tiene y no están ya asociadas)
        for variant_data in variants_data:
            variant_type = variant_data.get('type')
            variant_value = variant_data.get('value')

            if not variant_type or not variant_value:
                logger.warning(f"Variante incompleta: {variant_data}")
                continue

            # Get or create variante
            variant, variant_created = ProductVariant.objects.get_or_create(
                type=variant_type,
                value=variant_value
            )

            if variant_created:
                logger.info(f"✓ Variante CREADA: {variant_type}={variant_value}")

            # Verificar si la variante ya está asociada al producto
            if not ProductVariantAssignment.objects.filter(product=product, variant=variant).exists():
                ProductVariantAssignment.objects.create(
                    product=product,
                    variant=variant
                )
                logger.info(f"✓ Variante '{variant_type}:{variant_value}' asociada a producto '{product_name}'")
            else:
                logger.debug(f"Variante '{variant_type}:{variant_value}' ya asociada a '{product_name}'")

        return product

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime.date]:
        """
        Parsea fecha en formato YYYY-MM-DD.

        Args:
            date_str: String de fecha

        Returns:
            datetime.date o None
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            logger.warning(f"Fecha inválida: {date_str}")
            return None

    def _parse_time(self, time_str: Optional[str]) -> Optional[datetime.time]:
        """
        Parsea hora en formato HH:MM:SS o HH:MM.

        Args:
            time_str: String de hora

        Returns:
            datetime.time o None
        """
        if not time_str:
            return None

        try:
            # Intentar HH:MM:SS
            return datetime.strptime(time_str, '%H:%M:%S').time()
        except (ValueError, TypeError):
            try:
                # Intentar HH:MM
                return datetime.strptime(time_str, '%H:%M').time()
            except (ValueError, TypeError):
                logger.warning(f"Hora inválida: {time_str}")
                return None

    def _generate_summary(self, purchase: Purchase) -> str:
        """
        Genera resumen de texto para enviar a Telegram.

        Args:
            purchase: Purchase creado

        Returns:
            Texto formateado
        """
        items_count = purchase.items.count()
        establishment_name = purchase.establishment.name if purchase.establishment else 'Desconocido'

        summary = f"""✅ Factura procesada exitosamente

📍 Establecimiento: {establishment_name}
📅 Fecha: {purchase.purchase_date}
🛒 Items: {items_count}

💰 Total: Bs.{purchase.total_ves:,.2f}
💵 USD (BCV): ${purchase.total_usd_bcv:,.2f}
💵 USD (Binance): ${purchase.total_usd_binance:,.2f}

📊 Tasas usadas:
   • BCV: Bs.{purchase.bcv_rate:,.2f}
   • Binance: Bs.{purchase.binance_rate:,.2f}

ID: {purchase.id}"""

        return summary
