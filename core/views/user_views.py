"""
User Management Views
Ultra compact UI with HTMX + Alpine.js
"""

import logging
import traceback

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import make_password

from core.models import User, Company, Brand, Store

logger = logging.getLogger(__name__)


@login_required
def user_list(request):
    """
    User list with search and pagination (compact UI)
    """
    # Get filters
    search = request.GET.get('search', '')
    
    # Base queryset
    users = User.objects.all().select_related('company', 'store')
    
    # Apply Role/Scope Filters (RBAC)
    if request.user.is_superuser or request.user.role_scope == 'global':
        # Admin / No Scope sees ALL users (no global filter applied)
        # This is for user management purposes
        pass
    elif request.user.role_scope == 'store':
        users = users.filter(store=request.user.store)
    elif request.user.role_scope == 'brand':
        users = users.filter(brand=request.user.brand)
    elif request.user.role_scope == 'company':
        users = users.filter(company=request.user.company)
    # Fallback for any other case (e.g. unknown scope)
    else:
        pass

    # Apply Role Scope Filter (from URL query param, e.g. sidebar links)
    scope_filter = request.GET.get('role_scope')
    if scope_filter in ['company', 'brand', 'store']:
        users = users.filter(role_scope=scope_filter)

    # Apply search filter
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Pagination (10 items per page)
    paginator = Paginator(users.order_by('username'), 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search': search,
        'total_count': users.count(),
    }
    
    # HTMX partial response
    if request.htmx:
        return render(request, 'core/user/_table.html', context)
    
    return render(request, 'core/user/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    """
    Create new user (HTMX)
    """
    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            
            role = request.POST.get('role', 'cashier')
            role_scope = request.POST.get('role_scope', 'store')
            
            company_id = request.POST.get('company_id')
            brand_id = request.POST.get('brand_id')
            store_id = request.POST.get('store_id')
            
            # Validation
            if not username or not password:
                return JsonResponse({
                    'success': False,
                    'message': 'Username and Password are required'
                }, status=200)
            
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Username already exists'
                }, status=200)

            # Validate Scope Requirements
            if role_scope in ['company', 'brand', 'store'] and not company_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Company is required for this role scope'
                }, status=200)
            
            if role_scope in ['brand', 'store'] and not brand_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Brand is required for this role scope'
                }, status=200)
                
            if role_scope == 'store' and not store_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Store is required for this role scope'
                }, status=200)

                
            # RBAC Validation
            if request.user.role_scope == 'company':
                company_id = request.user.company.id
                # Can only create users for own company
            elif request.user.role_scope == 'brand':
                company_id = request.user.company.id
                brand_id = request.user.brand.id
                # Can only create users for own brand
            elif request.user.role_scope == 'store':
                company_id = request.user.company.id
                brand_id = request.user.brand.id
                store_id = request.user.store.id
            
            # Create user
            user = User.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                first_name=first_name,
                last_name=last_name,
                role=role,
                role_scope=role_scope,
                company_id=company_id if company_id else None,
                brand_id=brand_id if brand_id else None,
                store_id=store_id if store_id else None,
                is_active=True
            )
            
            messages.success(request, f'User "{user.username}" created successfully')
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=200)
    
    # GET: Show form
    context = {
        'roles': User.ROLE_CHOICES,
        'role_scopes': User.ROLE_SCOPE_CHOICES,
        'user_obj': None,
        'selected_company_id': '',
    }
    
    # Populate Companies/Brands/Stores based on permissions
    if request.user.is_superuser or request.user.role_scope == 'global':
        # Admin / No Scope
        context['companies'] = Company.objects.filter(is_active=True).order_by('name')
        
        # If company selected in Global Filter, filter brands
        if hasattr(request, 'current_company') and request.current_company:
            context['brands'] = Brand.objects.filter(company=request.current_company, is_active=True).order_by('name')
            context['stores'] = Store.objects.filter(company=request.current_company, is_active=True).order_by('store_name')
            context['selected_company_id'] = request.current_company.id
        else:
            context['brands'] = Brand.objects.filter(is_active=True).order_by('company__name', 'name')
            context['stores'] = Store.objects.filter(is_active=True).order_by('company__name', 'store_name')
            
        # If brand selected in Global Filter, filter stores further
        if hasattr(request, 'current_brand') and request.current_brand:
            context['stores'] = Store.objects.filter(brands=request.current_brand, is_active=True).order_by('store_name')
            
    elif request.user.role_scope == 'company':
        context['companies'] = [request.user.company] if request.user.company else []
        context['brands'] = Brand.objects.filter(company=request.user.company, is_active=True) if request.user.company else []
        context['stores'] = Store.objects.filter(company=request.user.company, is_active=True) if request.user.company else []
        context['selected_company_id'] = request.user.company.id if request.user.company else ''
    elif request.user.role_scope == 'brand':
        context['companies'] = [request.user.company] if request.user.company else []
        context['brands'] = [request.user.brand] if request.user.brand else []
        context['stores'] = Store.objects.filter(brands=request.user.brand, is_active=True) if request.user.brand else []
        context['selected_company_id'] = request.user.company.id if request.user.company else ''
    elif request.user.role_scope == 'store':
        context['companies'] = [request.user.company] if request.user.company else []
        context['brands'] = [request.user.brand] if request.user.brand else []
        context['stores'] = [request.user.store] if request.user.store else []
        context['selected_company_id'] = request.user.company.id if request.user.company else ''
    else:
        # Fallback
        context['companies'] = []
        context['brands'] = []
        context['stores'] = []
            
    return render(request, 'core/user/_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def user_edit(request, pk):
    """
    Edit user (HTMX)
    """
    user = get_object_or_404(User, pk=pk)
    
    # RBAC Check
    if request.user.is_superuser or request.user.role_scope == 'global':
        pass # Allow everything
    elif request.user.role_scope == 'company' and user.company != request.user.company:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    elif request.user.role_scope == 'brand' and user.brand != request.user.brand:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    elif request.user.role_scope == 'store' and user.store != request.user.store:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    if request.method == 'POST':
        try:
            # Update fields
            user.email = request.POST.get('email', '').strip()
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            
            user.role = request.POST.get('role', user.role)
            user.role_scope = request.POST.get('role_scope', user.role_scope)
            
            # Handle password change if provided
            password = request.POST.get('password', '').strip()
            if password:
                user.password = make_password(password)
            
            # Update Company/Brand/Store (if allowed)
            company_id = request.POST.get('company_id')
            brand_id = request.POST.get('brand_id')
            store_id = request.POST.get('store_id')
            
            # Only allow changing company/brand/store if admin or within scope
            if not request.user.role_scope: # Super Admin
                user.company_id = company_id if company_id else None
                user.brand_id = brand_id if brand_id else None
                user.store_id = store_id if store_id else None
            elif request.user.role_scope == 'company':
                # Can only change brand/store within company
                user.brand_id = brand_id if brand_id else None
                user.store_id = store_id if store_id else None
            elif request.user.role_scope == 'brand':
                # Can only change store within brand
                user.store_id = store_id if store_id else None
            
            user.save()
            
            messages.success(request, f'User "{user.username}" updated successfully')
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=200)
            
    # GET: Show form
    context = {
        'user_obj': user, # 'user' is reserved
        'roles': User.ROLE_CHOICES,
        'role_scopes': User.ROLE_SCOPE_CHOICES,
        'selected_company_id': '',
    }
    
    # Populate Companies/Brands/Stores based on permissions
    if request.user.is_superuser or request.user.role_scope == 'global':
        context['companies'] = Company.objects.filter(is_active=True).order_by('name')
        
        # Filter brands/stores by selected company/brand (or user's current filter)
        company_to_filter = user.company or (hasattr(request, 'current_company') and request.current_company)
        brand_to_filter = user.brand or (hasattr(request, 'current_brand') and request.current_brand)
        
        if company_to_filter:
            context['brands'] = Brand.objects.filter(company=company_to_filter, is_active=True).order_by('name')
            context['stores'] = Store.objects.filter(company=company_to_filter, is_active=True).order_by('store_name')
            context['selected_company_id'] = company_to_filter.id
        else:
            context['brands'] = Brand.objects.filter(is_active=True).order_by('company__name', 'name')
            context['stores'] = Store.objects.filter(is_active=True).order_by('company__name', 'store_name')

        if brand_to_filter:
            context['stores'] = Store.objects.filter(brands=brand_to_filter, is_active=True).order_by('store_name')

    elif request.user.role_scope == 'company':
        context['companies'] = [request.user.company] if request.user.company else []
        context['brands'] = Brand.objects.filter(company=request.user.company, is_active=True) if request.user.company else []
        context['stores'] = Store.objects.filter(company=request.user.company, is_active=True) if request.user.company else []
        context['selected_company_id'] = request.user.company.id if request.user.company else ''
    elif request.user.role_scope == 'brand':
        context['companies'] = [request.user.company] if request.user.company else []
        context['brands'] = [request.user.brand] if request.user.brand else []
        context['stores'] = Store.objects.filter(brands=request.user.brand, is_active=True) if request.user.brand else []
        context['selected_company_id'] = request.user.company.id if request.user.company else ''
    elif request.user.role_scope == 'store':
        context['companies'] = [request.user.company] if request.user.company else []
        context['brands'] = [request.user.brand] if request.user.brand else []
        context['stores'] = [request.user.store] if request.user.store else []
        context['selected_company_id'] = request.user.company.id if request.user.company else ''
    else:
        context['companies'] = []
        context['brands'] = []
        context['stores'] = []

    return render(request, 'core/user/_form.html', context)


@login_required
@require_http_methods(["POST"])
def user_delete(request, pk):
    """
    Delete user
    """
    user = get_object_or_404(User, pk=pk)
    
    # Prevent self-deletion
    if user.id == request.user.id:
        return JsonResponse({
            'success': False,
            'message': 'Cannot delete your own account'
        }, status=200)
        
    # RBAC Check
    if request.user.is_superuser or request.user.role_scope == 'global':
        pass # Allow everything
    elif request.user.role_scope == 'company' and user.company != request.user.company:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    elif request.user.role_scope == 'brand' and user.brand != request.user.brand:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    elif request.user.role_scope == 'store' and user.store != request.user.store:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
        
    try:
        user.delete()
        messages.success(request, 'User deleted successfully')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=200)
