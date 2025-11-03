import uuid
from django.db import models


class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name='Categoría Padre')
    description = models.TextField(blank=True, null=True, verbose_name='Descripción')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        db_table = 'product_categories'
        verbose_name = 'Categoría de Producto'
        verbose_name_plural = 'Categorías de Productos'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    normalized_name = models.CharField(max_length=255, verbose_name='Nombre Normalizado')
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='Categoría')
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name='Marca')
    description = models.TextField(blank=True, null=True, verbose_name='Descripción')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        db_table = 'products'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['normalized_name', 'brand']
        unique_together = [['normalized_name', 'brand']]
        indexes = [
            models.Index(fields=['category'], name='idx_products_category'),
            models.Index(fields=['normalized_name'], name='idx_products_normalized_name'),
        ]

    def __str__(self):
        parts = [self.normalized_name]
        if self.brand:
            parts.append(f"({self.brand})")
        return ' '.join(parts)
