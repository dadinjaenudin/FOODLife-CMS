"""
Settings URLs
"""
from django.urls import path
from . import views
from . import import_log_views

app_name = 'settings'

urlpatterns = [
    # MinIO Configuration
    path('minio-config/', views.minio_config_view, name='minio_config'),
    path('minio-config/save/', views.save_minio_config, name='save_minio_config'),
    path('minio-config/test/', views.test_minio_connection, name='test_minio_connection'),
    path('minio-config/set-public/', views.set_bucket_public, name='set_bucket_public'),
    path('minio-auto-login/', views.minio_auto_login, name='minio_auto_login'),
    
    # Bulk Import (Original Template)
    path('bulk-import/', views.bulk_import_view, name='bulk_import'),
    path('download-template/', views.download_template, name='download_template'),
    path('upload-excel/', views.upload_excel, name='upload_excel'),
    
    # Bulk Import Products (Custom Format)
    path('bulk-import-products/', views.bulk_import_products_view, name='bulk_import_products'),
    path('bulk-import-two-sheet/', views.bulk_import_two_sheet_view, name='bulk_import_two_sheet'),
    path('download-products-template/', views.download_products_template, name='download_products_template'),
    path('download-two-sheet-template/', views.download_two_sheet_template, name='download_two_sheet_template'),
    path('upload-products-excel/', views.upload_products_excel, name='upload_products_excel'),
    path('upload-two-sheet-excel/', views.upload_two_sheet_excel, name='upload_two_sheet_excel'),
    
    # Bulk Delete Products
    path('bulk-delete-products/', views.bulk_delete_products_view, name='bulk_delete_products'),
    path('bulk-delete-products-action/', views.bulk_delete_products_action, name='bulk_delete_products_action'),
    
    # Import Logs
    path('import-logs/', import_log_views.import_log_view, name='import_logs'),
    path('api/import-logs/', import_log_views.get_import_logs, name='api_import_logs'),
]
