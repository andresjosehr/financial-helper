"""
Comando para actualizar tasas de Binance P2P en tiempo real

Estrategia de consulta:
1. Primera consulta SIN transAmount para obtener la mejor tasa actual
2. Calcular equivalente de 100 USD en VES con esa tasa
3. Segunda consulta CON transAmount en VES para filtrar ofertas de ~100 USD
4. Limpiar valores atípicos usando el método IQR (Interquartile Range)
5. Guardar el promedio de los precios limpios

Método de limpieza de outliers (IQR):
- Calcula Q1 (cuartil 25%) y Q3 (cuartil 75%)
- Define IQR = Q3 - Q1
- Descarta valores fuera del rango [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
- Esto elimina ofertas con precios anormalmente altos o bajos que afectan el promedio

Uso:
    docker compose exec web python manage.py update_binance_rates
"""

import requests
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from exchange_rates.models import ExchangeRate
import statistics


class Command(BaseCommand):
    help = 'Actualiza tasas de Binance P2P consultando el API directamente'

    # Configuración fija
    ASSET = 'USDT'
    FIAT = 'VES'
    TARGET_USD = 100  # Queremos ofertas para ~100 USD
    ROWS = 20  # Número de ofertas a promediar

    def _remove_outliers(self, prices):
        """
        Elimina valores atípicos usando el método IQR (Interquartile Range)

        Args:
            prices: Lista de precios

        Returns:
            tuple: (precios_limpios, outliers_removidos, stats_dict)
        """
        if len(prices) < 4:
            # No suficientes datos para calcular IQR
            return prices, [], None

        # Calcular cuartiles
        q1 = statistics.quantiles(prices, n=4)[0]  # Cuartil 25%
        q3 = statistics.quantiles(prices, n=4)[2]  # Cuartil 75%
        iqr = q3 - q1

        # Definir límites (1.5 * IQR es el estándar)
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Filtrar outliers
        cleaned_prices = [p for p in prices if lower_bound <= p <= upper_bound]
        outliers = [p for p in prices if p < lower_bound or p > upper_bound]

        stats = {
            'q1': q1,
            'q3': q3,
            'iqr': iqr,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'original_count': len(prices),
            'cleaned_count': len(cleaned_prices),
            'outliers_count': len(outliers)
        }

        return cleaned_prices, outliers, stats

    def handle(self, *args, **options):
        self.stdout.write('🔍 Consultando Binance P2P API...')

        # Timestamp actual
        now = timezone.now()

        try:
            # PASO 1: Consulta SIN transAmount para obtener la mejor tasa actual
            self.stdout.write('  📍 Paso 1: Obteniendo tasa de referencia...')

            buy_reference = self._fetch_binance_p2p(trade_type='BUY', trans_amount=None)
            sell_reference = self._fetch_binance_p2p(trade_type='SELL', trans_amount=None)

            if not buy_reference or not sell_reference:
                self.stdout.write(
                    self.style.ERROR('❌ Error: No se pudo obtener tasa de referencia')
                )
                return

            # Obtener el precio de la primera oferta (mejor precio)
            best_buy_price = float(buy_reference['data'][0]['adv']['price'])
            best_sell_price = float(sell_reference['data'][0]['adv']['price'])

            # PASO 2: Calcular equivalente de 100 USD en VES
            trans_amount_buy = int(self.TARGET_USD * best_buy_price)
            trans_amount_sell = int(self.TARGET_USD * best_sell_price)

            self.stdout.write(f'  📊 Mejor tasa BUY: {best_buy_price:.4f} VES/USDT')
            self.stdout.write(f'  📊 Mejor tasa SELL: {best_sell_price:.4f} VES/USDT')
            self.stdout.write(f'  💰 {self.TARGET_USD} USD = {trans_amount_buy:,.0f} Bs (BUY) / {trans_amount_sell:,.0f} Bs (SELL)')

            # PASO 3: Consulta CON transAmount en VES para filtrar ofertas de ~100 USD
            self.stdout.write(f'  📍 Paso 2: Obteniendo ofertas para ~{self.TARGET_USD} USD...')

            buy_data = self._fetch_binance_p2p(trade_type='BUY', trans_amount=trans_amount_buy)
            sell_data = self._fetch_binance_p2p(trade_type='SELL', trans_amount=trans_amount_sell)

            if not buy_data or not sell_data:
                self.stdout.write(
                    self.style.ERROR('❌ Error: No se pudieron obtener datos de Binance')
                )
                return

            # PASO 4: Extraer precios y limpiar outliers
            buy_prices_raw = [float(ad['adv']['price']) for ad in buy_data.get('data', [])]
            sell_prices_raw = [float(ad['adv']['price']) for ad in sell_data.get('data', [])]

            if not buy_prices_raw or not sell_prices_raw:
                self.stdout.write(
                    self.style.ERROR('❌ Error: No hay ofertas disponibles')
                )
                return

            # Limpiar outliers con método IQR
            self.stdout.write('  🧹 Limpiando valores atípicos (método IQR)...')

            buy_prices, buy_outliers, buy_stats = self._remove_outliers(buy_prices_raw)
            sell_prices, sell_outliers, sell_stats = self._remove_outliers(sell_prices_raw)

            # Validar que queden suficientes datos después de limpiar
            if not buy_prices or not sell_prices:
                self.stdout.write(
                    self.style.ERROR('❌ Error: No hay suficientes ofertas válidas después de limpiar outliers')
                )
                return

            # Calcular promedios con datos limpios
            avg_buy = sum(buy_prices) / len(buy_prices)
            avg_sell = sum(sell_prices) / len(sell_prices)

            # Mostrar estadísticas detalladas
            self.stdout.write(f'  📊 Ofertas BUY:')
            self.stdout.write(f'     • Original: {len(buy_prices_raw)} ofertas - Rango: {min(buy_prices_raw):.4f} - {max(buy_prices_raw):.4f}')
            if buy_stats and buy_outliers:
                self.stdout.write(f'     • Outliers removidos: {len(buy_outliers)} ({", ".join([f"{o:.4f}" for o in buy_outliers])})')
                self.stdout.write(f'     • Límites IQR: [{buy_stats["lower_bound"]:.4f}, {buy_stats["upper_bound"]:.4f}]')
            self.stdout.write(f'     • Final: {len(buy_prices)} ofertas - Promedio: {avg_buy:.4f}')

            self.stdout.write(f'  📊 Ofertas SELL:')
            self.stdout.write(f'     • Original: {len(sell_prices_raw)} ofertas - Rango: {min(sell_prices_raw):.4f} - {max(sell_prices_raw):.4f}')
            if sell_stats and sell_outliers:
                self.stdout.write(f'     • Outliers removidos: {len(sell_outliers)} ({", ".join([f"{o:.4f}" for o in sell_outliers])})')
                self.stdout.write(f'     • Límites IQR: [{sell_stats["lower_bound"]:.4f}, {sell_stats["upper_bound"]:.4f}]')
            self.stdout.write(f'     • Final: {len(sell_prices)} ofertas - Promedio: {avg_sell:.4f}')

            # Guardar en la base de datos
            buy_note = f'Promedio de {len(buy_prices)} ofertas P2P'
            if buy_outliers:
                buy_note += f' ({len(buy_outliers)} outlier(s) removido(s) con IQR)'

            sell_note = f'Promedio de {len(sell_prices)} ofertas P2P'
            if sell_outliers:
                sell_note += f' ({len(sell_outliers)} outlier(s) removido(s) con IQR)'

            buy_rate, buy_created = ExchangeRate.objects.update_or_create(
                source=ExchangeRate.SOURCE_BINANCE_BUY,
                timestamp=now,
                defaults={
                    'date': now.date(),
                    'rate': Decimal(str(avg_buy)).quantize(Decimal('0.0001')),
                    'notes': buy_note
                }
            )

            sell_rate, sell_created = ExchangeRate.objects.update_or_create(
                source=ExchangeRate.SOURCE_BINANCE_SELL,
                timestamp=now,
                defaults={
                    'date': now.date(),
                    'rate': Decimal(str(avg_sell)).quantize(Decimal('0.0001')),
                    'notes': sell_note
                }
            )

            # Mostrar resultados
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(
                self.style.SUCCESS(f'✓ BINANCE_BUY: {avg_buy:,.4f} Bs/USD {"(creado)" if buy_created else "(actualizado)"}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ BINANCE_SELL: {avg_sell:,.4f} Bs/USD {"(creado)" if sell_created else "(actualizado)"}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Spread: {abs(avg_sell - avg_buy):,.4f} Bs/USD')
            )
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write('')

            # SISTEMA DE ALERTAS: Verificar spread y enviar alertas si cambió de banda
            self.stdout.write('🔔 Verificando sistema de alertas de spread...')

            from exchange_rates.alert_utils import check_and_alert

            try:
                alert_result = check_and_alert()

                if alert_result['success']:
                    spread_pct = alert_result['spread_percent']
                    current_band = alert_result['current_band']
                    previous_band = alert_result['previous_band']

                    # Mostrar información de bandas
                    if alert_result['bands_recalculated']:
                        self.stdout.write(self.style.WARNING('  📊 Bandas recalculadas (nuevo día):'))
                        bands = alert_result['bands']
                        self.stdout.write(f"     MIN: {bands['min']:.2f}% | AVG: {bands['avg']:.2f}% | P75: {bands['p75']:.2f}% | MAX: {bands['max']:.2f}%")

                    # Mostrar estado actual
                    self.stdout.write(f'  📈 Spread actual: {spread_pct:.2f}% → Banda: {current_band}')

                    # Mostrar si hubo cambio de banda
                    if alert_result['band_changed']:
                        self.stdout.write(
                            self.style.WARNING(f'  🚨 CAMBIO DE BANDA: {previous_band} → {current_band}')
                        )

                        if alert_result['alert_sent']:
                            self.stdout.write(
                                self.style.SUCCESS('  ✓ Alerta enviada a Telegram')
                            )
                        else:
                            self.stdout.write(
                                self.style.ERROR('  ✗ Error enviando alerta a Telegram (verificar TELEGRAM_ALERT_URL)')
                            )
                    else:
                        self.stdout.write(f'  ✓ Sin cambios (banda: {current_band})')

                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠️  {alert_result.get('error', 'Error desconocido')}")
                    )

            except Exception as alert_error:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Error en sistema de alertas: {alert_error}')
                )
                # No fallar el comando si las alertas fallan

            self.stdout.write('')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error inesperado: {e}')
            )
            raise

    def _fetch_binance_p2p(self, trade_type, trans_amount=None):
        """
        Consulta el API de Binance P2P

        Args:
            trade_type: Tipo de operación (BUY o SELL)
            trans_amount: Monto en VES para filtrar ofertas (None = sin filtro)

        Returns:
            dict con la respuesta del API o None si falla
        """
        url = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'

        headers = {
            'accept': '*/*',
            'accept-language': 'es-ES,es;q=0.9,en;q=0.8',
            'bnc-level': '0',
            'bnc-location': 'VE',
            'bnc-time-zone': 'America/Caracas',
            'c2ctype': 'c2c_web',
            'cache-control': 'no-cache',
            'clienttype': 'web',
            'content-type': 'application/json',
            'lang': 'es',
            'origin': 'https://p2p.binance.com',
            'pragma': 'no-cache',
            'referer': 'https://p2p.binance.com/es',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        }

        payload = {
            'fiat': self.FIAT,
            'page': 1,
            'rows': self.ROWS,
            'tradeType': trade_type,
            'asset': self.ASSET,
            'countries': [],
            'proMerchantAds': False,
            'shieldMerchantAds': False,
            'filterType': 'all',
            'periods': [],
            'additionalKycVerifyFilter': 0,
            'publisherType': 'merchant',
            'payTypes': [],
            'classifies': ['mass', 'profession', 'fiat_trade'],
            'tradedWith': False,
            'followed': False,
        }

        # Solo agregar transAmount si se especifica (en VES)
        if trans_amount is not None:
            payload['transAmount'] = trans_amount

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # Validar respuesta
            if data.get('code') != '000000':
                self.stdout.write(
                    self.style.ERROR(f'❌ Error del API Binance: {data.get("message", "Unknown error")}')
                )
                return None

            # Validar que haya datos
            if not data.get('data'):
                self.stdout.write(
                    self.style.WARNING(f'⚠️  No hay ofertas disponibles para {trade_type}')
                )
                return None

            return data

        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error de conexión: {e}')
            )
            return None
