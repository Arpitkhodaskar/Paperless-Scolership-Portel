from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db import transaction
from .models import (
    Student, StudentDocument, AcademicRecord, 
    ScholarshipApplication, DocumentVerification
)
from .serializers import (
    StudentRegistrationSerializer, StudentSerializer, StudentDocumentSerializer,
    StudentDocumentUploadSerializer, AcademicRecordSerializer,
    ScholarshipApplicationCreateSerializer, ScholarshipApplicationSerializer,
    ScholarshipApplicationUpdateSerializer, ScholarshipApplicationSubmitSerializer,
    ScholarshipApplicationReviewSerializer
)
from authentication.permissions import IsStudent, IsInstituteAdmin, IsDepartmentAdmin, IsSystemAdmin


class StudentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for student profile management
    
    Actions:
    - list: Get all students (admin only)
    - retrieve: Get student profile
    - create: Register as student
    - update/partial_update: Update profile
    - destroy: Delete profile (admin only)
    - me: Get current user's student profile
    - verify: Verify student profile (admin only)
    - documents: Get student documents
    - academic_records: Get academic records
    - applications: Get scholarship applications
    """
    
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['institute', 'department', 'course_level', 'academic_year', 'category', 'is_verified']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'student_id', 'roll_number']
    ordering_fields = ['created_at', 'user__first_name', 'academic_year']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        user = self.request.user
        
        if user.is_superuser or user.user_type == 'system_admin':
            return Student.objects.select_related(
                'user', 'institute', 'department', 'verified_by'
            ).prefetch_related('documents', 'academic_records', 'scholarship_applications')
        
        elif user.user_type in ['institute_admin', 'department_admin']:
            # Institute/Department admins can see their students
            filters = Q()
            if hasattr(user, 'institute_admin'):
                filters |= Q(institute=user.institute_admin.institute)
            if hasattr(user, 'department_admin'):
                filters |= Q(department=user.department_admin.department)
            
            return Student.objects.filter(filters).select_related(
                'user', 'institute', 'department', 'verified_by'
            ).prefetch_related('documents', 'academic_records', 'scholarship_applications')
        
        elif user.user_type == 'student':
            # Students can only see their own profile
            return Student.objects.filter(user=user).select_related(
                'user', 'institute', 'department', 'verified_by'
            ).prefetch_related('documents', 'academic_records', 'scholarship_applications')
        
        return Student.objects.none()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated, IsStudent]
        elif self.action in ['list', 'verify']:
            permission_classes = [permissions.IsAuthenticated, IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin]
        elif self.action == 'destroy':
            permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return StudentRegistrationSerializer
        return StudentSerializer
    
    def perform_create(self, serializer):
        """Create student profile for authenticated user"""
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's student profile"""
        try:
            student = request.user.student_profile
            serializer = self.get_serializer(student)
            return Response(serializer.data)
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin])
    def verify(self, request, pk=None):
        """Verify student profile"""
        student = self.get_object()
        
        # Check permissions
        user = request.user
        can_verify = False
        
        if user.is_superuser or user.user_type == 'system_admin':
            can_verify = True
        elif user.user_type == 'institute_admin' and hasattr(user, 'institute_admin'):
            can_verify = student.institute == user.institute_admin.institute
        elif user.user_type == 'department_admin' and hasattr(user, 'department_admin'):
            can_verify = student.department == user.department_admin.department
        
        if not can_verify:
            return Response(
                {'error': 'You do not have permission to verify this student'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        student.is_verified = True
        student.verification_date = timezone.now()
        student.verified_by = user
        student.save()
        
        return Response({'message': 'Student verified successfully'})
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Get student documents"""
        student = self.get_object()
        documents = student.documents.select_related('verified_by').prefetch_related('verification')
        serializer = StudentDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def academic_records(self, request, pk=None):
        """Get student academic records"""
        student = self.get_object()
        records = student.academic_records.all().order_by('-academic_year', '-semester')
        serializer = AcademicRecordSerializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """Get student scholarship applications"""
        student = self.get_object()
        applications = student.scholarship_applications.select_related(
            'assigned_to', 'reviewed_by', 'approved_by'
        ).order_by('-created_at')
        serializer = ScholarshipApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class StudentDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for student document management
    
    Actions:
    - list: Get documents for current student
    - retrieve: Get specific document
    - create: Upload new document
    - update/partial_update: Update document
    - destroy: Delete document
    - verify: Verify document (admin only)
    - bulk_upload: Upload multiple documents
    """
    
    serializer_class = StudentDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['document_type', 'is_verified', 'document_name']
    search_fields = ['document_name', 'document_number', 'issuing_authority']
    ordering_fields = ['uploaded_at', 'document_type']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        """Get documents for current student or all for admins"""
        user = self.request.user
        
        if user.user_type == 'student':
            try:
                student = user.student_profile
                return StudentDocument.objects.filter(student=student).select_related(
                    'verified_by'
                ).prefetch_related('verification')
            except Student.DoesNotExist:
                return StudentDocument.objects.none()
        
        elif user.user_type in ['institute_admin', 'department_admin', 'system_admin'] or user.is_superuser:
            # Admins can see all documents in their jurisdiction
            filters = Q()
            if user.user_type == 'institute_admin' and hasattr(user, 'institute_admin'):
                filters = Q(student__institute=user.institute_admin.institute)
            elif user.user_type == 'department_admin' and hasattr(user, 'department_admin'):
                filters = Q(student__department=user.department_admin.department)
            
            return StudentDocument.objects.filter(filters).select_related(
                'student__user', 'verified_by'
            ).prefetch_related('verification')
        
        return StudentDocument.objects.none()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'verify':
            permission_classes = [permissions.IsAuthenticated, IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated, IsStudent]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return StudentDocumentUploadSerializer
        return StudentDocumentSerializer
    
    @action(detail=True, methods=['post'], permission_classes=[IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin])
    def verify(self, request, pk=None):
        """Verify a document"""
        document = self.get_object()
        
        # Check permissions
        user = request.user
        can_verify = False
        
        if user.is_superuser or user.user_type == 'system_admin':
            can_verify = True
        elif user.user_type == 'institute_admin' and hasattr(user, 'institute_admin'):
            can_verify = document.student.institute == user.institute_admin.institute
        elif user.user_type == 'department_admin' and hasattr(user, 'department_admin'):
            can_verify = document.student.department == user.department_admin.department
        
        if not can_verify:
            return Response(
                {'error': 'You do not have permission to verify this document'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        with transaction.atomic():
            document.is_verified = True
            document.verification_date = timezone.now()
            document.verified_by = user
            document.save()
            
            # Create verification record
            DocumentVerification.objects.create(
                document=document,
                verified_by=user,
                verification_status='approved',
                comments=request.data.get('comments', ''),
            )
        
        return Response({'message': 'Document verified successfully'})
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """Upload multiple documents at once"""
        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {'error': 'No files provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        results = []
        for file in files:
            serializer = StudentDocumentUploadSerializer(
                data={
                    'document_file': file,
                    'document_name': file.name,
                    'document_type': 'other',  # Default type
                },
                context={'request': request}
            )
            
            if serializer.is_valid():
                serializer.save()
                results.append({'file': file.name, 'status': 'success'})
            else:
                results.append({'file': file.name, 'status': 'error', 'errors': serializer.errors})
        
        return Response(results)


class ScholarshipApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for scholarship application management
    
    Actions:
    - list: Get applications (filtered by permissions)
    - retrieve: Get specific application
    - create: Create new application
    - update/partial_update: Update draft application
    - destroy: Delete draft application
    - submit: Submit application for review
    - review: Review application (admin only)
    - approve: Approve application (admin only)
    - reject: Reject application (admin only)
    - assign: Assign application to reviewer (admin only)
    """
    
    serializer_class = ScholarshipApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'scholarship_type', 'academic_year', 'priority']
    search_fields = ['application_id', 'scholarship_name', 'student__user__first_name', 'student__user__last_name']
    ordering_fields = ['created_at', 'amount_requested', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter applications based on user permissions"""
        user = self.request.user
        
        if user.user_type == 'student':
            try:
                student = user.student_profile
                return ScholarshipApplication.objects.filter(student=student).select_related(
                    'student__user', 'assigned_to', 'reviewed_by', 'approved_by'
                )
            except Student.DoesNotExist:
                return ScholarshipApplication.objects.none()
        
        elif user.user_type in ['institute_admin', 'department_admin', 'system_admin'] or user.is_superuser:
            # Admins can see applications in their jurisdiction
            filters = Q()
            if user.user_type == 'institute_admin' and hasattr(user, 'institute_admin'):
                filters = Q(student__institute=user.institute_admin.institute)
            elif user.user_type == 'department_admin' and hasattr(user, 'department_admin'):
                filters = Q(student__department=user.department_admin.department)
            
            return ScholarshipApplication.objects.filter(filters).select_related(
                'student__user', 'student__institute', 'student__department',
                'assigned_to', 'reviewed_by', 'approved_by'
            )
        
        return ScholarshipApplication.objects.none()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create', 'submit']:
            permission_classes = [permissions.IsAuthenticated, IsStudent]
        elif self.action in ['review', 'approve', 'reject', 'assign']:
            permission_classes = [permissions.IsAuthenticated, IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ScholarshipApplicationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ScholarshipApplicationUpdateSerializer
        elif self.action == 'submit':
            return ScholarshipApplicationSubmitSerializer
        elif self.action in ['review', 'approve', 'reject']:
            return ScholarshipApplicationReviewSerializer
        return ScholarshipApplicationSerializer
    
    @action(detail=True, methods=['post'], permission_classes=[IsStudent])
    def submit(self, request, pk=None):
        """Submit application for review"""
        application = self.get_object()
        
        # Check if user owns the application
        if application.student.user != request.user:
            return Response(
                {'error': 'You can only submit your own applications'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if application.status != 'draft':
            return Response(
                {'error': 'Only draft applications can be submitted'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            application.status = 'submitted'
            application.submitted_at = timezone.now()
            application.save()
            
            return Response({'message': 'Application submitted successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin])
    def review(self, request, pk=None):
        """Start or update application review"""
        application = self.get_object()
        
        if application.status not in ['submitted', 'under_review']:
            return Response(
                {'error': 'Application is not in reviewable state'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            if application.status == 'submitted':
                application.review_started_at = timezone.now()
                application.assigned_to = request.user
            
            application.reviewed_by = request.user
            serializer.save()
            
            return Response({'message': 'Application review updated successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin])
    def approve(self, request, pk=None):
        """Approve application"""
        application = self.get_object()
        
        if application.status not in ['eligibility_check', 'under_review']:
            return Response(
                {'error': 'Application cannot be approved in current state'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        amount_approved = request.data.get('amount_approved', application.amount_requested)
        
        with transaction.atomic():
            application.status = 'approved'
            application.approved_at = timezone.now()
            application.approved_by = request.user
            application.amount_approved = amount_approved
            application.review_completed_at = timezone.now()
            application.save()
        
        return Response({'message': 'Application approved successfully'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin])
    def reject(self, request, pk=None):
        """Reject application"""
        application = self.get_object()
        
        if application.status in ['approved', 'disbursed', 'rejected']:
            return Response(
                {'error': 'Application cannot be rejected in current state'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_reason = request.data.get('rejection_reason', '')
        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            application.status = 'rejected'
            application.rejected_at = timezone.now()
            application.reviewed_by = request.user
            application.rejection_reason = rejection_reason
            application.review_completed_at = timezone.now()
            application.save()
        
        return Response({'message': 'Application rejected successfully'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin])
    def assign(self, request, pk=None):
        """Assign application to a reviewer"""
        application = self.get_object()
        assignee_id = request.data.get('assignee_id')
        
        if not assignee_id:
            return Response(
                {'error': 'Assignee ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            assignee = User.objects.get(id=assignee_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Assignee not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        application.assigned_to = assignee
        application.save()
        
        return Response({'message': f'Application assigned to {assignee.get_full_name()}'})


class AcademicRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for academic record management"""
    
    serializer_class = AcademicRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['academic_year', 'semester', 'grade']
    ordering_fields = ['academic_year', 'semester', 'gpa']
    ordering = ['-academic_year', '-semester']
    
    def get_queryset(self):
        """Get academic records based on user permissions"""
        user = self.request.user
        
        if user.user_type == 'student':
            try:
                student = user.student_profile
                return AcademicRecord.objects.filter(student=student)
            except Student.DoesNotExist:
                return AcademicRecord.objects.none()
        
        elif user.user_type in ['institute_admin', 'department_admin', 'system_admin'] or user.is_superuser:
            # Admins can see records in their jurisdiction
            filters = Q()
            if user.user_type == 'institute_admin' and hasattr(user, 'institute_admin'):
                filters = Q(student__institute=user.institute_admin.institute)
            elif user.user_type == 'department_admin' and hasattr(user, 'department_admin'):
                filters = Q(student__department=user.department_admin.department)
            
            return AcademicRecord.objects.filter(filters).select_related('student__user')
        
        return AcademicRecord.objects.none()
    
    def perform_create(self, serializer):
        """Create academic record for current student"""
        if self.request.user.user_type == 'student':
            student = self.request.user.student_profile
            serializer.save(student=student)
