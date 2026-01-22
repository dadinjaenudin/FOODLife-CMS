"""
Analytics URLs - Reporting & Analytics Endpoints
"""
from django.urls import path
from . import api_views, report_views

app_name = 'analytics'

urlpatterns = [
    # UI Reports (HTML)
    path('sales-report/', report_views.sales_report_dashboard, name='sales-report'),
    path('product-performance/', report_views.product_performance_report, name='product-performance'),
    path('hourly-sales/', report_views.hourly_sales_report, name='hourly-sales'),
    
    # API Endpoints (JSON)
    path('api/daily-sales/', api_views.daily_sales_report, name='api-daily-sales'),
    path('api/product-sales/', api_views.product_sales_report, name='api-product-sales'),
    path('api/promotion-performance/', api_views.promotion_performance_report, name='api-promotion-performance'),
    path('api/member-analytics/', api_views.member_analytics_report, name='api-member-analytics'),
    path('api/inventory-cogs/', api_views.inventory_cogs_report, name='api-inventory-cogs'),
    path('api/cashier-performance/', api_views.cashier_performance_report, name='api-cashier-performance'),
    path('api/payment-methods/', api_views.payment_method_report, name='api-payment-methods'),
]
