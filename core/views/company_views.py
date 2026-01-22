"""
Company CRUD Views
Ultra compact UI with HTMX + Alpine.js
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import Company


@login_required
def company_list(request):
    """
    Company list with search and pagination (compact UI)
    """
    # Get search query
    search = request.GET.get('search', '')
    
    # Base queryset
    companies = Company.objects.all()
    
    # Apply search filter
    if search:
        companies = companies.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search)
        )
    
    # Pagination (10 items per page for compact UI)
    paginator = Paginator(companies, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'companies': page_obj,
        'search': search,
        'total_count': companies.count(),
    }
    
    # HTMX partial response
    if request.htmx:
        return render(request, 'core/company/_table.html', context)
    
    return render(request, 'core/company/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def company_create(request):
    """
    Create new company (HTMX)
    """
    if request.method == 'POST':
        try:
            # Get form data
            code = request.POST.get('code', '').strip()
            name = request.POST.get('name', '').strip()
            timezone = request.POST.get('timezone', 'Asia/Jakarta')
            point_expiry_months = request.POST.get('point_expiry_months', 12)
            points_per_currency = request.POST.get('points_per_currency', 1.00)
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not code or not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Code and Name are required'
                }, status=400)
            
            # Check duplicate code
            if Company.objects.filter(code=code).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Company code "{code}" already exists'
                }, status=400)
            
            # Create company
            company = Company.objects.create(
                code=code,
                name=name,
                timezone=timezone,
                point_expiry_months=int(point_expiry_months),
                points_per_currency=float(points_per_currency),
                is_active=is_active
            )
            
            # Handle logo upload
            if request.FILES.get('logo'):
                company.logo = request.FILES['logo']
                company.save()
            
            messages.success(request, f'Company "{company.name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Company created successfully',
                'redirect': '/company/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return render(request, 'core/company/_form.html')


@login_required
@require_http_methods(["GET", "POST"])
def company_update(request, pk):
    """
    Update existing company (HTMX)
    """
    company = get_object_or_404(Company, pk=pk)
    
    if request.method == 'POST':
        try:
            # Get form data
            code = request.POST.get('code', '').strip()
            name = request.POST.get('name', '').strip()
            timezone = request.POST.get('timezone', 'Asia/Jakarta')
            point_expiry_months = request.POST.get('point_expiry_months', 12)
            points_per_currency = request.POST.get('points_per_currency', 1.00)
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not code or not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Code and Name are required'
                }, status=400)
            
            # Check duplicate code (exclude current)
            if Company.objects.filter(code=code).exclude(pk=pk).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Company code "{code}" already exists'
                }, status=400)
            
            # Update company
            company.code = code
            company.name = name
            company.timezone = timezone
            company.point_expiry_months = int(point_expiry_months)
            company.points_per_currency = float(points_per_currency)
            company.is_active = is_active
            
            # Handle logo upload
            if request.FILES.get('logo'):
                company.logo = request.FILES['logo']
            
            company.save()
            
            messages.success(request, f'Company "{company.name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Company updated successfully',
                'redirect': '/company/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    context = {'company': company}
    return render(request, 'core/company/_form.html', context)


@login_required
@require_http_methods(["POST", "DELETE"])
def company_delete(request, pk):
    """
    Delete company (HTMX)
    """
    company = get_object_or_404(Company, pk=pk)
    
    try:
        company_name = company.name
        company.delete()
        
        messages.success(request, f'Company "{company_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Company deleted successfully',
            'redirect': '/company/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
