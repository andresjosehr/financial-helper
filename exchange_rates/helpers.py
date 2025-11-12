"""
Funciones helper para trabajar con tasas de cambio.

Este módulo provee una API conveniente para consultar y convertir
montos usando las tasas de cambio almacenadas.
"""

from decimal import Decimal
from datetime import date
from typing import Optional, Dict
from .models import ExchangeRate


def get_bcv_rate(target_date: Optional[date] = None) -> Optional[Decimal]:
    """
    Obtiene la tasa del BCV para una fecha específica.

    Args:
        target_date: Fecha objetivo (default: hoy)

    Returns:
        Decimal con la tasa o None si no existe

    Examples:
        >>> rate = get_bcv_rate()
        >>> rate = get_bcv_rate(date(2024, 1, 15))
    """
    return ExchangeRate.get_rate_value(ExchangeRate.SOURCE_BCV, target_date)


def get_binance_buy_rate(target_date: Optional[date] = None) -> Optional[Decimal]:
    """
    Obtiene la tasa de compra de Binance P2P para una fecha específica.

    Args:
        target_date: Fecha objetivo (default: hoy)

    Returns:
        Decimal con la tasa o None si no existe

    Examples:
        >>> rate = get_binance_buy_rate()
    """
    return ExchangeRate.get_rate_value(ExchangeRate.SOURCE_BINANCE_BUY, target_date)


def get_binance_sell_rate(target_date: Optional[date] = None) -> Optional[Decimal]:
    """
    Obtiene la tasa de venta de Binance P2P para una fecha específica.

    Args:
        target_date: Fecha objetivo (default: hoy)

    Returns:
        Decimal con la tasa o None si no existe

    Examples:
        >>> rate = get_binance_sell_rate()
    """
    return ExchangeRate.get_rate_value(ExchangeRate.SOURCE_BINANCE_SELL, target_date)


def get_all_rates(target_date: Optional[date] = None) -> Dict[str, Decimal]:
    """
    Obtiene todas las tasas disponibles para una fecha.

    Args:
        target_date: Fecha objetivo (default: hoy)

    Returns:
        Diccionario con {source_code: rate_value}

    Examples:
        >>> rates = get_all_rates()
        >>> print(rates)
        {'BCV': Decimal('36.50'), 'BINANCE_BUY': Decimal('37.00')}
    """
    return ExchangeRate.get_latest_rates(target_date)


def ves_to_usd(
    ves_amount: Decimal,
    source: str = ExchangeRate.SOURCE_BINANCE_BUY,
    target_date: Optional[date] = None
) -> Optional[Decimal]:
    """
    Convierte de VES a USD.

    Args:
        ves_amount: Cantidad en bolívares
        source: Fuente de tasa a usar (default: BINANCE_BUY)
        target_date: Fecha objetivo (default: hoy)

    Returns:
        Decimal con el monto en USD o None si no hay tasa

    Examples:
        >>> usd = ves_to_usd(Decimal('365.00'))
        >>> usd = ves_to_usd(Decimal('730.00'), source=ExchangeRate.SOURCE_BCV)
    """
    return ExchangeRate.convert_ves_to_usd(ves_amount, source, target_date)


def usd_to_ves(
    usd_amount: Decimal,
    source: str = ExchangeRate.SOURCE_BINANCE_BUY,
    target_date: Optional[date] = None
) -> Optional[Decimal]:
    """
    Convierte de USD a VES.

    Args:
        usd_amount: Cantidad en dólares
        source: Fuente de tasa a usar (default: BINANCE_BUY)
        target_date: Fecha objetivo (default: hoy)

    Returns:
        Decimal con el monto en VES o None si no hay tasa

    Examples:
        >>> ves = usd_to_ves(Decimal('10.00'))
        >>> ves = usd_to_ves(Decimal('20.00'), source=ExchangeRate.SOURCE_BCV)
    """
    return ExchangeRate.convert_usd_to_ves(usd_amount, source, target_date)


def get_rate_spread(target_date: Optional[date] = None) -> Optional[Decimal]:
    """
    Calcula el spread entre la tasa de compra y venta de Binance.

    Args:
        target_date: Fecha objetivo (default: hoy)

    Returns:
        Decimal con el spread o None si no hay tasas

    Examples:
        >>> spread = get_rate_spread()
        >>> print(f"Spread: {spread:.4f} Bs")
    """
    buy = get_binance_buy_rate(target_date)
    sell = get_binance_sell_rate(target_date)

    if buy and sell:
        return sell - buy

    return None


def get_bcv_binance_diff(target_date: Optional[date] = None) -> Optional[Decimal]:
    """
    Calcula la diferencia entre BCV y Binance (compra).

    Args:
        target_date: Fecha objetivo (default: hoy)

    Returns:
        Decimal con la diferencia o None si no hay tasas

    Examples:
        >>> diff = get_bcv_binance_diff()
        >>> print(f"Binance está {diff:.4f} Bs más alto que BCV")
    """
    bcv = get_bcv_rate(target_date)
    binance = get_binance_buy_rate(target_date)

    if bcv and binance:
        return binance - bcv

    return None


def get_rate_info(target_date: Optional[date] = None) -> Dict:
    """
    Obtiene información completa sobre las tasas de una fecha.

    Args:
        target_date: Fecha objetivo (default: hoy)

    Returns:
        Diccionario con toda la información de tasas y análisis

    Examples:
        >>> info = get_rate_info()
        >>> print(f"BCV: {info['bcv']}")
        >>> print(f"Spread Binance: {info['binance_spread']}")
    """
    if target_date is None:
        target_date = date.today()

    bcv = get_bcv_rate(target_date)
    binance_buy = get_binance_buy_rate(target_date)
    binance_sell = get_binance_sell_rate(target_date)
    spread = get_rate_spread(target_date)
    bcv_diff = get_bcv_binance_diff(target_date)

    return {
        'date': target_date,
        'bcv': bcv,
        'binance_buy': binance_buy,
        'binance_sell': binance_sell,
        'binance_spread': spread,
        'bcv_binance_diff': bcv_diff,
        'has_all_rates': all([bcv, binance_buy, binance_sell]),
    }


def format_rate(rate: Optional[Decimal], decimals: int = 2) -> str:
    """
    Formatea una tasa para mostrar en UI.

    Args:
        rate: Tasa a formatear
        decimals: Número de decimales (default: 2)

    Returns:
        String formateado o "N/A" si rate es None

    Examples:
        >>> formatted = format_rate(Decimal('36.5000'))
        >>> print(formatted)  # "36.50 Bs/USD"
    """
    if rate is None:
        return "N/A"

    format_str = f"{{:,.{decimals}f}} Bs/USD"
    return format_str.format(rate)


def format_money(amount: Optional[Decimal], currency: str = 'VES', decimals: int = 2) -> str:
    """
    Formatea un monto de dinero para mostrar en UI.

    Args:
        amount: Monto a formatear
        currency: Moneda ('VES' o 'USD')
        decimals: Número de decimales (default: 2)

    Returns:
        String formateado con símbolo de moneda

    Examples:
        >>> formatted = format_money(Decimal('1234.56'), 'VES')
        >>> print(formatted)  # "Bs 1,234.56"
    """
    if amount is None:
        return "N/A"

    symbol = 'Bs' if currency == 'VES' else '$'
    format_str = f"{{}} {{:,.{decimals}f}}"
    return format_str.format(symbol, amount)
