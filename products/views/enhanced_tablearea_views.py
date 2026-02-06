"""
Enhanced Table Area Views - Restaurant Operations Focused
Provides enhanced visualization and management for F&B operations
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from products.models import TableArea, Tables
from core.models import Brand, Store


@login_required
def enhanced_tablearea_list(request):
    """Enhanced table area list with operational insights"""
    search = request.GET.get('search', '').strip()
    brand_id = request.GET.get('brand', '')
    status_filter = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    # Base queryset with related data
    tableareas = TableArea.objects.select_related('brand', 'store', 'brand__company').prefetch_related('tables')
    
    # Apply global filters from middleware first
    if hasattr(request, 'current_company') and request.current_company:
        tableareas = tableareas.filter(company=request.current_company)
    
    if hasattr(request, 'current_brand') and request.current_brand:
        tableareas = tableareas.filter(brand=request.current_brand)
    
    if hasattr(request, 'current_store') and request.current_store:
        tableareas = tableareas.filter(store=request.current_store)
    
    # Apply search
    if search:
        tableareas = tableareas.filter(
            Q(name__icontains=search) |
            Q(brand__name__icontains=search) |
            Q(store__store_name__icontains=search) |
            Q(brand__company__name__icontains=search)
        )
    
    # Apply URL parameter filters (can override if needed)
    if brand_id:
        tableareas = tableareas.filter(brand_id=brand_id)
    
    store_id = request.GET.get('store', '')
    if store_id:
        tableareas = tableareas.filter(store_id=store_id)
    
    # Apply area type filter
    area_type = request.GET.get('area_type', '')
    if area_type == 'store_specific':
        tableareas = tableareas.filter(store__isnull=False)
    elif area_type == 'brand_wide':
        tableareas = tableareas.filter(store__isnull=True)
    
    # Apply status filter
    if status_filter == 'active':
        tableareas = tableareas.filter(is_active=True)
    elif status_filter == 'inactive':
        tableareas = tableareas.filter(is_active=False)
    
    # Apply ordering
    tableareas = tableareas.order_by('sort_order', 'name')
    
    # Add annotations for table counts and capacity
    tableareas = tableareas.annotate(
        table_count=Count('tables', filter=Q(tables__is_active=True)),
        total_capacity=Sum('tables__capacity', filter=Q(tables__is_active=True))
    )
    
    # Pagination
    paginator = Paginator(tableareas, 12)  # Show more items for grid view
    tableareas_page = paginator.get_page(page)
    
    # Get brands for filter
    brands = Brand.objects.filter(is_active=True).order_by('name')
    
    # Calculate overall stats
    total_areas = TableArea.objects.count()
    active_areas = TableArea.objects.filter(is_active=True).count()
    total_tables = Tables.objects.filter(is_active=True).count()
    total_capacity = Tables.objects.filter(is_active=True).aggregate(
        total=Sum('capacity')
    )['total'] or 0
    
    # Get brands and stores for filter
    brands = Brand.objects.filter(is_active=True).order_by('name')
    stores = Store.objects.filter(is_active=True).select_related('company').prefetch_related('brands').order_by('company__name', 'store_name')
    
    context = {
        'tableareas': tableareas_page,
        'brands': brands,
        'stores': stores,
        'search': search,
        'selected_brand': brand_id,
        'selected_store': store_id,
        'area_type': area_type,
        'status_filter': status_filter,
        'stats': {
            'total_areas': total_areas,
            'active_areas': active_areas,
            'total_tables': total_tables,
            'total_capacity': total_capacity,
        }
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'products/tablearea/enhanced_list.html', context)
    
    return render(request, 'products/tablearea/enhanced_list.html', context)


@login_required
def tablearea_dashboard(request):
    """Table area dashboard with real-time insights"""
    brand_id = request.GET.get('brand', '')
    
    # Base queryset
    areas = TableArea.objects.select_related('brand', 'brand__company', 'store').prefetch_related('tables', 'store__brands')
    
    if brand_id:
        areas = areas.filter(brand_id=brand_id)
    
    # Calculate metrics per area
    area_metrics = []
    for area in areas:
        tables = area.tables.filter(is_active=True)
        
        # In real implementation, these would come from actual table status
        available_tables = tables.filter(status='available').count()
        occupied_tables = tables.filter(status='occupied').count()
        reserved_tables = tables.filter(status='reserved').count()
        total_capacity = tables.aggregate(total=Sum('capacity'))['total'] or 0
        
        occupancy_rate = (occupied_tables / tables.count() * 100) if tables.count() > 0 else 0
        
        area_metrics.append({
            'area': area,
            'table_count': tables.count(),
            'available_tables': available_tables,
            'occupied_tables': occupied_tables,
            'reserved_tables': reserved_tables,
            'total_capacity': total_capacity,
            'occupancy_rate': round(occupancy_rate, 1),
            'tables': tables
        })
    
    # Get brands for filter
    brands = Brand.objects.filter(is_active=True).order_by('name')
    
    # Overall metrics
    total_tables = sum(metric['table_count'] for metric in area_metrics)
    total_occupied = sum(metric['occupied_tables'] for metric in area_metrics)
    overall_occupancy = (total_occupied / total_tables * 100) if total_tables > 0 else 0
    
    context = {
        'area_metrics': area_metrics,
        'brands': brands,
        'selected_brand': brand_id,
        'overall_stats': {
            'total_areas': len(area_metrics),
            'total_tables': total_tables,
            'total_occupied': total_occupied,
            'overall_occupancy': round(overall_occupancy, 1),
            'total_capacity': sum(metric['total_capacity'] for metric in area_metrics),
        }
    }
    
    return render(request, 'products/tablearea/dashboard.html', context)


@login_required
def floor_plan_overview(request):
    """Floor plan overview for POS - shows all areas in one screen"""
    store_id = request.GET.get('store', '')
    brand_id = request.GET.get('brand', '')
    search = request.GET.get('search', '').strip()
    
    # Base queryset with all related data
    tableareas = TableArea.objects.select_related(
        'brand', 'store', 'brand__company'
    ).prefetch_related('tables', 'store__brands').filter(is_active=True)
    
    # Apply global filters from middleware first
    if hasattr(request, 'current_company') and request.current_company:
        tableareas = tableareas.filter(company=request.current_company)
    
    if hasattr(request, 'current_brand') and request.current_brand:
        tableareas = tableareas.filter(brand=request.current_brand)
    
    if hasattr(request, 'current_store') and request.current_store:
        tableareas = tableareas.filter(store=request.current_store)
    
    # Apply search filter
    if search:
        tableareas = tableareas.filter(
            Q(name__icontains=search) |
            Q(brand__name__icontains=search) |
            Q(store__store_name__icontains=search) |
            Q(brand__company__name__icontains=search)
        )
    
    # Apply URL parameter filters (can override global filters if needed)
    if store_id:
        tableareas = tableareas.filter(store_id=store_id)
    elif brand_id:
        tableareas = tableareas.filter(brand_id=brand_id)
    
    # Order by store and sort order
    tableareas = tableareas.order_by('store__store_name', 'sort_order', 'name')
    
    # Add table counts and status info for each area
    enhanced_areas = []
    for area in tableareas:
        tables = area.tables.filter(is_active=True)
        
        # Count tables by status
        available_count = tables.filter(status='available').count()
        occupied_count = tables.filter(status='occupied').count() 
        reserved_count = tables.filter(status='reserved').count()
        total_capacity = tables.aggregate(total=Sum('capacity'))['total'] or 0
        
        # Add counts to area object
        area.table_count = tables.count()
        area.available_count = available_count
        area.occupied_count = occupied_count
        area.reserved_count = reserved_count
        area.total_capacity = total_capacity
        
        # IMPORTANT: Pass filtered tables to template
        area.active_tables = list(tables)
        
        enhanced_areas.append(area)
    
    # Calculate overall stats
    total_areas = len(enhanced_areas)
    active_areas = total_areas  # Since we filter by is_active=True
    total_tables = sum(area.table_count for area in enhanced_areas)
    total_capacity = sum(area.total_capacity for area in enhanced_areas)
    
    # Get stores for filter
    from core.models import Store
    stores = Store.objects.filter(is_active=True).select_related('company').prefetch_related('brands').order_by('company__name', 'store_name')
    
    context = {
        'tableareas': enhanced_areas,
        'stores': stores,
        'selected_store': store_id,
        'selected_brand': brand_id,
        'stats': {
            'total_areas': total_areas,
            'active_areas': active_areas,
            'total_tables': total_tables,
            'total_capacity': total_capacity,
        }
    }
    
    return render(request, 'products/tablearea/floor_plan.html', context)


@login_required
@require_http_methods(["GET"])
def area_table_layout(request, area_id):
    """Get table layout for a specific area (for floor plan view)"""
    area = get_object_or_404(TableArea.objects.select_related('brand'), pk=area_id)
    tables = area.tables.filter(is_active=True).order_by('number')
    
    # Group tables by position if available, otherwise create a simple grid
    layout_data = []
    for table in tables:
        layout_data.append({
            'id': str(table.id),
            'number': table.number,
            'capacity': table.capacity,
            'status': table.status,
            'pos_x': table.pos_x or 0,
            'pos_y': table.pos_y or 0,
            'shape': table.shape,
            'qr_code': table.qr_code
        })
    
    return JsonResponse({
        'area': {
            'id': str(area.id),
            'name': area.name,
            'brand': area.brand.name
        },
        'tables': layout_data
    })


@login_required
@require_http_methods(["POST"])
def update_table_status(request):
    """Update table status (for real-time updates from Edge)"""
    table_id = request.POST.get('table_id')
    status = request.POST.get('status')
    
    if not table_id or status not in ['available', 'occupied', 'reserved']:
        return JsonResponse({
            'success': False,
            'message': 'Invalid table ID or status'
        }, status=400)
    
    try:
        table = get_object_or_404(Tables, pk=table_id)
        table.status = status
        table.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Table {table.number} status updated to {status}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def create_table(request):
    """Create a new table in a table area"""
    import json
    
    try:
        data = json.loads(request.body)
        area_id = data.get('area_id')
        number = data.get('number', '').strip()
        capacity = data.get('capacity')
        pos_x = data.get('pos_x', 0)
        pos_y = data.get('pos_y', 0)
        shape = data.get('shape', 'square')
        status = data.get('status', 'available')
        is_active = data.get('is_active', True)
        
        if not area_id or not number:
            return JsonResponse({
                'success': False,
                'message': 'Area ID and table number are required'
            }, status=400)
        
        if not capacity or capacity < 1:
            return JsonResponse({
                'success': False,
                'message': 'Valid capacity is required'
            }, status=400)
        
        # Get table area
        area = get_object_or_404(TableArea, pk=area_id)
        
        # Check for duplicate table number in this area
        if Tables.objects.filter(area=area, number=number).exists():
            return JsonResponse({
                'success': False,
                'message': f'Table {number} already exists in this area'
            }, status=400)
        
        # Create table
        table = Tables.objects.create(
            area=area,
            number=number,
            capacity=capacity,
            pos_x=pos_x,
            pos_y=pos_y,
            shape=shape,
            status=status,
            is_active=is_active,
            qr_code=f'QR-{area.store.store_name if area.store else area.brand.name}-{area.name}-{number}'
        )
        
        response = JsonResponse({
            'success': True,
            'message': f'Table {number} created successfully',
            'table': {
                'id': str(table.id),
                'number': table.number,
                'capacity': table.capacity,
                'pos_x': table.pos_x,
                'pos_y': table.pos_y,
                'status': table.status,
                'shape': table.shape,
                'qr_code': table.qr_code
            },
            'reload': False  # Keep modal open for adding more tables
        })
        
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_table(request):
    """Update an existing table"""
    import json
    
    try:
        data = json.loads(request.body)
        table_id = data.get('table_id')
        number = data.get('number', '').strip()
        capacity = data.get('capacity')
        pos_x = data.get('pos_x', 0)
        pos_y = data.get('pos_y', 0)
        shape = data.get('shape', 'square')
        
        if not table_id or not number:
            return JsonResponse({
                'success': False,
                'message': 'Table ID and table number are required'
            }, status=400)
        
        # Convert capacity to integer and validate
        try:
            capacity = int(capacity) if capacity is not None else None
            if not capacity or capacity < 1:
                return JsonResponse({
                    'success': False,
                    'message': 'Valid capacity (minimum 1) is required'
                }, status=400)
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': 'Capacity must be a valid number'
            }, status=400)
        
        # Convert position values to int
        try:
            pos_x = int(float(pos_x)) if pos_x is not None else 0
            pos_y = int(float(pos_y)) if pos_y is not None else 0
        except (ValueError, TypeError):
            pos_x = 0
            pos_y = 0

        # Validate shape
        valid_shapes = {choice[0] for choice in Tables.SHAPE_CHOICES}
        if shape not in valid_shapes:
            return JsonResponse({
                'success': False,
                'message': 'Invalid table shape'
            }, status=400)
        
        # Get table
        table = get_object_or_404(Tables, pk=table_id)
        
        # Check for duplicate table number in this area (excluding current table)
        duplicate = Tables.objects.filter(
            area=table.area, 
            number=number
        ).exclude(pk=table_id)
        
        if duplicate.exists():
            return JsonResponse({
                'success': False,
                'message': f'Table {number} already exists in this area'
            }, status=400)
        
        # Update table
        table.number = number
        table.capacity = capacity
        table.pos_x = pos_x
        table.pos_y = pos_y
        table.shape = shape
        table.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Table {number} updated successfully',
            'table': {
                'id': str(table.id),
                'number': table.number,
                'capacity': table.capacity,
                'pos_x': table.pos_x,
                'pos_y': table.pos_y,
                'shape': table.shape,
                'status': table.status,
                'qr_code': table.qr_code
            },
            'reload': False  # Keep modal open, avoid full reload
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def delete_table(request):
    """Delete a table"""
    import json
    
    try:
        data = json.loads(request.body)
        table_id = data.get('table_id')
        
        if not table_id:
            return JsonResponse({
                'success': False,
                'message': 'Table ID is required'
            }, status=400)
        
        # Get table
        table = get_object_or_404(Tables, pk=table_id)
        table_number = table.number  # Store for response message
        
        # Delete table
        table.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Table {table_number} deleted successfully',
            'reload': True  # Tell frontend to reload page
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)