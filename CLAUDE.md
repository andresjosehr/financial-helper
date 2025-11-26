# CLAUDE.md

This file provides technical guidance for Claude Code when working with this repository.

## Project Overview

**Financial Helper** is a Django 5.2.7 system with 6 apps combining:
- **Exchange rate tracking** (BCV + Binance P2P) with real-time updates and statistical analysis
- **Expense tracking** with immutable exchange rate snapshots (VES, USD-BCV, USD-Binance)
- **Interactive dashboard** with 5 TradingView charts (spread analysis, volatility, distribution)
- **OCR invoice processing** with 7-step pipeline and 3 detection algorithms
- **Product normalization** with 900+ hierarchical categories

**Core feature**: Each purchase stores bcv_rate and binance_rate snapshots → immutable historical analysis in USD.

## Docker Environment

**All commands must run inside containers**:

```bash
# Quick start
docker-compose up -d                                    # Start (auto-migrate + collectstatic)
docker-compose logs -f web                              # View logs
docker-compose down                                     # Stop

# Common Django commands (prefix all with: docker-compose exec web python manage.py)
createsuperuser                                         # Create admin user
populate_product_categories                             # 900+ categories (~2s)
migrate / makemigrations                                # DB migrations
shell                                                   # Django shell
test [app_name]                                         # Run tests

# Exchange rates (automate with cron: */15 for Binance, hourly for BCV)
update_binance_rates                                    # Binance P2P (IQR outlier removal)
fetch_bcv_rate [--force] [--test-rate 50.12]          # BCV scraping (BeautifulSoup + Playwright)

# Database
docker-compose exec db mysql -u django_user -p financial_helper   # MySQL CLI (pass: from .env)
curl -X POST "http://localhost:8000/api/backup/download/" \       # Backup API
  -H "Authorization: Bearer financial-helper-backup-secret-2024" \
  --output backup.sql.gz
gunzip -c backup.sql.gz | docker-compose exec -T db mysql -u root -p financial_helper  # Restore
```

## Architecture (6 Django Apps)

### 1. exchange_rates/ ⭐ (Core System)

**Model**: `ExchangeRate`
- Fields: `id` (UUID), `source` (BCV/BINANCE_BUY/BINANCE_SELL), `rate` (Decimal 12,4), `date`, `timestamp`, `notes`
- Indexes: `source+timestamp` (unique), `source+date`, `timestamp DESC`, `date DESC`
- Methods: `get_rate()`, `get_rate_value()`, `get_latest_rates()`, `convert_ves_to_usd()`, `convert_usd_to_ves()`

**update_binance_rates.py** (management command):
1. Reference query → get best BUY/SELL rates → calculate ~100 USD in VES
2. Filtered query with `transAmount` in VES → 20 BUY + 20 SELL offers
3. **IQR outlier removal**: Q1, Q3, IQR = Q3-Q1, remove outside [Q1-1.5×IQR, Q3+1.5×IQR]
4. Average clean prices → save with timestamp + outlier count in notes
5. API: `https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search`

**fetch_bcv_rate.py** (management command):
- **Strategy 1**: requests + BeautifulSoup (fast, fails if JS required)
- **Strategy 2**: Playwright headless browser (slow, reliable)
- Validates: rate changed + range 50-500 Bs/USD
- Flags: `--force` (force save), `--test-rate X.XX` (testing)

**API**: `GET/POST /api/exchange-rates/bcv/?days=7&end_date=2025-11-25`
- Returns: `{start_date, end_date, days, bcv: [{date, rate}], binance_sell: [{timestamp, rate}]}`

**Dashboard** (`templates/exchange_rates/chart.html`):
- **Tech**: Alpine.js + TailwindCSS + TradingView Lightweight Charts
- **5 charts**:
  1. Spread % (purple line + MIN/AVG/P75/MAX bands)
  2. BCV rate (blue area, zoom 7d)
  3. Binance P2P (orange area, zoom 24h)
  4. Volatility (green/red histogram of daily changes)
  5. Distribution (20-bin frequency histogram)
- **Spread indicator**: Visual bar (red→amber→lime→green) with current position
- **Bidirectional calculator**: BCV ↔ Binance conversion
- **Auto-refresh**: 5 min interval
- **Stats**: Client-side percentile calculation (P25, P50, P75), excludes today for historical bands

### 2. purchases/

**Models**:
- `Purchase`: user (FK), establishment (FK optional), purchase_date, purchase_time, **bcv_rate** (Decimal snapshot), **binance_rate** (Decimal snapshot), total_ves, total_usd_bcv (calculated), total_usd_binance (calculated), tax_type, tax_percentage, raw_json
- `PurchaseItem`: purchase (FK), product (FK optional), description, quantity, unit_type, total_ves, total_usd_bcv (calculated), total_usd_binance (calculated)
- **Properties**: `unit_price_ves`, `unit_price_usd_bcv`, `unit_price_usd_binance`

**Admin**: `PurchaseAdmin` with `PurchaseItemInline` (TabularInline) for efficient editing

### 3. products/

**Models**:
- `ProductCategory`: name, description, parent (FK self, optional) → hierarchical
- `ProductBrand`: name (unique)
- `Product`: name (unique), category (FK optional), brand (FK optional)
- `ProductVariant`: variant_type (size/flavor/color/material/version/package), value
- `ProductVariantAssignment`: product (FK), variant (FK) → M2M

**Commands**: `populate_product_categories`, `populate_common_products`, `populate_test_products`, `delete_all_products`

**API**: `POST /api/products/by-categories/`
- Request: `{"categories": ["Bebidas", "Lácteos"]}`
- Response: Products with brands and variants

### 4. image_processor/

**Pipeline** (7 steps in `process_invoice_optimal`):
1. Aggressive preprocessing: median(5×5), bilateral, morphology closing, CLAHE
2. Invoice detection: 3 parallel strategies (Canny, Otsu, brightness) → select best by area
3. Grayscale conversion
4. Noise cleaning: median(5×5), gaussian(3×3), bilateral(9×9)
5. Contrast boost: CLAHE aggressive (clipLimit=4.0), sharpening (1.5×)
6. Adaptive thresholding: GAUSSIAN_C, window 31×31, offset +15
7. Morphological cleanup: opening, closing, median(3×3)

**APIs**:
- `POST /api/process-invoice/` → optimal params, returns base64/binary PNG
- `POST /api/process-with-params/` → custom params (median_blur, clahe_clip, etc.)

**Tuning page**: `/image-processor/tuning/` for real-time parameter adjustment

**Libraries**: OpenCV (cv2), Pillow, NumPy, SciPy

### 5. establishments/

**Model**: `Establishment` - name, legal_name, tax_id (RIF/NIT), address, city, state, postal_code, country, phone, email, website

### 6. users/

Empty structure extending Django User (FK in Purchase)

## Key Design Patterns

**1. Immutable Exchange Rate Snapshots**
```python
# Purchase model stores rates at purchase time
purchase.bcv_rate = Decimal('50.12')           # Frozen snapshot
purchase.binance_rate = Decimal('51.45')       # Frozen snapshot
purchase.total_usd_bcv = total_ves / bcv_rate  # Calculated once
# → Historical USD values never change, even if rates update
```

**2. UUID Primary Keys** - All models use UUIDs (not auto-increment)

**3. Two-tier Product Tracking**
- `PurchaseItem.description` (always stored) → raw receipt text
- `PurchaseItem.product` (optional FK) → normalized for aggregation

**4. Statistical Outlier Removal** (IQR method in Binance updates)
```python
Q1 = percentile(prices, 25)
Q3 = percentile(prices, 75)
IQR = Q3 - Q1
valid = [p for p in prices if Q1 - 1.5*IQR <= p <= Q3 + 1.5*IQR]
avg_rate = sum(valid) / len(valid)
```

**5. Client-side Chart Statistics**
- Dashboard calculates percentiles in JavaScript (not backend)
- Historical bands exclude today's data for stable reference
- Auto-refresh every 5 minutes without full page reload

## Database Schema

```
User (auth_user)
  └─> Purchase
       ├─> Establishment (optional FK)
       ├─> bcv_rate, binance_rate (Decimal snapshots)
       └─> PurchaseItem[]
            └─> Product (optional FK)
                 ├─> ProductCategory (hierarchical parent-child)
                 ├─> ProductBrand
                 └─> ProductVariant[] (M2M via ProductVariantAssignment)

ExchangeRate (standalone historical table)
  └─> Unique index: source + timestamp
```

**Critical indexes**:
- `exchange_rates`: `source+timestamp` (unique), `source+date`, `timestamp DESC`
- `purchases`: `user+date`, `date`, `establishment`
- `purchase_items`: `purchase`, `product+date`
- `products`: `category`, `name`

## Model Development Workflow

**Adding/modifying models**:
```bash
# 1. Edit model in app's models.py
# 2. Generate migration
docker-compose exec web python manage.py makemigrations

# 3. Review migration file in app/migrations/
# 4. Apply migration
docker-compose exec web python manage.py migrate

# 5. Update admin.py if needed
# 6. Consider adding indexes for frequent queries
```

**Model conventions** (strictly enforced):
- `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- `created_at = models.DateTimeField(auto_now_add=True)` (optional)
- `updated_at = models.DateTimeField(auto_now=True)` (optional)
- Spanish `verbose_name` and `verbose_name_plural` in Meta
- `__str__` method returns meaningful representation
- Explicit indexes in `Meta.indexes = [...]`

## Configuration & URLs

**Environment** (`.env`):
```env
SECRET_KEY=<django-secret>              # Generate with get_random_secret_key()
DEBUG=True                              # False in production
ALLOWED_HOSTS=localhost,127.0.0.1       # Domain list in production
DB_NAME=financial_helper
DB_USER=django_user
DB_PASSWORD=django_password             # Strong password in production
DB_HOST=db                              # Docker service name
DB_PORT=3306
WEB_PORT=8000
```

**URL Map** (`config/urls.py`):
| Route | Handler | Description |
|-------|---------|-------------|
| `/` | `chart_view` | Dashboard with 5 charts |
| `/admin/` | Django Admin | CRUD interface |
| `/api/status/` | `api_status` | JSON status |
| `/api/exchange-rates/bcv/` | `api_bcv_rates` | Historical rates API |
| `/api/products/by-categories/` | `get_products_by_categories` | Filter products |
| `/api/process-invoice/` | `process_invoice_optimal` | OCR optimal |
| `/api/process-with-params/` | `process_with_params` | OCR custom |
| `/api/backup/download/` | `download_database_backup` | MySQL dump |
| `/image-processor/test/` | `test_page` | OCR upload form |
| `/image-processor/tuning/` | `tuning_page` | OCR param tuning |

**Static files**: WhiteNoise middleware, auto-collected on container start

## Backup System

**Endpoint**: `POST /api/backup/download/`
- **Auth**: `Authorization: Bearer financial-helper-backup-secret-2024`
- **Token location**: `config/backup_views.py` line 40 (`HARDCODED_TOKEN`)
- **Response**: `financial_helper_backup_YYYYMMDD_HHMMSS.sql.gz` (~100KB)
- **Contents**: Full MySQL dump (DROP/CREATE + INSERT, gzip level 9)

**Usage**:
```bash
# Download
curl -X POST "http://localhost:8000/api/backup/download/" \
  -H "Authorization: Bearer financial-helper-backup-secret-2024" \
  --output backup.sql.gz

# Restore
gunzip -c backup.sql.gz | docker-compose exec -T db mysql -u root -p financial_helper
```

**Implementation**: Pure Python (no mysqldump binary), MySQLdb library, streaming response

## Important Technical Details

### Exchange Rate Update Strategy

**Binance P2P** (every 15 min recommended):
1. Reference query (no transAmount) → get best rates
2. Calculate ~100 USD equivalent in VES
3. Filtered query with transAmount in VES → 20 offers each side
4. IQR outlier removal on prices
5. Save average + outlier count in notes

**BCV** (hourly recommended):
- Dual strategy: requests+BeautifulSoup (fast) → fallback to Playwright (reliable)
- Only saves if rate changed (dedup by value)
- Validates range: 50-500 Bs/USD

### Chart.html Technical Notes

**Data synchronization**:
- BCV: Daily data (one rate per date)
- Binance: Hourly snapshots (multiple per day)
- **Gap filling**: `fillBcvGaps()` function repeats BCV rate for each Binance timestamp

**Spread calculation**:
```javascript
spreadBs = binanceRate - bcvRate
spreadPercent = (spreadBs / binanceRate) × 100
```

**Historical bands** (excludes today):
```javascript
const today = new Date().setHours(0,0,0,0);
const historical = data.filter(r => r.date < todayStr);
// Calculate MIN, AVG, P75, MAX on historical only
```

**Zoom levels**:
- BCV chart: 7 days initial
- Binance chart: 24 hours initial
- Spread chart: Full range (user adjustable)

### OCR Pipeline Technical Details

**Detection strategy selection**:
```python
# Run 3 algorithms in parallel, select by area
areas = {
    'canny': detect_with_canny(img),
    'otsu': detect_with_otsu(img),
    'brightness': detect_with_brightness(img)
}
best = max(areas, key=lambda k: areas[k]['area'])
```

**Aspect ratio validation**: 0.3 ≤ height/width ≤ 3.0
**Margin**: 3% added to detected bounds
**Output formats**: `response_format=base64` (JSON) or `binary` (PNG)

## Production Checklist

**Before deploying**:
1. Generate new `SECRET_KEY`: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
2. Set `DEBUG=False` in `.env`
3. Update `ALLOWED_HOSTS` with domain
4. Change `DB_PASSWORD` and `DB_ROOT_PASSWORD`
5. Change `HARDCODED_TOKEN` in `config/backup_views.py`
6. Setup cron jobs:
   ```cron
   */15 * * * * docker-compose exec -T web python manage.py update_binance_rates
   0 * * * * docker-compose exec -T web python manage.py fetch_bcv_rate
   0 3 * * * curl -X POST "http://localhost:8000/api/backup/download/" -H "Authorization: Bearer <token>" -o /backups/backup_$(date +\%Y\%m\%d).sql.gz
   ```
7. Configure HTTPS (Nginx reverse proxy recommended)
8. Restrict `/admin/` by IP if possible

## Tech Stack Summary

- **Backend**: Django 5.2.7, Python 3.11, MySQL 8.0, Gunicorn
- **Frontend**: Alpine.js 3.x, TailwindCSS, TradingView Lightweight Charts
- **Processing**: OpenCV, Pillow, NumPy, SciPy, BeautifulSoup4, Playwright
- **Deployment**: Docker Compose, WhiteNoise (static), python-decouple (env)
