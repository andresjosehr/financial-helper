from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Max, Min
from .models import ExchangeRate, AlertState


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    """
    Configuración del admin para tasas de cambio.
    """

    list_display = [
        'date',
        'source_display',
        'rate_formatted',
        'variation_indicator',
        'fetched_at',
        'has_notes'
    ]

    list_filter = [
        'source',
        'date',
        ('fetched_at', admin.DateFieldListFilter),
    ]

    search_fields = [
        'notes',
    ]

    ordering = ['-date', 'source']

    readonly_fields = [
        'id',
        'fetched_at',
        'rate_formatted',
        'previous_rate_comparison'
    ]

    fieldsets = [
        ('Información Principal', {
            'fields': ['source', 'rate', 'date']
        }),
        ('Metadatos', {
            'fields': ['id', 'fetched_at', 'notes'],
            'classes': ['collapse']
        }),
        ('Análisis', {
            'fields': ['rate_formatted', 'previous_rate_comparison'],
            'classes': ['collapse']
        }),
    ]

    date_hierarchy = 'date'

    actions = ['duplicate_for_today']

    def source_display(self, obj):
        """Muestra la fuente con color distintivo."""
        colors = {
            'BCV': '#1e40af',  # Azul oscuro
            'BINANCE_BUY': '#15803d',  # Verde oscuro
            'BINANCE_SELL': '#b91c1c',  # Rojo oscuro
        }
        color = colors.get(obj.source, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_source_display()
        )
    source_display.short_description = 'Fuente'
    source_display.admin_order_field = 'source'

    def rate_formatted(self, obj):
        """Muestra la tasa formateada con separadores de miles."""
        return f"{obj.rate:,.4f} Bs/USD"
    rate_formatted.short_description = 'Tasa Formateada'

    def variation_indicator(self, obj):
        """Muestra un indicador visual de variación vs. día anterior."""
        try:
            previous = ExchangeRate.objects.filter(
                source=obj.source,
                date__lt=obj.date
            ).order_by('-date').first()

            if not previous:
                return format_html('<span style="color: gray;">—</span>')

            diff = obj.rate - previous.rate
            percent = (diff / previous.rate) * 100

            if abs(diff) < 0.01:  # Cambio insignificante
                return format_html('<span style="color: gray;">→ Sin cambio</span>')

            if diff > 0:
                return format_html(
                    '<span style="color: #dc2626; font-weight: bold;">↑ +{:.2f}% (+{:.4f})</span>',
                    percent, diff
                )
            else:
                return format_html(
                    '<span style="color: #16a34a; font-weight: bold;">↓ {:.2f}% ({:.4f})</span>',
                    percent, diff
                )
        except Exception:
            return format_html('<span style="color: gray;">—</span>')

    variation_indicator.short_description = 'Variación'

    def has_notes(self, obj):
        """Indicador de si tiene notas."""
        if obj.notes:
            return format_html('<span style="color: #2563eb;">✓ Sí</span>')
        return format_html('<span style="color: #9ca3af;">—</span>')
    has_notes.short_description = 'Notas'
    has_notes.admin_order_field = 'notes'

    def previous_rate_comparison(self, obj):
        """Muestra comparación con tasas anteriores (últimos 7 días)."""
        try:
            from datetime import timedelta

            week_ago = obj.date - timedelta(days=7)
            previous_rates = ExchangeRate.objects.filter(
                source=obj.source,
                date__gte=week_ago,
                date__lt=obj.date
            ).order_by('-date')[:7]

            if not previous_rates:
                return "No hay datos anteriores para comparar"

            html = ['<table style="border-collapse: collapse; width: 100%;">']
            html.append('<tr style="background: #f3f4f6;"><th>Fecha</th><th>Tasa</th><th>Diferencia</th></tr>')

            for prev in previous_rates:
                diff = obj.rate - prev.rate
                diff_color = '#dc2626' if diff > 0 else '#16a34a' if diff < 0 else '#6b7280'
                diff_symbol = '↑' if diff > 0 else '↓' if diff < 0 else '→'

                html.append(
                    f'<tr>'
                    f'<td style="padding: 4px;">{prev.date}</td>'
                    f'<td style="padding: 4px;">{prev.rate:,.4f}</td>'
                    f'<td style="padding: 4px; color: {diff_color};">{diff_symbol} {diff:+.4f}</td>'
                    f'</tr>'
                )

            html.append('</table>')
            return format_html(''.join(html))

        except Exception as e:
            return f"Error al calcular: {str(e)}"

    previous_rate_comparison.short_description = 'Comparación (7 días)'

    def duplicate_for_today(self, request, queryset):
        """Acción para duplicar tasas seleccionadas para la fecha de hoy."""
        from datetime import date

        today = date.today()
        created_count = 0

        for rate in queryset:
            # Verificar que no exista ya
            exists = ExchangeRate.objects.filter(
                source=rate.source,
                date=today
            ).exists()

            if not exists:
                ExchangeRate.objects.create(
                    source=rate.source,
                    rate=rate.rate,
                    date=today,
                    notes=f"Duplicado de {rate.date} - {rate.notes or 'Sin notas'}"
                )
                created_count += 1

        self.message_user(
            request,
            f"Se crearon {created_count} tasas para hoy ({today}). "
            f"Las que ya existían fueron omitidas."
        )

    duplicate_for_today.short_description = "Duplicar tasas seleccionadas para hoy"

    def get_queryset(self, request):
        """Optimiza queryset para evitar N+1 queries."""
        qs = super().get_queryset(request)
        # Podríamos agregar select_related/prefetch_related si tuviéramos FKs
        return qs

    class Media:
        css = {
            'all': ['admin/css/changelists.css']
        }


@admin.register(AlertState)
class AlertStateAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el estado de alertas.
    Solo debe existir 1 registro (singleton).
    """

    list_display = [
        'current_band_display',
        'spread_info',
        'last_check',
        'last_alert_sent',
        'bands_calculation_date',
    ]

    readonly_fields = [
        'id',
        'current_band_display',
        'last_check',
        'last_alert_sent',
        'bands_calculation_date',
        'band_min_value',
        'band_avg_value',
        'band_p75_value',
        'band_max_value',
        'spread_info',
    ]

    fieldsets = [
        ('Estado Actual', {
            'fields': ['current_band_display', 'spread_info']
        }),
        ('Timestamps', {
            'fields': ['last_check', 'last_alert_sent']
        }),
        ('Bandas Históricas (Cache)', {
            'fields': [
                'bands_calculation_date',
                'band_min_value',
                'band_avg_value',
                'band_p75_value',
                'band_max_value',
            ],
            'description': 'Bandas calculadas una vez al día (excluye datos del día actual)'
        }),
        ('Metadatos', {
            'fields': ['id'],
            'classes': ['collapse']
        }),
    ]

    def has_add_permission(self, request):
        """No permitir crear nuevos registros (singleton)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar el registro (singleton)."""
        return False

    def current_band_display(self, obj):
        """Muestra la banda actual con color distintivo."""
        colors = {
            'MIN': '#16a34a',  # Verde
            'AVG': '#eab308',  # Amarillo
            'P75': '#f97316',  # Naranja
            'MAX': '#dc2626',  # Rojo
        }
        color = colors.get(obj.current_band, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 16px;">{}</span>',
            color,
            obj.get_current_band_display()
        )
    current_band_display.short_description = 'Banda Actual'

    def spread_info(self, obj):
        """Muestra información del spread actual."""
        try:
            from exchange_rates.alert_utils import calculate_current_spread

            spread_percent, bcv_rate, binance_rate = calculate_current_spread()

            if spread_percent is None:
                return format_html('<span style="color: gray;">Sin datos</span>')

            # Determinar color según banda
            colors = {
                'MIN': '#16a34a',
                'AVG': '#eab308',
                'P75': '#f97316',
                'MAX': '#dc2626',
            }
            color = colors.get(obj.current_band, '#6b7280')

            html = [
                f'<div style="padding: 10px; background: #f3f4f6; border-radius: 4px;">',
                f'<div style="font-size: 18px; font-weight: bold; color: {color};">',
                f'{spread_percent:.2f}%</div>',
                f'<div style="margin-top: 8px; font-size: 12px; color: #6b7280;">',
                f'BCV: {bcv_rate:.4f} Bs/USD<br>',
                f'Binance: {binance_rate:.4f} Bs/USD',
                f'</div>',
                f'</div>'
            ]

            return format_html(''.join(html))
        except Exception as e:
            return format_html(
                '<span style="color: #dc2626;">Error: {}</span>',
                str(e)
            )

    spread_info.short_description = 'Spread Actual'

    def changelist_view(self, request, extra_context=None):
        """Redirigir al único registro si existe."""
        if AlertState.objects.exists():
            obj = AlertState.get_instance()
            from django.shortcuts import redirect
            from django.urls import reverse
            return redirect(
                reverse('admin:exchange_rates_alertstate_change', args=[obj.pk])
            )
        return super().changelist_view(request, extra_context=extra_context)
