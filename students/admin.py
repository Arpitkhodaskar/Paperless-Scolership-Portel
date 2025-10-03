from django.contrib import admin
from .models import Student, StudentDocument, AcademicRecord, ScholarshipApplication


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'user', 'institute', 'department', 'course_level', 'academic_year', 'is_active')
    list_filter = ('institute', 'department', 'course_level', 'academic_year', 'is_active')
    search_fields = ('student_id', 'user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ('student', 'document_type', 'document_name', 'is_verified', 'uploaded_at')
    list_filter = ('document_type', 'is_verified', 'uploaded_at')
    search_fields = ('student__student_id', 'document_name')
    readonly_fields = ('uploaded_at',)


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'academic_year', 'semester', 'gpa', 'total_credits')
    list_filter = ('academic_year', 'semester')
    search_fields = ('student__student_id', 'student__user__username')


@admin.register(ScholarshipApplication)
class ScholarshipApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_id', 'student', 'scholarship_type', 'amount_requested', 'status', 'submitted_at')
    list_filter = ('scholarship_type', 'status', 'submitted_at')
    search_fields = ('application_id', 'student__student_id', 'scholarship_name')
    readonly_fields = ('application_id', 'created_at', 'updated_at')
