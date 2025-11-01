# Financial Helper 💰

Sistema de gestión de compras personales y seguimiento de precios desarrollado en Django. Permite registrar y analizar compras detalladamente, realizar seguimiento de precios de productos, gestionar establecimientos comerciales y convertir montos entre VES y USD utilizando tasas de cambio del BCV y Binance.

## 📋 Descripción

Financial Helper es una aplicación web que ayuda a controlar gastos personales y hacer seguimiento de precios de productos en el tiempo. El sistema está diseñado para el mercado venezolano, pero puede adaptarse a otros contextos.

### Características Principales

- 🛒 **Gestión de Compras**: Registro completo de compras con metadata del documento (tipo, número, fecha, hora)
- 📦 **Control de Productos**: Sistema de productos con normalización de nombres, marcas, categorías y tipos de unidad
- 🏪 **Gestión de Establecimientos**: Base de datos de comercios con información completa (razón social, RIF, dirección, etc.)
- 💱 **Conversión de Monedas**: Almacenamiento de tasas BCV y Binance para cada compra, permitiendo análisis en VES y USD
- 📊 **Categorización Inteligente**: Sistema jerárquico de categorías con más de 900 subcategorías predefinidas
- 🔍 **Seguimiento de Precios**: Permite comparar precios de productos en el tiempo
- 💳 **Información de Pago**: Registro de métodos de pago, referencias bancarias, tarjetas utilizadas
- 📱 **Panel de Administración**: Interfaz completa de Django Admin para gestión de datos
- 🐳 **Dockerizado**: Configuración lista para desarrollo y producción con Docker Compose

## 🏗️ Arquitectura del Sistema

### Modelos de Datos

#### Establishments (Establecimientos)
Gestiona los comercios donde se realizan compras:
- Información legal (nombre comercial, razón social, RIF/NIT)
- Ubicación (dirección, ciudad, estado, código postal, país)
- Contacto (teléfono, email, sitio web)
- Timestamps de creación y actualización

#### Products (Productos)
Sistema de productos con normalización:
- **ProductCategory**: Categorías jerárquicas (padre-hijo)
- **Product**: Productos normalizados con:
  - Nombre normalizado
  - Marca (opcional)
  - Categoría
  - Tipo de unidad (kg, g, litros, ml, unidad)
  - Restricción de unicidad por nombre + marca + tipo de unidad

#### Purchases (Compras)
Registro completo de transacciones:
- **Purchase**: Compra completa con:
  - Usuario propietario
  - Establecimiento
  - Metadata del documento (tipo, número, fecha, hora)
  - Totales en VES (subtotal, descuento, total, impuestos)
  - Tasas de cambio (BCV y Binance) snapshot
  - Totales calculados en USD
  - Información fiscal (tipo de impuesto, porcentaje, base imponible)
  - Datos de pago (método, referencia, banco, últimos 4 dígitos)
  - Información adicional (cajero, vendedor, número de caja)
  - JSON original de la compra

- **PurchaseItem**: Items individuales de cada compra:
  - Referencia al producto normalizado (opcional)
  - Detalles del recibo (código, descripción, cantidad, unidad)
  - Precios en VES (unitario, descuento, impuesto, subtotal)
  - Precios calculados en USD (BCV y Binance)
  - Precio normalizado por unidad estándar (para comparación)

### Aplicaciones Django

```
config/              # Configuración principal del proyecto
├── settings.py      # Configuración de Django
├── urls.py          # Rutas principales
└── wsgi.py          # Punto de entrada WSGI

establishments/      # App de establecimientos comerciales
├── models.py        # Modelo Establishment
├── admin.py         # Configuración del admin
└── migrations/      # Migraciones de base de datos

products/           # App de productos y categorías
├── models.py       # ProductCategory, Product
├── admin.py        # Configuración del admin
├── management/     # Comandos personalizados
│   └── commands/
│       └── populate_product_categories.py  # Poblar 900+ categorías
└── migrations/

purchases/          # App de compras
├── models.py       # Purchase, PurchaseItem
├── admin.py        # Configuración del admin con inlines
└── migrations/
```

## 🛠️ Tecnologías Utilizadas

- **Backend**: Django 4.2+
- **Base de Datos**: MySQL 8.0
- **Servidor Web**: Gunicorn
- **Archivos Estáticos**: WhiteNoise
- **Contenedores**: Docker & Docker Compose
- **Lenguaje**: Python 3.11

### Dependencias Python

```
Django>=4.2,<5.0          # Framework web
mysqlclient>=2.2.0        # Conector MySQL
python-decouple>=3.8      # Manejo de variables de entorno
gunicorn>=21.2.0          # Servidor WSGI
whitenoise>=6.5.0         # Servir archivos estáticos
```

## 🚀 Instalación y Configuración

### Requisitos Previos

- Docker
- Docker Compose
- Git (opcional)

### Pasos de Instalación

1. **Clonar o descargar el proyecto**
```bash
cd /ruta/al/proyecto
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
```

Editar `.env` según tus necesidades (los valores por defecto funcionan para desarrollo):
```env
# Django Settings
SECRET_KEY=django-insecure-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DB_NAME=financial_helper
DB_USER=django_user
DB_PASSWORD=django_password
DB_HOST=db
DB_PORT=3306
DB_ROOT_PASSWORD=root_password

# Docker Ports
WEB_PORT=8000
```

3. **Iniciar los servicios con Docker**
```bash
docker-compose up -d
```

Esto iniciará:
- Contenedor `financial_helper_db`: MySQL 8.0
- Contenedor `financial_helper_web`: Django + Gunicorn

4. **Esperar a que la base de datos esté lista**

El servicio web tiene un healthcheck y esperará automáticamente a que MySQL esté disponible.

5. **Las migraciones se ejecutan automáticamente** al iniciar el contenedor web

6. **Crear un superusuario**
```bash
docker-compose exec web python manage.py createsuperuser
```

7. **Poblar categorías de productos (opcional pero recomendado)**
```bash
docker-compose exec web python manage.py populate_product_categories
```

Este comando crea 900+ categorías organizadas jerárquicamente:
- Alimentos y Bebidas
- Limpieza y Hogar
- Cuidado Personal
- Farmacia y Salud
- Mascotas
- Tecnología y Electrónica
- Ropa y Calzado
- Hogar y Decoración
- Deportes y Fitness
- Papelería y Oficina
- Ferretería y Construcción
- Automotriz
- Bebés y Niños
- Libros y Medios
- Juguetes y Entretenimiento
- Jardinería
- Otros

## 📱 Uso del Sistema

### Acceso a la Aplicación

- **Home (API Info)**: http://localhost:8000
- **Panel de Administración**: http://localhost:8000/admin
- **Base de Datos MySQL**: localhost:3306

### Panel de Administración

El sistema utiliza el Django Admin para gestión de datos. Accede con el superusuario creado:

1. **Establecimientos**: Gestiona comercios y tiendas
   - Filtros por país, estado, ciudad
   - Búsqueda por nombre, razón social, RIF, email

2. **Categorías de Productos**: Organiza productos en categorías jerárquicas
   - Filtros por categoría padre
   - Búsqueda por nombre y descripción

3. **Productos**: Catálogo de productos normalizados
   - Filtros por categoría, tipo de unidad, marca
   - Búsqueda por nombre, marca, descripción
   - Unicidad por nombre + marca + unidad

4. **Compras**: Registro de transacciones completas
   - Visualización inline de items
   - Filtros por fecha, usuario, establecimiento, tipo de documento, método de pago
   - Búsqueda por usuario, establecimiento, número de documento
   - Vista detallada con todos los items

5. **Items de Compra**: Productos individuales de cada compra
   - Filtros por tipo de unidad, producto
   - Búsqueda por descripción, código, usuario

## 🐳 Comandos Docker

### Gestión de Contenedores

```bash
# Iniciar servicios
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Ver logs solo del servicio web
docker-compose logs -f web

# Ver logs solo de la base de datos
docker-compose logs -f db

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (⚠️ elimina la base de datos)
docker-compose down -v

# Reiniciar servicios
docker-compose restart

# Reconstruir imágenes
docker-compose build --no-cache
```

### Comandos de Django

```bash
# Ejecutar migraciones
docker-compose exec web python manage.py migrate

# Crear migraciones
docker-compose exec web python manage.py makemigrations

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Poblar categorías de productos
docker-compose exec web python manage.py populate_product_categories

# Abrir shell de Django
docker-compose exec web python manage.py shell

# Ejecutar tests
docker-compose exec web python manage.py test

# Collectstatic (ya se ejecuta automáticamente)
docker-compose exec web python manage.py collectstatic --noinput

# Ver comandos disponibles
docker-compose exec web python manage.py help
```

### Comandos de Base de Datos

```bash
# Acceder a MySQL CLI
docker-compose exec db mysql -u django_user -p financial_helper
# Password: django_password (o el que hayas configurado)

# Acceder como root
docker-compose exec db mysql -u root -p
# Password: root_password (o el que hayas configurado)

# Backup de base de datos
docker-compose exec db mysqldump -u root -p financial_helper > backup.sql

# Restaurar base de datos
docker-compose exec -T db mysql -u root -p financial_helper < backup.sql
```

## 📁 Estructura del Proyecto

```
financial-helper/
├── config/                      # Configuración de Django
│   ├── __init__.py
│   ├── settings.py             # Configuración principal
│   ├── urls.py                 # Rutas URL
│   └── wsgi.py                 # Configuración WSGI
│
├── establishments/             # App de establecimientos
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py               # Admin de establecimientos
│   ├── apps.py
│   ├── models.py              # Modelo Establishment
│   ├── tests.py
│   └── views.py
│
├── products/                   # App de productos
│   ├── management/
│   │   └── commands/
│   │       └── populate_product_categories.py
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py               # Admin de productos y categorías
│   ├── apps.py
│   ├── models.py              # ProductCategory, Product
│   ├── tests.py
│   └── views.py
│
├── purchases/                  # App de compras
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py               # Admin de compras con inlines
│   ├── apps.py
│   ├── models.py              # Purchase, PurchaseItem
│   ├── tests.py
│   └── views.py
│
├── staticfiles/               # Archivos estáticos (generados)
│   └── admin/
│
├── apache/                    # Configuración Apache (si aplica)
├── venv/                      # Entorno virtual Python (local)
│
├── .env                       # Variables de entorno (no en repo)
├── .env.example              # Plantilla de variables de entorno
├── .gitignore                # Archivos ignorados por Git
├── docker-compose.yml        # Orquestación de contenedores
├── Dockerfile                # Imagen Docker de Django
├── manage.py                 # CLI de Django
├── requirements.txt          # Dependencias Python
├── sql.sql                   # Script SQL de referencia
├── image.png                 # Imagen del proyecto
├── financial-helper.andresjosehr.com.conf  # Config Nginx/Apache
└── README.md                 # Este archivo
```

## 🔒 Consideraciones de Seguridad

### Para Desarrollo

Los valores por defecto en `.env.example` son seguros para desarrollo local.

### Para Producción

⚠️ **IMPORTANTE**: Antes de desplegar en producción:

1. **Cambiar `SECRET_KEY`**:
   ```python
   # Generar una nueva con:
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

2. **Configurar `DEBUG=False`**:
   ```env
   DEBUG=False
   ```

3. **Actualizar `ALLOWED_HOSTS`**:
   ```env
   ALLOWED_HOSTS=tudominio.com,www.tudominio.com
   ```

4. **Cambiar contraseñas de base de datos**:
   ```env
   DB_PASSWORD=contraseña_segura_aleatoria
   DB_ROOT_PASSWORD=otra_contraseña_segura
   ```

5. **Configurar HTTPS** (usar Nginx como proxy reverso)

6. **Implementar backups automáticos** de la base de datos

7. **Limitar acceso al panel de administración** por IP si es posible

## 🗄️ Esquema de Base de Datos

El proyecto incluye un archivo `sql.sql` con la definición completa del esquema en SQL puro (para referencia). Las tablas se crean automáticamente mediante las migraciones de Django.

### Tablas Principales

- `establishments` - Establecimientos comerciales
- `product_categories` - Categorías de productos (jerárquicas)
- `products` - Productos normalizados
- `purchases` - Compras completas
- `purchase_items` - Items individuales de compras
- `auth_user` - Usuarios (tabla de Django)

### Índices Optimizados

El sistema incluye índices para optimizar consultas frecuentes:
- Búsqueda de establecimientos por nombre
- Búsqueda de productos por nombre y categoría
- Filtrado de compras por usuario y fecha
- Relaciones entre items y productos

## 🔄 Flujo de Trabajo Típico

1. **Usuario registra un establecimiento** (o lo selecciona si ya existe)
2. **Usuario crea una compra** con información del recibo:
   - Fecha, hora, tipo de documento
   - Totales en VES
   - Tasas de cambio actuales (BCV/Binance)
   - Método de pago
3. **Para cada item del recibo**:
   - Se registra la descripción original
   - Opcionalmente se vincula a un producto normalizado
   - Se calculan automáticamente precios en USD
   - Se normalizan precios por unidad
4. **El sistema almacena**:
   - Datos originales del recibo
   - Snapshot de tasas de cambio
   - Conversiones calculadas
5. **Permite análisis posterior**:
   - Evolución de precios en el tiempo
   - Comparación entre establecimientos
   - Análisis en VES y USD
   - Reportes de gastos

## 🌐 API y Extensibilidad

Actualmente el sistema usa Django Admin como interfaz. Para extender con una API REST:

1. Instalar Django REST Framework:
   ```bash
   pip install djangorestframework
   ```

2. Crear serializers y viewsets para cada modelo

3. Configurar rutas en `urls.py`

4. Habilitar autenticación con tokens o JWT

## 📊 Casos de Uso

- **Control de Gastos Personal**: Registro detallado de compras del hogar
- **Comparación de Precios**: Seguimiento de precios de productos en diferentes establecimientos
- **Análisis de Inflación**: Seguimiento de variación de precios en el tiempo
- **Control Presupuestario**: Análisis de gastos por categoría
- **Planificación de Compras**: Identificación de mejores momentos y lugares para comprar
- **Análisis en Dólares**: Evaluación del poder adquisitivo considerando el tipo de cambio

## 🤝 Contribuciones

Para contribuir al proyecto:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto es de uso personal. Consulta con el autor para usos comerciales.

## 👤 Autor

**Andrés José Hernández**
- Website: financial-helper.andresjosehr.com

## 🐛 Reporte de Errores

Si encuentras algún error o tienes sugerencias, por favor:
1. Verifica los logs: `docker-compose logs -f web`
2. Revisa la configuración en `.env`
3. Consulta la documentación de Django: https://docs.djangoproject.com/

## 📞 Soporte

Para preguntas o soporte técnico, contacta al administrador del sistema.

---

**¡Gracias por usar Financial Helper!** 💰✨
