"""
Promotion CRUD Views - Ultra Compact
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from promotions.models import Promotion
from core.models import Company, Brand


@login_required
def promotion_list(request):
    """List all promotions with search and company filter"""
    search = request.GET.get('search', '').strip()
    company_id = request.GET.get('company_id', '').strip()
    promo_type = request.GET.get('promo_type', '').strip()
    page = request.GET.get('page', 1)
    
    # Base queryset
    promotions = Promotion.objects.select_related('company', 'brand')
    
    # Apply search
    if search:
        promotions = promotions.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Apply company filter
    if company_id:
        promotions = promotions.filter(company_id=company_id)
    
    # Apply promo type filter
    if promo_type:
        promotions = promotions.filter(promo_type=promo_type)
    
    # Apply ordering
    promotions = promotions.order_by('-start_date', 'name')
    
    # Pagination
    paginator = Paginator(promotions, 10)
    promotions_page = paginator.get_page(page)
    
    # Get companies for filter
    companies = Company.objects.filter(is_active=True).order_by('name')
    
    if request.headers.get('HX-Request'):
        return render(request, 'promotions/promotion/_table.html', {
            'promotions': promotions_page
        })
    
    return render(request, 'promotions/promotion/list.html', {
        'promotions': promotions_page,
        'search': search,
        'company_id': company_id,
        'promo_type': promo_type,
        'companies': companies
    })


@login_required
@require_http_methods(["GET", "POST"])
def promotion_create(request):
    """Create new promotion"""
    if request.method == 'POST':
        try:
            company_id = request.POST.get('company_id', '').strip()
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            description = request.POST.get('description', '').strip()
            promo_type = request.POST.get('promo_type', '').strip()
            discount_percent = request.POST.get('discount_percent', '0')
            discount_amount = request.POST.get('discount_amount', '0')
            min_purchase = request.POST.get('min_purchase', '0')
            max_discount_amount = request.POST.get('max_discount_amount', '') or None
            start_date = request.POST.get('start_date', '').strip()
            end_date = request.POST.get('end_date', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            if not company_id or not name or not code or not promo_type:
                return JsonResponse({
                    'success': False,
                    'message': 'Company, Name, Code and Promotion Type are required'
                }, status=400)
            
            # Check code uniqueness
            if Promotion.objects.filter(code=code).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Code "{code}" already exists'
                }, status=400)
            
            # Create promotion
            promotion = Promotion.objects.create(
                company_id=company_id,
                name=name,
                code=code,
                description=description,
                promo_type=promo_type,
                discount_percent=discount_percent,
                discount_amount=discount_amount,
                min_purchase=min_purchase,
                max_discount_amount=max_discount_amount,
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else None,
                is_active=is_active,
                created_by=request.user
            )
            
            messages.success(request, f'Promotion "{promotion.name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Promotion created successfully',
                'redirect': '/promotions/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    companies = Company.objects.filter(is_active=True).order_by('name')
    return render(request, 'promotions/promotion/_form.html', {
        'companies': companies
    })


@login_required
@require_http_methods(["GET", "POST"])
def promotion_update(request, pk):
    """Update existing promotion"""
    promotion = get_object_or_404(Promotion.objects.select_related('company'), pk=pk)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            description = request.POST.get('description', '').strip()
            promo_type = request.POST.get('promo_type', '').strip()
            discount_percent = request.POST.get('discount_percent', '0')
            discount_amount = request.POST.get('discount_amount', '0')
            min_purchase = request.POST.get('min_purchase', '0')
            max_discount_amount = request.POST.get('max_discount_amount', '') or None
            start_date = request.POST.get('start_date', '').strip()
            end_date = request.POST.get('end_date', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            if not name or not code or not promo_type:
                return JsonResponse({
                    'success': False,
                    'message': 'Name, Code and Promotion Type are required'
                }, status=400)
            
            # Check code uniqueness (exclude current)
            if Promotion.objects.filter(code=code).exclude(pk=pk).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Code "{code}" already exists'
                }, status=400)
            
            # Update promotion
            promotion.name = name
            promotion.code = code
            promotion.description = description
            promotion.promo_type = promo_type
            promotion.discount_percent = discount_percent
            promotion.discount_amount = discount_amount
            promotion.min_purchase = min_purchase
            promotion.max_discount_amount = max_discount_amount
            promotion.start_date = start_date if start_date else None
            promotion.end_date = end_date if end_date else None
            promotion.is_active = is_active
            promotion.save()
            
            messages.success(request, f'Promotion "{promotion.name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Promotion updated successfully',
                'redirect': '/promotions/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    companies = Company.objects.filter(is_active=True).order_by('name')
    return render(request, 'promotions/promotion/_form.html', {
        'promotion': promotion,
        'companies': companies
    })


@login_required
@require_http_methods(["POST", "DELETE"])
def promotion_delete(request, pk):
    """Delete promotion"""
    try:
        promotion = get_object_or_404(Promotion, pk=pk)
        promotion_name = promotion.name
        promotion.delete()
        
        messages.success(request, f'Promotion "{promotion_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Promotion deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
