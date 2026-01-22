"""
URL configuration for F&B POS HO System
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Root redirect to dashboard
    path('', lambda request: redirect('dashboard:index')),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # Authentication
    path('auth/', include('core.urls_auth')),
    
    # Dashboard
    path('dashboard/', include('dashboard.urls')),
    
    # Company Management
    path('company/', include('core.urls_company')),
    
    # Brand Management
    path('brand/', include('core.urls_brand')),
    
    # Store Management
    path('store/', include('core.urls_store')),
    
    # Product Management
    path('products/', include('products.urls_product')),
    path('products/categories/', include('products.urls_category')),
    path('products/modifiers/', include('products.urls_modifier')),
    path('products/tableareas/', include('products.urls_tablearea')),
    path('products/kitchenstations/', include('products.urls_kitchenstation')),
    
    # Members & Promotions
    path('members/', include('members.urls')),
    path('promotions/', include('promotions.urls')),
    
    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
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
