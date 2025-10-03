from django.urls import path
from . import views

urlpatterns = [
    path('', views.grievance_list, name='grievance_list'),
    path('create/', views.create_grievance, name='create_grievance'),
    path('<str:grievance_id>/', views.grievance_detail, name='grievance_detail'),
    path('<str:grievance_id>/comments/', views.grievance_comments, name='grievance_comments'),
    path('categories/', views.grievance_categories, name='grievance_categories'),
    path('faqs/', views.faqs, name='faqs'),
]
