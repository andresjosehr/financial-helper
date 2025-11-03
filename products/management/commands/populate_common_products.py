from django.core.management.base import BaseCommand
from products.models import ProductCategory, ProductBrand, ProductVariant, Product, ProductVariantAssignment
from django.db import transaction


class Command(BaseCommand):
    help = 'Registra productos comunes genéricos con múltiples marcas y variantes'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Registrando productos comunes...\n')

        # Crear marcas
        brands_data = {
            'Coca-Cola': None,
            'Pepsi': None,
            'Mavesa': None,
            'Los Andes': None,
            'Plumrose': None,
            'Lays': None,
            'Doritos': None,
            'Savoy': None,
        }

        for brand_name in brands_data.keys():
            brand, _ = ProductBrand.objects.get_or_create(name=brand_name)
            brands_data[brand_name] = brand

        # Crear variantes
        variants_data = {
            'size:350ml': {'type': 'size', 'value': '350ml'},
            'size:500ml': {'type': 'size', 'value': '500ml'},
            'size:1L': {'type': 'size', 'value': '1L'},
            'size:2L': {'type': 'size', 'value': '2L'},
            'size:200gm': {'type': 'size', 'value': '200gm'},
            'size:500gm': {'type': 'size', 'value': '500gm'},
            'size:1kg': {'type': 'size', 'value': '1kg'},
            'size:100gm': {'type': 'size', 'value': '100gm'},
            'version:Light': {'type': 'version', 'value': 'Light'},
            'version:Zero': {'type': 'version', 'value': 'Zero'},
            'version:Descremada': {'type': 'version', 'value': 'Descremada'},
        }

        variants = {}
        for key, data in variants_data.items():
            variant, _ = ProductVariant.objects.get_or_create(**data)
            variants[key] = variant

        # Definir productos genéricos por categoría
        products_to_create = [
            {
                'category': 'Bebidas no Alcohólicas',
                'name': 'Coca-Cola',
                'brands': ['Coca-Cola'],
                'variants': ['size:350ml', 'size:500ml', 'size:1L', 'size:2L', 'version:Zero']
            },
            {
                'category': 'Bebidas no Alcohólicas',
                'name': 'Pepsi',
                'brands': ['Pepsi'],
                'variants': ['size:350ml', 'size:500ml', 'size:1L', 'size:2L']
            },
            {
                'category': 'Lácteos y Huevos',
                'name': 'Mantequilla',
                'brands': ['Mavesa', 'Los Andes'],
                'variants': ['size:200gm', 'size:500gm']
            },
            {
                'category': 'Lácteos y Huevos',
                'name': 'Leche',
                'brands': ['Los Andes'],
                'variants': ['size:1L', 'version:Descremada']
            },
            {
                'category': 'Carnes y Embutidos',
                'name': 'Jamón',
                'brands': ['Plumrose'],
                'variants': ['size:500gm', 'size:1kg']
            },
            {
                'category': 'Carnes y Embutidos',
                'name': 'Salchicha',
                'brands': ['Plumrose'],
                'variants': ['size:500gm']
            },
            {
                'category': 'Snacks y Dulces',
                'name': 'Papas Fritas',
                'brands': ['Lays'],
                'variants': ['size:100gm', 'size:200gm']
            },
            {
                'category': 'Snacks y Dulces',
                'name': 'Doritos',
                'brands': ['Doritos'],
                'variants': ['size:100gm', 'size:200gm']
            },
            {
                'category': 'Snacks y Dulces',
                'name': 'Chocolate',
                'brands': ['Savoy'],
                'variants': ['size:100gm']
            },
        ]

        products_created = 0

        for product_data in products_to_create:
            # Obtener categoría
            try:
                category = ProductCategory.objects.get(name=product_data['category'])
            except ProductCategory.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  ✗ Categoría no encontrada: {product_data["category"]}'))
                continue

            # Crear producto genérico
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults={'category': category}
            )

            if created:
                products_created += 1
                self.stdout.write(f'  ✓ Producto creado: {product.name} ({category.name})')

            # Asignar marcas
            for brand_name in product_data['brands']:
                brand = brands_data.get(brand_name)
                if brand:
                    product.brands.add(brand)

            # Asignar variantes
            for variant_key in product_data['variants']:
                variant = variants.get(variant_key)
                if variant:
                    ProductVariantAssignment.objects.get_or_create(
                        product=product,
                        variant=variant
                    )

            brands_str = ', '.join(product_data['brands'])
            variants_str = ', '.join([variants[k].value for k in product_data['variants'] if k in variants])
            self.stdout.write(f'    - Marcas: {brands_str}')
            self.stdout.write(f'    - Variantes: {variants_str}\n')

        self.stdout.write(self.style.SUCCESS(f'✓ Productos creados: {products_created}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Total productos: {Product.objects.count()}'))
