from django.contrib import admin
from django.utils.html import format_html
from .models import UserGeminiConfig


@admin.register(UserGeminiConfig)
class UserGeminiConfigAdmin(admin.ModelAdmin):
    list_display = ['user', 'telegram_user', 'is_active', 'status_display', 'last_used', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'telegram_user']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_used', 'cookies_preview']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user', 'telegram_user', 'is_active')
        }),
        ('Cookies de Gemini', {
            'fields': ('gemini_psid', 'gemini_psidts', 'gemini_papisid'),
            'description': '''
                <p><strong>Cómo obtener las cookies:</strong></p>
                <ol>
                    <li>Inicia sesión en <a href="https://gemini.google.com/" target="_blank">gemini.google.com</a></li>
                    <li>Presiona F12 para abrir DevTools</li>
                    <li>Ve a Application (Chrome) o Storage (Firefox) → Cookies → https://gemini.google.com</li>
                    <li>Copia los valores de las cookies y pégalos aquí</li>
                </ol>
                <p><strong>Nota:</strong> Las cookies son sensibles. No las compartas.</p>
            '''
        }),
        ('Configuración Adicional', {
            'fields': ('proxy',),
            'classes': ('collapse',)
        }),
        ('Información', {
            'fields': ('id', 'created_at', 'updated_at', 'last_used', 'cookies_preview'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        """Muestra el estado visual de la configuración"""
        if not obj.is_active:
            return format_html('<span style="color: gray;">⚫ Inactivo</span>')
        
        # Validar que tenga las cookies mínimas
        if obj.gemini_psid and obj.gemini_psidts:
            return format_html('<span style="color: green;">✅ Configurado</span>')
        else:
            return format_html('<span style="color: red;">❌ Incompleto</span>')
    
    status_display.short_description = 'Estado'
    
    def cookies_preview(self, obj):
        """Muestra un preview de las cookies (primeros y últimos caracteres)"""
        if not obj.gemini_psid:
            return "No configurado"
        
        def preview_cookie(value):
            if not value or len(value) < 20:
                return value
            return f"{value[:10]}...{value[-10:]}"
        
        html = f"""
        <div style="font-family: monospace; font-size: 12px;">
            <strong>__Secure-1PSID:</strong> {preview_cookie(obj.gemini_psid)}<br>
            <strong>__Secure-1PSIDTS:</strong> {preview_cookie(obj.gemini_psidts)}<br>
            {f'<strong>__Secure-1PAPISID:</strong> {preview_cookie(obj.gemini_papisid)}<br>' if obj.gemini_papisid else ''}
        </div>
        """
        return format_html(html)
    
    cookies_preview.short_description = 'Preview de Cookies'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Los superusuarios ven todo, los demás solo su configuración
        if not request.user.is_superuser:
            qs = qs.filter(user=request.user)
        return qs
    
    def has_add_permission(self, request):
        # Solo puede agregar si no tiene ya una configuración
        if request.user.is_superuser:
            return True
        return not UserGeminiConfig.objects.filter(user=request.user).exists()
    
    def has_change_permission(self, request, obj=None):
        # Superusuarios pueden editar todo, usuarios normales solo su config
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.user == request.user
    
    def has_delete_permission(self, request, obj=None):
        # Superusuarios pueden borrar todo, usuarios normales solo su config
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.user == request.user
    
    def save_model(self, request, obj, form, change):
        # Si no es superusuario y está creando, asignar automáticamente
        if not change and not request.user.is_superuser:
            obj.user = request.user
        super().save_model(request, obj, form, change)
