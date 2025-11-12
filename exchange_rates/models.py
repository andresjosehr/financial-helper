import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta


class ExchangeRate(models.Model):
    """
    Tasas de cambio VES/USD de diferentes fuentes.

    Almacena un snapshot histórico de tasas para análisis y conversiones.
    Cada fuente puede tener una sola tasa por día (unique_together).
    """

    # Fuentes de tasas de cambio
    SOURCE_BCV = 'BCV'
    SOURCE_BINANCE_BUY = 'BINANCE_BUY'
    SOURCE_BINANCE_SELL = 'BINANCE_SELL'

    SOURCES = [
        (SOURCE_BCV, 'Banco Central de Venezuela'),
        (SOURCE_BINANCE_BUY, 'Binance (Compra P2P)'),
        (SOURCE_BINANCE_SELL, 'Binance (Venta P2P)'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCES,
        verbose_name='Fuente',
        help_text='Origen de la tasa de cambio'
    )

    rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        verbose_name='Tasa',
        help_text='VES por 1 USD (ej: 36.5000 significa 36.50 Bs por dólar)'
    )

    date = models.DateField(
        verbose_name='Fecha',
        help_text='Fecha de vigencia de la tasa',
        db_index=True
    )

    timestamp = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Timestamp',
        help_text='Fecha y hora exacta del snapshot (para tasas con intervalo horario)',
        db_index=True
    )

    fetched_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Registro',
        help_text='Momento en que se registró esta tasa en el sistema'
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notas',
        help_text='Información adicional sobre esta tasa (opcional)'
    )

    class Meta:
        db_table = 'exchange_rates'
        verbose_name = 'Tasa de Cambio'
        verbose_name_plural = 'Tasas de Cambio'
        ordering = ['-timestamp', '-date', 'source']
        unique_together = [['source', 'timestamp']]
        indexes = [
            models.Index(fields=['source', 'timestamp'], name='idx_source_timestamp'),
            models.Index(fields=['-timestamp'], name='idx_timestamp_desc'),
            models.Index(fields=['source', '-timestamp'], name='idx_source_ts_desc'),
            models.Index(fields=['source', 'date'], name='idx_source_date'),
            models.Index(fields=['-date'], name='idx_date_desc'),
        ]

    def __str__(self):
        return f"{self.get_source_display()} - {self.date}: {self.rate:,.4f} Bs/USD"

    def clean(self):
        """Validaciones personalizadas."""
        super().clean()

        # No permitir tasas futuras (más de 1 día en el futuro para tolerancia)
        if self.date and self.date > date.today() + timedelta(days=1):
            raise ValidationError({
                'date': 'No se pueden registrar tasas de cambio futuras.'
            })

        # Validar que la tasa sea razonable (mayor a 0.01, menor a 1,000,000)
        if self.rate and (self.rate < Decimal('0.01') or self.rate > Decimal('1000000')):
            raise ValidationError({
                'rate': 'La tasa debe estar entre 0.01 y 1,000,000 Bs/USD.'
            })

    def save(self, *args, **kwargs):
        """Override save para ejecutar validaciones."""
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_rate(cls, source, target_date=None):
        """
        Obtiene la tasa más reciente para una fuente y fecha.

        Args:
            source: Constante SOURCE_* o string con el código de fuente
            target_date: Fecha objetivo (default: hoy)

        Returns:
            ExchangeRate instance o None si no existe

        Examples:
            >>> rate = ExchangeRate.get_rate(ExchangeRate.SOURCE_BCV)
            >>> rate = ExchangeRate.get_rate('BINANCE_BUY', date(2024, 1, 15))
        """
        if target_date is None:
            target_date = date.today()

        try:
            return cls.objects.filter(
                source=source,
                date__lte=target_date
            ).order_by('-date').first()
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_rate_value(cls, source, target_date=None, default=None):
        """
        Obtiene solo el valor decimal de la tasa.

        Args:
            source: Constante SOURCE_* o string con el código de fuente
            target_date: Fecha objetivo (default: hoy)
            default: Valor por defecto si no existe (default: None)

        Returns:
            Decimal con la tasa o default si no existe

        Examples:
            >>> bcv_rate = ExchangeRate.get_rate_value('BCV', default=Decimal('36.50'))
        """
        rate_obj = cls.get_rate(source, target_date)
        return rate_obj.rate if rate_obj else default

    @classmethod
    def get_latest_rates(cls, target_date=None):
        """
        Obtiene las últimas tasas de todas las fuentes.

        Args:
            target_date: Fecha objetivo (default: hoy)

        Returns:
            Dict con {source_code: rate_value} para cada fuente disponible

        Examples:
            >>> rates = ExchangeRate.get_latest_rates()
            >>> print(rates)  # {'BCV': Decimal('36.50'), 'BINANCE_BUY': Decimal('36.75')}
        """
        if target_date is None:
            target_date = date.today()

        result = {}
        for source_code, _ in cls.SOURCES:
            rate = cls.get_rate_value(source_code, target_date)
            if rate:
                result[source_code] = rate

        return result

    @classmethod
    def convert_ves_to_usd(cls, ves_amount, source, target_date=None):
        """
        Convierte de VES a USD usando la tasa especificada.

        Args:
            ves_amount: Cantidad en bolívares
            source: Fuente de tasa a usar
            target_date: Fecha objetivo (default: hoy)

        Returns:
            Decimal con el monto en USD o None si no hay tasa

        Examples:
            >>> usd = ExchangeRate.convert_ves_to_usd(Decimal('365.00'), 'BCV')
        """
        rate = cls.get_rate_value(source, target_date)
        if rate and rate > 0:
            return ves_amount / rate
        return None

    @classmethod
    def convert_usd_to_ves(cls, usd_amount, source, target_date=None):
        """
        Convierte de USD a VES usando la tasa especificada.

        Args:
            usd_amount: Cantidad en dólares
            source: Fuente de tasa a usar
            target_date: Fecha objetivo (default: hoy)

        Returns:
            Decimal con el monto en VES o None si no hay tasa

        Examples:
            >>> ves = ExchangeRate.convert_usd_to_ves(Decimal('10.00'), 'BINANCE_BUY')
        """
        rate = cls.get_rate_value(source, target_date)
        if rate:
            return usd_amount * rate
        return None
