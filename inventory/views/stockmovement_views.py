"""
Stock Movement Views - Read-only for HO reporting
Data synced from Edge servers
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from inventory.models import StockMovement
from core.models import Store


@login_required
def stockmovement_list(request):
    """List all stock movements (read-only)"""
    search = request.GET.get('search', '').strip()
    store_id = request.GET.get('store_id', '').strip()
    movement_type = request.GET.get('movement_type', '').strip()
    page = request.GET.get('page', 1)
    
    # Base queryset
    movements = StockMovement.objects.select_related(
        'store__brand__company',
        'inventory_item',
        'created_by'
    )
    
    # Apply search
    if search:
        movements = movements.filter(
            Q(reference_no__icontains=search) |
            Q(inventory_item__name__icontains=search) |
            Q(inventory_item__item_code__icontains=search)
        )
    
    # Apply store filter
    if store_id:
        movements = movements.filter(store_id=store_id)
    
    # Apply movement type filter
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    
    # Apply ordering
    movements = movements.order_by('-movement_date', '-created_at')
    
    # Pagination
    paginator = Paginator(movements, 20)
    movements_page = paginator.get_page(page)
    
    # Get stores for filter
    stores = Store.objects.filter(is_active=True).select_related('brand').order_by('store_name')
    
    if request.headers.get('HX-Request'):
        return render(request, 'inventory/stockmovement/_table.html', {
            'movements': movements_page,
            'page_obj': movements_page
        })
    
    return render(request, 'inventory/stockmovement/list.html', {
        'movements': movements_page,
        'page_obj': movements_page,
        'search': search,
        'store_id': store_id,
        'movement_type': movement_type,
        'stores': stores,
        'total_count': movements.count()
    })
