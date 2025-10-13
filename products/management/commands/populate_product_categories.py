from django.core.management.base import BaseCommand
from products.models import ProductCategory


class Command(BaseCommand):
    help = 'Popula categorías de productos con datos iniciales'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚀 Creando categorías de productos...'))

        # Estructura: 'Categoría Principal': ['Subcategoría 1', 'Subcategoría 2', ...]
        categories_structure = {
            'Alimentos y Bebidas': [
                # Lácteos
                'Leche',
                'Yogurt',
                'Quesos',
                'Mantequilla y Margarina',
                'Crema de Leche',
                'Huevos',

                # Carnes
                'Carne de Res',
                'Carne de Cerdo',
                'Pollo',
                'Pavo',
                'Carnes Frías',
                'Embutidos',
                'Jamón',
                'Salchichas',
                'Tocineta',

                # Pescados y Mariscos
                'Pescado Fresco',
                'Pescado Congelado',
                'Mariscos',
                'Atún Enlatado',
                'Sardinas',

                # Frutas
                'Frutas Frescas',
                'Frutas Congeladas',
                'Frutas Enlatadas',
                'Frutas Secas',
                'Mermeladas y Jaleas',

                # Verduras
                'Verduras Frescas',
                'Verduras Congeladas',
                'Verduras Enlatadas',
                'Legumbres',
                'Ensaladas Preparadas',

                # Panadería
                'Pan',
                'Pan de Sandwich',
                'Pan Dulce',
                'Tortillas',
                'Galletas Saladas',
                'Galletas Dulces',
                'Pasteles y Tortas',
                'Donas',

                # Granos y Cereales
                'Arroz',
                'Avena',
                'Cereales para Desayuno',
                'Granola',
                'Quinoa',
                'Lentejas',
                'Frijoles',
                'Garbanzos',
                'Arvejas',

                # Pastas
                'Pasta Seca',
                'Pasta Fresca',
                'Fideos',
                'Harinas',
                'Premezclas',

                # Aceites y Grasas
                'Aceite Vegetal',
                'Aceite de Oliva',
                'Aceite de Girasol',
                'Aceite de Maíz',
                'Aceite en Spray',
                'Manteca',

                # Condimentos y Especias
                'Sal',
                'Azúcar',
                'Pimienta',
                'Especias',
                'Condimentos',
                'Ajo y Cebolla',
                'Cubitos y Caldos',
                'Vinagre',

                # Salsas
                'Salsa de Tomate',
                'Mayonesa',
                'Mostaza',
                'Ketchup',
                'Salsa Picante',
                'Salsa de Soya',
                'Salsa BBQ',
                'Aderezos',

                # Enlatados y Conservas
                'Vegetales Enlatados',
                'Sopas Enlatadas',
                'Frijoles Enlatados',
                'Tomate Enlatado',
                'Conservas',

                # Snacks
                'Papas Fritas',
                'Doritos y Similares',
                'Palomitas de Maíz',
                'Frutos Secos',
                'Semillas',
                'Barras Energéticas',
                'Pretzels',

                # Dulces y Chocolates
                'Chocolates',
                'Caramelos',
                'Chicles',
                'Gomitas',
                'Bombones',
                'Dulces',

                # Bebidas sin Alcohol
                'Agua',
                'Jugos',
                'Refrescos',
                'Bebidas Energéticas',
                'Bebidas Deportivas',
                'Té Frío',
                'Maltas',

                # Bebidas Alcohólicas
                'Cerveza',
                'Vino',
                'Ron',
                'Whisky',
                'Vodka',
                'Tequila',
                'Licores',

                # Café y Té
                'Café Molido',
                'Café Instantáneo',
                'Café en Grano',
                'Café Descafeinado',
                'Té',
                'Infusiones',

                # Productos de Repostería
                'Mezclas para Hornear',
                'Levadura',
                'Gelatina',
                'Pudines',
                'Coberturas',
                'Chispas de Chocolate',
                'Esencias',

                # Comida Preparada y Congelada
                'Pizzas Congeladas',
                'Lasañas',
                'Comidas Congeladas',
                'Empanadas',
                'Helados',
                'Postres Congelados',

                # Productos Orgánicos
                'Productos Orgánicos',
                'Alimentos Veganos',
                'Alimentos Sin Gluten',
                'Alimentos Dietéticos',
            ],

            'Limpieza y Hogar': [
                # Limpieza General
                'Desinfectantes',
                'Limpiadores Multiusos',
                'Limpiadores de Pisos',
                'Limpiadores de Baño',
                'Limpiadores de Cocina',
                'Limpiadores de Vidrios',
                'Limpiadores de Muebles',
                'Cera para Pisos',
                'Lustramuebles',

                # Lavado de Ropa
                'Detergente en Polvo',
                'Detergente Líquido',
                'Detergente en Cápsulas',
                'Suavizante de Telas',
                'Blanqueador',
                'Quitamanchas',
                'Jabón de Lavar',

                # Lavado de Platos
                'Lavaloza Líquido',
                'Detergente para Lavavajillas',
                'Esponjas',
                'Estropajos',
                'Guantes de Limpieza',

                # Papel
                'Papel Higiénico',
                'Papel Toalla',
                'Servilletas',
                'Pañuelos Desechables',

                # Bolsas
                'Bolsas de Basura',
                'Bolsas Plásticas',
                'Bolsas para Congelar',
                'Papel Aluminio',
                'Papel Film',

                # Desechables
                'Platos Desechables',
                'Vasos Desechables',
                'Cubiertos Desechables',
                'Envases Desechables',

                # Control de Plagas
                'Insecticidas',
                'Raticidas',
                'Repelentes',
                'Trampas',

                # Accesorios de Limpieza
                'Escobas',
                'Trapeadores',
                'Cepillos',
                'Paños de Limpieza',
                'Baldes',
                'Recogedores',

                # Aromatizantes
                'Ambientadores',
                'Velas Aromáticas',
                'Inciensos',
                'Desodorantes de Ambiente',
            ],

            'Cuidado Personal': [
                # Higiene Corporal
                'Jabón de Tocador',
                'Jabón Líquido',
                'Gel de Ducha',
                'Esponjas de Baño',

                # Cuidado del Cabello
                'Shampoo',
                'Acondicionador',
                'Tratamientos Capilares',
                'Mascarillas para Cabello',
                'Tintes',
                'Decolorantes',
                'Gel para Cabello',
                'Spray para Cabello',
                'Ceras y Pomadas',

                # Cuidado Dental
                'Pasta Dental',
                'Cepillos de Dientes',
                'Hilo Dental',
                'Enjuague Bucal',
                'Blanqueadores Dentales',

                # Desodorantes
                'Desodorante en Barra',
                'Desodorante en Aerosol',
                'Desodorante Roll-On',
                'Antitranspirantes',

                # Cuidado Facial
                'Limpiadores Faciales',
                'Exfoliantes',
                'Tónicos',
                'Cremas Faciales',
                'Cremas Antiarrugas',
                'Cremas para Ojos',
                'Mascarillas Faciales',
                'Protector Solar Facial',

                # Cuidado Corporal
                'Cremas Corporales',
                'Lociones Corporales',
                'Aceites Corporales',
                'Exfoliantes Corporales',
                'Protector Solar Corporal',

                # Maquillaje
                'Base de Maquillaje',
                'Polvo Compacto',
                'Rubor',
                'Corrector',
                'Sombras',
                'Delineadores',
                'Máscaras de Pestañas',
                'Labiales',
                'Brillo Labial',
                'Desmaquillantes',

                # Afeitado y Depilación
                'Rastrillos',
                'Máquinas de Afeitar',
                'Espuma de Afeitar',
                'Gel de Afeitar',
                'Loción Aftershave',
                'Cera Depilatoria',
                'Cremas Depilatorias',

                # Fragancias
                'Perfumes',
                'Colonias',
                'Splash',

                # Cuidado de Manos y Pies
                'Cremas para Manos',
                'Cremas para Pies',
                'Esmaltes de Uñas',
                'Removedor de Esmalte',
                'Tratamientos para Uñas',

                # Accesorios
                'Algodón',
                'Hisopos',
                'Toallas Húmedas',
                'Pañuelos Faciales',
            ],

            'Farmacia y Salud': [
                # Medicamentos
                'Analgésicos',
                'Antiinflamatorios',
                'Antigripales',
                'Antiácidos',
                'Laxantes',
                'Antidiarreicos',
                'Antihistamínicos',
                'Antitusivos',
                'Antibióticos',
                'Pomadas y Ungüentos',

                # Vitaminas
                'Vitamina C',
                'Vitamina D',
                'Vitamina E',
                'Complejo B',
                'Multivitamínicos',

                # Suplementos
                'Suplementos Proteicos',
                'Omega 3',
                'Calcio',
                'Hierro',
                'Zinc',
                'Magnesio',

                # Primeros Auxilios
                'Vendas',
                'Gasas',
                'Curitas',
                'Alcohol',
                'Agua Oxigenada',
                'Algodón',
                'Tijeras',
                'Termómetros',

                # Cuidado de Bebés
                'Biberones',
                'Chupones',
                'Leche de Fórmula',
                'Papillas',
                'Cremas para Bebé',
                'Talco',
                'Aceite para Bebé',
                'Toallitas Húmedas',

                # Pañales
                'Pañales Desechables',
                'Pañales de Tela',
                'Pañitos Húmedos',

                # Productos Femeninos
                'Toallas Sanitarias',
                'Tampones',
                'Copas Menstruales',
                'Protectores Diarios',

                # Salud Sexual
                'Preservativos',
                'Lubricantes',
                'Pruebas de Embarazo',

                # Equipos Médicos
                'Tensiómetros',
                'Glucómetros',
                'Nebulizadores',
                'Oxímetros',
            ],

            'Mascotas': [
                # Perros
                'Alimento Seco para Perros',
                'Alimento Húmedo para Perros',
                'Snacks para Perros',
                'Huesos y Juguetes',
                'Correas y Collares',
                'Camas para Perros',
                'Ropa para Perros',

                # Gatos
                'Alimento Seco para Gatos',
                'Alimento Húmedo para Gatos',
                'Snacks para Gatos',
                'Arena para Gatos',
                'Juguetes para Gatos',
                'Rascadores',

                # Aves
                'Alimento para Aves',
                'Jaulas',

                # Peces
                'Alimento para Peces',
                'Acuarios',

                # Otros Animales
                'Alimento para Roedores',
                'Alimento para Reptiles',

                # Higiene
                'Shampoo para Mascotas',
                'Cepillos',
                'Cortauñas',
                'Desparasitantes',
                'Antipulgas',

                # Salud Animal
                'Vitaminas para Mascotas',
                'Suplementos para Mascotas',
            ],

            'Tecnología y Electrónica': [
                # Computación
                'Laptops',
                'Computadoras de Escritorio',
                'Tablets',
                'Monitores',
                'Teclados',
                'Ratones',
                'Webcams',
                'Audífonos',
                'Bocinas',
                'Impresoras',
                'Escáneres',
                'Discos Duros',
                'Memorias USB',
                'Tarjetas de Memoria',

                # Telefonía
                'Celulares',
                'Teléfonos Fijos',
                'Fundas para Celular',
                'Protectores de Pantalla',
                'Cargadores',
                'Cables',
                'Audífonos Bluetooth',

                # Fotografía
                'Cámaras Digitales',
                'Cámaras de Video',
                'Lentes',
                'Trípodes',
                'Memorias para Cámara',

                # Audio y Video
                'Televisores',
                'Reproductores de DVD',
                'Sistemas de Sonido',
                'Barras de Sonido',
                'Equipos de Música',

                # Gaming
                'Consolas de Videojuegos',
                'Videojuegos',
                'Controles',
                'Auriculares Gaming',

                # Accesorios
                'Pilas',
                'Baterías Recargables',
                'Adaptadores',
                'Extensiones',
                'Reguladores de Voltaje',
            ],

            'Ropa y Calzado': [
                # Ropa de Hombre
                'Camisas',
                'Camisetas',
                'Pantalones',
                'Jeans',
                'Shorts',
                'Trajes',
                'Ropa Interior Hombre',
                'Calcetines Hombre',
                'Pijamas Hombre',
                'Ropa Deportiva Hombre',

                # Ropa de Mujer
                'Blusas',
                'Vestidos',
                'Faldas',
                'Pantalones Mujer',
                'Jeans Mujer',
                'Ropa Interior Mujer',
                'Medias y Calcetines',
                'Pijamas Mujer',
                'Ropa Deportiva Mujer',
                'Trajes de Baño',

                # Ropa Infantil
                'Ropa para Bebés',
                'Ropa para Niños',
                'Ropa para Niñas',
                'Uniformes Escolares',

                # Calzado
                'Zapatos Formales',
                'Zapatos Casuales',
                'Tenis',
                'Sandalias',
                'Botas',
                'Pantuflas',
                'Zapatos Deportivos',

                # Accesorios
                'Cinturones',
                'Corbatas',
                'Carteras',
                'Bolsos',
                'Mochilas',
                'Gorras',
                'Sombreros',
                'Bufandas',
                'Guantes',
                'Lentes de Sol',
                'Relojes',
                'Joyas',
                'Bisutería',
            ],

            'Hogar y Decoración': [
                # Muebles
                'Sofás',
                'Sillas',
                'Mesas',
                'Camas',
                'Colchones',
                'Armarios',
                'Estanterías',
                'Escritorios',

                # Cocina
                'Ollas y Sartenes',
                'Utensilios de Cocina',
                'Cuchillos',
                'Tablas de Cortar',
                'Vajillas',
                'Cubiertos',
                'Vasos y Copas',
                'Tazas',
                'Termos',
                'Recipientes',
                'Electrodomésticos Menores',

                # Electrodomésticos
                'Refrigeradores',
                'Cocinas',
                'Hornos',
                'Microondas',
                'Licuadoras',
                'Batidoras',
                'Cafeteras',
                'Tostadoras',
                'Planchas',
                'Aspiradoras',
                'Lavadoras',
                'Secadoras',
                'Ventiladores',
                'Aire Acondicionado',
                'Calentadores',

                # Textiles
                'Sábanas',
                'Cobijas',
                'Edredones',
                'Almohadas',
                'Toallas',
                'Cortinas',
                'Manteles',
                'Cojines',
                'Alfombras',

                # Decoración
                'Cuadros',
                'Espejos',
                'Floreros',
                'Velas Decorativas',
                'Plantas Artificiales',
                'Adornos',

                # Iluminación
                'Lámparas',
                'Focos',
                'Bombillos LED',
                'Linternas',

                # Organización
                'Cestas',
                'Cajas Organizadoras',
                'Ganchos',
                'Percheros',
            ],

            'Deportes y Fitness': [
                # Ropa Deportiva
                'Camisetas Deportivas',
                'Shorts Deportivos',
                'Pantalones Deportivos',
                'Ropa de Yoga',
                'Ropa de Gimnasio',

                # Calzado Deportivo
                'Zapatos para Correr',
                'Zapatos de Fútbol',
                'Zapatos de Basketball',
                'Zapatos de Tenis',

                # Equipamiento
                'Balones',
                'Raquetas',
                'Pesas',
                'Mancuernas',
                'Bandas Elásticas',
                'Colchonetas',
                'Bicicletas',
                'Patines',
                'Skateboards',

                # Fitness
                'Suplementos Deportivos',
                'Proteínas',
                'Pre-Entreno',
                'Shakers',

                # Camping
                'Carpas',
                'Sacos de Dormir',
                'Termos',
                'Linternas',
                'Navajas',

                # Accesorios
                'Guantes Deportivos',
                'Rodilleras',
                'Coderas',
                'Botellas de Agua',
                'Mochilas Deportivas',
                'Relojes Deportivos',
            ],

            'Papelería y Oficina': [
                # Escritura
                'Bolígrafos',
                'Lápices',
                'Marcadores',
                'Resaltadores',
                'Plumas',
                'Correctores',

                # Papel
                'Cuadernos',
                'Libretas',
                'Blocks',
                'Hojas Blancas',
                'Papel Bond',
                'Cartulinas',
                'Papel de Colores',

                # Organización
                'Carpetas',
                'Archivadores',
                'Separadores',
                'Clips',
                'Grapas',
                'Chinches',
                'Ligas',

                # Adhesivos
                'Pegamentos',
                'Cintas Adhesivas',
                'Silicón',

                # Instrumentos
                'Tijeras',
                'Reglas',
                'Escuadras',
                'Compases',
                'Calculadoras',

                # Material Escolar
                'Mochilas Escolares',
                'Loncheras',
                'Colores',
                'Crayones',
                'Acuarelas',
                'Pinceles',
                'Plastilina',

                # Oficina
                'Grapadoras',
                'Perforadoras',
                'Engrapadoras',
                'Sellos',
                'Tintas',
            ],

            'Ferretería y Construcción': [
                # Herramientas Manuales
                'Martillos',
                'Destornilladores',
                'Llaves',
                'Alicates',
                'Pinzas',
                'Sierras',
                'Limas',
                'Cinceles',

                # Herramientas Eléctricas
                'Taladros',
                'Pulidoras',
                'Sierras Eléctricas',
                'Lijadoras',

                # Materiales de Construcción
                'Cemento',
                'Arena',
                'Grava',
                'Ladrillos',
                'Bloques',
                'Varillas',
                'Alambre',

                # Pintura
                'Pinturas',
                'Brochas',
                'Rodillos',
                'Solventes',
                'Selladores',

                # Fontanería
                'Tuberías',
                'Llaves de Agua',
                'Conexiones',
                'Pegamento PVC',

                # Electricidad
                'Cables',
                'Tomas',
                'Interruptores',
                'Focos',
                'Extensiones',

                # Fijación
                'Tornillos',
                'Clavos',
                'Tuercas',
                'Arandelas',
                'Tarugos',

                # Seguridad
                'Candados',
                'Cerraduras',
                'Cadenas',
                'Bisagras',
            ],

            'Automotriz': [
                # Lubricantes
                'Aceite de Motor',
                'Aceite de Transmisión',
                'Líquido de Frenos',
                'Refrigerante',
                'Líquido Limpiaparabrisas',

                # Partes
                'Filtros de Aceite',
                'Filtros de Aire',
                'Bujías',
                'Baterías',
                'Llantas',
                'Limpiaparabrisas',

                # Accesorios
                'Fundas para Asientos',
                'Alfombras',
                'Ambientadores',
                'Cargadores',

                # Limpieza
                'Shampoo para Auto',
                'Ceras',
                'Limpiadores',
                'Esponjas',

                # Herramientas
                'Gatos Hidráulicos',
                'Llaves',
                'Infladores',
            ],

            'Bebés y Niños': [
                # Alimentación
                'Biberones',
                'Teteros',
                'Chupones',
                'Leche de Fórmula',
                'Papillas',
                'Cereales Infantiles',

                # Higiene
                'Pañales',
                'Toallitas Húmedas',
                'Cremas',
                'Talcos',
                'Aceites',
                'Shampoo para Bebé',
                'Jabón para Bebé',

                # Ropa
                'Bodys',
                'Pijamas',
                'Baberos',
                'Mitones',
                'Gorros',

                # Accesorios
                'Coches',
                'Sillas de Auto',
                'Cunas',
                'Andaderas',
                'Corrales',

                # Juguetes
                'Sonajeros',
                'Peluches',
                'Juguetes Didácticos',
                'Libros para Bebés',
            ],

            'Libros y Medios': [
                'Libros',
                'Revistas',
                'Periódicos',
                'Cómics',
                'Manga',
                'E-books',
                'Audiolibros',
                'Películas DVD',
                'Películas Blu-ray',
                'Música CD',
                'Vinilos',
            ],

            'Juguetes y Entretenimiento': [
                'Juguetes para Bebés',
                'Muñecas',
                'Figuras de Acción',
                'Carros de Juguete',
                'Legos',
                'Rompecabezas',
                'Juegos de Mesa',
                'Juegos de Cartas',
                'Peluches',
                'Juguetes Educativos',
                'Juguetes Electrónicos',
                'Instrumentos Musicales de Juguete',
            ],

            'Jardinería': [
                # Plantas
                'Plantas Naturales',
                'Plantas Artificiales',
                'Semillas',
                'Bulbos',

                # Herramientas
                'Palas',
                'Rastrillos',
                'Tijeras de Podar',
                'Regaderas',
                'Mangueras',

                # Insumos
                'Tierra',
                'Abonos',
                'Fertilizantes',
                'Insecticidas para Plantas',

                # Macetas y Decoración
                'Macetas',
                'Maceteros',
                'Jarrones',
                'Piedras Decorativas',
            ],

            'Otros': [
                'Artículos Varios',
                'Productos Especiales',
                'Servicios',
            ],
        }

        # Crear categorías principales y subcategorías
        main_categories = {}
        total_created = 0

        for main_cat_name, subcategories in categories_structure.items():
            # Crear categoría principal
            category, created = ProductCategory.objects.get_or_create(
                name=main_cat_name,
                defaults={'description': f'Productos de {main_cat_name.lower()}'}
            )
            main_categories[main_cat_name] = category

            if created:
                total_created += 1
                self.stdout.write(self.style.SUCCESS(f'✓ {main_cat_name}'))
            else:
                self.stdout.write(f'  {main_cat_name} (ya existe)')

            # Crear subcategorías
            for subcat_name in subcategories:
                subcat, created = ProductCategory.objects.get_or_create(
                    name=subcat_name,
                    defaults={'parent': category}
                )
                if created:
                    total_created += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {subcat_name}'))

        total = ProductCategory.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Categorías creadas en esta ejecución: {total_created}'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total de categorías en la base de datos: {total}'))
