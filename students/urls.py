from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'students', views.StudentViewSet, basename='student')
router.register(r'documents', views.StudentDocumentViewSet, basename='student-document')
router.register(r'applications', views.ScholarshipApplicationViewSet, basename='scholarship-application')
router.register(r'academic-records', views.AcademicRecordViewSet, basename='academic-record')

urlpatterns = [
    # Include ViewSet URLs
    path('api/', include(router.urls)),
    
    # Legacy endpoints (can be removed once frontend is updated)
    # These are kept for backward compatibility
    # path('profile/', views.get_student_profile, name='student_profile'),
    # path('profile/update/', views.update_student_profile, name='update_student_profile'),
    # path('documents/', views.student_documents, name='student_documents'),
    # path('academic-records/', views.academic_records, name='academic_records'),
    # path('scholarship-applications/', views.scholarship_applications, name='scholarship_applications'),
    # path('scholarship-applications/<str:application_id>/', views.scholarship_application_detail, name='scholarship_application_detail'),
    # path('scholarship-applications/<str:application_id>/submit/', views.submit_scholarship_application, name='submit_scholarship_application'),
]
