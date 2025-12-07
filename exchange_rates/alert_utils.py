"""
Utilidades para el sistema de alertas de spread.

Proporciona funciones para:
- Calcular bandas históricas de spread (MIN/AVG/P75/MAX)
- Clasificar el spread actual en una banda
- Enviar alertas a Telegram
"""

import statistics
import requests
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.conf import settings


def calculate_historical_spreads(days=30, exclude_today=True):
    """
    Calcula los spreads históricos desde ExchangeRate.

    Args:
        days: Número de días históricos a consultar (default: 30)
        exclude_today: Si True, excluye datos del día actual (default: True)

    Returns:
        Lista de spreads porcentuales (floats)
    """
    from exchange_rates.models import ExchangeRate

    # Calcular fecha de inicio
    end_date = date.today()
    if exclude_today:
        end_date = end_date - timedelta(days=1)

    start_date = end_date - timedelta(days=days)

    # Obtener tasas BCV
    bcv_rates = ExchangeRate.objects.filter(
        source=ExchangeRate.SOURCE_BCV,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date').values_list('date', 'rate')

    # Obtener tasas Binance SELL
    binance_rates = ExchangeRate.objects.filter(
        source=ExchangeRate.SOURCE_BINANCE_SELL,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('timestamp').values_list('timestamp', 'rate')

    # Convertir a diccionarios para cruce rápido
    bcv_dict = {}
    for rate_date, rate_value in bcv_rates:
        if rate_date not in bcv_dict:
            bcv_dict[rate_date] = float(rate_value)

    # Calcular spreads
    spreads = []
    for timestamp, binance_rate in binance_rates:
        rate_date = timestamp.date()

        # Buscar tasa BCV más reciente para esta fecha
        bcv_rate = None
        for d in range(7):  # Buscar hasta 7 días atrás
            check_date = rate_date - timedelta(days=d)
            if check_date in bcv_dict:
                bcv_rate = bcv_dict[check_date]
                break

        if bcv_rate:
            binance_float = float(binance_rate)
            spread_bs = binance_float - bcv_rate
            spread_percent = (spread_bs / binance_float) * 100
            spreads.append(spread_percent)

    return spreads


def calculate_spread_bands(spreads):
    """
    Calcula las bandas estadísticas de spread.

    Args:
        spreads: Lista de spreads porcentuales

    Returns:
        Dict con {'min': x, 'avg': x, 'p75': x, 'max': x} o None si no hay datos
    """
    if not spreads or len(spreads) < 4:
        return None

    # Calcular percentiles
    sorted_spreads = sorted(spreads)

    return {
        'min': Decimal(str(round(min(sorted_spreads), 2))),
        'avg': Decimal(str(round(statistics.median(sorted_spreads), 2))),  # Percentil 50
        'p75': Decimal(str(round(statistics.quantiles(sorted_spreads, n=4)[2], 2))),  # Percentil 75
        'max': Decimal(str(round(max(sorted_spreads), 2))),
    }


def calculate_current_spread():
    """
    Calcula el spread actual entre BCV y Binance SELL.

    Returns:
        Tuple (spread_percent, bcv_rate, binance_rate) o (None, None, None) si no hay datos
    """
    from exchange_rates.models import ExchangeRate

    # Obtener última tasa BCV
    latest_bcv = ExchangeRate.objects.filter(
        source=ExchangeRate.SOURCE_BCV
    ).order_by('-date').first()

    # Obtener última tasa Binance SELL
    latest_binance = ExchangeRate.objects.filter(
        source=ExchangeRate.SOURCE_BINANCE_SELL
    ).order_by('-timestamp').first()

    if not latest_bcv or not latest_binance:
        return None, None, None

    bcv_rate = float(latest_bcv.rate)
    binance_rate = float(latest_binance.rate)

    spread_bs = binance_rate - bcv_rate
    spread_percent = (spread_bs / binance_rate) * 100

    return spread_percent, bcv_rate, binance_rate


def classify_spread(spread_percent, bands):
    """
    Clasifica el spread actual en una banda.

    Args:
        spread_percent: Spread porcentual actual (float)
        bands: Dict con valores de bandas {'min', 'avg', 'p75', 'max'}

    Returns:
        String con la banda: 'MIN', 'AVG', 'P75', o 'MAX'
    """
    from exchange_rates.models import AlertState

    if spread_percent < float(bands['avg']):
        return AlertState.BAND_MIN
    elif spread_percent < float(bands['p75']):
        return AlertState.BAND_AVG
    elif spread_percent < float(bands['max']):
        return AlertState.BAND_P75
    else:
        return AlertState.BAND_MAX


def send_telegram_alert(current_band, previous_band, spread_percent, bcv_rate, binance_rate):
    """
    Envía una alerta a Telegram cuando cambia la banda.

    Args:
        current_band: Banda actual ('MIN', 'AVG', 'P75', 'MAX')
        previous_band: Banda anterior
        spread_percent: Spread porcentual actual
        bcv_rate: Tasa BCV actual
        binance_rate: Tasa Binance actual

    Returns:
        True si se envió correctamente, False si falló
    """
    telegram_url = getattr(settings, 'TELEGRAM_ALERT_URL', None)

    if not telegram_url:
        return False

    # Formatear mensaje para CallMeBot (texto plano, sin HTML)
    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    # Emojis de bandas (colores consistentes con chart.html)
    # Indicador visual: rojo (bajo) → amarillo → verde (alto)
    # MIN: red (#ef4444) → 🔴
    # AVG: amber (#f59e0b) → 🟠
    # P75: lime/green (#10b981) → 🟢
    # MAX: blue (#2563eb) → 🔵
    band_emoji = {
        'MIN': '🔴',  # Rojo - spread bajo
        'AVG': '🟠',  # Naranja/Amber - spread medio
        'P75': '🟢',  # Verde - spread bueno
        'MAX': '🔵'   # Azul - spread máximo
    }

    message = f"""🚨 Alerta de Spread

📊 Banda: {band_emoji.get(previous_band, '')} {previous_band} → {band_emoji.get(current_band, '')} {current_band}
📈 Spread: {spread_percent:.2f}%

💵 BCV: {bcv_rate:.4f} Bs/USD
💰 Binance: {binance_rate:.4f} Bs/USD

🕐 {timestamp}"""

    try:
        # CallMeBot API: texto plano sin HTML
        full_url = f"{telegram_url}{requests.utils.quote(message)}"

        response = requests.get(full_url, timeout=10)
        response.raise_for_status()

        return True
    except Exception as e:
        # Log error pero no fallar
        print(f"Error enviando alerta Telegram: {e}")
        return False


def update_alert_state_bands(force=False):
    """
    Actualiza las bandas históricas en AlertState si cambió el día.

    Args:
        force: Si True, fuerza el recálculo incluso si no cambió el día

    Returns:
        True si se recalcularon las bandas, False si se usó cache
    """
    from exchange_rates.models import AlertState

    state = AlertState.get_instance()
    today = date.today()

    # Verificar si necesitamos recalcular
    if not force and state.bands_calculation_date == today:
        return False

    # Calcular nuevas bandas
    spreads = calculate_historical_spreads(days=5, exclude_today=True)
    bands = calculate_spread_bands(spreads)

    if not bands:
        # No hay suficientes datos, mantener bandas actuales
        return False

    # Actualizar estado
    state.bands_calculation_date = today
    state.band_min_value = bands['min']
    state.band_avg_value = bands['avg']
    state.band_p75_value = bands['p75']
    state.band_max_value = bands['max']
    state.save()

    return True


def check_and_alert():
    """
    Verifica el spread actual y envía alerta si cambió de banda.

    Esta es la función principal que debe llamarse desde el comando
    fetch_binance_rates cada 15 minutos.

    Returns:
        Dict con información del estado actual
    """
    from exchange_rates.models import AlertState

    # 1. Obtener estado actual
    state = AlertState.get_instance()

    # 2. Actualizar bandas si cambió el día
    bands_recalculated = update_alert_state_bands()

    # 2.1 Refrescar objeto desde BD para obtener bandas actualizadas
    state.refresh_from_db()

    # 3. Calcular spread actual
    spread_percent, bcv_rate, binance_rate = calculate_current_spread()

    if spread_percent is None:
        return {
            'success': False,
            'error': 'No hay datos suficientes para calcular spread'
        }

    # 4. Obtener bandas desde cache
    bands = {
        'min': state.band_min_value,
        'avg': state.band_avg_value,
        'p75': state.band_p75_value,
        'max': state.band_max_value,
    }

    # 5. Clasificar banda actual
    new_band = classify_spread(spread_percent, bands)

    # 6. Detectar cambio de banda
    previous_band = state.current_band
    band_changed = new_band != previous_band

    # 7. Enviar alerta si cambió
    alert_sent = False
    if band_changed:
        alert_sent = send_telegram_alert(
            new_band,
            previous_band,
            spread_percent,
            bcv_rate,
            binance_rate
        )

    # 8. Actualizar estado
    state.current_band = new_band
    state.last_check = timezone.now()
    if alert_sent:
        state.last_alert_sent = timezone.now()
    state.save()

    return {
        'success': True,
        'spread_percent': spread_percent,
        'current_band': new_band,
        'previous_band': previous_band,
        'band_changed': band_changed,
        'alert_sent': alert_sent,
        'bands_recalculated': bands_recalculated,
        'bands': bands,
    }
