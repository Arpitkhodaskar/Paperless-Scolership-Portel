"""
Finance Module Permissions
Comprehensive permission classes for Finance operations
"""

from rest_framework.permissions import BasePermission, IsAuthenticated
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
import json

from .models import FinanceAdmin, ScholarshipDisbursement, Budget, Transaction
from students.models import ScholarshipApplication


class IsFinanceAdminAuthenticated(BasePermission):
    """
    Custom permission to only allow access to finance administrators.
    """
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated and is a finance admin.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            finance_admin = FinanceAdmin.objects.get(user=request.user)
            # Add finance admin to request for later use
            request.finance_admin = finance_admin
            return True
        except FinanceAdmin.DoesNotExist:
            return False


class FinanceAdminBasePermission(BasePermission):
    """
    Base permission class for finance admin operations
    """
    
    def has_permission(self, request, view):
        """Base permission check"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            finance_admin = FinanceAdmin.objects.select_related('institute').get(
                user=request.user
            )
            request.finance_admin = finance_admin
            return True
        except FinanceAdmin.DoesNotExist:
            return False
    
    def get_finance_admin(self, request):
        """Get finance admin from request"""
        return getattr(request, 'finance_admin', None)


class CanProcessPaymentsPermission(FinanceAdminBasePermission):
    """
    Permission to process scholarship payments and disbursements
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        # Check if user has payment processing permissions
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_process_payments', True)
    
    def has_object_permission(self, request, view, obj):
        """Check if admin can process specific payment/disbursement"""
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        # For disbursements, check institute access
        if isinstance(obj, ScholarshipDisbursement):
            if finance_admin.institute:
                return obj.application.student.institute == finance_admin.institute
        
        # For applications, check institute access
        if isinstance(obj, ScholarshipApplication):
            if finance_admin.institute:
                return obj.student.institute == finance_admin.institute
        
        return True


class CanCalculateAmountsPermission(FinanceAdminBasePermission):
    """
    Permission to calculate scholarship amounts
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_calculate_amounts', True)


class CanManageDisbursementsPermission(FinanceAdminBasePermission):
    """
    Permission to manage disbursements (create, update, cancel)
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_manage_disbursements', True)
    
    def has_object_permission(self, request, view, obj):
        """Check if admin can manage specific disbursement"""
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        # Ensure disbursement belongs to admin's institute
        if isinstance(obj, ScholarshipDisbursement):
            if finance_admin.institute:
                return obj.application.student.institute == finance_admin.institute
        
        return True


class CanGenerateFinanceReportsPermission(FinanceAdminBasePermission):
    """
    Permission to generate finance reports and access analytics
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_generate_reports', True)


class CanManageBudgetsPermission(FinanceAdminBasePermission):
    """
    Permission to manage budgets and financial allocations
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_manage_budgets', False)  # More restrictive by default
    
    def has_object_permission(self, request, view, obj):
        """Check if admin can manage specific budget"""
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        # Ensure budget belongs to admin's institute
        if isinstance(obj, Budget):
            if finance_admin.institute:
                return obj.institute == finance_admin.institute
        
        return True


class CanManageTransactionsPermission(FinanceAdminBasePermission):
    """
    Permission to manage financial transactions
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_manage_transactions', True)
    
    def has_object_permission(self, request, view, obj):
        """Check if admin can manage specific transaction"""
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        # Ensure transaction belongs to admin's institute
        if isinstance(obj, Transaction):
            if finance_admin.institute:
                return obj.institute == finance_admin.institute
        
        return True


class CanManageScholarshipSchemesPermission(FinanceAdminBasePermission):
    """
    Permission to manage scholarship schemes
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        # Only primary admins can manage schemes
        if not finance_admin.is_primary_admin:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_manage_schemes', False)


class IsPrimaryFinanceAdmin(FinanceAdminBasePermission):
    """
    Permission for primary finance administrators only
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        return finance_admin.is_primary_admin


class FinanceDataAccessPermission(FinanceAdminBasePermission):
    """
    Permission to access finance-specific data based on institute
    """
    
    def has_permission(self, request, view):
        return super().has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        """Ensure admin can only access data from their institute"""
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        # System-wide access for primary admins without institute restriction
        if finance_admin.is_primary_admin and not finance_admin.institute:
            return True
        
        # Check different object types
        if hasattr(obj, 'institute'):
            return obj.institute == finance_admin.institute
        elif hasattr(obj, 'application') and hasattr(obj.application, 'student'):
            return obj.application.student.institute == finance_admin.institute
        elif hasattr(obj, 'student') and hasattr(obj.student, 'institute'):
            return obj.student.institute == finance_admin.institute
        
        return False


class DBTTransferPermission(FinanceAdminBasePermission):
    """
    Permission for DBT (Direct Benefit Transfer) operations
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        # DBT operations require special permission
        return permissions.get('can_perform_dbt_transfers', True)


class BulkOperationsPermission(FinanceAdminBasePermission):
    """
    Permission for bulk operations (bulk payments, bulk processing)
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_perform_bulk_operations', True)


class FinanceAuditPermission(FinanceAdminBasePermission):
    """
    Permission for finance audit and compliance operations
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        finance_admin = self.get_finance_admin(request)
        if not finance_admin:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get('can_access_audit_features', False)


class FinanceSystemAdminPermission(BasePermission):
    """
    Permission for system-level finance administration
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            finance_admin = FinanceAdmin.objects.get(user=request.user)
            request.finance_admin = finance_admin
            
            # Must be primary admin with no institute restriction (system-wide access)
            return finance_admin.is_primary_admin and not finance_admin.institute
        except FinanceAdmin.DoesNotExist:
            return False


# Combined Permission Classes for Specific Views
class PendingApplicationsPermission(CanProcessPaymentsPermission, FinanceDataAccessPermission):
    """Permission for viewing pending applications"""
    
    def has_permission(self, request, view):
        return (CanProcessPaymentsPermission.has_permission(self, request, view) and
                FinanceDataAccessPermission.has_permission(self, request, view))


class ScholarshipCalculationPermission(CanCalculateAmountsPermission, FinanceDataAccessPermission):
    """Permission for scholarship calculations"""
    
    def has_permission(self, request, view):
        return (CanCalculateAmountsPermission.has_permission(self, request, view) and
                FinanceDataAccessPermission.has_permission(self, request, view))


class PaymentProcessingPermission(CanProcessPaymentsPermission, CanManageDisbursementsPermission):
    """Permission for payment processing operations"""
    
    def has_permission(self, request, view):
        return (CanProcessPaymentsPermission.has_permission(self, request, view) and
                CanManageDisbursementsPermission.has_permission(self, request, view))


class ReportsAndAnalyticsPermission(CanGenerateFinanceReportsPermission, FinanceDataAccessPermission):
    """Permission for reports and analytics"""
    
    def has_permission(self, request, view):
        return (CanGenerateFinanceReportsPermission.has_permission(self, request, view) and
                FinanceDataAccessPermission.has_permission(self, request, view))


# Utility Functions for Permission Management
def create_finance_admin_groups():
    """
    Create default permission groups for finance admins
    """
    groups_permissions = {
        'Finance_System_Admin': [
            'can_process_payments',
            'can_calculate_amounts',
            'can_manage_disbursements',
            'can_generate_reports',
            'can_manage_budgets',
            'can_manage_transactions',
            'can_manage_schemes',
            'can_perform_dbt_transfers',
            'can_perform_bulk_operations',
            'can_access_audit_features'
        ],
        'Finance_Primary_Admin': [
            'can_process_payments',
            'can_calculate_amounts',
            'can_manage_disbursements',
            'can_generate_reports',
            'can_manage_budgets',
            'can_manage_transactions',
            'can_perform_dbt_transfers',
            'can_perform_bulk_operations'
        ],
        'Finance_Admin': [
            'can_process_payments',
            'can_calculate_amounts',
            'can_manage_disbursements',
            'can_generate_reports',
            'can_manage_transactions',
            'can_perform_dbt_transfers'
        ],
        'Finance_Officer': [
            'can_process_payments',
            'can_calculate_amounts',
            'can_generate_reports',
            'can_manage_transactions'
        ],
        'Finance_Clerk': [
            'can_process_payments',
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


def get_default_finance_permissions(role='admin'):
    """
    Get default permissions based on role
    """
    permission_sets = {
        'system_admin': {
            'can_process_payments': True,
            'can_calculate_amounts': True,
            'can_manage_disbursements': True,
            'can_generate_reports': True,
            'can_manage_budgets': True,
            'can_manage_transactions': True,
            'can_manage_schemes': True,
            'can_perform_dbt_transfers': True,
            'can_perform_bulk_operations': True,
            'can_access_audit_features': True
        },
        'primary_admin': {
            'can_process_payments': True,
            'can_calculate_amounts': True,
            'can_manage_disbursements': True,
            'can_generate_reports': True,
            'can_manage_budgets': True,
            'can_manage_transactions': True,
            'can_perform_dbt_transfers': True,
            'can_perform_bulk_operations': True,
            'can_manage_schemes': False,
            'can_access_audit_features': False
        },
        'admin': {
            'can_process_payments': True,
            'can_calculate_amounts': True,
            'can_manage_disbursements': True,
            'can_generate_reports': True,
            'can_manage_budgets': False,
            'can_manage_transactions': True,
            'can_perform_dbt_transfers': True,
            'can_perform_bulk_operations': False,
            'can_manage_schemes': False,
            'can_access_audit_features': False
        },
        'officer': {
            'can_process_payments': True,
            'can_calculate_amounts': True,
            'can_manage_disbursements': False,
            'can_generate_reports': True,
            'can_manage_budgets': False,
            'can_manage_transactions': True,
            'can_perform_dbt_transfers': False,
            'can_perform_bulk_operations': False,
            'can_manage_schemes': False,
            'can_access_audit_features': False
        },
        'clerk': {
            'can_process_payments': True,
            'can_calculate_amounts': False,
            'can_manage_disbursements': False,
            'can_generate_reports': True,
            'can_manage_budgets': False,
            'can_manage_transactions': False,
            'can_perform_dbt_transfers': False,
            'can_perform_bulk_operations': False,
            'can_manage_schemes': False,
            'can_access_audit_features': False
        }
    }
    
    return permission_sets.get(role, permission_sets['clerk'])


def check_finance_permission(user, permission_key, institute=None):
    """
    Utility function to check if user has specific finance permission
    """
    try:
        finance_admin = FinanceAdmin.objects.get(user=user)
        
        if institute and finance_admin.institute and finance_admin.institute != institute:
            return False
        
        permissions = finance_admin.permissions
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return permissions.get(permission_key, False)
    
    except FinanceAdmin.DoesNotExist:
        return False


def get_user_finance_permissions(user):
    """
    Get all permissions for a finance admin user
    """
    try:
        finance_admin = FinanceAdmin.objects.get(user=user)
        permissions = finance_admin.permissions
        
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = {}
        
        return {
            'institute': finance_admin.institute.name if finance_admin.institute else 'System Wide',
            'is_primary_admin': finance_admin.is_primary_admin,
            'designation': finance_admin.designation,
            'permissions': permissions
        }
    
    except FinanceAdmin.DoesNotExist:
        return None


def validate_institute_access(user, target_institute):
    """
    Validate if finance admin has access to specific institute
    """
    try:
        finance_admin = FinanceAdmin.objects.get(user=user)
        
        # System-wide access
        if not finance_admin.institute and finance_admin.is_primary_admin:
            return True
        
        # Institute-specific access
        return finance_admin.institute == target_institute
    
    except FinanceAdmin.DoesNotExist:
        return False
