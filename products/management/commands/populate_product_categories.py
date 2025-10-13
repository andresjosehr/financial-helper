from django.core.management.base import BaseCommand
from products.models import ProductCategory


class Command(BaseCommand):
    help = 'Popula categorías de productos con datos iniciales'

    def handle(self, *args, **options):
        self.stdout.write('Creando categorías de productos...')

        categories_data = [
            # Categorías principales
            {'name': 'Alimentos y Bebidas', 'description': 'Productos alimenticios y bebidas'},
            {'name': 'Limpieza y Hogar', 'description': 'Productos de limpieza y artículos para el hogar'},
            {'name': 'Cuidado Personal', 'description': 'Productos de higiene y cuidado personal'},
            {'name': 'Farmacia y Salud', 'description': 'Medicamentos y productos de salud'},
            {'name': 'Mascotas', 'description': 'Productos para mascotas'},
            {'name': 'Tecnología', 'description': 'Productos tecnológicos y electrónicos'},
            {'name': 'Ropa y Calzado', 'description': 'Vestimenta y calzado'},
            {'name': 'Hogar y Decoración', 'description': 'Artículos para el hogar y decoración'},
            {'name': 'Deportes', 'description': 'Artículos deportivos y fitness'},
            {'name': 'Papelería', 'description': 'Artículos de oficina y papelería'},
        ]

        # Crear categorías principales
        main_categories = {}
        for cat_data in categories_data:
            category, created = ProductCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            main_categories[cat_data['name']] = category
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Creada: {category.name}'))
            else:
                self.stdout.write(f'  Ya existe: {category.name}')

        # Subcategorías de Alimentos y Bebidas
        food_subcategories = [
            'Lácteos y Huevos',
            'Carnes y Embutidos',
            'Pescados y Mariscos',
            'Frutas',
            'Verduras y Hortalizas',
            'Panadería y Repostería',
            'Granos y Cereales',
            'Pastas y Harinas',
            'Aceites y Condimentos',
            'Salsas y Aderezos',
            'Enlatados y Conservas',
            'Snacks y Dulces',
            'Bebidas sin Alcohol',
            'Bebidas Alcohólicas',
            'Café y Té',
            'Congelados',
        ]

        parent = main_categories['Alimentos y Bebidas']
        for subcat_name in food_subcategories:
            category, created = ProductCategory.objects.get_or_create(
                name=subcat_name,
                defaults={'parent': parent}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creada subcategoría: {category.name}'))

        # Subcategorías de Limpieza y Hogar
        cleaning_subcategories = [
            'Limpiadores',
            'Desinfectantes',
            'Detergentes',
            'Papel Higiénico',
            'Servilletas y Toallas',
            'Bolsas de Basura',
            'Desechables',
            'Insecticidas',
        ]

        parent = main_categories['Limpieza y Hogar']
        for subcat_name in cleaning_subcategories:
            category, created = ProductCategory.objects.get_or_create(
                name=subcat_name,
                defaults={'parent': parent}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creada subcategoría: {category.name}'))

        # Subcategorías de Cuidado Personal
        personal_care_subcategories = [
            'Jabones y Geles',
            'Shampoo y Acondicionador',
            'Cuidado Dental',
            'Desodorantes',
            'Cuidado Facial',
            'Cuidado Corporal',
            'Maquillaje',
            'Afeitado',
            'Cuidado del Cabello',
        ]

        parent = main_categories['Cuidado Personal']
        for subcat_name in personal_care_subcategories:
            category, created = ProductCategory.objects.get_or_create(
                name=subcat_name,
                defaults={'parent': parent}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creada subcategoría: {category.name}'))

        # Subcategorías de Farmacia y Salud
        pharmacy_subcategories = [
            'Medicamentos',
            'Vitaminas y Suplementos',
            'Primeros Auxilios',
            'Cuidado de Bebés',
            'Pañales',
            'Productos Femeninos',
        ]

        parent = main_categories['Farmacia y Salud']
        for subcat_name in pharmacy_subcategories:
            category, created = ProductCategory.objects.get_or_create(
                name=subcat_name,
                defaults={'parent': parent}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creada subcategoría: {category.name}'))

        # Subcategorías de Mascotas
        pet_subcategories = [
            'Alimento para Perros',
            'Alimento para Gatos',
            'Accesorios para Mascotas',
            'Higiene de Mascotas',
        ]

        parent = main_categories['Mascotas']
        for subcat_name in pet_subcategories:
            category, created = ProductCategory.objects.get_or_create(
                name=subcat_name,
                defaults={'parent': parent}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creada subcategoría: {category.name}'))

        total = ProductCategory.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Total de categorías en la base de datos: {total}'))
