from django.contrib import admin
from .models import ProductCategory, Product


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'created_at']
    list_filter = ['parent']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['normalized_name', 'brand', 'category', 'unit_type', 'created_at']
    list_filter = ['category', 'unit_type', 'brand']
    search_fields = ['normalized_name', 'brand', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
