"""
Institute Module Permissions
Role-based permissions for institute administration
"""

from rest_framework import permissions
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.contrib.auth import get_user_model

from .models import Institute, InstituteAdmin

User = get_user_model()


class InstituteAdminPermission(BasePermission):
    """
    Permission class to ensure user is an institute admin
    and has access to their institute's data only
    """
    
    def has_permission(self, request, view):
        """Check if user has institute admin permission"""
        if not request.user.is_authenticated:
            return False
        
        # Check if user is an institute admin
        try:
            institute_admin = InstituteAdmin.objects.get(user=request.user)
            # Store institute in request for later use
            request.institute = institute_admin.institute
            return True
        except InstituteAdmin.DoesNotExist:
            return False
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific object"""
        if not request.user.is_authenticated:
            return False
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=request.user)
            
            # Check based on object type
            if hasattr(obj, 'institute'):
                return obj.institute == institute_admin.institute
            elif hasattr(obj, 'student') and hasattr(obj.student, 'institute'):
                return obj.student.institute == institute_admin.institute
            elif hasattr(obj, 'user') and hasattr(obj.user, 'student_profile'):
                return obj.user.student_profile.institute == institute_admin.institute
            
            return True
        except InstituteAdmin.DoesNotExist:
            return False


class InstitutePrimaryAdminPermission(BasePermission):
    """
    Permission class for primary institute admin only
    Allows access to sensitive operations like managing other admins
    """
    
    def has_permission(self, request, view):
        """Check if user is a primary institute admin"""
        if not request.user.is_authenticated:
            return False
        
        try:
            institute_admin = InstituteAdmin.objects.get(
                user=request.user,
                is_primary_admin=True
            )
            request.institute = institute_admin.institute
            return True
        except InstituteAdmin.DoesNotExist:
            return False


class InstituteReportsPermission(BasePermission):
    """
    Permission class for institute reports access
    Allows institute admins to access reports for their institute
    """
    
    def has_permission(self, request, view):
        """Check if user can access institute reports"""
        if not request.user.is_authenticated:
            return False
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=request.user)
            request.institute = institute_admin.institute
            
            # Additional check: only allow GET requests for reports
            if request.method in ['GET']:
                return True
            
            # For other methods, require primary admin
            return institute_admin.is_primary_admin
        except InstituteAdmin.DoesNotExist:
            return False


class InstituteDocumentPermission(BasePermission):
    """
    Permission class for institute document management
    """
    
    def has_permission(self, request, view):
        """Check if user can manage institute documents"""
        if not request.user.is_authenticated:
            return False
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=request.user)
            request.institute = institute_admin.institute
            
            # Read permissions for all institute admins
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                return True
            
            # Write permissions for primary admin or specific designation
            return (institute_admin.is_primary_admin or 
                   institute_admin.designation.lower() in ['registrar', 'admin officer'])
        except InstituteAdmin.DoesNotExist:
            return False


class StudentVerificationPermission(BasePermission):
    """
    Permission class for student verification operations
    """
    
    def has_permission(self, request, view):
        """Check if user can verify students"""
        if not request.user.is_authenticated:
            return False
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=request.user)
            request.institute = institute_admin.institute
            
            # Only allow admins with verification rights
            verification_roles = ['registrar', 'academic officer', 'admin officer']
            return (institute_admin.is_primary_admin or 
                   institute_admin.designation.lower() in verification_roles)
        except InstituteAdmin.DoesNotExist:
            return False


class ApplicationProcessingPermission(BasePermission):
    """
    Permission class for scholarship application processing
    """
    
    def has_permission(self, request, view):
        """Check if user can process scholarship applications"""
        if not request.user.is_authenticated:
            return False
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=request.user)
            request.institute = institute_admin.institute
            
            # Read permissions for all institute admins
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                return True
            
            # Processing permissions for authorized roles
            processing_roles = ['scholarship officer', 'admin officer', 'registrar']
            return (institute_admin.is_primary_admin or 
                   institute_admin.designation.lower() in processing_roles)
        except InstituteAdmin.DoesNotExist:
            return False


class InstituteBankAccountPermission(BasePermission):
    """
    Permission class for institute bank account management
    """
    
    def has_permission(self, request, view):
        """Check if user can manage bank accounts"""
        if not request.user.is_authenticated:
            return False
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=request.user)
            request.institute = institute_admin.institute
            
            # Read permissions for all institute admins
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                return True
            
            # Write permissions only for primary admin or finance officer
            return (institute_admin.is_primary_admin or 
                   institute_admin.designation.lower() in ['finance officer', 'treasurer'])
        except InstituteAdmin.DoesNotExist:
            return False


class BulkOperationPermission(BasePermission):
    """
    Permission class for bulk operations on applications
    """
    
    def has_permission(self, request, view):
        """Check if user can perform bulk operations"""
        if not request.user.is_authenticated:
            return False
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=request.user)
            request.institute = institute_admin.institute
            
            # Bulk operations require higher privileges
            bulk_operation_roles = ['registrar', 'admin officer']
            return (institute_admin.is_primary_admin or 
                   institute_admin.designation.lower() in bulk_operation_roles)
        except InstituteAdmin.DoesNotExist:
            return False


class InstituteDataExportPermission(BasePermission):
    """
    Permission class for data export operations
    """
    
    def has_permission(self, request, view):
        """Check if user can export institute data"""
        if not request.user.is_authenticated:
            return False
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=request.user)
            request.institute = institute_admin.institute
            
            # Data export permissions for authorized roles
            export_roles = ['registrar', 'admin officer', 'data analyst']
            return (institute_admin.is_primary_admin or 
                   institute_admin.designation.lower() in export_roles)
        except InstituteAdmin.DoesNotExist:
            return False


# Utility functions for permission checking
def is_institute_admin(user):
    """Check if user is an institute admin"""
    try:
        InstituteAdmin.objects.get(user=user)
        return True
    except InstituteAdmin.DoesNotExist:
        return False


def is_primary_institute_admin(user):
    """Check if user is a primary institute admin"""
    try:
        InstituteAdmin.objects.get(user=user, is_primary_admin=True)
        return True
    except InstituteAdmin.DoesNotExist:
        return False


def get_user_institute(user):
    """Get institute for a user"""
    try:
        institute_admin = InstituteAdmin.objects.get(user=user)
        return institute_admin.institute
    except InstituteAdmin.DoesNotExist:
        return None


def has_institute_permission(user, permission_type):
    """
    Check if user has specific institute permission
    
    Args:
        user: User object
        permission_type: Type of permission to check
            - 'verification': Can verify students/documents
            - 'processing': Can process applications
            - 'reports': Can access reports
            - 'bulk_operations': Can perform bulk operations
            - 'finance': Can manage financial data
            - 'admin': Can manage institute settings
    """
    try:
        institute_admin = InstituteAdmin.objects.get(user=user)
        
        if institute_admin.is_primary_admin:
            return True
        
        designation = institute_admin.designation.lower()
        
        permission_map = {
            'verification': ['registrar', 'academic officer', 'admin officer'],
            'processing': ['scholarship officer', 'admin officer', 'registrar'],
            'reports': [],  # All institute admins can access reports
            'bulk_operations': ['registrar', 'admin officer'],
            'finance': ['finance officer', 'treasurer', 'admin officer'],
            'admin': ['admin officer', 'registrar']
        }
        
        allowed_roles = permission_map.get(permission_type, [])
        
        # If no specific roles defined, allow all institute admins
        if not allowed_roles:
            return True
        
        return designation in allowed_roles
        
    except InstituteAdmin.DoesNotExist:
        return False


# Custom permission mixins for views
class InstituteAdminMixin:
    """Mixin to ensure view is accessed by institute admin"""
    
    permission_classes = [InstituteAdminPermission]
    
    def get_institute(self):
        """Get current user's institute"""
        return get_user_institute(self.request.user)
    
    def get_queryset(self):
        """Filter queryset by institute"""
        queryset = super().get_queryset()
        institute = self.get_institute()
        
        if institute and hasattr(queryset.model, 'institute'):
            return queryset.filter(institute=institute)
        elif institute and hasattr(queryset.model, 'student'):
            return queryset.filter(student__institute=institute)
        
        return queryset


class PrimaryAdminMixin:
    """Mixin to ensure view is accessed by primary institute admin only"""
    
    permission_classes = [InstitutePrimaryAdminPermission]


class ReportsAccessMixin:
    """Mixin for reports access"""
    
    permission_classes = [InstituteReportsPermission]


# Role-based decorators for function-based views
def institute_admin_required(view_func):
    """Decorator to require institute admin permission"""
    def wrapper(request, *args, **kwargs):
        if not is_institute_admin(request.user):
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {'error': 'Institute admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def primary_admin_required(view_func):
    """Decorator to require primary institute admin permission"""
    def wrapper(request, *args, **kwargs):
        if not is_primary_institute_admin(request.user):
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {'error': 'Primary institute admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def institute_permission_required(permission_type):
    """Decorator to require specific institute permission"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not has_institute_permission(request.user, permission_type):
                from rest_framework.response import Response
                from rest_framework import status
                return Response(
                    {'error': f'Institute {permission_type} permission required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
