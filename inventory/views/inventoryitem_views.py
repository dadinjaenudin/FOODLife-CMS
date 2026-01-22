"""
Inventory Item (Raw Material) CRUD Views - Ultra Compact
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from inventory.models import InventoryItem
from core.models import Brand


@login_required
def inventoryitem_list(request):
    """List all inventory items with search and brand filter"""
    search = request.GET.get('search', '').strip()
    brand_id = request.GET.get('brand_id', '').strip()
    item_type = request.GET.get('item_type', '').strip()
    page = request.GET.get('page', 1)
    
    # Base queryset
    items = InventoryItem.objects.select_related('brand__company')
    
    # Apply search
    if search:
        items = items.filter(
            Q(name__icontains=search) |
            Q(item_code__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Apply brand filter
    if brand_id:
        items = items.filter(brand_id=brand_id)
    
    # Apply item type filter
    if item_type:
        items = items.filter(item_type=item_type)
    
    # Apply ordering
    items = items.order_by('name')
    
    # Pagination
    paginator = Paginator(items, 10)
    items_page = paginator.get_page(page)
    
    # Get brands for filter
    brands = Brand.objects.filter(is_active=True).select_related('company').order_by('name')
    
    if request.headers.get('HX-Request'):
        return render(request, 'inventory/inventoryitem/_table.html', {
            'items': items_page,
            'page_obj': items_page
        })
    
    return render(request, 'inventory/inventoryitem/list.html', {
        'items': items_page,
        'page_obj': items_page,
        'search': search,
        'brand_id': brand_id,
        'item_type': item_type,
        'brands': brands,
        'total_count': items.count()
    })


@login_required
@require_http_methods(["GET", "POST"])
def inventoryitem_create(request):
    """Create new inventory item"""
    if request.method == 'POST':
        try:
            brand_id = request.POST.get('brand_id', '').strip()
            item_code = request.POST.get('item_code', '').strip()
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            item_type = request.POST.get('item_type', '').strip()
            base_unit = request.POST.get('base_unit', '').strip()
            cost_per_unit = request.POST.get('cost_per_unit', '0')
            min_stock = request.POST.get('min_stock', '0')
            max_stock = request.POST.get('max_stock', '0')
            track_stock = request.POST.get('track_stock') == 'on'
            is_active = request.POST.get('is_active') == 'on'
            
            if not brand_id or not item_code or not name or not item_type or not base_unit:
                return JsonResponse({
                    'success': False,
                    'message': 'Brand, Item Code, Name, Item Type and Base Unit are required'
                }, status=400)
            
            # Check code uniqueness per brand
            if InventoryItem.objects.filter(brand_id=brand_id, item_code=item_code).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Item Code "{item_code}" already exists for this brand'
                }, status=400)
            
            # Create inventory item
            item = InventoryItem.objects.create(
                brand_id=brand_id,
                item_code=item_code,
                name=name,
                description=description,
                item_type=item_type,
                base_unit=base_unit,
                cost_per_unit=cost_per_unit,
                min_stock=min_stock,
                max_stock=max_stock,
                track_stock=track_stock,
                is_active=is_active
            )
            
            messages.success(request, f'Inventory Item "{item.name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Inventory Item created successfully',
                'redirect': '/inventory/items/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    brands = Brand.objects.filter(is_active=True).select_related('company').order_by('name')
    return render(request, 'inventory/inventoryitem/_form.html', {
        'brands': brands
    })


@login_required
@require_http_methods(["GET", "POST"])
def inventoryitem_update(request, pk):
    """Update existing inventory item"""
    item = get_object_or_404(InventoryItem.objects.select_related('brand__company'), pk=pk)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            item_code = request.POST.get('item_code', '').strip()
            description = request.POST.get('description', '').strip()
            item_type = request.POST.get('item_type', '').strip()
            base_unit = request.POST.get('base_unit', '').strip()
            cost_per_unit = request.POST.get('cost_per_unit', '0')
            min_stock = request.POST.get('min_stock', '0')
            max_stock = request.POST.get('max_stock', '0')
            track_stock = request.POST.get('track_stock') == 'on'
            is_active = request.POST.get('is_active') == 'on'
            
            if not name or not item_code or not item_type or not base_unit:
                return JsonResponse({
                    'success': False,
                    'message': 'Name, Item Code, Item Type and Base Unit are required'
                }, status=400)
            
            # Check code uniqueness per brand (exclude current)
            if InventoryItem.objects.filter(brand=item.brand, item_code=item_code).exclude(pk=pk).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Item Code "{item_code}" already exists for this brand'
                }, status=400)
            
            # Update inventory item
            item.name = name
            item.item_code = item_code
            item.description = description
            item.item_type = item_type
            item.base_unit = base_unit
            item.cost_per_unit = cost_per_unit
            item.min_stock = min_stock
            item.max_stock = max_stock
            item.track_stock = track_stock
            item.is_active = is_active
            item.save()
            
            messages.success(request, f'Inventory Item "{item.name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Inventory Item updated successfully',
                'redirect': '/inventory/items/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    brands = Brand.objects.filter(is_active=True).select_related('company').order_by('name')
    return render(request, 'inventory/inventoryitem/_form.html', {
        'item': item,
        'brands': brands
    })


@login_required
@require_http_methods(["POST", "DELETE"])
def inventoryitem_delete(request, pk):
    """Delete inventory item"""
    try:
        item = get_object_or_404(InventoryItem, pk=pk)
        item_name = item.name
        item.delete()
        
        messages.success(request, f'Inventory Item "{item_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Inventory Item deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
