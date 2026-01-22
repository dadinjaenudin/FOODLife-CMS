"""
Table Area CRUD Views - Ultra Compact
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from products.models import TableArea
from core.models import Brand


@login_required
def tablearea_list(request):
    """List all table areas with search and filter"""
    search = request.GET.get('search', '').strip()
    brand_id = request.GET.get('brand', '')
    page = request.GET.get('page', 1)
    
    # Base queryset
    tableareas = TableArea.objects.select_related('brand')
    
    # Apply search
    if search:
        tableareas = tableareas.filter(
            Q(name__icontains=search) |
            Q(brand__name__icontains=search)
        )
    
    # Apply brand filter
    if brand_id:
        tableareas = tableareas.filter(brand_id=brand_id)
    
    # Apply ordering
    tableareas = tableareas.order_by('sort_order', 'name')
    
    # Pagination
    paginator = Paginator(tableareas, 10)
    tableareas_page = paginator.get_page(page)
    
    # Get brands for filter
    brands = Brand.objects.filter(is_active=True).order_by('name')
    
    if request.headers.get('HX-Request'):
        return render(request, 'products/tablearea/_table.html', {
            'tableareas': tableareas_page,
            'brands': brands
        })
    
    return render(request, 'products/tablearea/list.html', {
        'tableareas': tableareas_page,
        'brands': brands,
        'search': search,
        'selected_brand': brand_id
    })


@login_required
@require_http_methods(["GET", "POST"])
def tablearea_create(request):
    """Create new table area"""
    if request.method == 'POST':
        try:
            brand_id = request.POST.get('brand_id')
            name = request.POST.get('name', '').strip()
            sort_order = request.POST.get('sort_order', '0')
            is_active = request.POST.get('is_active') == 'on'
            
            if not brand_id or not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Brand and Name are required'
                }, status=400)
            
            # Create table area
            tablearea = TableArea.objects.create(
                brand_id=brand_id,
                name=name,
                sort_order=int(sort_order) if sort_order else 0,
                is_active=is_active
            )
            
            messages.success(request, f'Table Area "{tablearea.name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Table Area created successfully',
                'redirect': '/products/tableareas/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    brands = Brand.objects.filter(is_active=True).order_by('name')
    
    return render(request, 'products/tablearea/_form.html', {
        'brands': brands
    })


@login_required
@require_http_methods(["GET", "POST"])
def tablearea_update(request, pk):
    """Update existing table area"""
    tablearea = get_object_or_404(TableArea.objects.select_related('brand'), pk=pk)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            sort_order = request.POST.get('sort_order', '0')
            is_active = request.POST.get('is_active') == 'on'
            
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Name is required'
                }, status=400)
            
            # Update table area
            tablearea.name = name
            tablearea.sort_order = int(sort_order) if sort_order else 0
            tablearea.is_active = is_active
            tablearea.save()
            
            messages.success(request, f'Table Area "{tablearea.name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Table Area updated successfully',
                'redirect': '/products/tableareas/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    brands = Brand.objects.filter(is_active=True).order_by('name')
    
    return render(request, 'products/tablearea/_form.html', {
        'tablearea': tablearea,
        'brands': brands
    })


@login_required
@require_http_methods(["POST", "DELETE"])
def tablearea_delete(request, pk):
    """Delete table area"""
    try:
        tablearea = get_object_or_404(TableArea, pk=pk)
        tablearea_name = tablearea.name
        tablearea.delete()
        
        messages.success(request, f'Table Area "{tablearea_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Table Area deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
