from django.contrib import admin
from .models import (
    ScholarshipScheme, ScholarshipDisbursement, FinanceAdmin,
    Budget, Transaction, FinancialReport
)


@admin.register(ScholarshipScheme)
class ScholarshipSchemeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'scheme_type', 'eligibility_type', 'academic_year', 'is_active')
    list_filter = ('scheme_type', 'eligibility_type', 'academic_year', 'is_active')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ScholarshipDisbursement)
class ScholarshipDisbursementAdmin(admin.ModelAdmin):
    list_display = ('disbursement_id', 'application', 'amount', 'status', 'disbursement_method', 'disbursement_date')
    list_filter = ('status', 'disbursement_method', 'disbursement_date')
    search_fields = ('disbursement_id', 'application__application_id', 'application__student__student_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FinanceAdmin)
class FinanceAdminAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'institute', 'designation', 'is_primary_admin')
    list_filter = ('institute', 'is_primary_admin')
    search_fields = ('user__username', 'employee_id')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('name', 'institute', 'budget_type', 'total_amount', 'utilized_amount', 'financial_year')
    list_filter = ('budget_type', 'financial_year', 'institute')
    search_fields = ('name', 'institute__name')
    readonly_fields = ('remaining_amount', 'created_at', 'updated_at')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'institute', 'transaction_type', 'category', 'amount', 'transaction_date')
    list_filter = ('transaction_type', 'category', 'transaction_date', 'institute')
    search_fields = ('transaction_id', 'description', 'reference_number')
    readonly_fields = ('created_at',)


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'institute', 'report_period', 'start_date', 'end_date')
    list_filter = ('report_type', 'report_period', 'institute')
    search_fields = ('name', 'institute__name')
    readonly_fields = ('created_at',)
