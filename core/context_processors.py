from .models import Company, Brand, Store

def global_filters(request):
    if not request.user.is_authenticated:
        return {}

    context = {
        'filter_companies': [],
        'filter_brands': [],
        'filter_stores': [],
        'current_company': getattr(request, 'current_company', None),
        'current_brand': getattr(request, 'current_brand', None),
        'current_store': getattr(request, 'current_store', None),
        'can_filter_company': False,
        'can_filter_brand': False,
        'can_filter_store': False,
    }

    # Logic for Company Dropdown
    if getattr(request.user, 'store', None):
        # User is locked to a store (and thus company)
        context['can_filter_company'] = False
        context['filter_companies'] = [request.user.store.company]
    elif request.user.company:
        # User is locked to a company
        context['can_filter_company'] = False
        context['filter_companies'] = [request.user.company]
    else:
        # Super Admin / No Company Assigned
        context['can_filter_company'] = True
        context['filter_companies'] = Company.objects.filter(is_active=True).order_by('name')

    # Logic for Brand Dropdown
    if getattr(request.user, 'store', None):
        # User is locked to a store (get active brands)
        context['can_filter_brand'] = False
        context['filter_brands'] = list(request.user.store.brands.filter(is_active=True))
    elif request.user.brand:
        # User is locked to a brand
        context['can_filter_brand'] = False
        context['filter_brands'] = [request.user.brand]
    else:
        # Can select brand
        context['can_filter_brand'] = True
        
        # Filter brands based on selected company
        brands_qs = Brand.objects.filter(is_active=True)
        
        current_company = getattr(request, 'current_company', None)
        if current_company:
            brands_qs = brands_qs.filter(company=current_company)
        elif request.user.company:
            brands_qs = brands_qs.filter(company=request.user.company)
            
        context['filter_brands'] = brands_qs.order_by('name')

    # Logic for Store Dropdown
    if getattr(request.user, 'store', None):
        # User is locked to a store
        context['can_filter_store'] = False
        context['filter_stores'] = [request.user.store]
    else:
        # Can select store
        context['can_filter_store'] = True
        
        # Filter stores based on selected brand
        stores_qs = Store.objects.filter(is_active=True)
        
        current_brand = getattr(request, 'current_brand', None)
        if current_brand:
            stores_qs = stores_qs.filter(brands=current_brand)
        elif request.user.brand:
            stores_qs = stores_qs.filter(brands=request.user.brand)
        elif request.user.company:
            stores_qs = stores_qs.filter(company=request.user.company)
            
        context['filter_stores'] = stores_qs.order_by('store_name')

    return context
