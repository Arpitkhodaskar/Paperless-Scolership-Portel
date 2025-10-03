from django.contrib import admin
from .models import CustomUser, UserProfile


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_verified', 'is_active')
    list_filter = ('user_type', 'is_verified', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'profile_picture')}),
        ('Permissions', {'fields': ('user_type', 'is_verified', 'is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'state', 'postal_code')
    search_fields = ('user__username', 'user__email', 'city', 'state')
    list_filter = ('city', 'state')
