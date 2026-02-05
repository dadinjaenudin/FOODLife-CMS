from .models import Company, Brand, Store

class GlobalFilterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 0. Handle Store Scope (Highest Priority Restriction)
            if hasattr(request.user, 'store') and request.user.store:
                # User is tied to a specific store
                # Implicitly tied to that store's company and brands
                request.current_store = request.user.store
                # Get first active brand or None (multi-brand scenario)
                active_brands = request.user.store.brands.filter(is_active=True)
                request.current_brand = active_brands.first() if active_brands.exists() else None
                request.current_company = request.user.store.company
                
                # Force session consistency (optional but good for other apps reading session)
                if str(request.session.get('global_company_id')) != str(request.current_company.id):
                    request.session['global_company_id'] = str(request.current_company.id)
                if request.current_brand and str(request.session.get('global_brand_id')) != str(request.current_brand.id):
                    request.session['global_brand_id'] = str(request.current_brand.id)
                    
            else:
                # User not tied to specific store, check session
                # 1. Determine Company
                company_id = request.session.get('global_company_id')
                
                if request.user.company:
                    # User is tied to a company, force it
                    request.current_company = request.user.company
                    # If session has something else (or nothing), update it to match user's company
                    if company_id != str(request.user.company.id):
                         request.session['global_company_id'] = str(request.user.company.id)
                elif company_id:
                    # User is not tied (Super Admin), use session
                    try:
                        request.current_company = Company.objects.get(id=company_id)
                    except Company.DoesNotExist:
                        request.current_company = None
                        # Clear invalid session
                        del request.session['global_company_id']
                else:
                    # No filter selected - Auto-select first available company
                    available_companies = Company.objects.filter(is_active=True).order_by('name')
                    if available_companies.exists():
                        request.current_company = available_companies.first()
                        request.session['global_company_id'] = str(request.current_company.id)
                    else:
                        request.current_company = None
    
                # 2. Determine Brand
                brand_id = request.session.get('global_brand_id')
                
                if request.user.brand:
                    # User is tied to a brand, force it
                    request.current_brand = request.user.brand
                    if brand_id != str(request.user.brand.id):
                        request.session['global_brand_id'] = str(request.user.brand.id)
                elif brand_id:
                    try:
                        request.current_brand = Brand.objects.get(id=brand_id)
                        # Validate brand belongs to selected company (if company is selected)
                        if request.current_company and request.current_brand.company_id != request.current_company.id:
                            request.current_brand = None
                            del request.session['global_brand_id']
                    except Brand.DoesNotExist:
                        request.current_brand = None
                        del request.session['global_brand_id']
                else:
                    # No filter selected - Auto-select first available brand
                    available_brands = Brand.objects.filter(is_active=True)
                    if request.current_company:
                        available_brands = available_brands.filter(company=request.current_company)
                    elif request.user.company:
                        available_brands = available_brands.filter(company=request.user.company)
                    
                    available_brands = available_brands.order_by('name')
                    if available_brands.exists():
                        request.current_brand = available_brands.first()
                        request.session['global_brand_id'] = str(request.current_brand.id)
                    else:
                        request.current_brand = None
                
                # 3. Determine Store (after brand is determined)
                store_id = request.session.get('global_store_id')
                
                if store_id:
                    try:
                        request.current_store = Store.objects.prefetch_related('brands').get(id=store_id)
                        # Validate store has selected brand (many-to-many)
                        if request.current_brand and not request.current_store.brands.filter(id=request.current_brand.id).exists():
                            request.current_store = None
                            del request.session['global_store_id']
                    except Store.DoesNotExist:
                        request.current_store = None
                        if 'global_store_id' in request.session:
                            del request.session['global_store_id']
                else:
                    # No store selected - Auto-select first available store
                    if request.current_brand:
                        available_stores = Store.objects.filter(is_active=True, brands=request.current_brand).order_by('store_name')
                        if available_stores.exists():
                            request.current_store = available_stores.first()
                            request.session['global_store_id'] = str(request.current_store.id)
                        else:
                            request.current_store = None
                    else:
                        request.current_store = None
        else:
            request.current_company = None
            request.current_brand = None
            request.current_store = None

        response = self.get_response(request)
        return response
