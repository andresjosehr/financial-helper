from django.contrib import admin
from django.utils.html import format_html
from .models import UserGeminiConfig


@admin.register(UserGeminiConfig)
class UserGeminiConfigAdmin(admin.ModelAdmin):
    list_display = ['user', 'telegram_user', 'preferred_model_badge', 'is_active', 'status_display', 'last_used', 'updated_at']
    list_filter = ['is_active', 'preferred_model', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'telegram_user']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_used', 'cookies_preview']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user', 'telegram_user', 'is_active')
        }),
        ('Modelo de Gemini', {
            'fields': ('preferred_model',),
            'description': '''
                <p><strong>Selecciona el modelo de Gemini que prefieres usar:</strong></p>
                <ul>
                    <li><strong>Gemini 2.5 Flash:</strong> Rápido y eficiente. Ideal para uso general. ⚡</li>
                    <li><strong>Gemini 2.5 Pro:</strong> Más potente y preciso. Mejor para documentos complejos. (Límite diario) 🧠</li>
                    <li><strong>Gemini 2.0 Flash:</strong> Versión anterior, aún funcional.</li>
                    <li><strong>Gemini 2.0 Flash Thinking:</strong> Incluye proceso de razonamiento.</li>
                    <li><strong>Sin especificar:</strong> Usa el modelo por defecto de tu cuenta de Gemini.</li>
                </ul>
            '''
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
    
    def preferred_model_badge(self, obj):
        """Muestra un badge con el modelo preferido"""
        colors = {
            'gemini-2.5-flash': '#4CAF50',  # Verde
            'gemini-2.5-pro': '#2196F3',     # Azul
            'gemini-2.0-flash': '#FF9800',   # Naranja
            'gemini-2.0-flash-thinking': '#9C27B0',  # Púrpura
            'unspecified': '#757575',        # Gris
        }
        
        icons = {
            'gemini-2.5-flash': '⚡',
            'gemini-2.5-pro': '🧠',
            'gemini-2.0-flash': '📦',
            'gemini-2.0-flash-thinking': '💭',
            'unspecified': '❓',
        }
        
        color = colors.get(obj.preferred_model, '#757575')
        icon = icons.get(obj.preferred_model, '')
        model_name = obj.get_preferred_model_display()
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, model_name.split('(')[0].strip()
        )
    
    preferred_model_badge.short_description = 'Modelo'
    
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
