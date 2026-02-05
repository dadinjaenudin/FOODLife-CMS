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
from core.models import Company, Brand, Store
from products.models import Category, Product


@login_required
def promotion_list(request):
    """List all promotions with search and company filter"""
    search = request.GET.get('search', '').strip()
    company_id = request.GET.get('company_id', '').strip()
    promo_type = request.GET.get('promo_type', '').strip()
    page = request.GET.get('page', 1)
    
    # Base queryset
    promotions = Promotion.objects.select_related('company', 'brand').prefetch_related('stores')
    
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
        return render(request, 'promotions/_table.html', {
            'promotions': promotions_page
        })
    
    return render(request, 'promotions/list.html', {
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
            # Get company from global filter (middleware sets request.current_company)
            company_id = None
            if hasattr(request, 'current_company') and request.current_company:
                company_id = request.current_company.id
            elif request.user.company:
                company_id = request.user.company.id
            
            # VALIDATION: Company is REQUIRED
            if not company_id:
                return JsonResponse({
                    'success': False,
                    'message': '⚠️ Company is required! Please select a company from the global filter at the top of the page.'
                }, status=400)
            
            # Get brand from global filter
            brand_id = None
            if hasattr(request, 'current_brand') and request.current_brand:
                brand_id = request.current_brand.id
            elif request.user.brand:
                brand_id = request.user.brand.id
            
            # VALIDATION: Brand is REQUIRED (enforced for data consistency)
            if not brand_id:
                return JsonResponse({
                    'success': False,
                    'message': '⚠️ Brand is required! Please select a brand from the global filter at the top of the page.'
                }, status=400)
            
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            description = request.POST.get('description', '').strip()
            promo_type = request.POST.get('promo_type', '').strip()
            apply_to = request.POST.get('apply_to', 'all').strip()
            category_ids = request.POST.getlist('categories')
            product_ids = request.POST.getlist('products')
            exclude_category_ids = request.POST.getlist('exclude_categories')
            exclude_product_ids = request.POST.getlist('exclude_products')
            
            # Cross-brand fields
            is_cross_brand = request.POST.get('is_cross_brand') == 'on'
            cross_brand_type = request.POST.get('cross_brand_type', '').strip() if is_cross_brand else None
            trigger_brand_ids = request.POST.getlist('trigger_brands') if is_cross_brand else []
            benefit_brand_ids = request.POST.getlist('benefit_brands') if is_cross_brand else []
            trigger_min_amount = request.POST.get('trigger_min_amount', '').strip().replace(',', '') or None
            
            # DEBUG: Log RAW POST data FIRST
            print("=" * 80)
            print("DEBUG CREATE - RAW POST DATA:")
            print(f"  discount_percent (raw): '{request.POST.get('discount_percent')}'")
            print(f"  discount_amount (raw): '{request.POST.get('discount_amount')}'")
            print(f"  min_purchase (raw): '{request.POST.get('min_purchase')}'")
            print(f"  max_discount_amount (raw): '{request.POST.get('max_discount_amount')}'")
            print("=" * 80)
            
            # Handle decimal fields - convert empty to 0, remove commas
            discount_percent = request.POST.get('discount_percent', '').strip().replace(',', '') or '0'
            discount_amount = request.POST.get('discount_amount', '').strip().replace(',', '') or '0'
            min_purchase = request.POST.get('min_purchase', '').strip().replace(',', '') or '0'
            max_discount_amount = request.POST.get('max_discount_amount', '').strip().replace(',', '') or None
            
            # DEBUG: Log processed values
            print("DEBUG CREATE - AFTER PROCESSING:")
            print(f"  discount_percent: {discount_percent}")
            print(f"  discount_amount: {discount_amount}")
            print(f"  min_purchase: {min_purchase}")
            print(f"  max_discount_amount: {max_discount_amount}")
            print("=" * 80)
            
            start_date = request.POST.get('start_date', '').strip()
            end_date = request.POST.get('end_date', '').strip()
            valid_time_start = request.POST.get('valid_time_start', '').strip() or None
            valid_time_end = request.POST.get('valid_time_end', '').strip() or None
            is_active = request.POST.get('is_active') == 'on'
            all_stores = request.POST.get('all_stores') == 'on'
            store_ids = request.POST.getlist('stores')
            
            if not name or not code or not promo_type:
                return JsonResponse({
                    'success': False,
                    'message': 'Name, Code and Promotion Type are required'
                }, status=400)
            
            # Check code uniqueness
            if Promotion.objects.filter(code=code).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Code "{code}" already exists'
                }, status=400)
            
            # Validate store selection
            if not all_stores and not store_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'Please select at least one store or check "Apply to All Stores"'
                }, status=400)
            
            # Get BOGO fields
            buy_quantity = 0
            get_quantity = 0
            if promo_type == 'buy_x_get_y':
                buy_quantity = request.POST.get('buy_quantity', 0)
                get_quantity = request.POST.get('get_quantity', 0)
                try:
                    buy_quantity = int(buy_quantity)
                    get_quantity = int(get_quantity)
                    if buy_quantity < 1 or get_quantity < 1:
                        return JsonResponse({
                            'success': False,
                            'message': 'Buy Quantity and Get Quantity must be at least 1 for BOGO promotion'
                        }, status=400)
                except (ValueError, TypeError):
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid Buy Quantity or Get Quantity'
                    }, status=400)
            
            # Get min_quantity and min_items (general fields)
            min_quantity = request.POST.get('min_quantity', '').strip() or '0'
            min_items = request.POST.get('min_items', '').strip() or '0'
            
            # Get usage limits and priority
            max_uses = request.POST.get('max_uses', '').strip() or None
            max_uses_per_customer = request.POST.get('max_uses_per_customer', '').strip() or None
            max_uses_per_day = request.POST.get('max_uses_per_day', '').strip() or None
            priority = request.POST.get('priority', '').strip() or '100'
            
            # Get execution settings (NEW)
            execution_stage = request.POST.get('execution_stage', 'item_level').strip()
            execution_priority = request.POST.get('execution_priority', '500').strip()
            is_auto_apply = request.POST.get('is_auto_apply') == 'on'
            
            # Create promotion
            promotion = Promotion.objects.create(
                company_id=company_id,
                brand_id=brand_id,  # Set brand from global filter
                name=name,
                code=code,
                description=description,
                promo_type=promo_type,
                apply_to=apply_to,
                discount_percent=discount_percent,
                discount_amount=discount_amount,
                min_purchase=min_purchase,
                max_discount_amount=max_discount_amount,
                buy_quantity=buy_quantity,  # BOGO
                get_quantity=get_quantity,  # BOGO
                min_quantity=min_quantity,  # General qty requirement
                min_items=min_items,  # General items requirement
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else None,
                valid_time_start=valid_time_start,
                valid_time_end=valid_time_end,
                is_active=is_active,
                is_auto_apply=is_auto_apply,  # NEW
                all_stores=all_stores,
                max_uses=max_uses,
                max_uses_per_customer=max_uses_per_customer,
                max_uses_per_day=max_uses_per_day,
                priority=priority,
                execution_stage=execution_stage,  # NEW
                execution_priority=execution_priority,  # NEW
                is_cross_brand=is_cross_brand,
                cross_brand_type=cross_brand_type,
                trigger_min_amount=trigger_min_amount if trigger_min_amount else None,
                created_by=request.user
            )
            
            # Add selected stores
            if not all_stores and store_ids:
                promotion.stores.set(store_ids)
            
            # Add selected categories
            if apply_to == 'category' and category_ids:
                promotion.categories.set(category_ids)
            
            # Add selected products
            if apply_to == 'product' and product_ids:
                promotion.products.set(product_ids)
            
            # Add excluded categories
            if exclude_category_ids:
                promotion.exclude_categories.set(exclude_category_ids)
            
            # Add excluded products
            if exclude_product_ids:
                promotion.exclude_products.set(exclude_product_ids)
            
            # Add cross-brand trigger brands
            if is_cross_brand and trigger_brand_ids:
                promotion.trigger_brands.set(trigger_brand_ids)
            
            # Add cross-brand benefit brands
            if is_cross_brand and benefit_brand_ids:
                promotion.benefit_brands.set(benefit_brand_ids)
            
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
    
    # Get stores based on global filter context
    # Note: Promotions apply at brand level, so show ALL stores in the brand (not filtered by current_store)
    stores = Store.objects.filter(is_active=True).select_related('company').prefetch_related('brands')
    
    # Filter stores based on user's global filter (company and brand only, NOT store)
    if hasattr(request, 'current_company') and request.current_company:
        stores = stores.filter(company=request.current_company)
    if hasattr(request, 'current_brand') and request.current_brand:
        stores = stores.filter(brands=request.current_brand)
    # DO NOT filter by current_store - promotions apply to all stores in the brand
    
    stores = stores.order_by('company__name', 'store_name')
    
    # Get categories and products based on global filter
    categories = Category.objects.filter(is_active=True).select_related('brand').prefetch_related('products')
    products = Product.objects.filter(is_active=True).select_related('category', 'brand')
    
    # Filter by brand (Category only has brand, not company)
    if hasattr(request, 'current_brand') and request.current_brand:
        categories = categories.filter(brand=request.current_brand)
        products = products.filter(brand=request.current_brand)
    elif hasattr(request, 'current_company') and request.current_company:
        # If no brand filter, filter by company through brand relationship
        categories = categories.filter(brand__company=request.current_company)
        products = products.filter(company=request.current_company)
    
    categories = categories.distinct().order_by('brand__name', 'name')
    products = products.distinct().order_by('brand__name', 'category__name', 'name')
    
    # Get all brands in current company for cross-brand promotion
    company_brands = []
    if hasattr(request, 'current_company') and request.current_company:
        from core.models import Brand
        company_brands = Brand.objects.filter(
            company=request.current_company,
            is_active=True
        ).order_by('name')
    
    return render(request, 'promotions/create.html', {
        'companies': companies,
        'stores': stores,
        'categories': categories,
        'products': products,
        'company_brands': company_brands
    })


@login_required
@require_http_methods(["GET", "POST"])
def promotion_update(request, pk):
    """Update existing promotion"""
    promotion = get_object_or_404(Promotion.objects.select_related('company'), pk=pk)
    
    if request.method == 'POST':
        try:
            # VALIDATION: Ensure promotion still belongs to a valid company and brand
            if not promotion.company_id:
                return JsonResponse({
                    'success': False,
                    'message': '⚠️ This promotion has no company assigned. Cannot update. Please contact administrator.'
                }, status=400)
            
            if not promotion.brand_id:
                return JsonResponse({
                    'success': False,
                    'message': '⚠️ This promotion has no brand assigned. Cannot update. Please contact administrator.'
                }, status=400)
            
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            description = request.POST.get('description', '').strip()
            promo_type = request.POST.get('promo_type', '').strip()
            apply_to = request.POST.get('apply_to', 'all').strip()
            category_ids = request.POST.getlist('categories')
            product_ids = request.POST.getlist('products')
            exclude_category_ids = request.POST.getlist('exclude_categories')
            exclude_product_ids = request.POST.getlist('exclude_products')
            
            # Cross-brand fields
            is_cross_brand = request.POST.get('is_cross_brand') == 'on'
            cross_brand_type = request.POST.get('cross_brand_type', '').strip() if is_cross_brand else None
            trigger_brand_ids = request.POST.getlist('trigger_brands') if is_cross_brand else []
            benefit_brand_ids = request.POST.getlist('benefit_brands') if is_cross_brand else []
            trigger_min_amount = request.POST.get('trigger_min_amount', '').strip().replace(',', '') or None
            
            # Handle decimal fields - convert empty to 0, remove commas
            discount_percent = request.POST.get('discount_percent', '').strip().replace(',', '') or '0'
            discount_amount = request.POST.get('discount_amount', '').strip().replace(',', '') or '0'
            min_purchase = request.POST.get('min_purchase', '').strip().replace(',', '') or '0'
            max_discount_amount = request.POST.get('max_discount_amount', '').strip().replace(',', '') or None
            
            # DEBUG: Log decimal values
            print(f"DEBUG UPDATE - discount_percent: {discount_percent}")
            print(f"DEBUG UPDATE - discount_amount: {discount_amount}")
            print(f"DEBUG UPDATE - min_purchase: {min_purchase}")
            print(f"DEBUG UPDATE - max_discount_amount: {max_discount_amount}")
            
            start_date = request.POST.get('start_date', '').strip()
            end_date = request.POST.get('end_date', '').strip()
            valid_time_start = request.POST.get('valid_time_start', '').strip() or None
            valid_time_end = request.POST.get('valid_time_end', '').strip() or None
            is_active = request.POST.get('is_active') == 'on'
            all_stores = request.POST.get('all_stores') == 'on'
            store_ids = request.POST.getlist('stores')
            
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
            
            # Validate store selection
            if not all_stores and not store_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'Please select at least one store or check "Apply to All Stores"'
                }, status=400)
            
            # Get BOGO fields
            buy_quantity = 0
            get_quantity = 0
            if promo_type == 'buy_x_get_y':
                buy_quantity = request.POST.get('buy_quantity', 0)
                get_quantity = request.POST.get('get_quantity', 0)
                try:
                    buy_quantity = int(buy_quantity)
                    get_quantity = int(get_quantity)
                    if buy_quantity < 1 or get_quantity < 1:
                        return JsonResponse({
                            'success': False,
                            'message': 'Buy Quantity and Get Quantity must be at least 1 for BOGO promotion'
                        }, status=400)
                except (ValueError, TypeError):
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid Buy Quantity or Get Quantity'
                    }, status=400)
            
            # Get min_quantity and min_items (general fields)
            min_quantity = request.POST.get('min_quantity', '').strip() or '0'
            min_items = request.POST.get('min_items', '').strip() or '0'
            
            # Get usage limits and priority
            max_uses = request.POST.get('max_uses', '').strip() or None
            max_uses_per_customer = request.POST.get('max_uses_per_customer', '').strip() or None
            max_uses_per_day = request.POST.get('max_uses_per_day', '').strip() or None
            priority = request.POST.get('priority', '').strip() or '100'
            
            # Get execution settings (NEW)
            execution_stage = request.POST.get('execution_stage', 'item_level').strip()
            execution_priority = request.POST.get('execution_priority', '500').strip()
            is_auto_apply = request.POST.get('is_auto_apply') == 'on'

            # Update promotion
            promotion.name = name
            promotion.code = code
            promotion.description = description
            promotion.promo_type = promo_type
            promotion.apply_to = apply_to
            promotion.discount_percent = discount_percent
            promotion.discount_amount = discount_amount
            promotion.min_purchase = min_purchase
            promotion.max_discount_amount = max_discount_amount
            promotion.buy_quantity = buy_quantity  # BOGO
            promotion.get_quantity = get_quantity  # BOGO
            promotion.min_quantity = min_quantity  # General qty requirement
            promotion.min_items = min_items  # General items requirement
            promotion.start_date = start_date if start_date else None
            promotion.end_date = end_date if end_date else None
            promotion.valid_time_start = valid_time_start
            promotion.valid_time_end = valid_time_end
            promotion.is_active = is_active
            promotion.is_auto_apply = is_auto_apply  # NEW
            promotion.all_stores = all_stores
            promotion.max_uses = max_uses
            promotion.max_uses_per_customer = max_uses_per_customer
            promotion.max_uses_per_day = max_uses_per_day
            promotion.priority = priority
            promotion.execution_stage = execution_stage  # NEW
            promotion.execution_priority = execution_priority  # NEW
            promotion.is_cross_brand = is_cross_brand
            promotion.cross_brand_type = cross_brand_type
            promotion.trigger_min_amount = trigger_min_amount if trigger_min_amount else None
            promotion.save()
            
            # Update selected stores
            if not all_stores and store_ids:
                promotion.stores.set(store_ids)
            else:
                promotion.stores.clear()
            
            # Update selected categories
            if apply_to == 'category':
                if category_ids:
                    promotion.categories.set(category_ids)
                # Don't clear if no category_ids - user might have global filter that hides them
                # Only clear when explicitly changing apply_to to something else
            elif apply_to != 'category':
                # Clear categories only when apply_to is NOT category
                promotion.categories.clear()
            
            # Update selected products
            if apply_to == 'product':
                if product_ids:
                    promotion.products.set(product_ids)
                # Don't clear if no product_ids - user might have global filter that hides them
            elif apply_to != 'product':
                # Clear products only when apply_to is NOT product
                promotion.products.clear()
            
            # Update excluded categories
            if exclude_category_ids:
                promotion.exclude_categories.set(exclude_category_ids)
            else:
                promotion.exclude_categories.clear()
            
            # Update excluded products
            if exclude_product_ids:
                promotion.exclude_products.set(exclude_product_ids)
            else:
                promotion.exclude_products.clear()
            
            # Update cross-brand trigger brands
            if is_cross_brand and trigger_brand_ids:
                promotion.trigger_brands.set(trigger_brand_ids)
            else:
                promotion.trigger_brands.clear()
            
            # Update cross-brand benefit brands
            if is_cross_brand and benefit_brand_ids:
                promotion.benefit_brands.set(benefit_brand_ids)
            else:
                promotion.benefit_brands.clear()
            
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
    
    # Get stores based on promotion's company/brand
    stores = Store.objects.filter(
        is_active=True,
        company=promotion.company
    ).select_related('company').prefetch_related('brands').order_by('company__name', 'store_name')
    
    # Get categories and products based on promotion's company/brand
    # Note: Category only has brand field, not company
    # IMPORTANT: Respect global filter - if user has brand filter, only show that brand's categories
    categories = Category.objects.filter(is_active=True).select_related('brand').prefetch_related('products')
    products = Product.objects.filter(is_active=True).select_related('category', 'brand')
    
    # Filter by user's current brand filter (from global filter middleware)
    if hasattr(request, 'current_brand') and request.current_brand:
        categories = categories.filter(brand=request.current_brand)
        products = products.filter(brand=request.current_brand)
    elif hasattr(request, 'current_company') and request.current_company:
        # If no brand filter, show all brands within the company
        categories = categories.filter(brand__company=request.current_company)
        products = products.filter(company=request.current_company)
    else:
        # Fallback: use promotion's company
        categories = categories.filter(brand__company=promotion.company)
        products = products.filter(company=promotion.company)
    
    categories = categories.distinct().order_by('brand__name', 'name')
    products = products.distinct().order_by('brand__name', 'category__name', 'name')
    
    # Get all brands in promotion's company for cross-brand promotion
    from core.models import Brand
    company_brands = Brand.objects.filter(
        company=promotion.company,
        is_active=True
    ).order_by('name')
    
    return render(request, 'promotions/edit.html', {
        'promotion': promotion,
        'companies': companies,
        'stores': stores,
        'categories': categories,
        'products': products,
        'company_brands': company_brands
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
