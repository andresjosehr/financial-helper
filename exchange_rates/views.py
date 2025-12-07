from datetime import date, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from .models import ExchangeRate, AlertState


def chart_view(request):
    """Vista para mostrar el gráfico de tasas BCV."""
    return render(request, 'exchange_rates/chart.html')


def api_bcv_rates(request):
    """
    API endpoint para obtener tasas BCV y Binance SELL.

    Query params:
    - days: número de días hacia atrás (default: 7)
    - end_date: fecha final en formato YYYY-MM-DD (default: hoy)
    """
    # Obtener parámetros
    days = int(request.GET.get('days', 7))
    end_date_str = request.GET.get('end_date')

    # Determinar fecha final
    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
    else:
        end_date = date.today()

    # Calcular fecha inicial
    start_date = end_date - timedelta(days=days - 1)

    # Obtener tasas BCV
    bcv_rates = ExchangeRate.objects.filter(
        source=ExchangeRate.SOURCE_BCV,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date').values('date', 'rate')

    # Obtener tasas Binance SELL (todos los snapshots horarios)
    binance_rates = ExchangeRate.objects.filter(
        source=ExchangeRate.SOURCE_BINANCE_SELL,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('timestamp').values('timestamp', 'rate')

    # Obtener bandas desde AlertState
    alert_state = AlertState.get_instance()

    # Formatear respuesta
    data = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'days': days,
        'bcv': [
            {
                'date': rate['date'].isoformat(),
                'rate': float(rate['rate'])
            }
            for rate in bcv_rates
        ],
        'binance_sell': [
            {
                'timestamp': rate['timestamp'].isoformat(),
                'rate': float(rate['rate'])
            }
            for rate in binance_rates
        ],
        'bands': {
            'min': float(alert_state.band_min_value),
            'avg': float(alert_state.band_avg_value),
            'p75': float(alert_state.band_p75_value),
            'max': float(alert_state.band_max_value),
            'calculation_date': alert_state.bands_calculation_date.isoformat(),
            'current_band': alert_state.current_band,
        }
    }

    return JsonResponse(data)
