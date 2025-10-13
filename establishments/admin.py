from django.contrib import admin
from .models import Establishment


@admin.register(Establishment)
class EstablishmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'country', 'phone', 'created_at']
    list_filter = ['country', 'state', 'city']
    search_fields = ['name', 'legal_name', 'tax_id', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']
