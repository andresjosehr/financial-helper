from django.core.management.base import BaseCommand
from products.models import ProductCategory


class Command(BaseCommand):
    help = 'Popula categorías de productos con datos iniciales'

    def handle(self, *args, **options):
        # Limpiar TODAS las categorías existentes
        existing_count = ProductCategory.objects.count()
        if existing_count > 0:
            self.stdout.write(self.style.WARNING(f'🗑️  Eliminando {existing_count} categorías existentes...'))
            ProductCategory.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Categorías eliminadas'))
        
        self.stdout.write(self.style.WARNING('🚀 Creando categorías de productos...'))

        # Estructura de 2 NIVELES: Categorías principales genéricas con subcategorías descriptivas
        # NIVEL 1: Categorías amplias (15 principales)
        # NIVEL 2: Subcategorías genéricas pero NO tan específicas que parezcan productos
        
        categories_structure = {
            'Alimentos y Bebidas': [
                'Lácteos y Huevos',
                'Carnes y Embutidos',
                'Pescados y Mariscos',
                'Frutas y Verduras',
                'Panadería y Repostería',
                'Granos y Cereales',
                'Pastas y Harinas',
                'Aceites y Condimentos',
                'Salsas y Aderezos',
                'Enlatados y Conservas',
                'Snacks y Dulces',
                'Bebidas no Alcohólicas',
                'Bebidas Alcohólicas',
                'Café, Té e Infusiones',
                'Productos Congelados',
                'Productos Dietéticos',
            ],

            'Limpieza y Hogar': [
                'Productos de Limpieza',
                'Lavandería',
                'Lavado de Vajilla',
                'Papelería del Hogar',
                'Bolsas y Envoltorios',
                'Desechables',
                'Control de Plagas',
                'Utensilios de Limpieza',
                'Aromatizantes',
            ],

            'Cuidado Personal': [
                'Higiene Corporal',
                'Cuidado del Cabello',
                'Cuidado Dental',
                'Desodorantes',
                'Cuidado Facial',
                'Cuidado Corporal',
                'Maquillaje',
                'Afeitado y Depilación',
                'Fragancias',
                'Cuidado de Manos y Uñas',
            ],

            'Salud y Farmacia': [
                'Medicamentos',
                'Vitaminas y Suplementos',
                'Primeros Auxilios',
                'Cuidado del Bebé',
                'Higiene Femenina',
                'Salud Sexual',
                'Equipos Médicos',
            ],

            'Mascotas': [
                'Alimento para Perros',
                'Alimento para Gatos',
                'Alimento para Otras Mascotas',
                'Accesorios para Mascotas',
                'Higiene de Mascotas',
                'Salud Animal',
            ],

            'Tecnología y Electrónica': [
                'Computación',
                'Telefonía y Accesorios',
                'Fotografía y Video',
                'Audio y Video',
                'Gaming',
                'Componentes y Accesorios',
            ],

            'Ropa y Calzado': [
                'Ropa para Hombre',
                'Ropa para Mujer',
                'Ropa Infantil',
                'Calzado',
                'Accesorios de Moda',
            ],

            'Hogar y Muebles': [
                'Muebles',
                'Cocina y Comedor',
                'Electrodomésticos',
                'Textiles del Hogar',
                'Decoración',
                'Iluminación',
                'Organización y Almacenamiento',
            ],

            'Deportes y Fitness': [
                'Ropa Deportiva',
                'Calzado Deportivo',
                'Equipamiento Deportivo',
                'Nutrición Deportiva',
                'Outdoor y Camping',
                'Accesorios Deportivos',
            ],

            'Papelería y Oficina': [
                'Útiles de Escritura',
                'Papel y Cuadernos',
                'Organización de Oficina',
                'Adhesivos',
                'Instrumentos de Dibujo',
                'Material Escolar',
                'Equipos de Oficina',
            ],

            'Ferretería y Construcción': [
                'Herramientas Manuales',
                'Herramientas Eléctricas',
                'Materiales de Construcción',
                'Pintura y Acabados',
                'Fontanería',
                'Electricidad',
                'Elementos de Fijación',
                'Seguridad y Cerrajería',
            ],

            'Automotriz': [
                'Lubricantes y Fluidos',
                'Repuestos y Partes',
                'Accesorios para Vehículos',
                'Limpieza Automotriz',
                'Herramientas Automotrices',
            ],

            'Bebés y Niños': [
                'Alimentación Infantil',
                'Higiene del Bebé',
                'Ropa de Bebé',
                'Accesorios para Bebé',
                'Juguetes Infantiles',
            ],

            'Entretenimiento': [
                'Libros',
                'Revistas y Periódicos',
                'Cómics y Manga',
                'Contenido Digital',
                'Películas y Series',
                'Música',
                'Juguetes',
                'Juegos de Mesa',
            ],

            'Jardinería': [
                'Plantas y Semillas',
                'Herramientas de Jardín',
                'Tierra y Fertilizantes',
                'Macetas y Decoración',
            ],
        }

        # Crear categorías principales y subcategorías
        main_categories = {}
        total_created = 0

        for main_cat_name, subcategories in categories_structure.items():
            # Crear categoría principal
            category = ProductCategory.objects.create(
                name=main_cat_name,
                description=f'Productos de {main_cat_name.lower()}'
            )
            main_categories[main_cat_name] = category
            total_created += 1
            self.stdout.write(self.style.SUCCESS(f'✓ {main_cat_name}'))

            # Crear subcategorías
            for subcat_name in subcategories:
                ProductCategory.objects.create(
                    name=subcat_name,
                    parent=category
                )
                total_created += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ {subcat_name}'))

        total = ProductCategory.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Total de categorías creadas: {total_created}'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total de categorías en la base de datos: {total}'))
