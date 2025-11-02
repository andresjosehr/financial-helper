import uuid
from django.db import models
from django.contrib.auth.models import User


class UserGeminiConfig(models.Model):
    """
    Configuración de Gemini por usuario.
    Cada usuario puede tener sus propias cookies de Gemini.
    """
    
    # Opciones de modelos disponibles
    MODEL_CHOICES = [
        ('gemini-2.5-flash', 'Gemini 2.5 Flash (Rápido y eficiente) ⚡'),
        ('gemini-2.5-pro', 'Gemini 2.5 Pro (Más potente, límite diario) 🧠'),
        ('gemini-2.0-flash', 'Gemini 2.0 Flash (Versión anterior)'),
        ('gemini-2.0-flash-thinking', 'Gemini 2.0 Flash Thinking (Con razonamiento)'),
        ('unspecified', 'Sin especificar (Usa modelo por defecto de Gemini)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='gemini_config',
        verbose_name='Usuario'
    )
    telegram_user = models.CharField(
        max_length=100, 
        unique=True, 
        blank=True, 
        null=True,
        verbose_name='Usuario de Telegram',
        help_text='Username de Telegram del usuario (sin @)'
    )
    
    # Cookies de Gemini
    gemini_psid = models.TextField(
        blank=True,
        null=True,
        verbose_name='__Secure-1PSID',
        help_text='Cookie __Secure-1PSID de gemini.google.com'
    )
    gemini_psidts = models.TextField(
        blank=True,
        null=True,
        verbose_name='__Secure-1PSIDTS',
        help_text='Cookie __Secure-1PSIDTS de gemini.google.com'
    )
    gemini_papisid = models.TextField(
        blank=True,
        null=True,
        verbose_name='__Secure-1PAPISID',
        help_text='Cookie __Secure-1PAPISID de gemini.google.com (opcional)'
    )
    
    # Modelo de Gemini preferido
    preferred_model = models.CharField(
        max_length=50,
        choices=MODEL_CHOICES,
        default='gemini-2.5-flash',
        verbose_name='Modelo Preferido',
        help_text='Modelo de Gemini que se usará por defecto para este usuario'
    )
    
    # Configuración adicional
    proxy = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Proxy',
        help_text='URL del proxy (opcional). Ejemplo: http://proxy.ejemplo.com:8080'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Si está desactivado, no se podrá usar OCR con este usuario'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')
    last_used = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Último Uso',
        help_text='Última vez que se usó OCR con estas credenciales'
    )
    
    class Meta:
        db_table = 'user_gemini_configs'
        verbose_name = 'Configuración de Gemini'
        verbose_name_plural = 'Configuraciones de Gemini'
        ordering = ['user__username']
    
    def __str__(self):
        telegram = f" (@{self.telegram_user})" if self.telegram_user else ""
        return f"{self.user.username}{telegram} - {self.get_preferred_model_display()}"
    
    @property
    def cookies_string(self):
        """Retorna las cookies en formato string para gemini-webapi"""
        cookies = []
        cookies.append(f"__Secure-1PSID={self.gemini_psid}")
        cookies.append(f"__Secure-1PSIDTS={self.gemini_psidts}")
        if self.gemini_papisid:
            cookies.append(f"__Secure-1PAPISID={self.gemini_papisid}")
        return "; ".join(cookies)
    
    def save(self, *args, **kwargs):
        # Limpiar espacios en blanco de las cookies
        if self.gemini_psid:
            self.gemini_psid = self.gemini_psid.strip()
        if self.gemini_psidts:
            self.gemini_psidts = self.gemini_psidts.strip()
        if self.gemini_papisid:
            self.gemini_papisid = self.gemini_papisid.strip()
        if self.telegram_user:
            # Remover @ si lo pusieron
            self.telegram_user = self.telegram_user.lstrip('@').strip()
        super().save(*args, **kwargs)
