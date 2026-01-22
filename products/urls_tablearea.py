"""
Table Area URLs
"""
from django.urls import path
from products.views import tablearea_views

app_name = 'tablearea'

urlpatterns = [
    path('', tablearea_views.tablearea_list, name='list'),
    path('create/', tablearea_views.tablearea_create, name='create'),
    path('<uuid:pk>/edit/', tablearea_views.tablearea_update, name='edit'),
    path('<uuid:pk>/delete/', tablearea_views.tablearea_delete, name='delete'),
]
