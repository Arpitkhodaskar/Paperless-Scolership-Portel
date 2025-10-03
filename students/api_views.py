from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from .models import Student, StudentDocument, ScholarshipApplication, AcademicRecord
from .serializers import (
    StudentRegistrationSerializer, StudentLoginSerializer, StudentSerializer,
    StudentProfileUpdateSerializer, UserProfileUpdateSerializer,
    StudentDocumentUploadSerializer, StudentDocumentSerializer,
    ScholarshipApplicationCreateSerializer, ScholarshipApplicationSerializer
)
from authentication.models import CustomUser


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def student_registration(request):
    """
    Student Registration API
    POST /api/students/register/
    
    Required fields:
    - user_data: {username, email, password, confirm_password, first_name, last_name, phone_number}
    - institute: institute_id
    - department: department_id
    - course_level: undergraduate/postgraduate/phd/diploma
    - course_name: string
    - academic_year: 1st/2nd/3rd/4th/5th
    - enrollment_date: YYYY-MM-DD
    - roll_number: string
    - admission_type: regular/management/nri
    - category: general/obc/sc/st/ews
    - father_name, mother_name: strings
    - family_income: decimal
    - permanent_address, current_address: text
    - emergency_contact: string
    """
    try:
        with transaction.atomic():
            serializer = StudentRegistrationSerializer(data=request.data)
            
            if serializer.is_valid():
                student = serializer.save()
                
                # Generate JWT tokens
                user = student.user
                refresh = RefreshToken.for_user(user)
                
                # Prepare response data
                student_data = StudentSerializer(student).data
                
                return Response({
                    'success': True,
                    'message': 'Student registered successfully',
                    'data': {
                        'student': student_data,
                        'tokens': {
                            'access': str(refresh.access_token),
                            'refresh': str(refresh)
                        }
                    }
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'message': 'Registration failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Registration failed due to server error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def student_login(request):
    """
    Student Login API
    POST /api/students/login/
    
    Required fields:
    - username_or_email: string (username or email)
    - password: string
    """
    try:
        serializer = StudentLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Get student data
            student_data = StudentSerializer(user.student_profile).data
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'data': {
                    'student': student_data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                }
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Login failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Login failed due to server error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_student_profile(request):
    """
    Get Student Profile API
    GET /api/students/profile/
    
    Returns complete student profile with user details, documents, and applications
    """
    try:
        if not hasattr(request.user, 'student_profile'):
            return Response({
                'success': False,
                'message': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        student = request.user.student_profile
        
        # Get related data
        documents = student.documents.all()
        applications = student.scholarship_applications.all().order_by('-created_at')
        academic_records = student.academic_records.all().order_by('-academic_year', '-semester')
        
        # Serialize data
        student_data = StudentSerializer(student).data
        documents_data = StudentDocumentSerializer(documents, many=True).data
        applications_data = ScholarshipApplicationSerializer(applications, many=True).data
        
        return Response({
            'success': True,
            'data': {
                'profile': student_data,
                'documents': documents_data,
                'applications': applications_data,
                'academic_records': academic_records,
                'statistics': {
                    'total_documents': documents.count(),
                    'verified_documents': documents.filter(is_verified=True).count(),
                    'total_applications': applications.count(),
                    'approved_applications': applications.filter(status='approved').count(),
                    'pending_applications': applications.filter(status__in=['draft', 'submitted', 'under_review']).count()
                }
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to retrieve profile',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_student_profile(request):
    """
    Update Student Profile API
    PUT/PATCH /api/students/profile/update/
    
    Updates both user and student profile information
    """
    try:
        if not hasattr(request.user, 'student_profile'):
            return Response({
                'success': False,
                'message': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        student = request.user.student_profile
        user = request.user
        
        with transaction.atomic():
            # Update user information
            user_data = request.data.get('user_data', {})
            if user_data:
                user_serializer = UserProfileUpdateSerializer(
                    user, data=user_data, partial=True
                )
                if user_serializer.is_valid():
                    user_serializer.save()
                else:
                    return Response({
                        'success': False,
                        'message': 'User profile update failed',
                        'errors': user_serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update student profile
            student_data = {k: v for k, v in request.data.items() if k != 'user_data'}
            if student_data:
                student_serializer = StudentProfileUpdateSerializer(
                    student, data=student_data, partial=True
                )
                if student_serializer.is_valid():
                    student_serializer.save()
                else:
                    return Response({
                        'success': False,
                        'message': 'Student profile update failed',
                        'errors': student_serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        # Return updated profile
        updated_student = StudentSerializer(student).data
        
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'data': {
                'student': updated_student
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Profile update failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def student_documents(request):
    """
    Student Documents API
    GET /api/students/documents/ - List all documents
    POST /api/students/documents/ - Upload new document
    """
    try:
        if not hasattr(request.user, 'student_profile'):
            return Response({
                'success': False,
                'message': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        student = request.user.student_profile
        
        if request.method == 'GET':
            documents = student.documents.all().order_by('-uploaded_at')
            
            # Filter by document type if provided
            doc_type = request.query_params.get('type')
            if doc_type:
                documents = documents.filter(document_type=doc_type)
            
            # Filter by verification status if provided
            verified = request.query_params.get('verified')
            if verified is not None:
                documents = documents.filter(is_verified=verified.lower() == 'true')
            
            serializer = StudentDocumentSerializer(documents, many=True)
            
            return Response({
                'success': True,
                'data': {
                    'documents': serializer.data,
                    'count': documents.count(),
                    'verified_count': documents.filter(is_verified=True).count()
                }
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            serializer = StudentDocumentUploadSerializer(
                data=request.data, 
                context={'request': request}
            )
            
            if serializer.is_valid():
                document = serializer.save()
                document_data = StudentDocumentSerializer(document).data
                
                return Response({
                    'success': True,
                    'message': 'Document uploaded successfully',
                    'data': {
                        'document': document_data
                    }
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'message': 'Document upload failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Document operation failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def document_detail(request, document_id):
    """
    Document Detail API
    GET /api/students/documents/{id}/ - Get document details
    PUT /api/students/documents/{id}/ - Update document
    DELETE /api/students/documents/{id}/ - Delete document
    """
    try:
        if not hasattr(request.user, 'student_profile'):
            return Response({
                'success': False,
                'message': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        student = request.user.student_profile
        document = get_object_or_404(StudentDocument, id=document_id, student=student)
        
        if request.method == 'GET':
            serializer = StudentDocumentSerializer(document)
            return Response({
                'success': True,
                'data': {
                    'document': serializer.data
                }
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'PUT':
            if document.is_verified:
                return Response({
                    'success': False,
                    'message': 'Cannot update verified document'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = StudentDocumentUploadSerializer(
                document, data=request.data, partial=True,
                context={'request': request}
            )
            
            if serializer.is_valid():
                serializer.save()
                document_data = StudentDocumentSerializer(document).data
                
                return Response({
                    'success': True,
                    'message': 'Document updated successfully',
                    'data': {
                        'document': document_data
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Document update failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            if document.is_verified:
                return Response({
                    'success': False,
                    'message': 'Cannot delete verified document'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            document.delete()
            return Response({
                'success': True,
                'message': 'Document deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
            
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Document operation failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def scholarship_applications(request):
    """
    Scholarship Applications API
    GET /api/students/applications/ - List all applications
    POST /api/students/applications/ - Create new application
    """
    try:
        if not hasattr(request.user, 'student_profile'):
            return Response({
                'success': False,
                'message': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        student = request.user.student_profile
        
        if request.method == 'GET':
            applications = student.scholarship_applications.all().order_by('-created_at')
            
            # Filter by status if provided
            status_filter = request.query_params.get('status')
            if status_filter:
                applications = applications.filter(status=status_filter)
            
            # Filter by scholarship type if provided
            type_filter = request.query_params.get('type')
            if type_filter:
                applications = applications.filter(scholarship_type=type_filter)
            
            serializer = ScholarshipApplicationSerializer(applications, many=True)
            
            # Calculate statistics
            stats = {
                'total': applications.count(),
                'draft': applications.filter(status='draft').count(),
                'submitted': applications.filter(status='submitted').count(),
                'under_review': applications.filter(status='under_review').count(),
                'approved': applications.filter(status='approved').count(),
                'rejected': applications.filter(status='rejected').count(),
            }
            
            return Response({
                'success': True,
                'data': {
                    'applications': serializer.data,
                    'statistics': stats
                }
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            serializer = ScholarshipApplicationCreateSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                application = serializer.save()
                application_data = ScholarshipApplicationSerializer(application).data
                
                return Response({
                    'success': True,
                    'message': 'Application created successfully',
                    'data': {
                        'application': application_data
                    }
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'message': 'Application creation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Application operation failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def application_detail(request, application_id):
    """
    Application Detail API
    GET /api/students/applications/{id}/ - Get application details
    PUT /api/students/applications/{id}/ - Update application (draft only)
    DELETE /api/students/applications/{id}/ - Delete application (draft only)
    """
    try:
        if not hasattr(request.user, 'student_profile'):
            return Response({
                'success': False,
                'message': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        student = request.user.student_profile
        application = get_object_or_404(
            ScholarshipApplication, 
            application_id=application_id, 
            student=student
        )
        
        if request.method == 'GET':
            serializer = ScholarshipApplicationSerializer(application)
            return Response({
                'success': True,
                'data': {
                    'application': serializer.data
                }
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'PUT':
            if application.status != 'draft':
                return Response({
                    'success': False,
                    'message': 'Can only edit draft applications'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ScholarshipApplicationCreateSerializer(
                application, data=request.data, partial=True,
                context={'request': request}
            )
            
            if serializer.is_valid():
                serializer.save()
                application_data = ScholarshipApplicationSerializer(application).data
                
                return Response({
                    'success': True,
                    'message': 'Application updated successfully',
                    'data': {
                        'application': application_data
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Application update failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            if application.status != 'draft':
                return Response({
                    'success': False,
                    'message': 'Can only delete draft applications'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            application.delete()
            return Response({
                'success': True,
                'message': 'Application deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
            
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Application operation failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_application(request, application_id):
    """
    Submit Application for Review API
    POST /api/students/applications/{id}/submit/
    
    Required fields:
    - declaration: boolean (must be true)
    """
    try:
        if not hasattr(request.user, 'student_profile'):
            return Response({
                'success': False,
                'message': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        student = request.user.student_profile
        application = get_object_or_404(
            ScholarshipApplication, 
            application_id=application_id, 
            student=student
        )
        
        if application.status != 'draft':
            return Response({
                'success': False,
                'message': 'Application is already submitted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        declaration = request.data.get('declaration', False)
        if not declaration:
            return Response({
                'success': False,
                'message': 'Declaration acceptance is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if student has required documents
        required_docs = ['identity_proof', 'address_proof', 'income_certificate']
        uploaded_doc_types = student.documents.filter(is_verified=True).values_list('document_type', flat=True)
        
        missing_docs = [doc for doc in required_docs if doc not in uploaded_doc_types]
        if missing_docs:
            return Response({
                'success': False,
                'message': f'Missing required documents: {", ".join(missing_docs)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Submit application
        with transaction.atomic():
            application.status = 'submitted'
            application.submitted_at = timezone.now()
            application.save()
        
        application_data = ScholarshipApplicationSerializer(application).data
        
        return Response({
            'success': True,
            'message': 'Application submitted successfully',
            'data': {
                'application': application_data
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Application submission failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def application_status_tracking(request, application_id):
    """
    Application Status Tracking API
    GET /api/students/applications/{id}/status/
    
    Returns detailed status tracking with timeline
    """
    try:
        if not hasattr(request.user, 'student_profile'):
            return Response({
                'success': False,
                'message': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        student = request.user.student_profile
        application = get_object_or_404(
            ScholarshipApplication, 
            application_id=application_id, 
            student=student
        )
        
        # Create status timeline
        timeline = []
        
        if application.created_at:
            timeline.append({
                'status': 'draft',
                'description': 'Application created',
                'timestamp': application.created_at,
                'completed': True
            })
        
        if application.submitted_at:
            timeline.append({
                'status': 'submitted',
                'description': 'Application submitted for review',
                'timestamp': application.submitted_at,
                'completed': True
            })
        
        if application.review_started_at:
            timeline.append({
                'status': 'under_review',
                'description': 'Review started',
                'timestamp': application.review_started_at,
                'completed': True,
                'reviewer': application.assigned_to.get_full_name() if application.assigned_to else None
            })
        
        if application.review_completed_at:
            if application.status == 'approved':
                timeline.append({
                    'status': 'approved',
                    'description': f'Application approved (Amount: ₹{application.amount_approved})',
                    'timestamp': application.approved_at,
                    'completed': True,
                    'approver': application.approved_by.get_full_name() if application.approved_by else None
                })
            elif application.status == 'rejected':
                timeline.append({
                    'status': 'rejected',
                    'description': f'Application rejected - {application.rejection_reason}',
                    'timestamp': application.rejected_at,
                    'completed': True,
                    'reviewer': application.reviewed_by.get_full_name() if application.reviewed_by else None
                })
        
        # Calculate processing time
        processing_time = None
        if application.submitted_at:
            end_time = application.review_completed_at or timezone.now()
            processing_time = (end_time - application.submitted_at).days
        
        return Response({
            'success': True,
            'data': {
                'application_id': application.application_id,
                'current_status': application.status,
                'status_display': application.get_status_display(),
                'timeline': timeline,
                'processing_time_days': processing_time,
                'is_overdue': application.is_overdue,
                'estimated_completion': None,  # Can be calculated based on average processing time
                'next_action': _get_next_action(application),
                'comments': application.review_comments if application.review_comments else None
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Status tracking failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_next_action(application):
    """Helper function to determine next action for application"""
    if application.status == 'draft':
        return 'Complete and submit application'
    elif application.status == 'submitted':
        return 'Waiting for initial review'
    elif application.status == 'under_review':
        return 'Under review by administrator'
    elif application.status == 'document_verification':
        return 'Document verification in progress'
    elif application.status == 'eligibility_check':
        return 'Eligibility verification in progress'
    elif application.status == 'approved':
        return 'Waiting for disbursement'
    elif application.status == 'rejected':
        return 'Application process completed'
    elif application.status == 'on_hold':
        return 'Additional information required'
    else:
        return 'Contact administrator for status update'


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    """
    Student Dashboard Summary API
    GET /api/students/dashboard/
    
    Returns summary information for student dashboard
    """
    try:
        if not hasattr(request.user, 'student_profile'):
            return Response({
                'success': False,
                'message': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        student = request.user.student_profile
        
        # Document statistics
        total_documents = student.documents.count()
        verified_documents = student.documents.filter(is_verified=True).count()
        pending_documents = total_documents - verified_documents
        
        # Application statistics
        total_applications = student.scholarship_applications.count()
        pending_applications = student.scholarship_applications.filter(
            status__in=['draft', 'submitted', 'under_review', 'document_verification', 'eligibility_check']
        ).count()
        approved_applications = student.scholarship_applications.filter(status='approved').count()
        rejected_applications = student.scholarship_applications.filter(status='rejected').count()
        
        # Recent activities
        recent_documents = student.documents.order_by('-uploaded_at')[:3]
        recent_applications = student.scholarship_applications.order_by('-created_at')[:3]
        
        # Profile completion percentage
        profile_fields = [
            student.father_name, student.mother_name, student.family_income,
            student.permanent_address, student.current_address, student.emergency_contact
        ]
        completed_fields = sum(1 for field in profile_fields if field)
        profile_completion = (completed_fields / len(profile_fields)) * 100
        
        return Response({
            'success': True,
            'data': {
                'student_info': {
                    'name': student.user.get_full_name(),
                    'student_id': student.student_id,
                    'institute': student.institute.name,
                    'department': student.department.name,
                    'course': student.course_name,
                    'academic_year': student.academic_year,
                    'is_verified': student.is_verified
                },
                'statistics': {
                    'documents': {
                        'total': total_documents,
                        'verified': verified_documents,
                        'pending': pending_documents,
                        'completion_rate': (verified_documents / total_documents * 100) if total_documents > 0 else 0
                    },
                    'applications': {
                        'total': total_applications,
                        'pending': pending_applications,
                        'approved': approved_applications,
                        'rejected': rejected_applications
                    },
                    'profile_completion': profile_completion
                },
                'recent_activities': {
                    'documents': StudentDocumentSerializer(recent_documents, many=True).data,
                    'applications': ScholarshipApplicationSerializer(recent_applications, many=True).data
                },
                'notifications': {
                    'pending_document_verification': pending_documents,
                    'incomplete_applications': student.scholarship_applications.filter(status='draft').count(),
                    'profile_incomplete': profile_completion < 100
                }
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Dashboard summary failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
