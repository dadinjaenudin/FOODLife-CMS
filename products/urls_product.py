"""
Product URLs
"""
from django.urls import path
from products.views import product_views

app_name = 'product'

urlpatterns = [
    path('', product_views.product_list, name='list'),
    path('create/', product_views.product_create, name='create'),
    path('<uuid:pk>/edit/', product_views.product_update, name='edit'),
    path('<uuid:pk>/delete/', product_views.product_delete, name='delete'),
    path('<uuid:pk>/modifier-assign/', product_views.product_modifier_assign, name='modifier-assign'),
    path('photo/<uuid:pk>/delete/', product_views.product_photo_delete, name='photo-delete'),
]
