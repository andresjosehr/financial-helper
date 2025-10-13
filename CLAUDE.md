# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Financial Helper is a Django-based personal expense tracking system designed for the Venezuelan market. It tracks purchases with detailed metadata including VES/USD conversions using BCV and Binance exchange rates, product categorization, and establishment management.

## Development Environment

The project runs entirely in Docker containers:

```bash
# Start services (runs migrations & collectstatic automatically)
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down
```

## Common Commands

### Django Management

All Django commands must be run inside the Docker container:

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create migrations after model changes
docker-compose exec web python manage.py makemigrations

# Create superuser for admin panel
docker-compose exec web python manage.py createsuperuser

# Populate product categories (900+ predefined categories)
docker-compose exec web python manage.py populate_product_categories

# Django shell
docker-compose exec web python manage.py shell

# Run tests
docker-compose exec web python manage.py test

# Run tests for specific app
docker-compose exec web python manage.py test establishments
docker-compose exec web python manage.py test products
docker-compose exec web python manage.py test purchases
```

### Database Access

```bash
# MySQL CLI access
docker-compose exec db mysql -u django_user -p financial_helper
# Password: django_password (or from .env)

# Database backup
docker-compose exec db mysqldump -u root -p financial_helper > backup.sql

# Database restore
docker-compose exec -T db mysql -u root -p financial_helper < backup.sql
```

### Development Workflow

```bash
# Rebuild containers after Dockerfile or requirements.txt changes
docker-compose build --no-cache

# Restart services
docker-compose restart

# View container status
docker-compose ps
```

## Architecture

### Three Main Django Apps

1. **establishments/** - Commercial establishments/stores
   - Single model: `Establishment` with legal info, location, contact details
   - Used as foreign key in purchases

2. **products/** - Product catalog with hierarchical categorization
   - `ProductCategory`: Hierarchical (parent-child) categories
   - `Product`: Normalized products (name + brand + unit_type uniqueness)
   - Includes management command to populate 900+ predefined categories

3. **purchases/** - Purchase tracking with detailed breakdowns
   - `Purchase`: Complete transaction with document metadata, VES/USD totals, payment info
   - `PurchaseItem`: Individual line items with price tracking
   - Stores exchange rate snapshots (BCV/Binance) for historical analysis

### Key Design Patterns

**UUID Primary Keys**: All models use UUID for IDs (not auto-incrementing integers)

**Exchange Rate Snapshots**: Each purchase stores BCV and Binance rates at purchase time, enabling:
- Historical price analysis in stable currency
- Comparison across different time periods
- Both VES and USD calculations for all amounts

**Product Normalization**: Two-tier product tracking:
- `PurchaseItem.description`: Raw description from receipt (always stored)
- `PurchaseItem.product`: Optional FK to normalized `Product` for aggregation/analysis

**Inline Admin**: Purchase admin shows all items inline for efficient data entry

### Database Relationships

```
User (Django auth)
  └─> Purchase
       ├─> Establishment (optional FK)
       └─> PurchaseItem[]
            └─> Product (optional FK)
                 └─> ProductCategory (optional FK, hierarchical)
```

### Configuration

- Settings: `config/settings.py` - Uses `python-decouple` for env vars
- URLs: `config/urls.py` - Currently only admin panel and API status endpoint
- All configuration via environment variables (`.env` file, see `.env.example`)

## Working with Models

### When Adding/Modifying Models:

1. Edit model in respective app's `models.py`
2. Run `docker-compose exec web python manage.py makemigrations`
3. Review generated migration file
4. Run `docker-compose exec web python manage.py migrate`
5. Update corresponding `admin.py` if needed
6. Update `sql.sql` reference file if documenting schema changes

### Model Conventions:

- All models use `UUIDField` as primary key
- All have `created_at` (auto_now_add) and/or `updated_at` (auto_now)
- All have Spanish `verbose_name` and `verbose_name_plural`
- All define `__str__` method for admin display
- Indexes defined explicitly in Meta class

## Admin Panel

Access at `http://localhost:8000/admin` - This is the primary interface (no frontend yet).

Admin configurations in each app's `admin.py`:
- List views with filters and search
- Readonly fields for IDs and timestamps
- PurchaseAdmin uses TabularInline for items

## Adding New Django Apps

```bash
# Create new app inside container
docker-compose exec web python manage.py startapp app_name

# Add to INSTALLED_APPS in config/settings.py
# Create models, admin, migrations as needed
```

## Database Schema

Reference SQL schema in `sql.sql` - kept for documentation but Django migrations are source of truth.

Key indexes:
- `establishments`: name
- `products`: category, normalized_name
- `purchases`: user, date, establishment, user+date composite
- `purchase_items`: purchase, product, product+date composite

## Environment Variables

Required in `.env` (copy from `.env.example`):
- Django: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- Database: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Docker: `WEB_PORT`

For production: Change `SECRET_KEY`, set `DEBUG=False`, update `ALLOWED_HOSTS`, use strong DB passwords.

## Static Files

Managed by WhiteNoise middleware. `collectstatic` runs automatically on container startup via docker-compose command.

## Application URLs

- Home (status): `http://localhost:8000/` - Returns JSON with API status
- Admin: `http://localhost:8000/admin/`
- Database: `localhost:3306` (from host machine)
