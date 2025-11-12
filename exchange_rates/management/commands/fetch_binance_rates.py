"""
Comando para actualizar tasas de Binance P2P en tiempo real

Estrategia de consulta:
1. Primera consulta SIN transAmount para obtener la mejor tasa actual
2. Calcular equivalente de 100 USD en VES con esa tasa
3. Segunda consulta CON transAmount en VES para filtrar ofertas de ~100 USD
4. Guardar el promedio simple de los precios

Uso:
    docker compose exec web python manage.py update_binance_rates
"""

import requests
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from exchange_rates.models import ExchangeRate


class Command(BaseCommand):
    help = 'Actualiza tasas de Binance P2P consultando el API directamente'

    # Configuración fija
    ASSET = 'USDT'
    FIAT = 'VES'
    TARGET_USD = 100  # Queremos ofertas para ~100 USD
    ROWS = 20  # Número de ofertas a promediar

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

            # PASO 4: Calcular promedios simples
            buy_prices = [float(ad['adv']['price']) for ad in buy_data.get('data', [])]
            sell_prices = [float(ad['adv']['price']) for ad in sell_data.get('data', [])]

            if not buy_prices or not sell_prices:
                self.stdout.write(
                    self.style.ERROR('❌ Error: No hay ofertas disponibles')
                )
                return

            avg_buy = sum(buy_prices) / len(buy_prices)
            avg_sell = sum(sell_prices) / len(sell_prices)

            self.stdout.write(f'  📊 Ofertas BUY: {len(buy_prices)} - Rango: {min(buy_prices):.4f} - {max(buy_prices):.4f}')
            self.stdout.write(f'  📊 Ofertas SELL: {len(sell_prices)} - Rango: {min(sell_prices):.4f} - {max(sell_prices):.4f}')

            # Guardar en la base de datos
            buy_rate, buy_created = ExchangeRate.objects.update_or_create(
                source=ExchangeRate.SOURCE_BINANCE_BUY,
                timestamp=now,
                defaults={
                    'date': now.date(),
                    'rate': Decimal(str(avg_buy)).quantize(Decimal('0.0001')),
                    'notes': f'Promedio simple de {len(buy_prices)} ofertas P2P'
                }
            )

            sell_rate, sell_created = ExchangeRate.objects.update_or_create(
                source=ExchangeRate.SOURCE_BINANCE_SELL,
                timestamp=now,
                defaults={
                    'date': now.date(),
                    'rate': Decimal(str(avg_sell)).quantize(Decimal('0.0001')),
                    'notes': f'Promedio simple de {len(sell_prices)} ofertas P2P'
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
