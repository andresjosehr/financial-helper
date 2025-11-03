import uuid
from django.db import models


class ProductBrand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        db_table = 'product_brands'
        verbose_name = 'Marca de Producto'
        verbose_name_plural = 'Marcas de Productos'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=50, verbose_name='Tipo')  # size, flavor, color, material, version, package
    value = models.CharField(max_length=100, verbose_name='Valor')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        db_table = 'product_variants'
        verbose_name = 'Variante de Producto'
        verbose_name_plural = 'Variantes de Productos'
        ordering = ['type', 'value']
        unique_together = [['type', 'value']]
        indexes = [
            models.Index(fields=['type', 'value'], name='idx_variants_type_value'),
        ]

    def __str__(self):
        return f"{self.type}: {self.value}"


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
    name = models.CharField(max_length=255, verbose_name='Nombre')
    brand = models.ForeignKey(ProductBrand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='Marca')
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='Categoría')
    variants = models.ManyToManyField('ProductVariant', through='ProductVariantAssignment', related_name='products', verbose_name='Variantes')
    description = models.TextField(blank=True, null=True, verbose_name='Descripción')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        db_table = 'products'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['name', 'brand']
        indexes = [
            models.Index(fields=['category'], name='idx_products_category'),
            models.Index(fields=['name'], name='idx_products_name'),
            models.Index(fields=['brand'], name='idx_products_brand'),
        ]

    def __str__(self):
        parts = [self.name]
        if self.brand:
            parts.append(f"({self.brand.name})")
        return ' '.join(parts)


class ProductVariantAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variant_assignments', verbose_name='Producto')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='product_assignments', verbose_name='Variante')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')

    class Meta:
        db_table = 'product_variant_assignments'
        verbose_name = 'Asignación de Variante'
        verbose_name_plural = 'Asignaciones de Variantes'
        unique_together = [['product', 'variant']]
        indexes = [
            models.Index(fields=['product'], name='idx_var_assign_product'),
            models.Index(fields=['variant'], name='idx_var_assign_variant'),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.variant}"
