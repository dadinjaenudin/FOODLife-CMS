"""
Sync API URL Configuration
URLs for Edge Server synchronization
"""

from django.urls import path
from sync_api import sync_views

app_name = 'sync_api'

urlpatterns = [
    # Sync endpoints
    path('promotions/', sync_views.sync_promotions, name='promotions'),
    path('categories/', sync_views.sync_categories, name='categories'),
    path('products/', sync_views.sync_products, name='products'),
    path('modifiers/', sync_views.sync_modifiers, name='modifiers'),
    path('modifier-options/', sync_views.sync_modifier_options, name='modifier_options'),
    path('product-modifiers/', sync_views.sync_product_modifiers, name='product_modifiers'),
    path('tables/', sync_views.sync_tables, name='tables'),  # Combined: areas + tables
    path('table-areas/', sync_views.sync_table_areas, name='table_areas'),  # Areas only
    path('table-groups/', sync_views.sync_table_groups, name='table_groups'),  # Table groups
    path('version/', sync_views.sync_version, name='version'),
    
    # Upload endpoints
    path('usage/', sync_views.upload_usage, name='upload_usage'),
    
    # Master Data endpoints
    path('companies/', sync_views.sync_companies, name='companies'),
    path('brands/', sync_views.sync_brands, name='brands'),
    path('stores/', sync_views.sync_stores, name='stores'),
    path('store-brands/', sync_views.sync_store_brands, name='store_brands'),
    
    # Product Photo Sync endpoint
    path('product-photos/', sync_views.sync_product_photos, name='product_photos'),
]
