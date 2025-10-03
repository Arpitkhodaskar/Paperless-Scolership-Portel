from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.core.mail import send_mail
from django.conf import settings
import logging

from .models import (
    Grievance, GrievanceCategory, GrievanceComment, GrievanceDocument,
    GrievanceAdmin, GrievanceStatusLog, FAQ, GrievanceTemplate,
    GrievanceNotificationLog
)
from .serializers import (
    GrievanceSerializer, GrievanceCategorySerializer, GrievanceCommentSerializer,
    GrievanceDocumentSerializer, GrievanceDetailSerializer, FAQSerializer,
    GrievanceTemplateSerializer, GrievanceStatsSerializer
)

logger = logging.getLogger(__name__)


class GrievanceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing grievances"""
    
    serializer_class = GrievanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Students can only see their own grievances
        if hasattr(user, 'student_profile'):
            return Grievance.objects.filter(student=user.student_profile)
        
        # Grievance admins can see assigned grievances and those in their categories
        elif hasattr(user, 'grievance_admin_profile'):
            admin_profile = user.grievance_admin_profile
            return Grievance.objects.filter(
                Q(assigned_to=user) |
                Q(category__in=admin_profile.categories_handled.all()) |
                Q(institute=admin_profile.institute)
            ).distinct()
        
        # Staff can see all grievances
        elif user.is_staff:
            return Grievance.objects.all()
        
        return Grievance.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GrievanceDetailSerializer
        return GrievanceSerializer
    
    def perform_create(self, serializer):
        """Create grievance and send notifications"""
        # Set student from authenticated user
        if hasattr(self.request.user, 'student_profile'):
            grievance = serializer.save(student=self.request.user.student_profile)
            
            # Send notification emails
            self.send_grievance_created_notifications(grievance)
            
            # Log creation
            logger.info(f"Grievance {grievance.grievance_id} created by {self.request.user.username}")
        else:
            raise PermissionError("Only students can create grievances")
    
    def send_grievance_created_notifications(self, grievance):
        """Send email notifications when grievance is created"""
        try:
            # Send notifications to category administrators
            category = grievance.category
            if category.notification_email_list:
                for email in category.notification_email_list:
                    self.send_email_notification(
                        recipient_email=email,
                        subject=f"New Grievance Submitted - {grievance.grievance_id}",
                        template='grievance_created_admin',
                        context={
                            'grievance': grievance,
                            'student_name': grievance.student.user.get_full_name(),
                            'category': category.name
                        }
                    )
            
            # Auto-assign if possible
            self.auto_assign_grievance(grievance)
            
        except Exception as e:
            logger.error(f"Error sending grievance creation notifications: {str(e)}")
    
    def auto_assign_grievance(self, grievance):
        """Auto-assign grievance to appropriate admin"""
        try:
            # Find available admin for this category
            category_admins = GrievanceAdmin.objects.filter(
                categories_handled=grievance.category,
                is_active=True,
                auto_assignment_enabled=True
            ).order_by('user__assigned_grievances__count')
            
            if category_admins.exists():
                assigned_admin = category_admins.first()
                grievance.assigned_to = assigned_admin.user
                grievance.assigned_at = timezone.now()
                grievance.status = 'acknowledged'
                grievance.save()
                
                # Create status log
                GrievanceStatusLog.objects.create(
                    grievance=grievance,
                    previous_status='submitted',
                    new_status='acknowledged',
                    changed_by=assigned_admin.user,
                    change_reason='Auto-assigned to admin',
                    automated_change=True
                )
                
                logger.info(f"Grievance {grievance.grievance_id} auto-assigned to {assigned_admin.user.username}")
        
        except Exception as e:
            logger.error(f"Error auto-assigning grievance: {str(e)}")
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add comment to grievance"""
        grievance = self.get_object()
        
        comment_data = {
            'grievance': grievance.id,
            'content': request.data.get('content'),
            'comment_type': request.data.get('comment_type', 'comment'),
            'is_internal': request.data.get('is_internal', False),
            'created_by': request.user.id
        }
        
        serializer = GrievanceCommentSerializer(data=comment_data)
        if serializer.is_valid():
            comment = serializer.save()
            
            # Send notification if not internal comment
            if not comment.is_internal:
                self.send_comment_notification(grievance, comment)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update grievance status"""
        grievance = self.get_object()
        old_status = grievance.status
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')
        
        if new_status and new_status != old_status:
            grievance.status = new_status
            grievance.save()
            
            # Create status log
            GrievanceStatusLog.objects.create(
                grievance=grievance,
                previous_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                change_reason=reason
            )
            
            # Send notification
            self.send_status_change_notification(grievance, old_status, new_status)
            
            return Response({'message': 'Status updated successfully'})
        
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve grievance"""
        grievance = self.get_object()
        resolution_summary = request.data.get('resolution_summary')
        
        if not resolution_summary:
            return Response({'error': 'Resolution summary is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        grievance.mark_resolved(resolution_summary, request.user)
        
        # Create resolution comment
        GrievanceComment.objects.create(
            grievance=grievance,
            content=resolution_summary,
            comment_type='resolution',
            created_by=request.user,
            is_visible_to_student=True
        )
        
        return Response({'message': 'Grievance resolved successfully'})
    
    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate grievance"""
        grievance = self.get_object()
        escalated_to_id = request.data.get('escalated_to')
        reason = request.data.get('reason')
        
        if not escalated_to_id or not reason:
            return Response({'error': 'Escalated to user and reason are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            escalated_to_user = User.objects.get(id=escalated_to_id)
            grievance.escalate_grievance(escalated_to_user, reason)
            
            # Send escalation notification
            self.send_escalation_notification(grievance, escalated_to_user, reason)
            
            return Response({'message': 'Grievance escalated successfully'})
        
        except User.DoesNotExist:
            return Response({'error': 'Invalid user ID'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def submit_feedback(self, request, pk=None):
        """Submit satisfaction feedback"""
        grievance = self.get_object()
        
        # Only student can submit feedback
        if grievance.student.user != request.user:
            return Response({'error': 'Only the grievance creator can submit feedback'}, status=status.HTTP_403_FORBIDDEN)
        
        rating = request.data.get('satisfaction_rating')
        feedback_text = request.data.get('feedback', '')
        
        if rating:
            grievance.satisfaction_rating = rating
            grievance.feedback = feedback_text
            grievance.feedback_submitted_at = timezone.now()
            grievance.save()
            
            return Response({'message': 'Feedback submitted successfully'})
        
        return Response({'error': 'Rating is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_grievances(self, request):
        """Get current user's grievances"""
        if hasattr(request.user, 'student_profile'):
            grievances = Grievance.objects.filter(student=request.user.student_profile)
            serializer = self.get_serializer(grievances, many=True)
            return Response(serializer.data)
        
        return Response({'error': 'Only students can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics"""
        if not request.user.is_staff:
            return Response({'error': 'Staff access required'}, status=status.HTTP_403_FORBIDDEN)
        
        queryset = self.get_queryset()
        
        stats = {
            'total_grievances': queryset.count(),
            'open_grievances': queryset.filter(status__in=['submitted', 'acknowledged', 'under_review']).count(),
            'resolved_grievances': queryset.filter(status='resolved').count(),
            'overdue_grievances': queryset.filter(is_overdue=True).count(),
            'average_resolution_time': self.calculate_average_resolution_time(queryset),
            'category_breakdown': self.get_category_breakdown(queryset),
            'priority_breakdown': self.get_priority_breakdown(queryset),
        }
        
        return Response(stats)
    
    def calculate_average_resolution_time(self, queryset):
        """Calculate average resolution time"""
        resolved_grievances = queryset.filter(resolution_date__isnull=False)
        if resolved_grievances.exists():
            total_time = sum([g.resolution_time_hours for g in resolved_grievances if g.resolution_time_hours])
            return total_time / resolved_grievances.count() if total_time else 0
        return 0
    
    def get_category_breakdown(self, queryset):
        """Get grievances by category"""
        return list(queryset.values('category__name').annotate(count=Count('id')))
    
    def get_priority_breakdown(self, queryset):
        """Get grievances by priority"""
        return list(queryset.values('priority').annotate(count=Count('id')))
    
    def send_email_notification(self, recipient_email, subject, template, context):
        """Send email notification"""
        try:
            # Create notification log
            GrievanceNotificationLog.objects.create(
                grievance=context.get('grievance'),
                notification_type=template,
                recipient_email=recipient_email,
                subject=subject,
                content=str(context)
            )
            
            # Send email using Django's send_mail
            send_mail(
                subject=subject,
                message=f"Subject: {subject}\n\nGrievance ID: {context.get('grievance').grievance_id}\nCategory: {context.get('category')}\nStudent: {context.get('student_name')}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False
            )
            
            # Update log as sent
            log = GrievanceNotificationLog.objects.filter(
                grievance=context.get('grievance'),
                recipient_email=recipient_email
            ).last()
            if log:
                log.sent_successfully = True
                log.save()
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            # Update log with error
            log = GrievanceNotificationLog.objects.filter(
                grievance=context.get('grievance'),
                recipient_email=recipient_email
            ).last()
            if log:
                log.error_message = str(e)
                log.save()
    
    def send_comment_notification(self, grievance, comment):
        """Send notification when comment is added"""
        try:
            # Notify student if comment is from staff
            if comment.created_by.is_staff and not comment.is_internal:
                self.send_email_notification(
                    recipient_email=grievance.student.user.email,
                    subject=f"Update on Grievance {grievance.grievance_id}",
                    template='grievance_comment',
                    context={'grievance': grievance, 'comment': comment}
                )
            
            # Notify assigned admin if comment is from student
            elif not comment.created_by.is_staff and grievance.assigned_to:
                self.send_email_notification(
                    recipient_email=grievance.assigned_to.email,
                    subject=f"New Response on Grievance {grievance.grievance_id}",
                    template='grievance_student_response',
                    context={'grievance': grievance, 'comment': comment}
                )
        
        except Exception as e:
            logger.error(f"Error sending comment notification: {str(e)}")
    
    def send_status_change_notification(self, grievance, old_status, new_status):
        """Send notification when status changes"""
        try:
            self.send_email_notification(
                recipient_email=grievance.student.user.email,
                subject=f"Status Update for Grievance {grievance.grievance_id}",
                template='grievance_status_change',
                context={
                    'grievance': grievance,
                    'old_status': old_status,
                    'new_status': new_status
                }
            )
        except Exception as e:
            logger.error(f"Error sending status change notification: {str(e)}")
    
    def send_escalation_notification(self, grievance, escalated_to_user, reason):
        """Send notification when grievance is escalated"""
        try:
            self.send_email_notification(
                recipient_email=escalated_to_user.email,
                subject=f"Grievance Escalated - {grievance.grievance_id}",
                template='grievance_escalation',
                context={
                    'grievance': grievance,
                    'escalated_to': escalated_to_user,
                    'reason': reason
                }
            )
        except Exception as e:
            logger.error(f"Error sending escalation notification: {str(e)}")


class GrievanceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for grievance categories"""
    
    queryset = GrievanceCategory.objects.filter(is_active=True)
    serializer_class = GrievanceCategorySerializer
    permission_classes = [IsAuthenticated]


class GrievanceCommentViewSet(viewsets.ModelViewSet):
    """ViewSet for grievance comments"""
    
    serializer_class = GrievanceCommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        grievance_id = self.request.query_params.get('grievance_id')
        if grievance_id:
            queryset = GrievanceComment.objects.filter(grievance_id=grievance_id)
            
            # Hide internal comments from students
            if not self.request.user.is_staff:
                queryset = queryset.filter(is_internal=False)
            
            return queryset
        
        return GrievanceComment.objects.none()


class GrievanceDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for grievance documents"""
    
    serializer_class = GrievanceDocumentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        grievance_id = self.request.query_params.get('grievance_id')
        if grievance_id:
            return GrievanceDocument.objects.filter(grievance_id=grievance_id)
        
        return GrievanceDocument.objects.none()


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for FAQs"""
    
    queryset = FAQ.objects.filter(is_active=True)
    serializer_class = FAQSerializer
    permission_classes = [permissions.AllowAny]  # FAQs can be public
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when FAQ is viewed"""
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def mark_helpful(self, request, pk=None):
        """Mark FAQ as helpful"""
        faq = self.get_object()
        faq.helpful_count += 1
        faq.save(update_fields=['helpful_count'])
        return Response({'message': 'Thank you for your feedback'})
    
    @action(detail=True, methods=['post'])
    def mark_not_helpful(self, request, pk=None):
        """Mark FAQ as not helpful"""
        faq = self.get_object()
        faq.not_helpful_count += 1
        faq.save(update_fields=['not_helpful_count'])
        return Response({'message': 'Thank you for your feedback'})
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search FAQs"""
        query = request.query_params.get('q', '')
        category_id = request.query_params.get('category')
        
        queryset = self.get_queryset()
        
        if query:
            queryset = queryset.filter(
                Q(question__icontains=query) | 
                Q(answer__icontains=query) |
                Q(tags__icontains=query)
            )
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class GrievanceTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for grievance response templates"""
    
    queryset = GrievanceTemplate.objects.filter(is_active=True)
    serializer_class = GrievanceTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only staff can access templates
        if self.request.user.is_staff:
            return self.queryset
        return GrievanceTemplate.objects.none()
    
    @action(detail=True, methods=['post'])
    def use_template(self, request, pk=None):
        """Increment usage count when template is used"""
        template = self.get_object()
        template.usage_count += 1
        template.save(update_fields=['usage_count'])
        return Response({'message': 'Template usage recorded'})


# Legacy API endpoints for backward compatibility
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_list(request):
    """List grievances"""
    return Response({'message': 'Use /api/grievances/ instead'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_grievance(request):
    """Create new grievance"""
    return Response({'message': 'Use POST /api/grievances/ instead'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_detail(request, grievance_id):
    """Get grievance details"""
    return Response({'message': f'Use /api/grievances/{grievance_id}/ instead'}, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def grievance_comments(request, grievance_id):
    """Get or add grievance comments"""
    return Response({'message': f'Use /api/grievance-comments/?grievance_id={grievance_id} instead'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_categories(request):
    """List grievance categories"""
    return Response({'message': 'Use /api/grievance-categories/ instead'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def faqs(request):
    """List FAQs"""
    return Response({'message': 'Use /api/faqs/ instead'}, status=status.HTTP_200_OK)
