from django.urls import path
from promotions.views import promotion_views

app_name = 'promotion'

urlpatterns = [
    path('', promotion_views.promotion_list, name='list'),
    path('create/', promotion_views.promotion_create, name='create'),
    path('<uuid:pk>/edit/', promotion_views.promotion_update, name='edit'),
    path('<uuid:pk>/delete/', promotion_views.promotion_delete, name='delete'),
]
