"""
Modifier CRUD Views - Ultra Compact
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from products.models import Modifier, ModifierOption
from core.models import Brand
import json


@login_required
def modifier_list(request):
    """List all modifiers with search and filter"""
    search = request.GET.get('search', '').strip()
    brand_id = request.GET.get('brand', '')
    page = request.GET.get('page', 1)
    
    # Base queryset with global filters
    modifiers = Modifier.objects.select_related('brand', 'brand__company').annotate(
        option_count=Count('options')
    )
    
    # Apply global filters first (from middleware)
    if hasattr(request, 'current_company') and request.current_company:
        modifiers = modifiers.filter(brand__company=request.current_company)
    
    if hasattr(request, 'current_brand') and request.current_brand:
        modifiers = modifiers.filter(brand=request.current_brand)
    
    # Apply search
    if search:
        modifiers = modifiers.filter(
            Q(name__icontains=search) |
            Q(brand__name__icontains=search)
        )
    
    # Apply URL parameter brand filter (override if specified)
    if brand_id:
        modifiers = modifiers.filter(brand_id=brand_id)
    
    # Apply ordering
    modifiers = modifiers.order_by('name')
    
    # Pagination
    paginator = Paginator(modifiers, 10)
    modifiers_page = paginator.get_page(page)
    
    # Get brands for filter
    brands = Brand.objects.filter(is_active=True).order_by('name')
    
    if request.headers.get('HX-Request'):
        return render(request, 'products/modifier/_table.html', {
            'modifiers': modifiers_page,
            'brands': brands
        })
    
    return render(request, 'products/modifier/list.html', {
        'modifiers': modifiers_page,
        'brands': brands,
        'search': search,
        'selected_brand': brand_id
    })


@login_required
@require_http_methods(["GET", "POST"])
def modifier_create(request):
    """Create new modifier"""
    if request.method == 'POST':
        try:
            # Get brand from global filter
            brand_id = None
            if hasattr(request, 'current_brand') and request.current_brand:
                brand_id = request.current_brand.id
            
            if not brand_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Please select a brand from global filter first'
                }, status=400)
            
            name = request.POST.get('name', '').strip()
            is_required = request.POST.get('is_required') == 'on'
            max_selections = request.POST.get('max_selections', '1')
            is_active = request.POST.get('is_active') == 'on'
            
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Name is required'
                }, status=400)
            
            # Create modifier
            modifier = Modifier.objects.create(
                brand_id=brand_id,
                name=name,
                is_required=is_required,
                max_selections=int(max_selections) if max_selections else 1,
                is_active=is_active
            )
            
            messages.success(request, f'Modifier "{modifier.name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Modifier created successfully',
                'redirect': '/products/modifiers/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    return render(request, 'products/modifier/_form.html', {
        'current_brand': getattr(request, 'current_brand', None)
    })


@login_required
@require_http_methods(["GET", "POST"])
def modifier_update(request, pk):
    """Update existing modifier"""
    modifier = get_object_or_404(Modifier.objects.select_related('brand'), pk=pk)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            is_required = request.POST.get('is_required') == 'on'
            max_selections = request.POST.get('max_selections', '1')
            is_active = request.POST.get('is_active') == 'on'
            
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Name is required'
                }, status=400)
            
            # Update modifier
            modifier.name = name
            modifier.is_required = is_required
            modifier.max_selections = int(max_selections) if max_selections else 1
            modifier.is_active = is_active
            modifier.save()
            
            messages.success(request, f'Modifier "{modifier.name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Modifier updated successfully',
                'redirect': '/products/modifiers/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form with prefetch options
    modifier = Modifier.objects.prefetch_related('options').get(pk=pk)
    
    # Serialize options for Alpine.js
    options_json = json.dumps([
        {
            'name': opt.name,
            'price_adjustment': float(opt.price_adjustment),
            'is_default': opt.is_default
        }
        for opt in modifier.options.all()
    ])
    
    return render(request, 'products/modifier/_form.html', {
        'modifier': modifier,
        'options_json': options_json,
        'current_brand': getattr(request, 'current_brand', None)
    })


@login_required
@require_http_methods(["POST", "DELETE"])
def modifier_delete(request, pk):
    """Delete modifier"""
    try:
        modifier = get_object_or_404(Modifier, pk=pk)
        modifier_name = modifier.name
        modifier.delete()
        
        messages.success(request, f'Modifier "{modifier_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Modifier deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def modifier_options_save(request, pk):
    """Save modifier options"""
    try:
        modifier = get_object_or_404(Modifier, pk=pk)
        
        # Parse JSON body
        data = json.loads(request.body)
        options_data = data.get('options', [])
        
        # Delete existing options
        modifier.options.all().delete()
        
        # Create new options
        for idx, option_data in enumerate(options_data):
            ModifierOption.objects.create(
                modifier=modifier,
                name=option_data.get('name'),
                price_adjustment=float(option_data.get('price_adjustment', 0)),
                is_default=option_data.get('is_default', False),
                sort_order=idx
            )
        
        return JsonResponse({
            'success': True,
            'message': f'{len(options_data)} options saved successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

