"""
Department Module Permissions
Comprehensive permission classes for Department administration
"""

from rest_framework.permissions import BasePermission, IsAuthenticated
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
import json

from .models import Department, DepartmentAdmin
from students.models import ScholarshipApplication


class IsDepartmentAdminAuthenticated(BasePermission):
    """
    Custom permission to only allow access to department administrators.
    """
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated and is a department admin.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            dept_admin = DepartmentAdmin.objects.get(user=request.user)
            # Add department admin to request for later use
            request.dept_admin = dept_admin
            return True
        except DepartmentAdmin.DoesNotExist:
            return False


class DepartmentAdminBasePermission(BasePermission):
    """
    Base permission class for department admin operations
    """
    
    def has_permission(self, request, view):
        """Base permission check"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            dept_admin = DepartmentAdmin.objects.select_related('department').get(
                user=request.user
            )
            request.dept_admin = dept_admin
            return True
        except DepartmentAdmin.DoesNotExist:
            return False
    
    def get_department_admin(self, request):
        """Get department admin from request"""
        return getattr(request, 'dept_admin', None)


class CanReviewApplicationsPermission(DepartmentAdminBasePermission):
    """
    Permission to review scholarship applications
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        # Check if user has review permissions
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_review_applications', True)
    
    def has_object_permission(self, request, view, obj):
        """Check if admin can review specific application"""
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        # Ensure application belongs to admin's department
        if hasattr(obj, 'student'):
            return obj.student.department == dept_admin.department
        
        return False


class CanApproveApplicationsPermission(DepartmentAdminBasePermission):
    """
    Permission to approve/reject scholarship applications
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        # Check specific action permissions
        if request.method in ['POST', 'PUT', 'PATCH']:
            action = request.data.get('action', '')
            if 'approve' in action.lower():
                return permissions.get('can_approve_applications', True)
            elif 'reject' in action.lower():
                return permissions.get('can_reject_applications', True)
        
        return permissions.get('can_review_applications', True)
    
    def has_object_permission(self, request, view, obj):
        """Check if admin can approve/reject specific application"""
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        # Ensure application belongs to admin's department
        if hasattr(obj, 'student'):
            return obj.student.department == dept_admin.department
        
        return False


class CanForwardToFinancePermission(DepartmentAdminBasePermission):
    """
    Permission to forward approved applications to finance
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_forward_to_finance', True)


class CanGenerateReportsPermission(DepartmentAdminBasePermission):
    """
    Permission to generate department reports and access dashboard
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_generate_reports', True)


class CanManageStudentsPermission(DepartmentAdminBasePermission):
    """
    Permission to manage students in the department
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_manage_students', False)


class CanManageCoursesPermission(DepartmentAdminBasePermission):
    """
    Permission to manage courses and subjects
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_manage_courses', False)


class CanManageFacultyPermission(DepartmentAdminBasePermission):
    """
    Permission to manage faculty members
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_manage_faculty', False)


class CanManageDepartmentSettingsPermission(DepartmentAdminBasePermission):
    """
    Permission to manage department settings and configurations
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        # Only primary admins can manage department settings
        if not dept_admin.is_primary_admin:
            return False
        
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_manage_department_settings', False)


class IsPrimaryDepartmentAdmin(DepartmentAdminBasePermission):
    """
    Permission for primary department administrators only
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        return dept_admin.is_primary_admin


class DepartmentDataAccessPermission(DepartmentAdminBasePermission):
    """
    Permission to access department-specific data
    """
    
    def has_permission(self, request, view):
        return super().has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        """Ensure admin can only access data from their department"""
        dept_admin = self.get_department_admin(request)
        if not dept_admin:
            return False
        
        # Check different object types
        if hasattr(obj, 'department'):
            return obj.department == dept_admin.department
        elif hasattr(obj, 'student') and hasattr(obj.student, 'department'):
            return obj.student.department == dept_admin.department
        elif hasattr(obj, 'institute') and hasattr(dept_admin, 'department'):
            # For institute-level objects, check if department belongs to institute
            return obj.institute == dept_admin.department.institute
        
        return False


class ApplicationStatusPermission(BasePermission):
    """
    Permission based on application status and department workflow
    """
    
    def has_permission(self, request, view):
        """Basic authentication check"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            dept_admin = DepartmentAdmin.objects.get(user=request.user)
            request.dept_admin = dept_admin
            return True
        except DepartmentAdmin.DoesNotExist:
            return False
    
    def has_object_permission(self, request, view, obj):
        """Check permissions based on application status"""
        if not isinstance(obj, ScholarshipApplication):
            return False
        
        dept_admin = getattr(request, 'dept_admin', None)
        if not dept_admin:
            return False
        
        # Ensure application belongs to admin's department
        if obj.student.department != dept_admin.department:
            return False
        
        # Check if application is in correct status for department review
        if request.method in ['POST', 'PUT', 'PATCH']:
            # Application must be institute-approved to be reviewed by department
            if obj.status != 'institute_approved':
                return False
            
            # Check if application is already processed by department
            if obj.internal_notes:
                if any(status in obj.internal_notes for status in ['DEPT_APPROVED', 'DEPT_REJECTED']):
                    # Already processed, no further changes allowed unless primary admin
                    return dept_admin.is_primary_admin
        
        return True


class DepartmentOperationPermission(BasePermission):
    """
    Combined permission class for department operations
    """
    
    def __init__(self, required_permissions=None):
        """
        Initialize with required permissions list
        :param required_permissions: List of permission keys required
        """
        self.required_permissions = required_permissions or []
    
    def has_permission(self, request, view):
        """Check if user has required permissions"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            dept_admin = DepartmentAdmin.objects.get(user=request.user)
            request.dept_admin = dept_admin
        except DepartmentAdmin.DoesNotExist:
            return False
        
        # Parse permissions
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        # Check all required permissions
        for perm in self.required_permissions:
            if not permissions.get(perm, False):
                return False
        
        return True


# Permission Classes for Specific Views
class VerifiedApplicationsListPermission(CanReviewApplicationsPermission):
    """Permission for viewing verified applications list"""
    pass


class ApplicationReviewPermission(CanApproveApplicationsPermission, ApplicationStatusPermission):
    """Permission for reviewing applications (approve/reject)"""
    
    def has_permission(self, request, view):
        return (CanApproveApplicationsPermission.has_permission(self, request, view) and
                ApplicationStatusPermission.has_permission(self, request, view))
    
    def has_object_permission(self, request, view, obj):
        return (CanApproveApplicationsPermission.has_object_permission(self, request, view, obj) and
                ApplicationStatusPermission.has_object_permission(self, request, view, obj))


class ForwardToFinancePermission(CanForwardToFinancePermission):
    """Permission for forwarding applications to finance"""
    pass


class DepartmentDashboardPermission(CanGenerateReportsPermission):
    """Permission for accessing department dashboard"""
    pass


class DepartmentReportsPermission(CanGenerateReportsPermission):
    """Permission for generating department reports"""
    pass


# Utility Functions for Permission Management
def create_department_admin_groups():
    """
    Create default permission groups for department admins
    """
    groups_permissions = {
        'Department_Primary_Admin': [
            'can_review_applications',
            'can_approve_applications', 
            'can_reject_applications',
            'can_forward_to_finance',
            'can_generate_reports',
            'can_manage_students',
            'can_manage_courses',
            'can_manage_faculty',
            'can_manage_department_settings'
        ],
        'Department_Admin': [
            'can_review_applications',
            'can_approve_applications',
            'can_reject_applications', 
            'can_forward_to_finance',
            'can_generate_reports'
        ],
        'Department_Reviewer': [
            'can_review_applications',
            'can_generate_reports'
        ]
    }
    
    created_groups = {}
    
    for group_name, permissions in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)
        created_groups[group_name] = {
            'group': group,
            'created': created,
            'permissions': permissions
        }
    
    return created_groups


def get_default_department_permissions(role='admin'):
    """
    Get default permissions based on role
    """
    permission_sets = {
        'primary_admin': {
            'can_review_applications': True,
            'can_approve_applications': True,
            'can_reject_applications': True,
            'can_forward_to_finance': True,
            'can_generate_reports': True,
            'can_manage_students': True,
            'can_manage_courses': True,
            'can_manage_faculty': True,
            'can_manage_department_settings': True
        },
        'admin': {
            'can_review_applications': True,
            'can_approve_applications': True,
            'can_reject_applications': True,
            'can_forward_to_finance': True,
            'can_generate_reports': True,
            'can_manage_students': False,
            'can_manage_courses': False,
            'can_manage_faculty': False,
            'can_manage_department_settings': False
        },
        'reviewer': {
            'can_review_applications': True,
            'can_approve_applications': False,
            'can_reject_applications': False,
            'can_forward_to_finance': False,
            'can_generate_reports': True,
            'can_manage_students': False,
            'can_manage_courses': False,
            'can_manage_faculty': False,
            'can_manage_department_settings': False
        }
    }
    
    return permission_sets.get(role, permission_sets['reviewer'])


def check_department_permission(user, permission_key, department=None):
    """
    Utility function to check if user has specific department permission
    """
    try:
        dept_admin = DepartmentAdmin.objects.get(user=user)
        
        if department and dept_admin.department != department:
            return False
        
        permissions = dept_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get(permission_key, False)
    
    except DepartmentAdmin.DoesNotExist:
        return False


def get_user_department_permissions(user):
    """
    Get all permissions for a department admin user
    """
    try:
        dept_admin = DepartmentAdmin.objects.get(user=user)
        permissions = dept_admin.permissions
        
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return {
            'department': dept_admin.department.name,
            'is_primary_admin': dept_admin.is_primary_admin,
            'permissions': permissions
        }
    
    except DepartmentAdmin.DoesNotExist:
        return None
