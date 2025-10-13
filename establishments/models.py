import uuid
from django.db import models


class Establishment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name='Nombre')
    legal_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Razón Social')
    tax_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='RIF/NIT')
    address = models.TextField(blank=True, null=True, verbose_name='Dirección')
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ciudad')
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name='Estado')
    postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name='Código Postal')
    country = models.CharField(max_length=100, default='Venezuela', verbose_name='País')
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name='Teléfono')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    website = models.URLField(blank=True, null=True, verbose_name='Sitio Web')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        db_table = 'establishments'
        verbose_name = 'Establecimiento'
        verbose_name_plural = 'Establecimientos'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='idx_establishments_name'),
        ]

    def __str__(self):
        return self.name
