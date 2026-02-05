from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from core.models import Company, Brand, Store

@login_required
@require_POST
def set_global_filter(request):
    """
    Update global filter for Company, Brand, and Store.
    Expects POST data: company_id, brand_id, store_id
    
    Auto-fill Logic:
    - When Company is selected (without brand_id) → auto-select first active Brand from that Company
    - When Store is selected → auto-select the Brand and Company from that Store
    - When Brand is explicitly selected → use the selected Brand
    """
    company_id = request.POST.get('company_id')
    brand_id = request.POST.get('brand_id')
    store_id = request.POST.get('store_id')
    
    # Case 1: Store is selected → Auto-fill Brand and Company from Store
    if store_id:
        try:
            store = Store.objects.select_related('company').prefetch_related('brands').get(id=store_id, is_active=True)
            request.session['global_store_id'] = store_id
            request.session['global_brand_id'] = str(store.brand.id)
            request.session['global_company_id'] = str(store.brand.company.id)
        except Store.DoesNotExist:
            pass
    
    # Case 2: Brand is explicitly selected → Use selected Brand
    elif brand_id:
        request.session['global_brand_id'] = brand_id
        
        # Also update company if brand has company relation
        try:
            brand = Brand.objects.select_related('company').get(id=brand_id, is_active=True)
            request.session['global_company_id'] = str(brand.company.id)
        except Brand.DoesNotExist:
            pass
        
        # Clear store selection when brand changes
        request.session.pop('global_store_id', None)
    
    # Case 3: Only Company is selected (without brand_id) → Auto-fill Brand
    elif company_id:
        request.session['global_company_id'] = company_id
        
        # Auto-select first active Brand from this Company only if no brand is currently in POST
        try:
            first_brand = Brand.objects.filter(
                company_id=company_id, 
                is_active=True
            ).order_by('name').first()
            
            if first_brand:
                request.session['global_brand_id'] = str(first_brand.id)
            else:
                # No brands available, clear brand selection
                request.session.pop('global_brand_id', None)
        except Exception:
            pass
        
        # Clear store selection when company changes
        request.session.pop('global_store_id', None)
    
    # If HTMX request, we might want to reload the page or partial
    # For global filter, usually full reload is safest to ensure all data updates
    
    next_url = request.META.get('HTTP_REFERER', '/')
    return redirect(next_url)
