"""
Kitchen Station URLs
"""
from django.urls import path
from products.views import kitchenstation_views

app_name = 'kitchenstation'

urlpatterns = [
    path('', kitchenstation_views.kitchenstation_list, name='list'),
    path('create/', kitchenstation_views.kitchenstation_create, name='create'),
    path('<uuid:pk>/edit/', kitchenstation_views.kitchenstation_update, name='edit'),
    path('<uuid:pk>/delete/', kitchenstation_views.kitchenstation_delete, name='delete'),
]
