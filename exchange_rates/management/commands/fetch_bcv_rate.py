"""
Comando para consultar y actualizar la tasa del BCV desde www.bcv.org.ve

Este comando debe ejecutarse cada hora para mantener actualizada la tasa oficial.
Solo guarda en la base de datos si la tasa ha cambiado.

Uso:
    docker-compose exec web python manage.py fetch_bcv_rate
    docker-compose exec web python manage.py fetch_bcv_rate --force  # Forzar guardado aunque no haya cambiado

Para ejecutar cada hora, agregar al crontab:
    0 * * * * cd /ruta/proyecto && docker-compose exec -T web python manage.py fetch_bcv_rate >> /var/log/bcv_fetch.log 2>&1

Nota: El sitio del BCV usa JavaScript, por lo que necesitas tener playwright instalado:
    pip install playwright beautifulsoup4 lxml
    playwright install chromium
"""

import re
import sys
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from exchange_rates.models import ExchangeRate


class Command(BaseCommand):
    help = 'Consulta la tasa del BCV desde www.bcv.org.ve y la guarda si ha cambiado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar guardado aunque la tasa no haya cambiado',
        )
        parser.add_argument(
            '--test-rate',
            type=str,
            help='Usar una tasa de prueba (ej: 233.0458) en lugar de consultar el sitio',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        test_rate = options.get('test_rate')

        self.stdout.write(
            self.style.MIGRATE_HEADING('═' * 70)
        )
        self.stdout.write(
            self.style.MIGRATE_HEADING('  Consultando tasa del BCV desde www.bcv.org.ve')
        )
        self.stdout.write(
            self.style.MIGRATE_HEADING('═' * 70)
        )
        self.stdout.write('')

        # Si hay una tasa de prueba, usarla
        if test_rate:
            try:
                current_rate = Decimal(test_rate)
                rate_date = date.today()
                self.stdout.write(
                    self.style.WARNING(f'⚠ Usando tasa de prueba: {current_rate:,.4f} Bs/USD')
                )
                rate_data = {'rate': current_rate, 'date': rate_date}
            except (InvalidOperation, ValueError):
                raise CommandError(f'Tasa de prueba inválida: {test_rate}')
        else:
            # Intentar obtener la tasa del sitio web
            try:
                rate_data = self._fetch_bcv_rate()

                if not rate_data:
                    self.stdout.write(
                        self.style.ERROR('✗ No se pudo extraer la tasa del sitio web')
                    )
                    return

                current_rate = rate_data['rate']
                rate_date = rate_data['date']

                self.stdout.write(
                    self.style.SUCCESS(f'✓ Tasa extraída: {current_rate:,.4f} Bs/USD')
                )
                self.stdout.write(f'  Fecha de la tasa: {rate_date}')
                self.stdout.write('')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error al consultar el sitio del BCV: {str(e)}')
                )
                raise CommandError(f'Error al consultar BCV: {str(e)}')

        current_rate = rate_data['rate']
        rate_date = rate_data['date']

        # Obtener la última tasa guardada para esta fecha
        latest_rate = ExchangeRate.objects.filter(
            source=ExchangeRate.SOURCE_BCV,
            date=rate_date
        ).order_by('-timestamp').first()

        # Verificar si la tasa ha cambiado
        if latest_rate and not force:
            if latest_rate.rate == current_rate:
                self.stdout.write(
                    self.style.WARNING(f'⊘ La tasa no ha cambiado ({latest_rate.rate:,.4f} Bs/USD)')
                )
                self.stdout.write(
                    self.style.WARNING(f'  Última actualización: {latest_rate.fetched_at}')
                )
                self.stdout.write('')
                self.stdout.write(
                    self.style.SUCCESS('  No se requiere actualización')
                )
                return
            else:
                self.stdout.write(
                    self.style.WARNING(f'  Tasa anterior: {latest_rate.rate:,.4f} Bs/USD')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'  Tasa nueva: {current_rate:,.4f} Bs/USD')
                )
                change = current_rate - latest_rate.rate
                change_pct = (change / latest_rate.rate) * 100
                self.stdout.write(
                    self.style.SUCCESS(f'  Cambio: {change:+,.4f} Bs/USD ({change_pct:+.2f}%)')
                )

        # Guardar la nueva tasa
        try:
            now = timezone.now()

            exchange_rate = ExchangeRate.objects.create(
                source=ExchangeRate.SOURCE_BCV,
                rate=current_rate,
                date=rate_date,
                timestamp=now,
                notes=f'Tasa obtenida automáticamente desde www.bcv.org.ve'
            )

            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('═' * 70)
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Tasa guardada exitosamente')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  ID: {exchange_rate.id}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Fecha: {exchange_rate.date}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Tasa: {exchange_rate.rate:,.4f} Bs/USD')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Timestamp: {exchange_rate.timestamp}')
            )
            self.stdout.write(
                self.style.SUCCESS('═' * 70)
            )

            # Mostrar estadísticas
            total_records = ExchangeRate.objects.filter(
                source=ExchangeRate.SOURCE_BCV
            ).count()

            self.stdout.write('')
            self.stdout.write(f'Total de tasas BCV en la base de datos: {total_records}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error al guardar la tasa: {str(e)}')
            )
            raise CommandError(f'Error al guardar: {str(e)}')

    def _fetch_bcv_rate(self):
        """
        Extrae la tasa del BCV desde www.bcv.org.ve.

        Primero intenta con requests simple (más rápido pero puede no funcionar si el sitio usa JS).
        Si falla, intenta con Playwright para renderizar JavaScript.

        Returns:
            dict: {'rate': Decimal, 'date': date} o None si falla
        """
        # Intentar primero con requests (más rápido)
        self.stdout.write('  → Intentando con requests...')
        result = self._fetch_with_requests()
        if result:
            return result

        # Si requests no funcionó, intentar con Playwright
        self.stdout.write('  → Requests no funcionó, intentando con Playwright...')
        return self._fetch_with_playwright()

    def _fetch_with_requests(self):
        """
        Intenta obtener la tasa usando requests y BeautifulSoup.

        Returns:
            dict o None
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(
                'https://www.bcv.org.ve/',
                headers=headers,
                timeout=30,
                verify=False  # BCV a veces tiene problemas con SSL
            )

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar la tasa en el HTML
            # Buscar patrones comunes
            patterns = [
                r'(?:D[oó]lar|USD|US\$)[^\d]*?([\d]{1,3}[,\.]\d{2,8})',
                r'([\d]{1,3}[,\.]\d{2,8})[^\d]*?(?:Bs|Bolivares|VES)',
            ]

            text_content = soup.get_text()

            for pattern in patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        try:
                            rate_str = match.replace(',', '.')
                            rate_value = Decimal(rate_str)

                            # Validar que sea una tasa razonable (entre 50 y 500 Bs/USD)
                            if Decimal('50') <= rate_value <= Decimal('500'):
                                return {
                                    'rate': rate_value,
                                    'date': date.today()
                                }
                        except (InvalidOperation, ValueError):
                            continue

            return None

        except ImportError:
            self.stdout.write(
                self.style.WARNING('  ⚠ beautifulsoup4 no está instalado')
            )
            return None
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Error con requests: {str(e)}')
            )
            return None

    def _fetch_with_playwright(self):
        """
        Extrae la tasa del BCV usando Playwright para renderizar JavaScript.

        Returns:
            dict: {'rate': Decimal, 'date': date} o None si falla
        """
        try:
            from playwright.sync_api import sync_playwright
            import time

            with sync_playwright() as p:
                # Lanzar navegador en modo headless
                self.stdout.write('  → Lanzando navegador...')
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    ignore_https_errors=True,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()

                # Navegar al sitio del BCV
                self.stdout.write('  → Navegando a www.bcv.org.ve...')
                try:
                    page.goto('https://www.bcv.org.ve/', wait_until='networkidle', timeout=30000)
                except Exception:
                    # A veces networkidle falla, intentar con domcontentloaded
                    page.goto('https://www.bcv.org.ve/', wait_until='domcontentloaded', timeout=30000)

                # Esperar que cargue el contenido dinámico
                self.stdout.write('  → Esperando carga del contenido...')
                time.sleep(3)

                # Obtener el contenido de la página
                page_content = page.content()
                page_text = page.inner_text('body')

                rate = None
                rate_date = date.today()

                # Estrategia 1: Buscar en el texto de la página
                patterns = [
                    r'(?:D[oó]lar|USD|US\$)[^\d]*?([\d]{1,3}[,\.]\d{2,8})',
                    r'([\d]{1,3}[,\.]\d{2,8})[^\d]*?(?:Bs|Bolivares|VES)',
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            try:
                                rate_str = match.replace(',', '.')
                                rate_value = Decimal(rate_str)

                                # Validar que sea una tasa razonable (entre 50 y 500)
                                if Decimal('50') <= rate_value <= Decimal('500'):
                                    rate = rate_value
                                    break
                            except (InvalidOperation, ValueError):
                                continue

                    if rate:
                        break

                # Estrategia 2: Buscar con selectores CSS
                if not rate:
                    self.stdout.write('  → Buscando con selectores CSS...')
                    selectors = [
                        '.view-tipo-de-cambio-oficial-del-bcv strong',
                        '#dolar strong',
                        '.recuadro strong',
                        '[id*="dolar"] strong',
                        '[class*="dolar"] strong',
                        '[class*="tipo-cambio"] strong',
                        '[class*="exchange"] strong',
                    ]

                    for selector in selectors:
                        try:
                            elements = page.query_selector_all(selector)
                            for element in elements:
                                text = element.inner_text().strip()
                                numbers = re.findall(r'[\d]{1,3}[,\.]?\d{2,8}', text)
                                for num in numbers:
                                    try:
                                        rate_str = num.replace(',', '.')
                                        rate_value = Decimal(rate_str)
                                        if Decimal('50') <= rate_value <= Decimal('500'):
                                            rate = rate_value
                                            break
                                    except (InvalidOperation, ValueError):
                                        continue
                                if rate:
                                    break
                            if rate:
                                break
                        except Exception:
                            continue

                browser.close()

                if rate:
                    return {
                        'rate': rate,
                        'date': rate_date
                    }
                else:
                    self.stdout.write(
                        self.style.WARNING('  ⚠ No se pudo encontrar la tasa en la página')
                    )
                    self.stdout.write(
                        self.style.WARNING('  El sitio del BCV puede haber cambiado su estructura')
                    )
                    return None

        except ImportError:
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR('✗ Playwright no está instalado')
            )
            self.stdout.write(
                self.style.WARNING('  Para instalar Playwright, ejecutar:')
            )
            self.stdout.write(
                self.style.WARNING('  1. pip install playwright beautifulsoup4 lxml')
            )
            self.stdout.write(
                self.style.WARNING('  2. playwright install chromium')
            )
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('  Mientras tanto, puedes usar --test-rate para probar:')
            )
            self.stdout.write(
                self.style.WARNING('  python manage.py fetch_bcv_rate --test-rate 233.0458')
            )
            return None

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error en Playwright: {str(e)}')
            )
            return None
