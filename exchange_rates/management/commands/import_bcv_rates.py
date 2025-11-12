"""
Comando para importar tasas del BCV desde bcv.json

Uso:
    docker compose exec web python manage.py import_bcv_rates
"""

import json
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from exchange_rates.models import ExchangeRate


class Command(BaseCommand):
    help = 'Importa tasas del BCV desde el archivo bcv.json'

    def handle(self, *args, **options):
        # Ruta al archivo JSON
        json_file = settings.BASE_DIR / 'bcv.json'

        if not json_file.exists():
            self.stdout.write(
                self.style.ERROR(f'❌ Archivo no encontrado: {json_file}')
            )
            return

        # Leer archivo JSON
        self.stdout.write(
            self.style.MIGRATE_HEADING('Leyendo archivo bcv.json...')
        )

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        rates = data.get('rates', [])
        total_rates = len(rates)

        self.stdout.write(f'Encontradas {total_rates} tasas en el archivo')
        self.stdout.write('')

        # Procesar tasas
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for rate_data in rates:
            date_str = rate_data.get('date')
            usd_rate = rate_data.get('usd')

            if not date_str or not usd_rate:
                skipped_count += 1
                continue

            # Convertir fecha
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Fecha inválida: {date_str}')
                )
                skipped_count += 1
                continue

            # Convertir tasa a Decimal
            try:
                rate_decimal = Decimal(str(usd_rate))
            except (ValueError, TypeError):
                self.stdout.write(
                    self.style.WARNING(f'⚠ Tasa inválida: {usd_rate}')
                )
                skipped_count += 1
                continue

            # Crear o actualizar tasa
            rate_obj, created = ExchangeRate.objects.update_or_create(
                source=ExchangeRate.SOURCE_BCV,
                date=date_obj,
                defaults={
                    'rate': rate_decimal,
                    'notes': f'Importado desde bcv.json - EUR: {rate_data.get("eur", "N/A")}'
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

            # Mostrar progreso cada 50 registros
            if (created_count + updated_count) % 50 == 0:
                self.stdout.write(f'  Procesados: {created_count + updated_count}/{total_rates}...')

        # Resumen
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✓ Tasas creadas: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Tasas actualizadas: {updated_count}'))

        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⊘ Tasas omitidas: {skipped_count}')
            )

        # Estadísticas
        total_in_db = ExchangeRate.objects.filter(
            source=ExchangeRate.SOURCE_BCV
        ).count()

        latest = ExchangeRate.objects.filter(
            source=ExchangeRate.SOURCE_BCV
        ).order_by('-date').first()

        self.stdout.write('')
        self.stdout.write(f'Total de tasas BCV en BD: {total_in_db}')
        if latest:
            self.stdout.write(
                f'Última tasa: {latest.date} = {latest.rate:,.4f} Bs/USD'
            )

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Importación completada'))
