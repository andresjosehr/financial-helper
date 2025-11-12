"""
Comando para importar tasas de Binance P2P desde el API

Uso:
    docker compose exec web python manage.py import_binance_rates
    docker compose exec web python manage.py import_binance_rates --date 2025-11-02
    docker compose exec web python manage.py import_binance_rates --start-date 2025-10-03 --end-date 2025-11-02
"""

import requests
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.core.management.base import BaseCommand
from exchange_rates.models import ExchangeRate


class Command(BaseCommand):
    help = 'Importa tasas de Binance P2P desde el API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Fecha específica (YYYY-MM-DD)'
        )

        parser.add_argument(
            '--start-date',
            type=str,
            help='Fecha inicial para rango (YYYY-MM-DD)'
        )

        parser.add_argument(
            '--end-date',
            type=str,
            help='Fecha final para rango (YYYY-MM-DD)'
        )

        parser.add_argument(
            '--api-url',
            type=str,
            default='https://finance.andresjosehr.com/api/binance-p2p/exchange-rates',
            help='URL del API'
        )

    def handle(self, *args, **options):
        api_url = options['api_url']

        # Determinar fechas a procesar
        dates_to_process = []

        if options['date']:
            # Una sola fecha
            try:
                single_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
                dates_to_process.append(single_date)
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(f'❌ Fecha inválida: {options["date"]}')
                )
                return

        elif options['start_date'] and options['end_date']:
            # Rango de fechas
            try:
                start = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
                end = datetime.strptime(options['end_date'], '%Y-%m-%d').date()

                if start > end:
                    self.stdout.write(
                        self.style.ERROR('❌ La fecha inicial debe ser menor o igual a la final')
                    )
                    return

                current = start
                while current <= end:
                    dates_to_process.append(current)
                    current += timedelta(days=1)

            except ValueError as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error en fechas: {e}')
                )
                return
        else:
            # Por defecto: rango desde 2025-10-03 hasta 2025-11-02
            start = date(2025, 10, 3)
            end = date(2025, 11, 2)

            current = start
            while current <= end:
                dates_to_process.append(current)
                current += timedelta(days=1)

        self.stdout.write(
            self.style.MIGRATE_HEADING(f'Procesando {len(dates_to_process)} fechas...')
        )
        self.stdout.write('')

        total_created = 0
        total_updated = 0
        total_errors = 0

        for target_date in dates_to_process:
            date_str = target_date.strftime('%Y-%m-%d')

            # Consultar API
            try:
                response = requests.get(
                    api_url,
                    params={'date': date_str, 'per_page': 100},
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

            except requests.exceptions.RequestException as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error al consultar {date_str}: {e}')
                )
                total_errors += 1
                continue

            # Procesar datos
            records = data.get('data', [])

            if not records:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Sin datos para {date_str}')
                )
                continue

            # Guardar cada snapshot individual con timestamp
            created_count = 0
            updated_count = 0

            for record in records:
                record_type = record.get('type')
                avg_price = record.get('avg_price')
                timestamp_str = record.get('timestamp')

                if not avg_price or not timestamp_str or not record_type:
                    continue

                # Parsear timestamp
                from django.utils import timezone

                try:
                    # El timestamp viene como "2025-11-02T00:00:06.000000Z"
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    continue

                # Determinar source
                if record_type == 'buy':
                    source = ExchangeRate.SOURCE_BINANCE_BUY
                elif record_type == 'sell':
                    source = ExchangeRate.SOURCE_BINANCE_SELL
                else:
                    continue

                # Crear/actualizar snapshot
                rate_obj, created = ExchangeRate.objects.update_or_create(
                    source=source,
                    timestamp=timestamp,
                    defaults={
                        'date': target_date,
                        'rate': Decimal(str(avg_price)).quantize(Decimal('0.0001')),
                        'notes': f'Snapshot horario de Binance P2P'
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            total_created += created_count
            total_updated += updated_count

            # Mostrar progreso
            status = '✓' if (created_count > 0 or updated_count > 0) else '⚠'
            self.stdout.write(
                f'{status} {date_str}: '
                f'{len(records)} snapshots totales '
                f'- Creadas: {created_count}, Actualizadas: {updated_count}'
            )

        # Resumen final
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'✓ Tasas creadas: {total_created}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Tasas actualizadas: {total_updated}'))

        if total_errors > 0:
            self.stdout.write(
                self.style.ERROR(f'❌ Errores: {total_errors}')
            )

        # Estadísticas finales
        buy_count = ExchangeRate.objects.filter(
            source=ExchangeRate.SOURCE_BINANCE_BUY
        ).count()

        sell_count = ExchangeRate.objects.filter(
            source=ExchangeRate.SOURCE_BINANCE_SELL
        ).count()

        self.stdout.write('')
        self.stdout.write(f'Total tasas BINANCE_BUY en BD: {buy_count}')
        self.stdout.write(f'Total tasas BINANCE_SELL en BD: {sell_count}')

        latest_buy = ExchangeRate.objects.filter(
            source=ExchangeRate.SOURCE_BINANCE_BUY
        ).order_by('-date').first()

        latest_sell = ExchangeRate.objects.filter(
            source=ExchangeRate.SOURCE_BINANCE_SELL
        ).order_by('-date').first()

        if latest_buy:
            self.stdout.write(
                f'Última tasa BUY: {latest_buy.date} = {latest_buy.rate:,.4f} Bs/USD'
            )

        if latest_sell:
            self.stdout.write(
                f'Última tasa SELL: {latest_sell.date} = {latest_sell.rate:,.4f} Bs/USD'
            )

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Importación completada'))
