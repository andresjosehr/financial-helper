"""
Comando para recalcular las bandas de spread manualmente.

Uso:
    docker compose exec web python manage.py recalculate_bands
    docker compose exec web python manage.py recalculate_bands --days 7
"""

from django.core.management.base import BaseCommand
from exchange_rates.models import AlertState
from exchange_rates.alert_utils import (
    calculate_historical_spreads,
    calculate_spread_bands,
    calculate_current_spread,
    classify_spread
)
from datetime import date


class Command(BaseCommand):
    help = 'Recalcula las bandas de spread manualmente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=5,
            help='Número de días para calcular las bandas (default: 5)'
        )

    def handle(self, *args, **options):
        days = options['days']

        self.stdout.write(f'Recalculando bandas con {days} días de historia...')
        self.stdout.write('')

        # Calcular spreads históricos
        spreads = calculate_historical_spreads(days=days, exclude_today=True)

        if not spreads:
            self.stdout.write(
                self.style.ERROR('No hay suficientes datos para calcular bandas')
            )
            return

        self.stdout.write(f'Spreads encontrados: {len(spreads)}')
        self.stdout.write(f'Rango: {min(spreads):.2f}% - {max(spreads):.2f}%')
        self.stdout.write('')

        # Calcular bandas
        bands = calculate_spread_bands(spreads)

        if not bands:
            self.stdout.write(
                self.style.ERROR('No se pudieron calcular las bandas')
            )
            return

        # Obtener estado actual
        state = AlertState.get_instance()

        # Mostrar bandas anteriores
        self.stdout.write('Bandas anteriores:')
        self.stdout.write(f'  MIN: {state.band_min_value}%')
        self.stdout.write(f'  AVG: {state.band_avg_value}%')
        self.stdout.write(f'  P75: {state.band_p75_value}%')
        self.stdout.write(f'  MAX: {state.band_max_value}%')
        self.stdout.write('')

        # Actualizar bandas
        state.bands_calculation_date = date.today()
        state.band_min_value = bands['min']
        state.band_avg_value = bands['avg']
        state.band_p75_value = bands['p75']
        state.band_max_value = bands['max']
        state.save()

        # Mostrar nuevas bandas
        self.stdout.write(self.style.SUCCESS('Nuevas bandas:'))
        self.stdout.write(self.style.SUCCESS(f'  MIN: {bands["min"]}%'))
        self.stdout.write(self.style.SUCCESS(f'  AVG: {bands["avg"]}%'))
        self.stdout.write(self.style.SUCCESS(f'  P75: {bands["p75"]}%'))
        self.stdout.write(self.style.SUCCESS(f'  MAX: {bands["max"]}%'))
        self.stdout.write('')

        # Mostrar spread actual y clasificación
        spread_actual, bcv, binance = calculate_current_spread()
        if spread_actual:
            banda_actual = classify_spread(spread_actual, bands)
            self.stdout.write(f'Spread actual: {spread_actual:.2f}% → Banda: {banda_actual}')
