from django.contrib import admin
from .models import ProductBrand, ProductVariant, ProductCategory, Product, ProductVariantAssignment


@admin.register(ProductBrand)
class ProductBrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['type', 'value', 'created_at']
    list_filter = ['type']
    search_fields = ['type', 'value']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'created_at']
    list_filter = ['parent']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


class ProductVariantAssignmentInline(admin.TabularInline):
    model = ProductVariantAssignment
    extra = 1
    readonly_fields = ['id', 'created_at']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'category', 'created_at']
    list_filter = ['category', 'brand']
    search_fields = ['name', 'brand__name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ProductVariantAssignmentInline]
