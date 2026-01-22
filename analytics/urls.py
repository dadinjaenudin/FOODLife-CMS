"""
Analytics URLs - Reporting & Analytics Endpoints
"""
from django.urls import path
from . import views

urlpatterns = [
    # Sales Reports
    path('daily-sales/', views.daily_sales_report, name='daily-sales'),
    path('product-sales/', views.product_sales_report, name='product-sales'),
    
    # Promotion Reports
    path('promotion-performance/', views.promotion_performance_report, name='promotion-performance'),
    
    # Member Reports
    path('member-analytics/', views.member_analytics_report, name='member-analytics'),
    
    # Inventory & COGS
    path('inventory-cogs/', views.inventory_cogs_report, name='inventory-cogs'),
    
    # Operational Reports
    path('cashier-performance/', views.cashier_performance_report, name='cashier-performance'),
    path('payment-methods/', views.payment_method_report, name='payment-methods'),
]
