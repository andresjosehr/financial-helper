"""
Management command para crear la categoría 'Sin Clasificar'.
"""
from django.core.management.base import BaseCommand
from products.models import ProductCategory


class Command(BaseCommand):
    help = 'Crea la categoría "Sin Clasificar" si no existe'

    def handle(self, *args, **options):
        category, created = ProductCategory.objects.get_or_create(
            name='Sin Clasificar',
            defaults={
                'description': 'Productos sin categoría asignada automáticamente'
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Categoría "Sin Clasificar" creada: {category.id}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Categoría "Sin Clasificar" ya existe: {category.id}')
            )
