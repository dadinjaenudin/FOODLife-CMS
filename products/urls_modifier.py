"""
Modifier URLs
"""
from django.urls import path
from products.views import modifier_views

app_name = 'modifier'

urlpatterns = [
    path('', modifier_views.modifier_list, name='list'),
    path('create/', modifier_views.modifier_create, name='create'),
    path('<uuid:pk>/edit/', modifier_views.modifier_update, name='edit'),
    path('<uuid:pk>/delete/', modifier_views.modifier_delete, name='delete'),
]
