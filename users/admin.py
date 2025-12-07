from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Telegram'
    fields = ['telegram_user']


# Unregister the default User admin
admin.site.unregister(User)


# Register User admin with inline UserProfile
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
