from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db import transaction
from .models import Institute, InstituteAdmin, Course, CourseSpecialization
from .serializers import (
    InstituteSerializer, InstituteRegistrationSerializer, InstituteUpdateSerializer,
    InstituteAdminSerializer, InstituteAdminCreateSerializer, InstituteVerificationSerializer,
    CourseSerializer, CourseCreateUpdateSerializer, CourseSpecializationSerializer
)
from authentication.permissions import IsSystemAdmin, IsInstituteAdmin, IsDepartmentAdmin
from students.models import Student, ScholarshipApplication


class InstituteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for institute management
    
    Actions:
    - list: Get all institutes (filtered by permissions)
    - retrieve: Get specific institute
    - create: Register new institute
    - update/partial_update: Update institute
    - destroy: Delete institute (system admin only)
    - verify: Verify institute (system admin only)
    - statistics: Get institute statistics
    - students: Get institute students
    - applications: Get scholarship applications from institute
    """
    
    serializer_class = InstituteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['institute_type', 'state', 'city', 'is_verified', 'recognition_status']
    search_fields = ['name', 'code', 'city', 'state', 'university_name']
    ordering_fields = ['name', 'established_year', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter institutes based on user permissions"""
        user = self.request.user
        
        if user.is_superuser or user.user_type == 'system_admin':
            return Institute.objects.select_related().prefetch_related(
                'admins__user', 'courses__department'
            )
        
        elif user.user_type == 'institute_admin':
            # Institute admins can see their own institute
            if hasattr(user, 'institute_admin'):
                return Institute.objects.filter(
                    id=user.institute_admin.institute.id
                ).select_related().prefetch_related('admins__user', 'courses__department')
        
        elif user.user_type in ['department_admin', 'student']:
            # Department admins and students can see verified institutes
            return Institute.objects.filter(is_verified=True).select_related()
        
        return Institute.objects.none()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]  # Allow public registration
        elif self.action in ['destroy', 'verify']:
            permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [permissions.IsAuthenticated, IsInstituteAdmin | IsSystemAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return InstituteRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return InstituteUpdateSerializer
        elif self.action == 'verify':
            return InstituteVerificationSerializer
        return InstituteSerializer
    
    @action(detail=True, methods=['post'], permission_classes=[IsSystemAdmin])
    def verify(self, request, pk=None):
        """Verify institute and activate admin accounts"""
        institute = self.get_object()
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            verification_status = serializer.validated_data['verification_status']
            comments = serializer.validated_data.get('verification_comments', '')
            
            with transaction.atomic():
                institute.is_verified = verification_status
                institute.verification_date = timezone.now()
                institute.save()
                
                if verification_status:
                    # Activate all admin accounts for this institute
                    institute.admins.update(is_active=True)
                    for admin in institute.admins.all():
                        admin.user.is_active = True
                        admin.user.save()
                
            return Response({
                'message': f'Institute {"verified" if verification_status else "rejected"} successfully',
                'comments': comments
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get comprehensive institute statistics"""
        institute = self.get_object()
        
        # Students statistics
        students_total = Student.objects.filter(institute=institute).count()
        students_verified = Student.objects.filter(institute=institute, is_verified=True).count()
        students_by_year = Student.objects.filter(institute=institute).values(
            'academic_year'
        ).annotate(count=Count('id')).order_by('academic_year')
        
        # Applications statistics
        applications_total = ScholarshipApplication.objects.filter(
            student__institute=institute
        ).count()
        applications_by_status = ScholarshipApplication.objects.filter(
            student__institute=institute
        ).values('status').annotate(count=Count('id'))
        
        # Courses statistics
        courses_total = institute.courses.count()
        courses_active = institute.courses.filter(is_active=True).count()
        
        statistics = {
            'students': {
                'total': students_total,
                'verified': students_verified,
                'verification_rate': (students_verified / students_total * 100) if students_total > 0 else 0,
                'by_year': list(students_by_year)
            },
            'applications': {
                'total': applications_total,
                'by_status': list(applications_by_status)
            },
            'courses': {
                'total': courses_total,
                'active': courses_active
            }
        }
        
        return Response(statistics)
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get students from this institute"""
        institute = self.get_object()
        
        # Check permissions
        user = request.user
        if not (user.is_superuser or user.user_type == 'system_admin'):
            if user.user_type == 'institute_admin':
                if not (hasattr(user, 'institute_admin') and user.institute_admin.institute == institute):
                    return Response(
                        {'error': 'You can only view students from your own institute'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {'error': 'Permission denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        from students.serializers import StudentSerializer
        students = Student.objects.filter(institute=institute).select_related(
            'user', 'department'
        ).prefetch_related('documents', 'scholarship_applications')
        
        # Apply filtering and pagination
        filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
        for backend in filter_backends:
            students = backend().filter_queryset(request, students, self)
        
        page = self.paginate_queryset(students)
        if page is not None:
            serializer = StudentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)


class InstituteAdminViewSet(viewsets.ModelViewSet):
    """ViewSet for institute admin management"""
    
    serializer_class = InstituteAdminSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['institute', 'is_active', 'position']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'position']
    ordering_fields = ['created_at', 'user__first_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter admins based on user permissions"""
        user = self.request.user
        
        if user.is_superuser or user.user_type == 'system_admin':
            return InstituteAdmin.objects.select_related('user', 'institute')
        
        elif user.user_type == 'institute_admin':
            # Institute admins can see other admins in their institute
            if hasattr(user, 'institute_admin'):
                return InstituteAdmin.objects.filter(
                    institute=user.institute_admin.institute
                ).select_related('user', 'institute')
        
        return InstituteAdmin.objects.none()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create', 'destroy', 'activate']:
            permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [permissions.IsAuthenticated, IsInstituteAdmin | IsSystemAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated, IsInstituteAdmin | IsSystemAdmin]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return InstituteAdminCreateSerializer
        return InstituteAdminSerializer


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet for course management"""
    
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['institute', 'department', 'level', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'level', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter courses based on user permissions"""
        user = self.request.user
        
        if user.is_superuser or user.user_type == 'system_admin':
            return Course.objects.select_related('institute', 'department').prefetch_related('specializations')
        
        elif user.user_type == 'institute_admin':
            if hasattr(user, 'institute_admin'):
                return Course.objects.filter(
                    institute=user.institute_admin.institute
                ).select_related('institute', 'department').prefetch_related('specializations')
        
        elif user.user_type == 'department_admin':
            if hasattr(user, 'department_admin'):
                return Course.objects.filter(
                    department=user.department_admin.department
                ).select_related('institute', 'department').prefetch_related('specializations')
        
        elif user.user_type == 'student':
            # Students can see all active courses
            return Course.objects.filter(is_active=True).select_related('institute', 'department')
        
        return Course.objects.none()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsInstituteAdmin | IsSystemAdmin]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [permissions.IsAuthenticated, IsInstituteAdmin | IsDepartmentAdmin | IsSystemAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return CourseCreateUpdateSerializer
        return CourseSerializer


class CourseSpecializationViewSet(viewsets.ModelViewSet):
    """ViewSet for course specialization management"""
    
    serializer_class = CourseSpecializationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter specializations based on user permissions"""
        user = self.request.user
        
        if user.is_superuser or user.user_type == 'system_admin':
            return CourseSpecialization.objects.select_related('course__institute')
        
        elif user.user_type == 'institute_admin':
            if hasattr(user, 'institute_admin'):
                return CourseSpecialization.objects.filter(
                    course__institute=user.institute_admin.institute
                ).select_related('course__institute')
        
        elif user.user_type == 'department_admin':
            if hasattr(user, 'department_admin'):
                return CourseSpecialization.objects.filter(
                    course__department=user.department_admin.department
                ).select_related('course__institute')
        
        elif user.user_type == 'student':
            # Students can see all active specializations
            return CourseSpecialization.objects.filter(
                is_active=True
            ).select_related('course__institute')
        
        return CourseSpecialization.objects.none()
