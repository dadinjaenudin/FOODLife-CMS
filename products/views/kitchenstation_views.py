"""
Kitchen Station CRUD Views - Ultra Compact
NOTE: Kitchen Station is GLOBAL (no brand field)
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from products.models import KitchenStation


@login_required
def kitchenstation_list(request):
    """List all kitchen stations with search"""
    search = request.GET.get('search', '').strip()
    page = request.GET.get('page', 1)
    
    # Base queryset
    kitchenstations = KitchenStation.objects.all()
    
    # Apply search
    if search:
        kitchenstations = kitchenstations.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search)
        )
    
    # Apply ordering
    kitchenstations = kitchenstations.order_by('name')
    
    # Pagination
    paginator = Paginator(kitchenstations, 10)
    kitchenstations_page = paginator.get_page(page)
    
    if request.headers.get('HX-Request'):
        return render(request, 'products/kitchenstation/_table.html', {
            'kitchenstations': kitchenstations_page
        })
    
    return render(request, 'products/kitchenstation/list.html', {
        'kitchenstations': kitchenstations_page,
        'search': search
    })


@login_required
@require_http_methods(["GET", "POST"])
def kitchenstation_create(request):
    """Create new kitchen station"""
    if request.method == 'POST':
        try:
            code = request.POST.get('code', '').strip()
            name = request.POST.get('name', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            if not code or not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Code and Name are required'
                }, status=400)
            
            # Check code uniqueness
            if KitchenStation.objects.filter(code=code).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Code "{code}" already exists'
                }, status=400)
            
            # Create kitchen station
            kitchenstation = KitchenStation.objects.create(
                code=code,
                name=name,
                is_active=is_active
            )
            
            messages.success(request, f'Kitchen Station "{kitchenstation.name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Kitchen Station created successfully',
                'redirect': '/products/kitchenstations/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    return render(request, 'products/kitchenstation/_form.html', {})


@login_required
@require_http_methods(["GET", "POST"])
def kitchenstation_update(request, pk):
    """Update existing kitchen station"""
    kitchenstation = get_object_or_404(KitchenStation, pk=pk)
    
    if request.method == 'POST':
        try:
            code = request.POST.get('code', '').strip()
            name = request.POST.get('name', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            if not code or not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Code and Name are required'
                }, status=400)
            
            # Check code uniqueness (exclude current)
            if KitchenStation.objects.filter(code=code).exclude(pk=pk).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Code "{code}" already exists'
                }, status=400)
            
            # Update kitchen station
            kitchenstation.code = code
            kitchenstation.name = name
            kitchenstation.is_active = is_active
            kitchenstation.save()
            
            messages.success(request, f'Kitchen Station "{kitchenstation.name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Kitchen Station updated successfully',
                'redirect': '/products/kitchenstations/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    return render(request, 'products/kitchenstation/_form.html', {
        'kitchenstation': kitchenstation
    })


@login_required
@require_http_methods(["POST", "DELETE"])
def kitchenstation_delete(request, pk):
    """Delete kitchen station"""
    try:
        kitchenstation = get_object_or_404(KitchenStation, pk=pk)
        kitchenstation_name = kitchenstation.name
        kitchenstation.delete()
        
        messages.success(request, f'Kitchen Station "{kitchenstation_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Kitchen Station deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
