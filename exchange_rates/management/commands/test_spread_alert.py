"""
Comando para simular cambios de banda y probar el sistema de alertas.

Simula un escenario realista donde el spread cambia gradualmente entre bandas,
permitiendo verificar que las alertas se envían correctamente.

Uso:
    docker compose exec web python manage.py test_spread_alert
    docker compose exec web python manage.py test_spread_alert --banda MIN
    docker compose exec web python manage.py test_spread_alert --banda AVG
    docker compose exec web python manage.py test_spread_alert --banda P75
    docker compose exec web python manage.py test_spread_alert --banda MAX
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from exchange_rates.models import AlertState, ExchangeRate
from exchange_rates.alert_utils import check_and_alert
from decimal import Decimal
import time


class Command(BaseCommand):
    help = 'Simula cambios de banda para probar el sistema de alertas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--banda',
            type=str,
            choices=['MIN', 'AVG', 'P75', 'MAX'],
            help='Banda específica a simular (opcional, simula secuencia completa si no se especifica)'
        )

    def handle(self, *args, **options):
        banda_target = options.get('banda')

        if banda_target:
            self._simulate_single_band(banda_target)
        else:
            self._simulate_full_sequence()

    def _simulate_single_band(self, banda):
        """Simula una única banda específica."""
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING(f'🧪 SIMULACIÓN: Forzando banda {banda}'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Obtener estado actual
        state = AlertState.get_instance()
        original_band = state.current_band

        self.stdout.write(f'📊 Banda actual: {original_band}')

        # Forzar cambio de banda
        if banda != original_band:
            self.stdout.write(f'🔄 Cambiando banda a: {banda}...')
            state.current_band = banda
            state.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Banda cambiada: {original_band} → {banda}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  La banda ya es {banda}, no hay cambio que simular'))
            return

        # Esperar 2 segundos
        self.stdout.write('⏳ Esperando 2 segundos antes de ejecutar check_and_alert()...')
        time.sleep(2)

        # Ejecutar verificación (esto debería detectar el cambio y enviar alerta)
        self.stdout.write('')
        self.stdout.write('🔔 Ejecutando verificación de alertas...')
        self.stdout.write('')

        result = check_and_alert()

        # Mostrar resultado
        if result['success']:
            if result['band_changed']:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ CAMBIO DETECTADO: {result['previous_band']} → {result['current_band']}")
                )
                if result['alert_sent']:
                    self.stdout.write(self.style.SUCCESS('✓ Alerta enviada exitosamente a Telegram'))
                else:
                    self.stdout.write(self.style.ERROR('✗ Error al enviar alerta (verificar TELEGRAM_ALERT_URL)'))
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  No se detectó cambio de banda (esto no debería pasar en simulación)')
                )

            self.stdout.write('')
            self.stdout.write(f"📈 Spread actual: {result['spread_percent']:.2f}%")
            self.stdout.write(f"📊 Banda final: {result['current_band']}")
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ Error: {result.get('error', 'Desconocido')}")
            )

        self.stdout.write('')

    def _simulate_full_sequence(self):
        """Simula una secuencia completa de cambios de banda."""
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('🧪 SIMULACIÓN COMPLETA: Secuencia MIN → AVG → P75 → MAX'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Obtener estado actual
        state = AlertState.get_instance()
        original_band = state.current_band

        self.stdout.write(f'📊 Banda inicial: {original_band}')
        self.stdout.write(f'📊 Bandas configuradas:')
        self.stdout.write(f'   MIN: {state.band_min_value}% | AVG: {state.band_avg_value}% | P75: {state.band_p75_value}% | MAX: {state.band_max_value}%')
        self.stdout.write('')

        # Secuencia de bandas a simular
        sequence = ['MIN', 'AVG', 'P75', 'MAX']

        # Encontrar índice de banda actual
        if original_band in sequence:
            start_index = sequence.index(original_band)
        else:
            start_index = 0

        # Rotar secuencia para empezar en la siguiente banda
        rotated_sequence = sequence[start_index + 1:] + sequence[:start_index + 1]

        self.stdout.write(f'🔄 Secuencia de cambios: {" → ".join(rotated_sequence)}')
        self.stdout.write('')

        # Ejecutar secuencia
        for i, banda in enumerate(rotated_sequence):
            self.stdout.write(self.style.WARNING(f'─── Paso {i+1}/{len(rotated_sequence)}: Simulando banda {banda} ───'))
            self.stdout.write('')

            # Cambiar banda
            previous_band = state.current_band
            state.current_band = banda
            state.save()

            self.stdout.write(f'✓ Banda cambiada: {previous_band} → {banda}')

            # Esperar 2 segundos
            self.stdout.write('⏳ Esperando 2 segundos...')
            time.sleep(2)

            # Ejecutar verificación
            self.stdout.write('🔔 Ejecutando verificación...')
            result = check_and_alert()

            if result['success']:
                if result['alert_sent']:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Alerta enviada: {result['previous_band']} → {result['current_band']}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('✗ Error al enviar alerta')
                    )

                self.stdout.write(f"📈 Spread: {result['spread_percent']:.2f}%")
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error: {result.get('error')}")
                )

            self.stdout.write('')

            # Esperar 3 segundos antes del siguiente paso (excepto en el último)
            if i < len(rotated_sequence) - 1:
                self.stdout.write('⏸️  Pausa de 3 segundos antes del siguiente cambio...')
                time.sleep(3)
                self.stdout.write('')

        # Resumen final
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('✓ SIMULACIÓN COMPLETA'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(f'📊 Banda inicial: {original_band}')
        self.stdout.write(f'📊 Banda final: {state.current_band}')
        self.stdout.write(f'📨 Alertas enviadas: {len(rotated_sequence)} (si todo funcionó correctamente)')
        self.stdout.write('')
        self.stdout.write('💡 Verifica tu Telegram para confirmar que recibiste todas las alertas')
        self.stdout.write('')
