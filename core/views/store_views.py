"""
Store CRUD Views - Ultra compact UI
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import Store, Brand, Company


@login_required
def store_list(request):
    """Store list with search and pagination"""
    search = request.GET.get('search', '')
    brand_id = request.GET.get('brand', '')
    company_id = request.GET.get('company', '')
    
    stores = Store.objects.select_related('company').prefetch_related('brands')
    
    if search:
        stores = stores.filter(
            Q(store_code__icontains=search) |
            Q(store_name__icontains=search) |
            Q(address__icontains=search)
        )
    
    if brand_id:
        stores = stores.filter(brands__id=brand_id)
    
    if company_id:
        stores = stores.filter(company_id=company_id)
    
    paginator = Paginator(stores, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    companies = Company.objects.filter(is_active=True).order_by('name')
    brands = Brand.objects.filter(is_active=True).select_related('company').order_by('name')
    
    context = {
        'stores': page_obj,
        'companies': companies,
        'brands': brands,
        'search': search,
        'selected_brand': brand_id,
        'selected_company': company_id,
        'total_count': stores.count(),
    }
    
    if request.htmx:
        return render(request, 'core/store/_table.html', context)
    
    return render(request, 'core/store/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def store_create(request):
    """Create new store"""
    if request.method == 'POST':
        try:
            company_id = request.POST.get('company_id')
            brand_ids = request.POST.getlist('brand_ids')
            store_code = request.POST.get('store_code', '').strip()
            store_name = request.POST.get('store_name', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()
            timezone = request.POST.get('timezone', 'Asia/Jakarta')
            latitude = request.POST.get('latitude', '')
            longitude = request.POST.get('longitude', '')
            is_active = request.POST.get('is_active') == 'on'
            
            if not company_id or not store_code or not store_name or not address or not phone:
                return JsonResponse({
                    'success': False,
                    'message': 'Company, Code, Name, Address and Phone are required'
                }, status=400)
            
            if Store.objects.filter(store_code=store_code).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Store code "{store_code}" already exists'
                }, status=400)
            
            company = get_object_or_404(Company, pk=company_id)
            
            store = Store.objects.create(
                company=company,
                store_code=store_code,
                store_name=store_name,
                address=address,
                phone=phone,
                timezone=timezone,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                is_active=is_active
            )
            
            # Add brands if provided
            if brand_ids:
                store.brands.set(brand_ids)
            
            messages.success(request, f'Store "{store.store_name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Store created successfully',
                'redirect': '/store/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    companies = Company.objects.filter(is_active=True).order_by('name')
    brands = Brand.objects.filter(is_active=True).select_related('company').order_by('name')
    context = {'companies': companies, 'brands': brands}
    return render(request, 'core/store/_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def store_update(request, pk):
    """Update existing store"""
    store = get_object_or_404(Store.objects.select_related('company').prefetch_related('brands'), pk=pk)
    
    if request.method == 'POST':
        try:
            brand_ids = request.POST.getlist('brand_ids')
            store_code = request.POST.get('store_code', '').strip()
            store_name = request.POST.get('store_name', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()
            timezone = request.POST.get('timezone', 'Asia/Jakarta')
            latitude = request.POST.get('latitude', '')
            longitude = request.POST.get('longitude', '')
            is_active = request.POST.get('is_active') == 'on'
            
            if not store_code or not store_name or not address or not phone:
                return JsonResponse({
                    'success': False,
                    'message': 'Code, Name, Address and Phone are required'
                }, status=400)
            
            if Store.objects.filter(store_code=store_code).exclude(pk=pk).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Store code "{store_code}" already exists'
                }, status=400)
            
            store.store_code = store_code
            store.store_name = store_name
            store.address = address
            store.phone = phone
            store.timezone = timezone
            store.latitude = float(latitude) if latitude else None
            store.longitude = float(longitude) if longitude else None
            store.is_active = is_active
            store.save()
            
            # Update brands
            if brand_ids:
                store.brands.set(brand_ids)
            else:
                store.brands.clear()
            
            messages.success(request, f'Store "{store.store_name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Store updated successfully',
                'redirect': '/store/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    companies = Company.objects.filter(is_active=True).order_by('name')
    brands = Brand.objects.filter(is_active=True).select_related('company').order_by('name')
    context = {
        'store': store,
        'companies': companies,
        'brands': brands
    }
    return render(request, 'core/store/_form.html', context)


@login_required
@require_http_methods(["POST", "DELETE"])
def store_delete(request, pk):
    """Delete store"""
    store = get_object_or_404(Store, pk=pk)
    
    try:
        # Check if there are related terminals (if Terminal model exists)
        # Uncomment when Terminal model is ready:
        # terminal_count = store.terminals.count()
        # if terminal_count > 0:
        #     return JsonResponse({
        #         'success': False,
        #         'message': f'Cannot delete store "{store.store_name}" because it has {terminal_count} terminal(s). Please delete all terminals first.'
        #     }, status=400)
        
        store_name = store.store_name
        store.delete()
        
        messages.success(request, f'Store "{store_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Store deleted successfully',
            'redirect': '/store/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete store: {str(e)}'
        }, status=500)
