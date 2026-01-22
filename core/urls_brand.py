"""
Brand URL Configuration
"""

from django.urls import path
from core.views import brand_views

app_name = 'brand'

urlpatterns = [
    path('', brand_views.brand_list, name='list'),
    path('create/', brand_views.brand_create, name='create'),
    path('<uuid:pk>/edit/', brand_views.brand_update, name='edit'),
    path('<uuid:pk>/delete/', brand_views.brand_delete, name='delete'),
]
