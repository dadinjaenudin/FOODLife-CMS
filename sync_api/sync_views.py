"""
Sync API Views for Edge Server
Provides REST API endpoints for Edge Server to download promotion data
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from datetime import datetime
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from promotions.models import Promotion
from promotions.models_settings import PromotionSyncSettings
from promotions.services.compiler import PromotionCompiler
from core.models import Store, Company, Brand
from products.models import Category, Product
from datetime import timedelta
import logging

logger = logging.getLogger('promotions.sync_api')


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter promotions'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter promotions'
                },
                'brand_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Brand UUID to filter promotions (optional)'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Promotions',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        ),
        OpenApiExample(
            'Sync Promotions with Brand',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here',
                'brand_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_promotions(request):
    """
    Get promotions for Edge Server
    
    POST /api/v1/sync/promotions/
    Body: {
        "company_id": "uuid",
        "store_id": "uuid",
        "brand_id": "uuid"  // Optional
        "updated_since": "2026-01-29T00:00:00Z"  // Optional
    }
    
    Returns:
        - promotions: List of compiled promotion JSON
        - deleted_ids: List of deleted promotion IDs
        - sync_timestamp: Current server timestamp
        - total: Total number of promotions
    """
    try:
        # Get parameters from POST request body
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        brand_id = request.data.get('brand_id')  # Optional
        updated_since = request.data.get('updated_since')
        
        # Validate required parameters
        if not company_id:
            return Response({
                'error': 'company_id is required in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id)
            # Get brand_id from store if not provided
            if not brand_id:
                brand_id = store.brand_id
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get sync settings for company
        try:
            company = Company.objects.get(id=company_id)
            sync_settings = PromotionSyncSettings.get_for_company(company)
        except Company.DoesNotExist:
            return Response({
                'error': 'Company not found',
                'code': 'COMPANY_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Build query based on sync strategy
        now = timezone.now()
        
        if sync_settings.sync_strategy == 'current_only':
            # Only promotions valid today
            query = Q(
                company_id=company_id,
                start_date__lte=now.date(),
                end_date__gte=now.date()
            )
        elif sync_settings.sync_strategy == 'include_future':
            # Promotions valid from past_days ago to future_days ahead
            query = Q(
                company_id=company_id,
                start_date__lte=now.date() + timedelta(days=sync_settings.future_days),
                end_date__gte=now.date() - timedelta(days=sync_settings.past_days)
            )
        else:  # 'all_active'
            # All active promotions regardless of dates
            query = Q(company_id=company_id)
        
        # Apply active filter based on settings
        if not sync_settings.include_inactive:
            query &= Q(is_active=True)
        
        # Filter by brand (REQUIRED)
        query &= Q(brand_id=brand_id)
        
        # Filter by store (if provided)
        if store:
            query &= (Q(all_stores=True) | Q(stores=store))
        
        # Incremental sync
        if updated_since:
            try:
                updated_since_dt = datetime.fromisoformat(updated_since.replace('Z', '+00:00'))
                query &= Q(updated_at__gte=updated_since_dt)
            except (ValueError, AttributeError):
                return Response({
                    'error': 'Invalid updated_since format. Use ISO 8601 format.',
                    'code': 'INVALID_DATE_FORMAT'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get promotions with limit from settings
        promotions = Promotion.objects.filter(query).distinct().order_by('-execution_priority', 'name')
        
        # Apply max promotions limit
        total_available = promotions.count()
        promotions = promotions[:sync_settings.max_promotions_per_sync]
        
        # Compile promotions
        compiler = PromotionCompiler()
        compiled_promotions = compiler.compile_multiple(promotions)
        
        # Get deleted IDs (if incremental sync)
        deleted_ids = []
        if updated_since:
            # TODO: Track deleted promotions in a separate table
            # For now, return empty list
            pass
        
        sync_timestamp = now.isoformat()
        
        logger.info(
            f"Sync request: company={company_id}, brand={brand_id}, store={store.store_code if store else 'ALL'}, "
            f"strategy={sync_settings.sync_strategy}, promotions={len(compiled_promotions)}/{total_available}"
        )
        
        response_data = {
            'promotions': compiled_promotions,
            'deleted_ids': deleted_ids,
            'sync_timestamp': sync_timestamp,
            'total': len(compiled_promotions),
            'total_available': total_available,
            'settings': {
                'strategy': sync_settings.sync_strategy,
                'future_days': sync_settings.future_days,
                'past_days': sync_settings.past_days,
                'max_promotions': sync_settings.max_promotions_per_sync
            },
            'filter': {
                'company_id': str(company_id),
                'brand_id': str(brand_id),
                'store_id': str(store_id) if store_id else None
            }
        }
        
        # Add store info if provided
        if store:
            response_data['store'] = {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name
            }
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"Error in sync_promotions: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter categories'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter categories'
                },
                'brand_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Brand UUID to filter categories (optional)'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Categories',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        ),
        OpenApiExample(
            'Sync Categories with Brand',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here',
                'brand_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_categories(request):
    """
    Get categories for Edge Server (for food court concept)
    
    POST /api/v1/sync/categories/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid",
        "brand_id": "uuid",  // optional
        "updated_since": "2026-01-29T00:00:00Z"  // optional
    }
    """
    try:
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        
        if not company_id:
            return Response({
                'error': 'company_id is required in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        brand_id = request.data.get('brand_id')
        updated_since = request.data.get('updated_since')
        
        # Get all brands operating in this store for food court concept
        store_brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).values_list('id', flat=True)
        
        # Build query - filter by brands in this store
        query = Q(brand_id__in=store_brands, is_active=True)
        
        # If specific brand_id provided, filter further
        if brand_id:
            query &= Q(brand_id=brand_id)
        
        if updated_since:
            try:
                updated_since_dt = datetime.fromisoformat(updated_since.replace('Z', '+00:00'))
                query &= Q(updated_at__gte=updated_since_dt)
            except (ValueError, AttributeError):
                return Response({
                    'error': 'Invalid updated_since format',
                    'code': 'INVALID_DATE_FORMAT'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        categories = Category.objects.filter(query).select_related('brand').values(
            'id', 'brand_id', 'brand__company_id', 'name', 
            'parent_id', 'is_active', 'sort_order',
            'created_at', 'updated_at'
        )
        
        # Convert to list and rename brand__company_id to company_id
        category_list = []
        for cat in categories:
            category_list.append({
                'id': str(cat['id']),
                'company_id': str(cat['brand__company_id']),
                'brand_id': str(cat['brand_id']),
                'name': cat['name'],
                'parent_id': str(cat['parent_id']) if cat['parent_id'] else None,
                'is_active': cat['is_active'],
                'sort_order': cat['sort_order'],
                'created_at': cat['created_at'].isoformat(),
                'updated_at': cat['updated_at'].isoformat(),
            })
        
        return Response({
            'categories': category_list,
            'deleted_ids': [],
            'sync_timestamp': timezone.now().isoformat(),
            'total': len(category_list),
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id),
                'brand_id': str(brand_id) if brand_id else None,
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Error in sync_categories: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter products'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter products'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Products',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_products(request):
    """
    Get products for Edge Server (for food court concept)
    
    POST /api/v1/sync/products/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid",
        "updated_since": "2026-01-29T00:00:00Z"  // optional
    }
    """
    try:
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        
        if not company_id:
            return Response({
                'error': 'company_id is required in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        updated_since = request.data.get('updated_since')
        
        # Get all brands operating in this store for food court concept
        store_brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).values_list('id', flat=True)
        
        # Build query - filter by company and brands operating in this store
        # Note: Product does NOT have store_id field, only brand_id
        query = Q(company_id=company_id, brand_id__in=store_brands, is_active=True)
        
        if updated_since:
            try:
                updated_since_dt = datetime.fromisoformat(updated_since.replace('Z', '+00:00'))
                query &= Q(updated_at__gte=updated_since_dt)
            except (ValueError, AttributeError):
                return Response({
                    'error': 'Invalid updated_since format',
                    'code': 'INVALID_DATE_FORMAT'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        products = Product.objects.filter(query).values(
            'id', 'company_id', 'brand_id', 'category_id',
            'name', 'sku', 'price', 'cost', 'is_active', 
            'description', 'created_at', 'updated_at'
        )
        
        # Convert to list and add store_id from context
        product_list = []
        for prod in products:
            product_list.append({
                'id': str(prod['id']),
                'company_id': str(prod['company_id']),
                'brand_id': str(prod['brand_id']),
                'category_id': str(prod['category_id']),
                'store_id': str(store_id),  # Add store_id from request context
                'name': prod['name'],
                'sku': prod['sku'],
                'price': str(prod['price']),
                'cost': str(prod['cost']),
                'is_active': prod['is_active'],
                'description': prod['description'] or '',
                'created_at': prod['created_at'].isoformat(),
                'updated_at': prod['updated_at'].isoformat(),
            })
        
        return Response({
            'products': product_list,
            'deleted_ids': [],
            'sync_timestamp': timezone.now().isoformat(),
            'total': len(product_list),
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id),
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Error in sync_products: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to get version info'
                }
            },
            'required': ['company_id']
        }
    },
    examples=[
        OpenApiExample(
            'Get Version Info',
            value={'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97'}
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_version(request):
    """
    Get sync version info
    
    POST /api/v1/sync/version/
    
    Request Body:
    {
        "company_id": "uuid"
    }
    
    Returns current data version to help Edge Server decide if sync is needed
    """
    try:
        company_id = request.data.get('company_id')
        
        if not company_id:
            return Response({
                'error': 'company_id is required in request body'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get latest promotion update
        latest_promotion = Promotion.objects.filter(
            company_id=company_id
        ).order_by('-updated_at').first()
        
        if latest_promotion:
            last_updated = latest_promotion.updated_at
            version = int(last_updated.timestamp())
        else:
            last_updated = timezone.now()
            version = 0
        
        return Response({
            'version': version,
            'last_updated': last_updated.isoformat(),
            'force_update': False
        })
        
    except Exception as e:
        logger.error(f"Error in sync_version: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'usages': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'promotion_id': {
                                'type': 'string',
                                'format': 'uuid',
                                'description': 'Promotion UUID'
                            },
                            'bill_id': {
                                'type': 'string',
                                'description': 'Bill transaction ID'
                            },
                            'discount_amount': {
                                'type': 'number',
                                'format': 'float',
                                'description': 'Discount amount applied'
                            },
                            'used_at': {
                                'type': 'string',
                                'format': 'date-time',
                                'description': 'Usage timestamp'
                            },
                            'store_id': {
                                'type': 'string',
                                'format': 'uuid',
                                'description': 'Store UUID where used'
                            },
                            'customer_id': {
                                'type': 'string',
                                'format': 'uuid',
                                'description': 'Customer UUID (optional)'
                            }
                        },
                        'required': ['promotion_id', 'bill_id', 'discount_amount', 'used_at', 'store_id']
                    },
                    'description': 'Array of promotion usage records'
                }
            },
            'required': ['usages']
        }
    },
    examples=[
        OpenApiExample(
            'Upload Usage Records',
            value={
                'usages': [
                    {
                        'promotion_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                        'bill_id': 'B001',
                        'discount_amount': 15000.0,
                        'used_at': '2026-01-27T10:00:00Z',
                        'store_id': 'uuid-here'
                    }
                ]
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_usage(request):
    """
    Upload promotion usage logs from Edge Server
    
    POST /api/v1/sync/usage/
    
    Body: {
        "usages": [
            {
                "promotion_id": "uuid",
                "bill_id": "B001",
                "discount_amount": 15000.0,
                "used_at": "2026-01-27T10:00:00Z",
                "store_id": "uuid",
                "customer_id": "uuid"
            }
        ]
    }
    """
    try:
        usages = request.data.get('usages', [])
        
        if not usages:
            return Response({
                'error': 'usages array is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        created = 0
        errors = []
        
        for usage_data in usages:
            try:
                # TODO: Create PromotionUsage model and save
                # For now, just log
                logger.info(f"Usage logged: promotion={usage_data.get('promotion_id')}, amount={usage_data.get('discount_amount')}")
                created += 1
            except Exception as e:
                errors.append({
                    'data': usage_data,
                    'error': str(e)
                })
        
        return Response({
            'created': created,
            'errors': errors,
            'total': len(usages)
        })
        
    except Exception as e:
        logger.error(f"Error in upload_usage: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# MASTER DATA APIs for Edge Server
# ============================================================================

@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {},
            'required': []
        }
    },
    examples=[
        OpenApiExample(
            'Sync All Companies',
            value={}
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_companies(request):
    """
    Get all active companies
    
    POST /api/v1/sync/companies/
    
    Request Body: {}  // empty body
    
    Returns:
        - companies: List of company objects
        - total: Total number of companies
        - sync_timestamp: Current server timestamp
    
    Response Format:
    {
        "companies": [
            {
                "id": "uuid",
                "code": "YGY",
                "name": "Yogya Group",
                "timezone": "Asia/Jakarta",
                "is_active": true,
                "point_expiry_months": 12,
                "points_per_currency": "1.00",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ],
        "total": 1,
        "sync_timestamp": "2024-01-15T10:30:00Z"
    }
    """
    try:
        # Get all active companies
        companies = Company.objects.filter(is_active=True).order_by('name')
        
        company_list = []
        for company in companies:
            company_list.append({
                'id': str(company.id),
                'code': company.code,
                'name': company.name,
                'timezone': company.timezone,
                'is_active': company.is_active,
                'point_expiry_months': company.point_expiry_months,
                'points_per_currency': str(company.points_per_currency),
                'created_at': company.created_at.isoformat(),
                'updated_at': company.updated_at.isoformat(),
            })
        
        return Response({
            'companies': company_list,
            'total': len(company_list),
            'sync_timestamp': timezone.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error in sync_companies: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter brands'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter brands'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Brands',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_brands(request):
    """
    Get brands filtered by company and store (for food court concept)
    
    POST /api/v1/sync/brands/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid"
    }
    
    Returns:
        - brands: List of brand objects
        - total: Total number of brands
        - sync_timestamp: Current server timestamp
    
    Response Format:
    {
        "brands": [
            {
                "id": "uuid",
                "company_id": "uuid",
                "company_code": "YGY",
                "company_name": "Yogya Group",
                "code": "YGY-001",
                "name": "Ayam Geprek Express",
                "address": "Jl. Contoh No. 123",
                "phone": "021-1234567",
                "tax_id": "01.234.567.8-901.000",
                "tax_rate": "11.00",
                "service_charge": "5.00",
                "point_expiry_months_override": null,
                "is_active": true,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ],
        "total": 1,
        "sync_timestamp": "2024-01-15T10:30:00Z"
    }
    """
    try:
        # Validate required parameters
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        
        if not company_id:
            return Response({
                'error': 'Missing required parameter: company_id in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'Missing required parameter: store_id in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate company exists
        try:
            company = Company.objects.get(id=company_id, is_active=True)
        except Company.DoesNotExist:
            return Response({
                'error': f'Company not found: {company_id}',
                'code': 'COMPANY_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get all active brands for this company that have stores in this location
        # For food court concept: get all brands that operate in this store
        brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).select_related('company').distinct().order_by('name')
        
        brand_list = []
        for brand in brands:
            brand_list.append({
                'id': str(brand.id),
                'company_id': str(brand.company.id),
                'company_code': brand.company.code,
                'company_name': brand.company.name,
                'code': brand.code,
                'name': brand.name,
                'address': brand.address,
                'phone': brand.phone,
                'tax_id': brand.tax_id,
                'tax_rate': str(brand.tax_rate),
                'service_charge': str(brand.service_charge),
                'point_expiry_months_override': brand.point_expiry_months_override,
                'point_expiry_months': brand.get_point_expiry_months(),
                'is_active': brand.is_active,
                'created_at': brand.created_at.isoformat(),
                'updated_at': brand.updated_at.isoformat(),
            })
        
        return Response({
            'brands': brand_list,
            'total': len(brand_list),
            'company': {
                'id': str(company.id),
                'code': company.code,
                'name': company.name,
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            },
            'sync_timestamp': timezone.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error in sync_brands: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter stores'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter stores'
                }
            },
            'required': ['company_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Stores',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_stores(request):
    """
    Get stores filtered by company (optionally by store for food court concept)
    
    POST /api/v1/sync/stores/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid"  # optional
    }
    
    Returns:
        - stores: List of store objects
        - total: Total number of stores
        - sync_timestamp: Current server timestamp
    
    Response Format:
    {
        "stores": [
            {
                "id": "uuid",
                "brand_id": "uuid",
                "brand_code": "YGY-001",
                "brand_name": "Ayam Geprek Express",
                "company_id": "uuid",
                "company_code": "YGY",
                "company_name": "Yogya Group",
                "store_code": "YGY-001-BSD",
                "store_name": "Cabang BSD",
                "address": "Jl. BSD Raya No. 123",
                "phone": "021-7654321",
                "timezone": "Asia/Jakarta",
                "latitude": "-6.302100",
                "longitude": "106.652900",
                "is_active": true,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ],
        "total": 1,
        "sync_timestamp": "2024-01-15T10:30:00Z"
    }
    """
    try:
        # Validate required parameters
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        
        if not company_id:
            return Response({
                'error': 'Missing required parameter: company_id in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate company exists
        try:
            company = Company.objects.get(id=company_id, is_active=True)
        except Company.DoesNotExist:
            return Response({
                'error': f'Company not found: {company_id}',
                'code': 'COMPANY_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        store = None
        query = Q(brand__company_id=company_id, is_active=True)
        
        if store_id:
            # Verify store exists and belongs to company
            try:
                store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
            except Store.DoesNotExist:
                return Response({
                    'error': 'Store not found or does not belong to the specified company',
                    'code': 'STORE_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Build query for stores - filter by specific store
            query &= Q(id=store_id)
        
        # Get stores
        stores = Store.objects.filter(query).select_related('brand__company').order_by('store_name')
        
        store_list = []
        for store in stores:
            store_list.append({
                'id': str(store.id),
                'brand_id': str(store.brand.id),
                'brand_code': store.brand.code,
                'brand_name': store.brand.name,
                'company_id': str(store.brand.company.id),
                'company_code': store.brand.company.code,
                'company_name': store.brand.company.name,
                'store_code': store.store_code,
                'store_name': store.store_name,
                'address': store.address,
                'phone': store.phone,
                'timezone': store.timezone,
                'latitude': str(store.latitude) if store.latitude else None,
                'longitude': str(store.longitude) if store.longitude else None,
                'is_active': store.is_active,
                'created_at': store.created_at.isoformat(),
                'updated_at': store.updated_at.isoformat(),
            })
        
        return Response({
            'stores': store_list,
            'total': len(store_list),
            'company': {
                'id': str(company.id),
                'code': company.code,
                'name': company.name,
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            } if store else None,
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id) if store_id else None,
            },
            'sync_timestamp': timezone.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error in sync_stores: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter tables'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter tables'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Tables',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_tables(request):
    """
    Get tables and table areas for Edge Server (for food court concept)
    
    POST /api/v1/sync/tables/
    Body: {
        "company_id": "uuid",
        "store_id": "uuid",
        "updated_since": "2026-01-29T00:00:00Z"  // Optional
    }
    
    Returns:
        - table_areas: List of dining areas with floor plans
        - tables: List of tables with positions and QR codes
        - total_areas: Count of table areas
        - total_tables: Count of tables
        - sync_timestamp: Current server timestamp
    """
    try:
        # Get parameters from POST request body
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        updated_since = request.data.get('updated_since')
        
        # Validate required parameters
        if not company_id:
            return Response({
                'error': 'company_id is required',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Import models
        from products.models import TableArea, Tables
        
        # Get all brands operating in this store for food court concept
        store_brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).values_list('id', flat=True)
        
        # Build query for table areas - get tables from all brands in this store
        areas_query = Q(
            company_id=company_id,
            brand_id__in=store_brands,
            store_id=store_id,
            is_active=True
        )
        
        # Incremental sync for areas
        if updated_since:
            try:
                updated_since_dt = datetime.fromisoformat(updated_since.replace('Z', '+00:00'))
                areas_query &= Q(updated_at__gte=updated_since_dt)
            except (ValueError, AttributeError):
                return Response({
                    'error': 'Invalid updated_since format. Use ISO 8601 format.',
                    'code': 'INVALID_DATE_FORMAT'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get table areas
        table_areas = TableArea.objects.filter(areas_query).order_by('sort_order', 'name')
        
        area_list = []
        for area in table_areas:
            area_list.append({
                'id': str(area.id),
                'company_id': str(area.company_id),
                'brand_id': str(area.brand_id),
                'store_id': str(area.store_id),
                'name': area.name,
                'description': area.description,
                'sort_order': area.sort_order,
                'floor_width': area.floor_width,
                'floor_height': area.floor_height,
                'floor_image': request.build_absolute_uri(area.floor_image.url) if area.floor_image else None,
                'is_active': area.is_active,
                'created_at': area.created_at.isoformat(),
                'updated_at': area.updated_at.isoformat(),
            })
        
        # Get tables for these areas
        area_ids = [area.id for area in table_areas]
        tables_query = Q(area_id__in=area_ids, is_active=True)
        
        if updated_since:
            tables_query &= Q(updated_at__gte=updated_since_dt)
        
        tables = Tables.objects.filter(tables_query).select_related('area').order_by('area', 'number')
        
        table_list = []
        for table in tables:
            table_list.append({
                'id': str(table.id),
                'area_id': str(table.area_id),
                'area_name': table.area.name,
                'number': table.number,
                'capacity': table.capacity,
                'qr_code': table.qr_code,
                'pos_x': table.pos_x,
                'pos_y': table.pos_y,
                'status': table.status,  # Note: Status managed by Edge
                'is_active': table.is_active,
                'created_at': table.created_at.isoformat(),
                'updated_at': table.updated_at.isoformat(),
            })
        
        logger.info(
            f"Tables sync: company={company_id}, store={store.store_code}, "
            f"areas={len(area_list)}, tables={len(table_list)}"
        )
        
        response_data = {
            'table_areas': area_list,
            'tables': table_list,
            'total_areas': len(area_list),
            'total_tables': len(table_list),
            'sync_timestamp': timezone.now().isoformat(),
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id)
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"Error in sync_tables: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter table areas'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter table areas'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Table Areas',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_table_areas(request):
    """
    Get table areas only for Edge Server (for food court concept)
    
    POST /api/v1/sync/table-areas/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid",
        "updated_since": "2026-01-29T00:00:00Z"  // optional
    }
    
    Returns:
        - table_areas: List of dining areas with floor plans
        - total: Total number of table areas
        - sync_timestamp: Current server timestamp
    
    Note: For full sync with tables, use /sync/tables/
    """
    try:
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        
        if not company_id:
            return Response({
                'error': 'company_id is required in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        updated_since = request.data.get('updated_since')
        
        # Get all brands operating in this store for food court concept
        store_brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).values_list('id', flat=True)
        
        # Import models
        from products.models import TableArea
        
        # Build query for table areas
        query = Q(
            company_id=company_id,
            brand_id__in=store_brands,
            store_id=store_id,
            is_active=True
        )
        
        if updated_since:
            try:
                updated_since_dt = datetime.fromisoformat(updated_since.replace('Z', '+00:00'))
                query &= Q(updated_at__gte=updated_since_dt)
            except (ValueError, AttributeError):
                return Response({
                    'error': 'Invalid updated_since format',
                    'code': 'INVALID_DATE_FORMAT'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        table_areas = TableArea.objects.filter(query).order_by('sort_order', 'name')
        
        area_list = []
        for area in table_areas:
            area_list.append({
                'id': str(area.id),
                'company_id': str(area.company_id),
                'brand_id': str(area.brand_id),
                'store_id': str(area.store_id),
                'name': area.name,
                'description': area.description,
                'sort_order': area.sort_order,
                'floor_width': area.floor_width,
                'floor_height': area.floor_height,
                'floor_image': request.build_absolute_uri(area.floor_image.url) if area.floor_image else None,
                'is_active': area.is_active,
                'created_at': area.created_at.isoformat(),
                'updated_at': area.updated_at.isoformat(),
            })
        
        return Response({
            'table_areas': area_list,
            'deleted_ids': [],
            'sync_timestamp': timezone.now().isoformat(),
            'total': len(area_list),
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id),
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Error in sync_table_areas: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter table groups'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter table groups'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Table Groups',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_table_groups(request):
    """
    Get table groups for Edge Server (for food court concept)
    
    POST /api/v1/sync/table-groups/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid",
        "updated_since": "2026-01-29T00:00:00Z"  // optional
    }
    
    Returns:
        - table_groups: List of table groups with members
        - total: Total number of table groups
        - sync_timestamp: Current server timestamp
    
    Note: Table groups are managed by Edge Server.
    This API is mainly for reference/reporting at HO.
    """
    try:
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        
        if not company_id:
            return Response({
                'error': 'company_id is required in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        updated_since = request.data.get('updated_since')
        
        # Get all brands operating in this store for food court concept
        store_brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).values_list('id', flat=True)
        
        # Import models
        from products.models import TableGroup
        
        # Build query for table groups
        query = Q(brand_id__in=store_brands)
        
        if updated_since:
            try:
                updated_since_dt = datetime.fromisoformat(updated_since.replace('Z', '+00:00'))
                query &= Q(created_at__gte=updated_since_dt)
            except (ValueError, AttributeError):
                return Response({
                    'error': 'Invalid updated_since format',
                    'code': 'INVALID_DATE_FORMAT'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        table_groups = TableGroup.objects.filter(query).select_related(
            'brand', 'main_table', 'created_by'
        ).prefetch_related('members__table').order_by('-created_at')
        
        group_list = []
        for group in table_groups:
            # Get member tables
            members = []
            for member in group.members.all():
                members.append({
                    'id': str(member.id),
                    'table_id': str(member.table_id),
                    'table_number': member.table.number,
                    'table_area': member.table.area.name,
                })
            
            group_list.append({
                'id': str(group.id),
                'brand_id': str(group.brand_id),
                'main_table_id': str(group.main_table_id),
                'main_table_number': group.main_table.number,
                'created_by_id': str(group.created_by_id),
                'created_by_name': group.created_by.get_full_name() if hasattr(group.created_by, 'get_full_name') else str(group.created_by),
                'created_at': group.created_at.isoformat(),
                'members': members,
                'total_members': len(members),
            })
        
        return Response({
            'table_groups': group_list,
            'deleted_ids': [],
            'sync_timestamp': timezone.now().isoformat(),
            'total': len(group_list),
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id),
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Error in sync_table_groups: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter modifiers'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter modifiers'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Modifiers',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_modifiers(request):
    """
    Get modifiers for Edge Server (for food court concept)
    
    POST /api/v1/sync/modifiers/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid",
        "updated_since": "2026-01-29T00:00:00Z"  // optional
    }
    
    Returns:
        - modifiers: List of modifier groups with their options
        - total: Total number of modifiers
        - sync_timestamp: Current server timestamp
    """
    try:
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        
        if not company_id:
            return Response({
                'error': 'company_id is required in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        updated_since = request.data.get('updated_since')
        
        # Get all brands operating in this store for food court concept
        store_brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).values_list('id', flat=True)
        
        # Import Modifier model
        from products.models import Modifier, ModifierOption
        
        # Build query - filter by brands operating in this store
        query = Q(brand_id__in=store_brands, is_active=True)
        
        if updated_since:
            try:
                updated_since_dt = datetime.fromisoformat(updated_since.replace('Z', '+00:00'))
                query &= Q(updated_at__gte=updated_since_dt)
            except (ValueError, AttributeError):
                return Response({
                    'error': 'Invalid updated_since format',
                    'code': 'INVALID_DATE_FORMAT'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        modifiers = Modifier.objects.filter(query).select_related('brand').prefetch_related('options')
        
        modifier_list = []
        for modifier in modifiers:
            # Get options for this modifier
            options = []
            for option in modifier.options.filter(is_active=True):
                options.append({
                    'id': str(option.id),
                    'modifier_id': str(option.modifier_id),
                    'name': option.name,
                    'price_adjustment': str(option.price_adjustment),
                    'is_default': option.is_default,
                    'sort_order': option.sort_order,
                    'is_active': option.is_active,
                    'created_at': option.created_at.isoformat(),
                })
            
            modifier_list.append({
                'id': str(modifier.id),
                'brand_id': str(modifier.brand_id),
                'company_id': str(modifier.brand.company_id),
                'name': modifier.name,
                'is_required': modifier.is_required,
                'max_selections': modifier.max_selections,
                'is_active': modifier.is_active,
                'options': options,
                'created_at': modifier.created_at.isoformat(),
                'updated_at': modifier.updated_at.isoformat(),
            })
        
        return Response({
            'modifiers': modifier_list,
            'deleted_ids': [],
            'sync_timestamp': timezone.now().isoformat(),
            'total': len(modifier_list),
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id),
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Error in sync_modifiers: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter modifier options'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter modifier options'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Modifier Options',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_modifier_options(request):
    """
    Get modifier options for Edge Server (for food court concept)
    
    POST /api/v1/sync/modifier-options/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid",
        "updated_since": "2026-01-29T00:00:00Z"  // optional
    }
    
    Returns:
        - modifier_options: List of modifier options
        - total: Total number of options
        - sync_timestamp: Current server timestamp
    
    Note: This is useful for incremental sync of options only.
    For full sync, use /sync/modifiers/ which includes options.
    """
    try:
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        
        if not company_id:
            return Response({
                'error': 'company_id is required in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        updated_since = request.data.get('updated_since')
        
        # Get all brands operating in this store for food court concept
        store_brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).values_list('id', flat=True)
        
        # Import ModifierOption model
        from products.models import ModifierOption
        
        # Build query - filter by modifiers from brands operating in this store
        query = Q(
            modifier__brand_id__in=store_brands,
            modifier__is_active=True,
            is_active=True
        )
        
        if updated_since:
            try:
                updated_since_dt = datetime.fromisoformat(updated_since.replace('Z', '+00:00'))
                query &= Q(created_at__gte=updated_since_dt)  # ModifierOption doesn't have updated_at
            except (ValueError, AttributeError):
                return Response({
                    'error': 'Invalid updated_since format',
                    'code': 'INVALID_DATE_FORMAT'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        options = ModifierOption.objects.filter(query).select_related(
            'modifier', 'modifier__brand'
        ).order_by('modifier', 'sort_order')
        
        option_list = []
        for option in options:
            option_list.append({
                'id': str(option.id),
                'modifier_id': str(option.modifier_id),
                'modifier_name': option.modifier.name,
                'brand_id': str(option.modifier.brand_id),
                'company_id': str(option.modifier.brand.company_id),
                'name': option.name,
                'price_adjustment': str(option.price_adjustment),
                'is_default': option.is_default,
                'sort_order': option.sort_order,
                'is_active': option.is_active,
                'created_at': option.created_at.isoformat(),
            })
        
        return Response({
            'modifier_options': option_list,
            'deleted_ids': [],
            'sync_timestamp': timezone.now().isoformat(),
            'total': len(option_list),
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id),
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Error in sync_modifier_options: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter product modifiers'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter product modifiers'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Product Modifiers',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here'
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_product_modifiers(request):
    """
    Get product-modifier relationships for Edge Server (for food court concept)
    
    POST /api/v1/sync/product-modifiers/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid",
        "updated_since": "2026-01-29T00:00:00Z"  // optional
    }
    
    Returns:
        - product_modifiers: List of product-modifier relationships
        - total: Total number of relationships
        - sync_timestamp: Current server timestamp
    """
    try:
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        
        if not company_id:
            return Response({
                'error': 'company_id is required in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get all brands operating in this store for food court concept
        store_brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).values_list('id', flat=True)
        
        # Import ProductModifier model
        from products.models import ProductModifier
        
        # Build query - get product modifiers for products in this store
        query = Q(
            product__company_id=company_id,
            product__brand_id__in=store_brands,
            product__is_active=True,
            modifier__is_active=True
        )
        
        product_modifiers = ProductModifier.objects.filter(query).select_related(
            'product', 'modifier'
        ).order_by('product', 'sort_order')
        
        pm_list = []
        for pm in product_modifiers:
            pm_list.append({
                'id': str(pm.id),
                'product_id': str(pm.product_id),
                'product_name': pm.product.name,
                'product_sku': pm.product.sku,
                'modifier_id': str(pm.modifier_id),
                'modifier_name': pm.modifier.name,
                'sort_order': pm.sort_order,
            })
        
        return Response({
            'product_modifiers': pm_list,
            'deleted_ids': [],
            'sync_timestamp': timezone.now().isoformat(),
            'total': len(pm_list),
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id),
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Error in sync_product_modifiers: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'company_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Company UUID to filter products'
                },
                'store_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Store UUID to filter products'
                },
                'updated_since': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'Last sync timestamp for incremental sync (optional)'
                },
                'limit': {
                    'type': 'integer',
                    'description': 'Max records per request (default: 100)'
                },
                'offset': {
                    'type': 'integer',
                    'description': 'Pagination offset (default: 0)'
                }
            },
            'required': ['company_id', 'store_id']
        }
    },
    examples=[
        OpenApiExample(
            'Sync Product Photos',
            value={
                'company_id': '812e76b6-f235-4bb2-948a-cae58ee62b97',
                'store_id': 'uuid-here',
                'limit': 100,
                'offset': 0
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_product_photos(request):
    """
    Get list of product photos for synchronization to Edge Server
    
    POST /api/v1/sync/product-photos/
    
    Request Body:
    {
        "company_id": "uuid",
        "store_id": "uuid",
        "updated_since": "2026-01-29T00:00:00Z",  // optional
        "limit": 100,  // optional, default 100
        "offset": 0    // optional, default 0
    }
    
    Returns:
        - photos: List of photo metadata with image URLs
        - total: Total number of photos
        - has_more: Boolean indicating if more records exist
        - next_offset: Next offset for pagination
    """
    try:
        from products.models import ProductPhoto
        
        company_id = request.data.get('company_id')
        store_id = request.data.get('store_id')
        updated_since = request.data.get('updated_since')
        limit = int(request.data.get('limit', 100))
        offset = int(request.data.get('offset', 0))
        
        if not company_id:
            return Response({
                'error': 'company_id is required in request body',
                'code': 'MISSING_COMPANY_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not store_id:
            return Response({
                'error': 'store_id is required in request body',
                'code': 'MISSING_STORE_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify store exists and belongs to company
        try:
            store = Store.objects.get(id=store_id, brand__company_id=company_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                'error': 'Store not found or does not belong to the specified company',
                'code': 'STORE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get all brands operating in this store for food court concept
        store_brands = Brand.objects.filter(
            company_id=company_id,
            is_active=True,
            stores__id=store_id
        ).values_list('id', flat=True)
        
        # Query photos for products in this store's brands
        queryset = ProductPhoto.objects.select_related('product').filter(
            product__company_id=company_id,
            product__brand_id__in=store_brands,
            product__is_active=True
        )
        
        if updated_since:
            try:
                updated_since_dt = datetime.fromisoformat(updated_since.replace('Z', '+00:00'))
                queryset = queryset.filter(updated_at__gte=updated_since_dt)
            except (ValueError, AttributeError):
                return Response({
                    'error': 'Invalid updated_since format',
                    'code': 'INVALID_DATE_FORMAT'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        total = queryset.count()
        photos = queryset.order_by('updated_at')[offset:offset + limit]
        
        data = []
        for photo in photos:
            data.append({
                'id': str(photo.id),
                'product_id': str(photo.product_id),
                'product_sku': photo.product.sku,
                'product_name': photo.product.name,
                'object_key': photo.object_key,
                'filename': photo.filename,
                'size': photo.size,
                'content_type': photo.content_type,
                'checksum': photo.checksum,
                'version': photo.version,
                'is_primary': photo.is_primary,
                'sort_order': photo.sort_order,
                'updated_at': photo.updated_at.isoformat() if photo.updated_at else None,
                'image_url': photo.image_url  # Includes cache-busting parameter
            })
        
        return Response({
            'photos': data,
            'deleted_ids': [],
            'sync_timestamp': timezone.now().isoformat(),
            'total': total,
            'has_more': (offset + limit) < total,
            'next_offset': offset + limit if (offset + limit) < total else None,
            'filter': {
                'company_id': str(company_id),
                'store_id': str(store_id),
            },
            'store': {
                'id': str(store.id),
                'code': store.store_code,
                'name': store.store_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Error in sync_product_photos: {str(e)}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
