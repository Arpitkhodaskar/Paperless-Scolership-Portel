"""
Institute Module ViewSets
Comprehensive ViewSets for Institute administration
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Prefetch, Sum, Avg
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import Institute, InstituteAdmin, InstituteBankAccount, InstituteDocument
from .institute_serializers import (
    InstituteSerializer, InstituteDetailSerializer, InstituteAdminSerializer,
    InstituteBankAccountSerializer, InstituteDocumentSerializer,
    StudentVerificationSerializer, DocumentVerificationSerializer
)
from .permissions import (
    InstituteAdminPermission, InstitutePrimaryAdminPermission,
    InstituteDocumentPermission, StudentVerificationPermission,
    InstituteBankAccountPermission
)
from students.models import Student, ScholarshipApplication, StudentDocument, DocumentVerification

User = get_user_model()


class InstituteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for institute management
    
    Actions:
    - list: Get institutes accessible to user
    - retrieve: Get specific institute details
    - update/partial_update: Update institute information
    - statistics: Get institute statistics
    - students: Get institute students
    - applications: Get scholarship applications
    """
    
    serializer_class = InstituteSerializer
    permission_classes = [InstituteAdminPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['institute_type', 'state', 'city', 'is_active']
    search_fields = ['name', 'code', 'city', 'state']
    ordering_fields = ['name', 'established_year', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter institutes based on user permissions"""
        user = self.request.user
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=user)
            return Institute.objects.filter(id=institute_admin.institute.id)
        except InstituteAdmin.DoesNotExist:
            return Institute.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'retrieve':
            return InstituteDetailSerializer
        return InstituteSerializer
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get comprehensive institute statistics"""
        institute = self.get_object()
        
        # Students statistics
        students_query = Student.objects.filter(institute=institute)
        students_total = students_query.count()
        students_verified = students_query.filter(is_verified=True).count()
        students_by_level = students_query.values('course_level').annotate(
            count=Count('id')
        ).order_by('course_level')
        
        # Applications statistics
        applications_query = ScholarshipApplication.objects.filter(
            student__institute=institute
        )
        applications_total = applications_query.count()
        applications_by_status = applications_query.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Financial statistics
        financial_stats = applications_query.aggregate(
            total_requested=Sum('amount_requested'),
            total_approved=Sum('amount_approved'),
            avg_requested=Avg('amount_requested')
        )
        
        statistics = {
            'students': {
                'total': students_total,
                'verified': students_verified,
                'verification_rate': (students_verified / students_total * 100) if students_total > 0 else 0,
                'by_level': list(students_by_level)
            },
            'applications': {
                'total': applications_total,
                'by_status': list(applications_by_status),
                'pending_count': applications_query.filter(
                    status__in=['submitted', 'under_review', 'document_verification']
                ).count()
            },
            'financial': {
                'total_requested': float(financial_stats['total_requested'] or 0),
                'total_approved': float(financial_stats['total_approved'] or 0),
                'average_requested': float(financial_stats['avg_requested'] or 0)
            }
        }
        
        return Response(statistics)


class InstituteAdminViewSet(viewsets.ModelViewSet):
    """ViewSet for institute admin management"""
    
    serializer_class = InstituteAdminSerializer
    permission_classes = [InstitutePrimaryAdminPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['designation', 'is_primary_admin']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'designation']
    ordering_fields = ['created_at', 'user__first_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter admins based on user permissions"""
        user = self.request.user
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=user)
            return InstituteAdmin.objects.filter(
                institute=institute_admin.institute
            ).select_related('user', 'institute')
        except InstituteAdmin.DoesNotExist:
            return InstituteAdmin.objects.none()
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate/deactivate admin"""
        admin = self.get_object()
        is_active = request.data.get('is_active', True)
        
        admin.user.is_active = is_active
        admin.user.save()
        
        return Response({
            'message': f'Admin {"activated" if is_active else "deactivated"} successfully'
        })


class InstituteBankAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for institute bank account management"""
    
    serializer_class = InstituteBankAccountSerializer
    permission_classes = [InstituteBankAccountPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['account_type', 'is_primary', 'is_active']
    search_fields = ['account_name', 'bank_name', 'branch_name']
    ordering_fields = ['created_at', 'account_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter bank accounts for user's institute"""
        user = self.request.user
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=user)
            return InstituteBankAccount.objects.filter(
                institute=institute_admin.institute
            )
        except InstituteAdmin.DoesNotExist:
            return InstituteBankAccount.objects.none()
    
    def perform_create(self, serializer):
        """Set institute when creating bank account"""
        user = self.request.user
        institute_admin = InstituteAdmin.objects.get(user=user)
        serializer.save(institute=institute_admin.institute)
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set account as primary"""
        account = self.get_object()
        
        # Remove primary status from other accounts
        InstituteBankAccount.objects.filter(
            institute=account.institute,
            is_primary=True
        ).update(is_primary=False)
        
        # Set this account as primary
        account.is_primary = True
        account.save()
        
        return Response({'message': 'Account set as primary successfully'})


class InstituteDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for institute document management"""
    
    serializer_class = InstituteDocumentSerializer
    permission_classes = [InstituteDocumentPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['document_type', 'is_verified']
    search_fields = ['document_name', 'description']
    ordering_fields = ['uploaded_at', 'document_name']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        """Filter documents for user's institute"""
        user = self.request.user
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=user)
            return InstituteDocument.objects.filter(
                institute=institute_admin.institute
            )
        except InstituteAdmin.DoesNotExist:
            return InstituteDocument.objects.none()
    
    def perform_create(self, serializer):
        """Set institute when uploading document"""
        user = self.request.user
        institute_admin = InstituteAdmin.objects.get(user=user)
        serializer.save(institute=institute_admin.institute)
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify institute document"""
        document = self.get_object()
        is_verified = request.data.get('is_verified', True)
        
        document.is_verified = is_verified
        document.verified_by = request.user
        document.verification_date = timezone.now()
        document.save()
        
        return Response({
            'message': f'Document {"verified" if is_verified else "rejected"} successfully'
        })


class StudentVerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for student verification by institute"""
    
    serializer_class = StudentVerificationSerializer
    permission_classes = [StudentVerificationPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course_level', 'academic_year', 'is_verified']
    search_fields = ['student_id', 'user__first_name', 'user__last_name', 'user__email']
    ordering_fields = ['created_at', 'user__first_name', 'enrollment_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter students for user's institute"""
        user = self.request.user
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=user)
            return Student.objects.filter(
                institute=institute_admin.institute
            ).select_related('user', 'department').prefetch_related(
                'documents', 'academic_records'
            )
        except InstituteAdmin.DoesNotExist:
            return Student.objects.none()
    
    @action(detail=True, methods=['post'])
    def verify_student(self, request, pk=None):
        """Verify student profile"""
        student = self.get_object()
        is_verified = request.data.get('is_verified', True)
        verification_notes = request.data.get('verification_notes', '')
        
        student.is_verified = is_verified
        student.verified_by = request.user
        student.verification_date = timezone.now()
        student.save()
        
        return Response({
            'message': f'Student {"verified" if is_verified else "rejected"} successfully',
            'verification_notes': verification_notes
        })
    
    @action(detail=False, methods=['get'])
    def pending_verification(self, request):
        """Get students pending verification"""
        students = self.get_queryset().filter(is_verified=False)
        
        page = self.paginate_queryset(students)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data)


class DocumentVerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for document verification by institute"""
    
    serializer_class = DocumentVerificationSerializer
    permission_classes = [StudentVerificationPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'verification_level', 'auto_verified']
    search_fields = ['document__document_name', 'document__student__student_id']
    ordering_fields = ['created_at', 'verification_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter document verifications for user's institute"""
        user = self.request.user
        
        try:
            institute_admin = InstituteAdmin.objects.get(user=user)
            return DocumentVerification.objects.filter(
                document__student__institute=institute_admin.institute
            ).select_related(
                'document', 'document__student', 'verified_by'
            )
        except InstituteAdmin.DoesNotExist:
            return DocumentVerification.objects.none()
    
    @action(detail=True, methods=['post'])
    def verify_document(self, request, pk=None):
        """Verify a document"""
        verification = self.get_object()
        
        status_value = request.data.get('status', 'verified')
        verification_notes = request.data.get('verification_notes', '')
        rejection_reason = request.data.get('rejection_reason', '')
        compliance_score = request.data.get('compliance_score', 100)
        
        verification.status = status_value
        verification.verification_notes = verification_notes
        verification.compliance_score = compliance_score
        verification.verified_by = request.user
        verification.verification_date = timezone.now()
        
        if status_value == 'rejected':
            verification.rejection_reason = rejection_reason
        
        verification.save()
        
        # Update parent document status
        document = verification.document
        document.status = 'verified' if status_value == 'verified' else 'rejected'
        document.is_verified = status_value == 'verified'
        document.verified_by = request.user
        document.verification_date = timezone.now()
        document.rejection_reason = rejection_reason if status_value == 'rejected' else ''
        document.save()
        
        return Response({
            'message': f'Document {status_value} successfully',
            'verification_id': verification.id
        })
    
    @action(detail=False, methods=['post'])
    def bulk_verify_documents(self, request):
        """Bulk verify multiple documents"""
        document_ids = request.data.get('document_ids', [])
        status_value = request.data.get('status', 'verified')
        verification_notes = request.data.get('verification_notes', '')
        
        verifications = self.get_queryset().filter(
            document__id__in=document_ids,
            status='pending'
        )
        
        updated_count = 0
        for verification in verifications:
            verification.status = status_value
            verification.verification_notes = verification_notes
            verification.verified_by = request.user
            verification.verification_date = timezone.now()
            verification.save()
            
            # Update parent document
            document = verification.document
            document.status = 'verified' if status_value == 'verified' else 'rejected'
            document.is_verified = status_value == 'verified'
            document.verified_by = request.user
            document.verification_date = timezone.now()
            document.save()
            
            updated_count += 1
        
        return Response({
            'message': f'Bulk verification completed for {updated_count} documents',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def pending_documents(self, request):
        """Get documents pending verification"""
        verifications = self.get_queryset().filter(status='pending')
        
        page = self.paginate_queryset(verifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(verifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def rejected_documents(self, request):
        """Get rejected documents"""
        verifications = self.get_queryset().filter(status='rejected')
        
        page = self.paginate_queryset(verifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(verifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def application_documents(self, request):
        """Get documents for a specific application"""
        application_id = request.query_params.get('application_id')
        
        if not application_id:
            return Response(
                {'error': 'application_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            application = ScholarshipApplication.objects.get(
                application_id=application_id
            )
            
            verifications = self.get_queryset().filter(
                document__student=application.student
            )
            
            serializer = self.get_serializer(verifications, many=True)
            return Response(serializer.data)
            
        except ScholarshipApplication.DoesNotExist:
            return Response(
                {'error': 'Application not found'},
                status=status.HTTP_404_NOT_FOUND
            )
