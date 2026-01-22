"""
Company URL Configuration
"""

from django.urls import path
from core.views import company_views

app_name = 'company'

urlpatterns = [
    path('', company_views.company_list, name='list'),
    path('create/', company_views.company_create, name='create'),
    path('<uuid:pk>/edit/', company_views.company_update, name='edit'),
    path('<uuid:pk>/delete/', company_views.company_delete, name='delete'),
]
