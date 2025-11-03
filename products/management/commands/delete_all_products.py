from django.core.management.base import BaseCommand
from products.models import Product, ProductBrand, ProductVariant, ProductVariantAssignment
from django.db import transaction


class Command(BaseCommand):
    help = 'Elimina todos los productos, marcas, variantes y asignaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma la eliminación sin pedir confirmación interactiva',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Contar registros actuales
        products_count = Product.objects.count()
        brands_count = ProductBrand.objects.count()
        variants_count = ProductVariant.objects.count()
        assignments_count = ProductVariantAssignment.objects.count()

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('ADVERTENCIA: Esta acción eliminará TODOS los datos'))
        self.stdout.write('='*60)
        self.stdout.write(f'Productos: {products_count}')
        self.stdout.write(f'Marcas: {brands_count}')
        self.stdout.write(f'Variantes: {variants_count}')
        self.stdout.write(f'Asignaciones: {assignments_count}')
        self.stdout.write('='*60 + '\n')

        if not options['confirm']:
            confirm = input('¿Estás seguro de que deseas eliminar TODOS estos datos? (escribe "SI" para confirmar): ')
            if confirm != 'SI':
                self.stdout.write(self.style.ERROR('Operación cancelada'))
                return

        self.stdout.write('Eliminando datos...\n')

        # Eliminar en orden correcto (primero relaciones, luego entidades)

        # 1. Asignaciones de variantes (tabla intermedia)
        ProductVariantAssignment.objects.all().delete()
        self.stdout.write(f'  ✓ Asignaciones eliminadas: {assignments_count}')

        # 2. Productos (esto eliminará automáticamente las relaciones M2M)
        Product.objects.all().delete()
        self.stdout.write(f'  ✓ Productos eliminados: {products_count}')

        # 3. Marcas
        ProductBrand.objects.all().delete()
        self.stdout.write(f'  ✓ Marcas eliminadas: {brands_count}')

        # 4. Variantes
        ProductVariant.objects.all().delete()
        self.stdout.write(f'  ✓ Variantes eliminadas: {variants_count}')

        self.stdout.write(self.style.SUCCESS('\n✓ Todos los productos, marcas y variantes han sido eliminados'))
