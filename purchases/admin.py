from django.contrib import admin
from django.utils.html import format_html
from .models import Purchase, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    readonly_fields = ['id', 'total_usd_bcv_display', 'total_usd_binance_display', 'created_at']
    fields = ['description', 'product', 'quantity', 'unit_type', 'total_ves', 'total_usd_bcv_display', 'total_usd_binance_display']

    @admin.display(description='Total VES')
    def total_ves_display(self, obj):
        return f"Bs.{obj.total_ves:,.2f}" if obj.total_ves else "-"

    @admin.display(description='USD (BCV)')
    def total_usd_bcv_display(self, obj):
        return f"${obj.total_usd_bcv:.2f}" if obj.total_usd_bcv else "-"

    @admin.display(description='USD (Binance)')
    def total_usd_binance_display(self, obj):
        return f"${obj.total_usd_binance:.2f}" if obj.total_usd_binance else "-"


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['purchase_date', 'user', 'establishment', 'total_ves_display', 'total_usd_bcv_display', 'total_usd_binance_display', 'created_at']
    list_filter = ['purchase_date', 'user', 'establishment']
    search_fields = ['user__username', 'establishment__name', 'notes']
    readonly_fields = ['id', 'total_usd_bcv_display', 'total_usd_binance_display', 'invoice_image_preview', 'created_at', 'updated_at']
    fieldsets = (
        ('Información General', {
            'fields': ('id', 'user', 'establishment', 'purchase_date', 'purchase_time')
        }),
        ('Montos en Bolívares', {
            'fields': ('subtotal_ves', 'tax_ves', 'tax_type', 'tax_percentage', 'total_ves')
        }),
        ('Tasas de Cambio', {
            'fields': ('bcv_rate', 'binance_rate')
        }),
        ('Montos en USD', {
            'fields': ('total_usd_bcv_display', 'total_usd_binance_display')
        }),
        ('Imagen de Factura', {
            'fields': ('invoice_image', 'invoice_image_preview')
        }),
        ('Adicional', {
            'fields': ('notes', 'raw_json', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [PurchaseItemInline]

    @admin.display(description='Total VES')
    def total_ves_display(self, obj):
        return f"Bs.{obj.total_ves:,.2f}" if obj.total_ves else "-"

    @admin.display(description='USD (BCV)')
    def total_usd_bcv_display(self, obj):
        return f"${obj.total_usd_bcv:.2f}" if obj.total_usd_bcv else "-"

    @admin.display(description='USD (Binance)')
    def total_usd_binance_display(self, obj):
        return f"${obj.total_usd_binance:.2f}" if obj.total_usd_binance else "-"

    @admin.display(description='Vista Previa')
    def invoice_image_preview(self, obj):
        if obj.invoice_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-height: 400px; max-width: 100%;"/></a>',
                obj.invoice_image.url,
                obj.invoice_image.url
            )
        return "Sin imagen"


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ['description', 'purchase', 'product', 'quantity', 'unit_type', 'total_ves_display', 'total_usd_bcv_display', 'total_usd_binance_display']
    list_filter = ['unit_type', 'product']
    search_fields = ['description', 'product_code', 'purchase__user__username']
    readonly_fields = ['id', 'total_usd_bcv_display', 'total_usd_binance_display', 'created_at']

    @admin.display(description='Total VES')
    def total_ves_display(self, obj):
        return f"Bs.{obj.total_ves:,.2f}" if obj.total_ves else "-"

    @admin.display(description='USD (BCV)')
    def total_usd_bcv_display(self, obj):
        return f"${obj.total_usd_bcv:.2f}" if obj.total_usd_bcv else "-"

    @admin.display(description='USD (Binance)')
    def total_usd_binance_display(self, obj):
        return f"${obj.total_usd_binance:.2f}" if obj.total_usd_binance else "-"
