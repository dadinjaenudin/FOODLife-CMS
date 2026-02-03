"""
URL configuration for F&B POS HO System
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
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
    
    # Global Filters
    path('global/', include('core.urls_global')),
    
    # Dashboard
    path('dashboard/', include('dashboard.urls')),
    
    # Company Management
    path('company/', include('core.urls_company')),
    
    # Brand Management
    path('brand/', include('core.urls_brand')),
    
    # Store Management
    path('store/', include('core.urls_store')),
    
    # User Management
    path('users/', include('core.urls_user')),
    
    # Product Management
    path('products/', include('products.urls_product')),
    path('products/categories/', include('products.urls_category')),
    path('products/modifiers/', include('products.urls_modifier')),
    path('products/tableareas/', include('products.urls_tablearea')),
    path('products/kitchenstations/', include('products.urls_kitchenstation')),
    
    # Members & Promotions
    path('members/', include('members.urls')),
    path('promotions/', include('promotions.urls')),
    
    # Sync API for Edge Server (versioned)
    path('api/v1/sync/', include(('sync_api.sync_urls', 'sync_api'), namespace='sync_api_v1')),
    
    # Settings
    path('settings/', include('settings.urls')),
    
    # Inventory Management
    path('inventory/items/', include('inventory.urls_inventoryitem')),
    path('inventory/recipes/', include('inventory.urls_recipe')),
    path('inventory/movements/', include('inventory.urls_stockmovement')),
    
    # POS & Queue Display
    path('pos/', include('transactions.urls')),
    
    # Reports & Analytics
    path('reports/', include('analytics.urls')),
    
    # JWT Authentication
    # Versioned endpoints (v1)
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair_v1'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh_v1'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
        
    # API Endpoints - Master Data (Products, Categories, Tables)
    path('api/v1/products/', include('products.api.urls')),
    
    # API Endpoints - Edge → HO (Transaction Push)
    path('api/v1/transactions/', include('transactions.api.urls')),
    
    # API Endpoints - Analytics & Reporting
    path('api/v1/analytics/', include('analytics.api_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
