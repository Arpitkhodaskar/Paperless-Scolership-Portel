from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

app_name = 'students'

urlpatterns = [
    # Authentication endpoints
    path('register/', api_views.student_registration, name='student_registration'),
    path('login/', api_views.student_login, name='student_login'),
    
    # Profile management
    path('profile/', api_views.get_student_profile, name='get_student_profile'),
    path('profile/update/', api_views.update_student_profile, name='update_student_profile'),
    path('dashboard/', api_views.dashboard_summary, name='dashboard_summary'),
    
    # Document management
    path('documents/', api_views.student_documents, name='student_documents'),
    path('documents/<int:document_id>/', api_views.document_detail, name='document_detail'),
    
    # Scholarship applications
    path('applications/', api_views.scholarship_applications, name='scholarship_applications'),
    path('applications/<str:application_id>/', api_views.application_detail, name='application_detail'),
    path('applications/<str:application_id>/submit/', api_views.submit_application, name='submit_application'),
    path('applications/<str:application_id>/status/', api_views.application_status_tracking, name='application_status_tracking'),
]
