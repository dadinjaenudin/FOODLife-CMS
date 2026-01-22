from django.urls import path
from .views import auth_views

app_name = 'auth'

urlpatterns = [
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
]
