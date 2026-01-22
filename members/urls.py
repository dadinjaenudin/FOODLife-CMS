from django.urls import path
from members.views import member_views

app_name = 'member'

urlpatterns = [
    path('', member_views.member_list, name='list'),
    path('create/', member_views.member_create, name='create'),
    path('<uuid:pk>/edit/', member_views.member_update, name='edit'),
    path('<uuid:pk>/delete/', member_views.member_delete, name='delete'),
]
