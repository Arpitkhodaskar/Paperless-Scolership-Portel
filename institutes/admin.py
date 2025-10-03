from django.contrib import admin
from .models import Institute, InstituteAdmin, InstituteBankAccount, InstituteDocument


@admin.register(Institute)
class InstituteAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'institute_type', 'city', 'state', 'is_active')
    list_filter = ('institute_type', 'state', 'is_active', 'accreditation')
    search_fields = ('name', 'code', 'city', 'email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(InstituteAdmin)
class InstituteAdminAdmin(admin.ModelAdmin):
    list_display = ('user', 'institute', 'designation', 'employee_id', 'is_primary_admin')
    list_filter = ('institute', 'is_primary_admin')
    search_fields = ('user__username', 'employee_id', 'institute__name')


@admin.register(InstituteBankAccount)
class InstituteBankAccountAdmin(admin.ModelAdmin):
    list_display = ('institute', 'account_name', 'bank_name', 'account_type', 'is_primary', 'is_active')
    list_filter = ('account_type', 'is_primary', 'is_active')
    search_fields = ('account_name', 'bank_name', 'institute__name')


@admin.register(InstituteDocument)
class InstituteDocumentAdmin(admin.ModelAdmin):
    list_display = ('institute', 'document_type', 'document_name', 'is_verified', 'uploaded_at')
    list_filter = ('document_type', 'is_verified', 'uploaded_at')
    search_fields = ('institute__name', 'document_name')
