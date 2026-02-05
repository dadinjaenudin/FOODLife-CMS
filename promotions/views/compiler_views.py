"""
Compiler & Sync Dashboard Views
Manages promotion compilation and Edge Server sync
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from promotions.models import Promotion
from promotions.services.compiler import PromotionCompiler
from core.models import Store
import json


@login_required
def compiler_dashboard(request):
    """
    Main compiler dashboard
    Shows compilation status, sync info, and API documentation
    """
    # Get statistics
    total_promotions = Promotion.objects.filter(company=request.user.company).count()
    active_promotions = Promotion.objects.filter(
        company=request.user.company,
        is_active=True,
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    ).count()
    
    # Promotions by type
    promotions_by_type = Promotion.objects.filter(
        company=request.user.company,
        is_active=True
    ).values('promo_type').annotate(count=Count('id')).order_by('-count')
    
    # Recent promotions
    recent_promotions = Promotion.objects.filter(
        company=request.user.company
    ).order_by('-updated_at')[:10]
    
    # Stores - Use global filter logic
    stores_qs = Store.objects.filter(is_active=True)
    
    # Apply user-based filtering
    if getattr(request.user, 'store', None):
        # User locked to specific store
        stores_qs = Store.objects.filter(id=request.user.store.id)
    else:
        # Filter based on current_brand or user's brand/company
        current_brand = getattr(request, 'current_brand', None)
        if current_brand:
            stores_qs = stores_qs.filter(brands=current_brand)
        elif request.user.brand:
            stores_qs = stores_qs.filter(brands=request.user.brand)
        elif request.user.company:
            stores_qs = stores_qs.filter(company=request.user.company)
    
    stores = stores_qs.order_by('store_name')
    
    context = {
        'total_promotions': total_promotions,
        'active_promotions': active_promotions,
        'inactive_promotions': total_promotions - active_promotions,
        'promotions_by_type': promotions_by_type,
        'recent_promotions': recent_promotions,
        'stores': stores,
        'page_title': 'Promotion Compiler & Sync',
    }
    
    return render(request, 'promotions/compiler_dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def compile_promotion(request, promotion_id):
    """
    Compile single promotion to JSON
    """
    try:
        promotion = Promotion.objects.get(id=promotion_id, company=request.user.company)
        
        compiler = PromotionCompiler()
        compiled_data = compiler.compile_promotion(promotion)
        
        return JsonResponse({
            'success': True,
            'promotion_code': promotion.code,
            'compiled_data': compiled_data
        })
        
    except Promotion.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Promotion not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def compile_all_active(request):
    """
    Compile all active promotions
    """
    try:
        # Get today's date - use localized timezone from settings
        from django.utils.timezone import localtime
        today = localtime(timezone.now()).date()
        
        # Build filter based on user context (use global filter if available)
        filter_kwargs = {}
        
        # Use global filter company if available, otherwise user's company
        if hasattr(request, 'current_company') and request.current_company:
            filter_kwargs['company'] = request.current_company
        elif request.user.company:
            filter_kwargs['company'] = request.user.company
        else:
            # No company context - return error
            return JsonResponse({
                'success': False,
                'error': 'No company context available. Please select a company from the global filter.',
                'debug': {
                    'user_company': None,
                    'current_company': None,
                }
            }, status=400)
        
        # Optionally filter by brand from global filter
        if hasattr(request, 'current_brand') and request.current_brand:
            filter_kwargs['brand'] = request.current_brand
        elif request.user.brand:
            filter_kwargs['brand'] = request.user.brand
        
        # Debug: Get all promotions first
        all_promotions = Promotion.objects.filter(**filter_kwargs)
        active_only = all_promotions.filter(is_active=True)
        
        # Final filter with dates - use __lte and __gte for inclusive comparison
        promotions = active_only.filter(
            start_date__lte=today,
            end_date__gte=today
        )
        
        # Enhanced debug info with timezone information
        import datetime
        debug_info = {
            'filter_company': str(filter_kwargs.get('company', 'None')),
            'filter_brand': str(filter_kwargs.get('brand', 'None')) if 'brand' in filter_kwargs else 'All brands',
            'user_company': str(request.user.company) if request.user.company else None,
            'user_brand': str(request.user.brand) if request.user.brand else None,
            'current_company': str(request.current_company) if hasattr(request, 'current_company') and request.current_company else None,
            'current_brand': str(request.current_brand) if hasattr(request, 'current_brand') and request.current_brand else None,
            'total_promotions': all_promotions.count(),
            'active_promotions': active_only.count(),
            'promotions_with_valid_dates': promotions.count(),
            'today': str(today),
            'server_utc_now': str(timezone.now()),
            'server_local_now': str(localtime(timezone.now())),
            'server_local_date': str(today),
        }
        
        # Add detail for each promotion (even if not active, to help debug)
        all_promo_list = Promotion.objects.filter(company=filter_kwargs['company'])
        if all_promo_list.count() > 0:
            debug_info['all_promotions_detail'] = []
            for p in all_promo_list[:10]:  # Limit to 10 for performance
                debug_info['all_promotions_detail'].append({
                    'code': p.code,
                    'name': p.name,
                    'company': str(p.company),
                    'brand': str(p.brand) if p.brand else 'NULL',
                    'is_active': p.is_active,
                    'start_date': str(p.start_date),
                    'end_date': str(p.end_date),
                    'matches_brand_filter': (not 'brand' in filter_kwargs) or (p.brand_id == filter_kwargs['brand'].id if 'brand' in filter_kwargs else True),
                    'passes_date_filter': (p.start_date <= today and p.end_date >= today),
                })
        
        # Add detail for each active promotion
        if active_only.count() > 0:
            debug_info['active_details'] = []
            for p in active_only:
                debug_info['active_details'].append({
                    'code': p.code,
                    'name': p.name,
                    'is_active': p.is_active,
                    'start_date': str(p.start_date),
                    'end_date': str(p.end_date),
                    'passes_date_filter': (p.start_date <= today and p.end_date >= today),
                })
        
        compiler = PromotionCompiler()
        compiled = compiler.compile_multiple(promotions)
        
        # Add store_id context if user has specific store or from global filter
        store_id_context = None
        if getattr(request.user, 'store', None):
            store_id_context = str(request.user.store.id)
        elif hasattr(request, 'current_store') and request.current_store:
            store_id_context = str(request.current_store.id)
        
        # Add store_id to each compiled promotion if available
        if store_id_context:
            for promo in compiled:
                promo['store_id'] = store_id_context
        
        return JsonResponse({
            'success': True,
            'count': len(compiled),
            'promotions': compiled,
            'debug': debug_info  # Add debug info to response
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@login_required
@require_http_methods(["POST"])
def compile_for_store(request, store_id):
    """
    Compile promotions for specific store
    """
    try:
        store = Store.objects.get(id=store_id, company=request.user.company)
        
        compiler = PromotionCompiler()
        compiled = compiler.compile_for_store(str(store_id))
        
        return JsonResponse({
            'success': True,
            'store_name': store.store_name,
            'store_code': store.store_code,
            'count': len(compiled),
            'promotions': compiled
        })
        
    except Store.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Store not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def compile_for_company(request):
    """
    Compile promotions for ALL stores in company
    
    This generates promotion JSON for every store and brand.
    Perfect for scheduled compilation and bulk distribution.
    """
    try:
        # Get company from user or global filter
        company = None
        if hasattr(request, 'current_company') and request.current_company:
            company = request.current_company
        elif request.user.company:
            company = request.user.company
        else:
            return JsonResponse({
                'success': False,
                'error': 'No company context available'
            }, status=400)
        
        compiler = PromotionCompiler()
        result = compiler.compile_for_company(str(company.id))
        
        if 'error' in result:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'company_name': result['company_name'],
            'compiled_at': result['compiled_at'],
            'summary': result['summary'],
            'stores': result['stores']
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@login_required
def preview_compiled_json(request, promotion_id):
    """
    Preview compiled JSON for a promotion
    """
    try:
        promotion = Promotion.objects.get(id=promotion_id, company=request.user.company)
        
        compiler = PromotionCompiler()
        compiled_data = compiler.compile_promotion(promotion)
        
        # Pretty print JSON
        json_str = json.dumps(compiled_data, indent=2, default=str)
        
        context = {
            'promotion': promotion,
            'json_data': json_str,
            'page_title': f'Preview: {promotion.code}',
        }
        
        return render(request, 'promotions/preview_json.html', context)
        
    except Promotion.DoesNotExist:
        return render(request, 'error.html', {
            'message': 'Promotion not found'
        }, status=404)


@login_required
def api_documentation(request):
    """
    API documentation for Edge Server integration
    """
    # Get sample store for examples
    stores_qs = Store.objects.filter(is_active=True)
    
    # Apply same filtering logic
    if getattr(request.user, 'store', None):
        sample_store = request.user.store
    else:
        current_brand = getattr(request, 'current_brand', None)
        if current_brand:
            stores_qs = stores_qs.filter(brands=current_brand)
        elif request.user.brand:
            stores_qs = stores_qs.filter(brands=request.user.brand)
        elif request.user.company:
            stores_qs = stores_qs.filter(company=request.user.company)
        
        sample_store = stores_qs.order_by('store_name').first()
    
    context = {
        'sample_store': sample_store,
        'page_title': 'API Documentation',
    }
    
    return render(request, 'promotions/api_documentation.html', context)
