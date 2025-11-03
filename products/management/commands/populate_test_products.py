from django.core.management.base import BaseCommand
from products.models import ProductCategory, ProductBrand, ProductVariant, Product, ProductVariantAssignment
from django.db import transaction


class Command(BaseCommand):
    help = 'Registra 3 productos de prueba por cada categoría con marcas y variantes'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Registrando productos de prueba...\n')

        # Obtener categorías de nivel hoja (sin hijos)
        leaf_categories = ProductCategory.objects.filter(children__isnull=True)[:10]  # Limitamos a 10 categorías para no saturar

        if not leaf_categories.exists():
            self.stdout.write(self.style.ERROR('No hay categorías disponibles. Ejecuta primero populate_product_categories'))
            return

        # Crear marcas genéricas
        brands_data = ['Marca A', 'Marca B', 'Marca C', 'Sin Marca']
        brands = {}
        for brand_name in brands_data:
            brand, created = ProductBrand.objects.get_or_create(name=brand_name)
            brands[brand_name] = brand
            if created:
                self.stdout.write(f'  ✓ Marca creada: {brand_name}')

        # Crear variantes comunes
        variants_data = [
            {'type': 'size', 'value': '100gm'},
            {'type': 'size', 'value': '200gm'},
            {'type': 'size', 'value': '500gm'},
            {'type': 'size', 'value': '1kg'},
            {'type': 'size', 'value': '500ml'},
            {'type': 'size', 'value': '1L'},
            {'type': 'size', 'value': '2L'},
            {'type': 'version', 'value': 'Light'},
            {'type': 'version', 'value': 'Diet'},
            {'type': 'version', 'value': 'Sin Azúcar'},
            {'type': 'version', 'value': 'Descremado'},
        ]
        variants = {}
        for variant_data in variants_data:
            variant, created = ProductVariant.objects.get_or_create(**variant_data)
            key = f"{variant_data['type']}:{variant_data['value']}"
            variants[key] = variant
            if created:
                self.stdout.write(f'  ✓ Variante creada: {variant_data["type"]} = {variant_data["value"]}')

        self.stdout.write('')

        # Productos de prueba por categoría
        products_created = 0

        for category in leaf_categories:
            self.stdout.write(f'Categoría: {category.name}')

            # Crear 3 productos por categoría
            for i in range(1, 4):
                product_name = f'{category.name} Genérico {i}'
                brand = brands[brands_data[i-1]]  # Rotar entre las primeras 3 marcas

                # Crear producto
                product, created = Product.objects.get_or_create(
                    name=product_name,
                    brand=brand,
                    defaults={'category': category}
                )

                if created:
                    products_created += 1

                    # Asignar variantes según el número del producto
                    if i == 1:
                        # Producto 1: Solo tamaño
                        variant_keys = ['size:200gm']
                    elif i == 2:
                        # Producto 2: Tamaño + versión
                        variant_keys = ['size:500gm', 'version:Light']
                    else:
                        # Producto 3: Solo tamaño grande
                        variant_keys = ['size:1kg']

                    for key in variant_keys:
                        variant = variants[key]
                        ProductVariantAssignment.objects.get_or_create(
                            product=product,
                            variant=variant
                        )

                    variants_str = ', '.join([variants[k].value for k in variant_keys])
                    self.stdout.write(f'  ✓ {product.name} ({brand.name}) - Variantes: {variants_str}')

            self.stdout.write('')

        self.stdout.write(self.style.SUCCESS(f'\n✓ Productos creados: {products_created}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Marcas totales: {ProductBrand.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Variantes totales: {ProductVariant.objects.count()}'))
