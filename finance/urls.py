from django.urls import path
from . import views

urlpatterns = [
    path('schemes/', views.scholarship_schemes, name='scholarship_schemes'),
    path('disbursements/', views.disbursements, name='disbursements'),
    path('budgets/', views.budgets, name='budgets'),
    path('transactions/', views.transactions, name='transactions'),
    path('reports/', views.financial_reports, name='financial_reports'),
]
