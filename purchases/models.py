import uuid
from django.db import models
from django.contrib.auth.models import User
from establishments.models import Establishment
from products.models import Product


class Purchase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases', verbose_name='Usuario')
    establishment = models.ForeignKey(Establishment, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases', verbose_name='Establecimiento')

    # Document metadata
    document_type = models.CharField(max_length=50, verbose_name='Tipo de Documento')
    document_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='Número de Documento')
    purchase_date = models.DateField(verbose_name='Fecha de Compra')
    purchase_time = models.TimeField(blank=True, null=True, verbose_name='Hora de Compra')

    # Totals in VES
    subtotal_ves = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Subtotal (VES)')
    discount_ves = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Descuento (VES)')
    total_ves = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Total (VES)')

    # Exchange rates snapshot
    bcv_rate = models.DecimalField(max_digits=20, decimal_places=8, blank=True, null=True, verbose_name='Tasa BCV')
    binance_rate = models.DecimalField(max_digits=20, decimal_places=8, blank=True, null=True, verbose_name='Tasa Binance')

    # Totals in USD
    total_usd_bcv = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Total USD (BCV)')
    total_usd_binance = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Total USD (Binance)')

    # Tax information
    tax_ves = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Impuesto (VES)')
    tax_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tipo de Impuesto')
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Porcentaje de Impuesto')
    tax_base = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Base Imponible')

    # Payment info
    payment_method = models.CharField(max_length=50, blank=True, null=True, verbose_name='Método de Pago')
    payment_reference = models.CharField(max_length=255, blank=True, null=True, verbose_name='Referencia de Pago')
    bank_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Banco')
    card_last_digits = models.CharField(max_length=4, blank=True, null=True, verbose_name='Últimos 4 Dígitos')
    tip_ves = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Propina (VES)')

    # Additional info
    cashier = models.CharField(max_length=100, blank=True, null=True, verbose_name='Cajero')
    vendor = models.CharField(max_length=100, blank=True, null=True, verbose_name='Vendedor')
    register_number = models.CharField(max_length=50, blank=True, null=True, verbose_name='Número de Caja')
    notes = models.TextField(blank=True, null=True, verbose_name='Notas')

    # Original JSON
    raw_json = models.JSONField(blank=True, null=True, verbose_name='JSON Original')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        db_table = 'purchases'
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-purchase_date', '-purchase_time']
        indexes = [
            models.Index(fields=['user'], name='idx_purchases_user'),
            models.Index(fields=['purchase_date'], name='idx_purchases_date'),
            models.Index(fields=['establishment'], name='idx_purchases_establishment'),
            models.Index(fields=['user', 'purchase_date'], name='idx_purchases_user_date'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.establishment or 'N/A'} - {self.purchase_date}"


class PurchaseItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items', verbose_name='Compra')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_items', verbose_name='Producto')

    # Item details from receipt
    product_code = models.CharField(max_length=100, blank=True, null=True, verbose_name='Código de Producto')
    description = models.CharField(max_length=500, verbose_name='Descripción')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='Cantidad')
    unit_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tipo de Unidad')

    # Prices
    total_ves = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Total (VES)')
    total_usd_bcv = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Total USD (BCV)')
    total_usd_binance = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Total USD (Binance)')

    # Normalized price per standard unit
    price_per_unit_ves = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Precio/Unidad Std (VES)')
    price_per_unit_usd_bcv = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Precio/Unidad Std USD (BCV)')
    price_per_unit_usd_binance = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name='Precio/Unidad Std USD (Binance)')

    notes = models.TextField(blank=True, null=True, verbose_name='Notas')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')

    class Meta:
        db_table = 'purchase_items'
        verbose_name = 'Item de Compra'
        verbose_name_plural = 'Items de Compra'
        ordering = ['purchase', 'id']
        indexes = [
            models.Index(fields=['purchase'], name='idx_purch_items_purchase'),
            models.Index(fields=['product'], name='idx_purch_items_product'),
            models.Index(fields=['product', 'created_at'], name='idx_purch_item_prod_date'),
        ]

    @property
    def unit_price_ves(self):
        """Calculate unit price in VES from total and quantity"""
        if self.quantity and self.quantity > 0:
            return self.total_ves / self.quantity
        return None

    @property
    def unit_price_usd_bcv(self):
        """Calculate unit price in USD (BCV rate) from total and quantity"""
        if self.quantity and self.quantity > 0 and self.total_usd_bcv:
            return self.total_usd_bcv / self.quantity
        return None

    @property
    def unit_price_usd_binance(self):
        """Calculate unit price in USD (Binance rate) from total and quantity"""
        if self.quantity and self.quantity > 0 and self.total_usd_binance:
            return self.total_usd_binance / self.quantity
        return None

    def __str__(self):
        return f"{self.description} - {self.quantity} {self.unit_type or ''}"
