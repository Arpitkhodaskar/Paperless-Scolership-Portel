from django.contrib import admin
from .models import (
    GrievanceCategory, Grievance, GrievanceComment, GrievanceDocument,
    GrievanceAdmin, GrievanceStatusLog, FAQ
)


@admin.register(GrievanceCategory)
class GrievanceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority_level', 'resolution_time_days', 'is_active')
    list_filter = ('priority_level', 'is_active')
    search_fields = ('name',)


@admin.register(Grievance)
class GrievanceAdmin(admin.ModelAdmin):
    list_display = ('grievance_id', 'student', 'category', 'priority', 'status', 'submitted_at')
    list_filter = ('category', 'priority', 'status', 'institute', 'submitted_at')
    search_fields = ('grievance_id', 'student__student_id', 'subject')
    readonly_fields = ('grievance_id', 'submitted_at', 'updated_at')


@admin.register(GrievanceComment)
class GrievanceCommentAdmin(admin.ModelAdmin):
    list_display = ('grievance', 'comment_type', 'created_by', 'is_internal', 'created_at')
    list_filter = ('comment_type', 'is_internal', 'created_at')
    search_fields = ('grievance__grievance_id', 'content')


@admin.register(GrievanceDocument)
class GrievanceDocumentAdmin(admin.ModelAdmin):
    list_display = ('grievance', 'document_name', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('grievance__grievance_id', 'document_name')


@admin.register(GrievanceAdmin)
class GrievanceAdminAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'institute', 'department', 'is_primary_admin')
    list_filter = ('institute', 'department', 'is_primary_admin')
    search_fields = ('user__username', 'employee_id')


@admin.register(GrievanceStatusLog)
class GrievanceStatusLogAdmin(admin.ModelAdmin):
    list_display = ('grievance', 'previous_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('previous_status', 'new_status', 'changed_at')
    search_fields = ('grievance__grievance_id',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'is_active', 'view_count', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('question', 'answer')
    readonly_fields = ('view_count', 'created_at', 'updated_at')
