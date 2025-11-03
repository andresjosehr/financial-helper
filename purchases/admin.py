from django.contrib import admin
from .models import Purchase, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    readonly_fields = ['id', 'created_at']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['purchase_date', 'user', 'establishment', 'total_ves', 'document_type', 'created_at']
    list_filter = ['purchase_date', 'user', 'establishment', 'document_type', 'payment_method']
    search_fields = ['user__username', 'establishment__name', 'document_number', 'notes']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [PurchaseItemInline]


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ['description', 'purchase', 'product', 'quantity', 'unit_type', 'total_ves']
    list_filter = ['unit_type', 'product']
    search_fields = ['description', 'product_code', 'purchase__user__username']
    readonly_fields = ['id', 'created_at']
