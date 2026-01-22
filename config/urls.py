"""
URL configuration for F&B POS HO System
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    
    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API Endpoints - HO → Edge (Master Data Pull)
    path('api/v1/core/', include('core.api.urls')),
    path('api/v1/products/', include('products.api.urls')),
    path('api/v1/members/', include('members.api.urls')),
    path('api/v1/promotions/', include('promotions.api.urls')),
    path('api/v1/inventory/', include('inventory.api.urls')),
    
    # API Endpoints - Edge → HO (Transaction Push)
    path('api/v1/transactions/', include('transactions.api.urls')),
    
    # API Endpoints - Analytics & Reporting
    path('api/v1/analytics/', include('analytics.urls')),
]
