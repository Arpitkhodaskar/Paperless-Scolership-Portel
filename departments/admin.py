from django.contrib import admin
from .models import Department, Course, DepartmentAdmin, Subject, Faculty


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'institute', 'department_type', 'is_active')
    list_filter = ('institute', 'department_type', 'is_active')
    search_fields = ('name', 'code', 'institute__name')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'course_type', 'duration_years', 'is_active')
    list_filter = ('department', 'course_type', 'is_active')
    search_fields = ('name', 'code', 'department__name')


@admin.register(DepartmentAdmin)
class DepartmentAdminAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'designation', 'employee_id', 'is_primary_admin')
    list_filter = ('department', 'is_primary_admin')
    search_fields = ('user__username', 'employee_id', 'department__name')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'course', 'subject_type', 'credits', 'semester')
    list_filter = ('course', 'subject_type', 'semester')
    search_fields = ('name', 'code', 'course__name')


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department', 'designation', 'is_active')
    list_filter = ('department', 'designation', 'is_active')
    search_fields = ('employee_id', 'user__username', 'user__first_name', 'user__last_name')
