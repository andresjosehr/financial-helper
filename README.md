# Financial Helper 💰

Sistema integral de gestión de compras personales y análisis de tasas de cambio desarrollado en Django. Diseñado para el mercado venezolano, combina tracking de gastos en VES/USD con monitoreo en tiempo real de tasas de cambio BCV y Binance P2P.

## 📋 Descripción

Financial Helper es una plataforma web completa para:
- **Control de gastos** con doble valoración (VES y USD según BCV/Binance)
- **Monitoreo de tasas de cambio** con actualización automática y análisis estadístico
- **Dashboard financiero interactivo** con gráficos en tiempo real
- **Procesamiento OCR** de facturas con pipeline de 7 pasos
- **Normalización de productos** con 900+ categorías jerárquicas

### 🎯 Características Principales

**📊 Sistema de Tasas de Cambio (Exchange Rates)**
- **Actualización automática**: Binance P2P cada 15 min, BCV cada hora
- **Limpieza de outliers**: Método IQR (Interquartile Range) para precisión estadística
- **Snapshots históricos**: Almacenamiento con timestamp exacto para análisis temporal
- **Dashboard interactivo** con 5 gráficos:
  - Spread porcentual con bandas estadísticas (MIN, AVG, P75, MAX)
  - Tasa BCV oficial (área chart con zoom 7 días)
  - Tasa Binance P2P (área chart con zoom 24 horas)
  - Volatilidad diaria (histograma de cambios %)
  - Distribución de spread (histograma de frecuencias)
- **Calculadora bidireccional** BCV ↔ Binance en tiempo real
- **API REST**: Consulta de tasas históricas con parámetros de fecha

**🛒 Gestión de Compras**
- **Doble valoración**: Cada compra se guarda en VES, USD-BCV y USD-Binance
- **Snapshots de tasas**: Las tasas se congelan al momento de la compra (análisis histórico inmutable)
- **Metadata completa**: Fecha, hora, tipo de documento, métodos de pago, impuestos
- **Items detallados**: Cantidad, unidad, precio unitario en 3 monedas
- **Admin inline**: Edición eficiente con todos los items en una pantalla

**📦 Productos y Categorías**
- **900+ categorías** predefinidas (Alimentos, Limpieza, Cuidado Personal, Tecnología, etc.)
- **Sistema jerárquico** parent-child para organización flexible
- **Marcas y variantes**: Talla, sabor, color, material, versión, empaque
- **Normalización**: Mapeo de descripciones crudas a productos estandarizados
- **API de filtrado**: Búsqueda por lista de categorías

**🖼️ Procesamiento OCR de Facturas**
- **Pipeline de 7 pasos**: Filtros, detección de documento, limpieza, contraste, umbralización
- **3 algoritmos de detección**: Canny edges, Otsu threshold, análisis de brillo
- **Preprocesamiento agresivo**: Mediana, bilateral, CLAHE, morfología
- **Parámetros ajustables**: Página de tuning para optimización
- **Salida flexible**: Base64 JSON o binario PNG

**🏪 Establecimientos**
- Información legal: RIF/NIT, razón social, nombre comercial
- Ubicación completa: Dirección, ciudad, estado, código postal, país
- Contacto: Teléfono, email, sitio web

**🔐 Backup Automatizado**
- **API endpoint**: `POST /api/backup/download/` con autenticación Bearer
- **Compresión**: gzip nivel 9 (~100KB típico)
- **Contenido completo**: DROP/CREATE + INSERT de todas las tablas
- **Descarga directa**: Un comando curl genera backup con timestamp

## 🏗️ Arquitectura del Sistema

### 6 Aplicaciones Django

**1. exchange_rates/** - Sistema de tasas de cambio (⭐ Core)
- **Modelo**: `ExchangeRate` (source, rate, date, timestamp, notes)
- **Sources**: BCV, BINANCE_BUY, BINANCE_SELL
- **Comandos**: `update_binance_rates`, `fetch_bcv_rate`
- **API**: `GET /api/exchange-rates/bcv/?days=7&end_date=2025-11-25`
- **Vista**: Dashboard interactivo con TradingView Lightweight Charts
- **Métodos del modelo**: `get_rate()`, `convert_ves_to_usd()`, `get_latest_rates()`

**2. purchases/** - Tracking de compras
- **Purchase**: Compra completa con snapshots de tasas (bcv_rate, binance_rate)
- **PurchaseItem**: Items individuales con precios en VES, USD-BCV, USD-Binance
- **Admin**: TabularInline para edición eficiente
- **Cálculos automáticos**: total_usd_bcv, total_usd_binance, unit_price_*

**3. products/** - Catálogo normalizado
- **ProductCategory**: Jerárquico con parent-child
- **ProductBrand**: Marcas únicas
- **Product**: Productos normalizados (nombre único)
- **ProductVariant**: Variantes (size, flavor, color, material, version, package)
- **ProductVariantAssignment**: Tabla M2M
- **Comandos**: `populate_product_categories`, `populate_common_products`
- **API**: `POST /api/products/by-categories/` (filtrado por categorías)

**4. image_processor/** - OCR de facturas
- **Pipeline**: 7 pasos (preprocessing → detección → limpieza → contraste → threshold)
- **Detección**: 3 algoritmos paralelos (Canny, Otsu, brillo)
- **API**: `POST /api/process-invoice/`, `POST /api/process-with-params/`
- **Tuning**: `/image-processor/tuning/` para ajuste de parámetros

**5. establishments/** - Establecimientos comerciales
- **Modelo**: `Establishment` (legal, ubicación, contacto)
- FK opcional en Purchase

**6. users/** - Sistema de usuarios
- Extiende User estándar de Django
- FK en Purchase (owner)

### Diseño Clave: Snapshots de Tasas

```python
# Cada Purchase guarda las tasas del momento
purchase.bcv_rate = Decimal('50.12')
purchase.binance_rate = Decimal('51.45')

# Permite análisis histórico sin depender de tasas actuales
purchase.total_usd_bcv = purchase.total_ves / purchase.bcv_rate
purchase.total_usd_binance = purchase.total_ves / purchase.binance_rate
```

### Relaciones de Base de Datos

```
User (Django auth)
  └─> Purchase
       ├─> Establishment (opcional FK)
       ├─> bcv_rate, binance_rate (snapshots Decimal)
       └─> PurchaseItem[]
            └─> Product (opcional FK)
                 ├─> ProductCategory (jerárquico)
                 ├─> ProductBrand
                 └─> ProductVariant[] (M2M)

ExchangeRate (histórico)
  └─> source (BCV/BINANCE_BUY/BINANCE_SELL)
  └─> timestamp (único con source)
```

## 🛠️ Stack Tecnológico

**Backend**
- Django 5.2.7 (Python 3.11)
- MySQL 8.0 (charset: utf8mb4)
- Gunicorn (WSGI server)
- WhiteNoise (static files)

**Frontend**
- Alpine.js 3.x (reactividad)
- TailwindCSS (estilos)
- TradingView Lightweight Charts (gráficos financieros)

**Procesamiento**
- OpenCV (cv2) - Detección y filtros de imagen
- Pillow (PIL) - Manipulación de imágenes
- NumPy - Operaciones matriciales
- Playwright - Web scraping BCV (fallback)
- BeautifulSoup4 - HTML parsing

**Infraestructura**
- Docker & Docker Compose
- python-decouple (env vars)

**Dependencias clave**
```txt
Django==5.2.7
mysqlclient>=2.2.0
opencv-python>=4.8.0
pillow>=10.0.0
numpy>=1.24.0
playwright>=1.40.0
beautifulsoup4>=4.12.0
```

## 🚀 Quick Start

### 1. Configurar entorno
```bash
cp .env.example .env
# Editar .env si es necesario (valores por defecto OK para desarrollo)
```

### 2. Levantar servicios
```bash
docker-compose up -d
# Esperar ~30s para healthcheck de MySQL
```

### 3. Crear superusuario
```bash
docker-compose exec web python manage.py createsuperuser
```

### 4. Poblar categorías (opcional)
```bash
docker-compose exec web python manage.py populate_product_categories
# Crea 900+ categorías en ~2 segundos
```

### 5. Acceder
- **Dashboard**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **Tuning OCR**: http://localhost:8000/image-processor/tuning/

## 📱 Uso del Sistema

### Dashboard de Tasas de Cambio (/)

**Métricas en tiempo real**:
- Tasa BCV actual y Binance P2P
- Calculadora bidireccional (conversión BCV ↔ Binance)
- Indicador de spread con bandas históricas

**5 Gráficos interactivos** (TradingView Lightweight Charts):
1. **Spread Porcentual**: Línea púrpura + bandas (MIN/AVG/P75/MAX)
2. **Tasa BCV**: Área azul (zoom 7 días)
3. **Tasa Binance P2P**: Área naranja (zoom 24 horas)
4. **Volatilidad**: Histograma verde/rojo de cambios diarios
5. **Distribución**: Histograma de frecuencia de spreads

**Funcionalidades**:
- Auto-refresh cada 5 minutos
- Tooltips interactivos con timestamp
- Zoom y navegación en gráficos
- Cálculos estadísticos en cliente (percentiles, IQR)

### Panel de Administración (/admin)

**Compras** (vista principal):
- Inline editing de PurchaseItems (todos los items en una pantalla)
- Filtros: fecha, usuario, establecimiento, método de pago
- Muestra totales en VES, USD-BCV y USD-Binance

**Productos**:
- Gestión de categorías jerárquicas
- Marcas y variantes (talla, sabor, color, etc.)
- Normalización de descripciones crudas

**Establecimientos**:
- CRUD básico con filtros geográficos
- Información legal y contacto

**Tasas de Cambio** (ExchangeRate):
- Historial completo con timestamp
- Filtros por source (BCV/BINANCE_BUY/BINANCE_SELL)
- Solo lectura (se actualiza con comandos)

## 🔧 Comandos Principales

### Tasas de Cambio (recomendado automatizar con cron)

```bash
# Actualizar Binance P2P (cada 15 minutos recomendado)
docker-compose exec web python manage.py update_binance_rates

# Actualizar BCV (cada hora recomendado)
docker-compose exec web python manage.py fetch_bcv_rate
docker-compose exec web python manage.py fetch_bcv_rate --force  # Forzar guardado
docker-compose exec web python manage.py fetch_bcv_rate --test-rate 50.12  # Testing
```

### Productos

```bash
# Poblar 900+ categorías (una vez)
docker-compose exec web python manage.py populate_product_categories

# Poblar productos comunes (opcional)
docker-compose exec web python manage.py populate_common_products

# Productos de prueba
docker-compose exec web python manage.py populate_test_products

# Limpiar productos
docker-compose exec web python manage.py delete_all_products
```

### Backup y Restauración

```bash
# Backup via API (recomendado)
curl -X POST "http://localhost:8000/api/backup/download/" \
  -H "Authorization: Bearer financial-helper-backup-secret-2024" \
  --output backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Producción
curl -X POST "https://financial-helper.andresjosehr.com/api/backup/download/" \
  -H "Authorization: Bearer financial-helper-backup-secret-2024" \
  --output backup.sql.gz

# Restaurar
gunzip -c backup.sql.gz | docker-compose exec -T db mysql -u root -p financial_helper
```

### Django Básico

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py test
```

### Docker

```bash
docker-compose up -d          # Iniciar
docker-compose logs -f web    # Ver logs
docker-compose down           # Detener
docker-compose restart        # Reiniciar
```

## 📁 Estructura del Proyecto

```
financial-helper/
├── config/                    # Configuración Django
│   ├── settings.py           # Django settings + env vars
│   ├── urls.py               # Rutas principales
│   └── backup_views.py       # Endpoint de backup
│
├── exchange_rates/           # ⭐ Sistema de tasas de cambio
│   ├── models.py             # ExchangeRate (BCV/BINANCE)
│   ├── views.py              # API + Dashboard
│   ├── management/commands/
│   │   ├── update_binance_rates.py  # Actualización automática
│   │   └── fetch_bcv_rate.py        # Scraping BCV
│   └── templates/exchange_rates/
│       └── chart.html        # Dashboard con 5 gráficos
│
├── purchases/                # Tracking de compras
│   ├── models.py             # Purchase (con snapshots), PurchaseItem
│   └── admin.py              # Inline editing
│
├── products/                 # Catálogo normalizado
│   ├── models.py             # Category, Brand, Product, Variant
│   ├── views.py              # API de filtrado
│   └── management/commands/
│       ├── populate_product_categories.py  # 900+ categorías
│       └── populate_common_products.py
│
├── image_processor/          # OCR de facturas
│   ├── views.py              # Pipeline de 7 pasos
│   └── templates/            # test.html, tuning.html
│
├── establishments/           # Establecimientos
│   └── models.py             # Establishment
│
├── users/                    # Usuarios (estructura vacía)
│
├── docker-compose.yml        # Orquestación (web + db)
├── Dockerfile                # Python 3.11 + deps
├── requirements.txt          # Django, OpenCV, Playwright, etc.
├── .env.example              # Variables de entorno
└── README.md                 # Este archivo
```

## 🔧 API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Dashboard principal (gráficos tasas) |
| `/admin/` | GET | Panel de administración Django |
| `/api/status/` | GET | Status del API (JSON) |
| `/api/exchange-rates/bcv/` | GET/POST | Tasas BCV y Binance históricos |
| `/api/products/by-categories/` | POST | Filtrar productos por categorías |
| `/api/process-invoice/` | POST | Procesar factura (OCR óptimo) |
| `/api/process-with-params/` | POST | Procesar factura (params custom) |
| `/api/backup/download/` | POST | Descargar backup MySQL (.sql.gz) |
| `/image-processor/test/` | GET | Página de prueba OCR |
| `/image-processor/tuning/` | GET | Ajuste de parámetros OCR |

**Ejemplo**: Obtener tasas de los últimos 30 días
```bash
curl "http://localhost:8000/api/exchange-rates/bcv/?days=30&end_date=2025-11-25"
```

**Respuesta**:
```json
{
  "start_date": "2025-10-26",
  "end_date": "2025-11-25",
  "days": 30,
  "bcv": [{"date": "2025-11-25", "rate": 50.12}],
  "binance_sell": [{"timestamp": "2025-11-25T14:30:00Z", "rate": 51.45}]
}
```

## 🔒 Producción

⚠️ **Antes de desplegar**:

```env
# .env producción
SECRET_KEY=<generar-con-get_random_secret_key>
DEBUG=False
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
DB_PASSWORD=<contraseña-fuerte-aleatoria>

# Cambiar token de backup en config/backup_views.py
HARDCODED_TOKEN = '<nuevo-token-seguro>'
```

**Automatización de tasas** (crontab del servidor):
```cron
*/15 * * * * docker-compose exec -T web python manage.py update_binance_rates
0 * * * * docker-compose exec -T web python manage.py fetch_bcv_rate
```

## 🎯 Casos de Uso

- **Trading de divisas**: Dashboard en tiempo real con bandas estadísticas para identificar oportunidades
- **Control de gastos**: Doble valoración (VES oficial vs mercado) para análisis real del poder adquisitivo
- **Análisis de inflación**: Comparación de precios históricos en USD estable
- **Procesamiento de facturas**: OCR automático con ajuste fino de parámetros
- **Gestión de inventario**: Normalización de productos con categorías jerárquicas

## 👤 Autor

**Andrés José Hernández**
🌐 [financial-helper.andresjosehr.com](https://financial-helper.andresjosehr.com)

## 📝 Licencia

Uso personal. Contactar al autor para uso comercial.
