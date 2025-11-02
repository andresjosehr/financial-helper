from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'telegram_user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email', 'telegram_user']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información del Usuario', {
            'fields': ('user', 'telegram_user')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
