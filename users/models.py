import uuid
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
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
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
        ordering = ['user__username']
    
    def __str__(self):
        telegram = f" (@{self.telegram_user})" if self.telegram_user else ""
        return f"{self.user.username}{telegram}"
    
    def save(self, *args, **kwargs):
        if self.telegram_user:
            self.telegram_user = self.telegram_user.lstrip('@').strip()
        super().save(*args, **kwargs)
