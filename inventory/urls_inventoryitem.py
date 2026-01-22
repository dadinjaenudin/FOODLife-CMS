from django.urls import path
from inventory.views import inventoryitem_views

app_name = 'inventoryitem'

urlpatterns = [
    path('', inventoryitem_views.inventoryitem_list, name='list'),
    path('create/', inventoryitem_views.inventoryitem_create, name='create'),
    path('<uuid:pk>/edit/', inventoryitem_views.inventoryitem_update, name='edit'),
    path('<uuid:pk>/delete/', inventoryitem_views.inventoryitem_delete, name='delete'),
]
