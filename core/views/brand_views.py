"""
Brand CRUD Views
Ultra compact UI with HTMX + Alpine.js
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import Brand, Company


@login_required
def brand_list(request):
    """
    Brand list with search and pagination (compact UI)
    """
    # Get filters
    search = request.GET.get('search', '')
    company_id = request.GET.get('company', '')
    
    # Base queryset with company relation
    brands = Brand.objects.select_related('company').annotate(
        store_count=Count('stores')
    )
    
    # Apply search filter
    if search:
        brands = brands.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search) |
            Q(company__name__icontains=search)
        )
    
    # Filter by company
    if company_id:
        brands = brands.filter(company_id=company_id)
    
    # Pagination (10 items per page)
    paginator = Paginator(brands, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get all companies for filter dropdown
    companies = Company.objects.filter(is_active=True).order_by('name')
    
    context = {
        'brands': page_obj,
        'companies': companies,
        'search': search,
        'selected_company': company_id,
        'total_count': brands.count(),
    }
    
    # HTMX partial response
    if request.htmx:
        return render(request, 'core/brand/_table.html', context)
    
    return render(request, 'core/brand/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def brand_create(request):
    """
    Create new brand (HTMX)
    """
    if request.method == 'POST':
        try:
            # Get form data
            company_id = request.POST.get('company_id')
            code = request.POST.get('code', '').strip()
            name = request.POST.get('name', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()
            tax_id = request.POST.get('tax_id', '').strip()
            tax_rate = request.POST.get('tax_rate', 11.00)
            service_charge = request.POST.get('service_charge', 5.00)
            point_expiry_override = request.POST.get('point_expiry_months_override', '')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not company_id or not code or not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Company, Code and Name are required'
                }, status=400)
            
            # Check duplicate code
            if Brand.objects.filter(code=code).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Brand code "{code}" already exists'
                }, status=400)
            
            # Get company
            company = get_object_or_404(Company, pk=company_id)
            
            # Create brand
            brand = Brand.objects.create(
                company=company,
                code=code,
                name=name,
                address=address,
                phone=phone,
                tax_id=tax_id,
                tax_rate=float(tax_rate),
                service_charge=float(service_charge),
                point_expiry_months_override=int(point_expiry_override) if point_expiry_override else None,
                is_active=is_active
            )
            
            messages.success(request, f'Brand "{brand.name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Brand created successfully',
                'redirect': '/brand/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - show form
    companies = Company.objects.filter(is_active=True).order_by('name')
    context = {'companies': companies}
    return render(request, 'core/brand/_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def brand_update(request, pk):
    """
    Update existing brand (HTMX)
    """
    brand = get_object_or_404(Brand.objects.select_related('company'), pk=pk)
    
    if request.method == 'POST':
        try:
            # Get form data
            code = request.POST.get('code', '').strip()
            name = request.POST.get('name', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()
            tax_id = request.POST.get('tax_id', '').strip()
            tax_rate = request.POST.get('tax_rate', 11.00)
            service_charge = request.POST.get('service_charge', 5.00)
            point_expiry_override = request.POST.get('point_expiry_months_override', '')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not code or not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Code and Name are required'
                }, status=400)
            
            # Check duplicate code (exclude current)
            if Brand.objects.filter(code=code).exclude(pk=pk).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Brand code "{code}" already exists'
                }, status=400)
            
            # Update brand
            brand.code = code
            brand.name = name
            brand.address = address
            brand.phone = phone
            brand.tax_id = tax_id
            brand.tax_rate = float(tax_rate)
            brand.service_charge = float(service_charge)
            brand.point_expiry_months_override = int(point_expiry_override) if point_expiry_override else None
            brand.is_active = is_active
            brand.save()
            
            messages.success(request, f'Brand "{brand.name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Brand updated successfully',
                'redirect': '/brand/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - show form
    companies = Company.objects.filter(is_active=True).order_by('name')
    context = {
        'brand': brand,
        'companies': companies
    }
    return render(request, 'core/brand/_form.html', context)


@login_required
@require_http_methods(["POST", "DELETE"])
def brand_delete(request, pk):
    """
    Delete brand (HTMX)
    """
    brand = get_object_or_404(Brand, pk=pk)
    
    try:
        brand_name = brand.name
        brand.delete()
        
        messages.success(request, f'Brand "{brand_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Brand deleted successfully',
            'redirect': '/brand/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
