"""
Product CRUD Views - Ultra Compact with Image Upload
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from products.models import Product, ProductPhoto, Category, Modifier, ProductModifier
from core.models import Brand


@login_required
def product_list(request):
    """List all products with search and filter"""
    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '')
    page = request.GET.get('page', 1)
    
    # Base queryset with modifiers
    products = Product.objects.select_related('brand', 'category').prefetch_related(
        'photos',
        'product_modifiers__modifier'
    )
    
    # Apply search
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Apply Global Filters (from Middleware) - Brand filter controlled in header
    current_company = getattr(request, 'current_company', None)
    current_brand = getattr(request, 'current_brand', None)

    if current_brand:
        products = products.filter(brand=current_brand)
    elif current_company:
        products = products.filter(brand__company=current_company)
    
    # Apply category filter (local page filter)
    if category_id:
        products = products.filter(
            Q(category_id=category_id) |
            Q(category__parent_id=category_id)
        )
    
    # Apply ordering
    products = products.order_by('sort_order', 'name')
    
    # Pagination
    paginator = Paginator(products, 10)
    products_page = paginator.get_page(page)
    
    # Get categories for filter (filtered by global brand context)
    categories_qs = Category.objects.filter(is_active=True, parent__isnull=True).select_related('brand')
    
    # Filter categories based on global context
    if current_brand:
        categories_qs = categories_qs.filter(brand=current_brand)
    elif current_company:
        categories_qs = categories_qs.filter(brand__company=current_company)
        
    categories = categories_qs.order_by('brand__name', 'name')
    
    context = {
        'products': products_page,
        'categories': categories,
        'search': search,
        'selected_category': category_id,
        'total_count': products.count()
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'products/product/_table.html', context)
    
    return render(request, 'products/product/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def product_create(request):
    """Create new product with image upload"""
    if request.method == 'POST':
        try:
            brand_id = request.POST.get('brand_id')
            if not brand_id and hasattr(request, 'current_brand') and request.current_brand:
                brand_id = request.current_brand.id
            
            category_id = request.POST.get('category_id')
            sku = request.POST.get('sku', '').strip()
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            price = request.POST.get('price', '0').replace(',', '')
            cost = request.POST.get('cost', '0').replace(',', '')
            printer_target = request.POST.get('printer_target', 'kitchen')
            track_stock = request.POST.get('track_stock') == 'on'
            stock_quantity = request.POST.get('stock_quantity', '0')
            sort_order = request.POST.get('sort_order', '0')
            is_active = request.POST.get('is_active') == 'on'
            
            if not all([brand_id, category_id, sku, name, price]):
                return JsonResponse({
                    'success': False,
                    'message': 'Brand, Category, SKU, Name and Price are required'
                }, status=400)
            
            # Check unique constraint: brand + category + name + sku
            if Product.objects.filter(
                brand_id=brand_id,
                category_id=category_id,
                name=name,
                sku=sku
            ).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Product with this combination already exists'
                }, status=400)
            
            product = Product.objects.create(
                brand_id=brand_id,
                category_id=category_id,
                sku=sku,
                name=name,
                description=description,
                price=float(price.replace(',', '')),
                cost=float(cost.replace(',', '')) if cost else 0,
                printer_target=printer_target,
                track_stock=track_stock,
                stock_quantity=float(stock_quantity.replace(',', '')) if stock_quantity else 0,
                sort_order=int(sort_order) if sort_order else 0,
                is_active=is_active
            )
            
            # Handle image uploads to MinIO
            images = request.FILES.getlist('images')
            if images:
                from core.storage import minio_storage
                for idx, image in enumerate(images):
                    try:
                        # Upload to MinIO
                        result = minio_storage.upload_product_image(
                            file=image,
                            product_id=str(product.id),
                            is_primary=(idx == 0)
                        )
                        
                        # Save metadata to database
                        ProductPhoto.objects.create(
                            product=product,
                            object_key=result['object_key'],
                            filename=result['filename'],
                            size=result['size'],
                            content_type=result['content_type'],
                            checksum=result['checksum'],
                            version=result['version'],
                            is_primary=(idx == 0),
                            sort_order=idx
                        )
                    except Exception as img_error:
                        logger.error(f"Image upload error: {str(img_error)}")
                        # Continue with other images even if one fails
            
            messages.success(request, f'Product "{product.name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Product created successfully',
                'redirect': '/products/'
            })
            
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    # Filter categories by current brand from global filter
    categories_qs = Category.objects.filter(is_active=True).select_related('brand', 'parent')
    
    if hasattr(request, 'current_brand') and request.current_brand:
        categories_qs = categories_qs.filter(brand=request.current_brand)
    
    # Build tree structure: [parent1, child1, child2, parent2, child3, ...]
    parents = categories_qs.filter(parent__isnull=True).order_by('sort_order', 'name')
    category_tree = []
    for parent in parents:
        category_tree.append(parent)
        children = categories_qs.filter(parent=parent).order_by('sort_order', 'name')
        category_tree.extend(children)
    
    return render(request, 'products/product/_form.html', {
        'category_tree': category_tree
    })


import logging
import traceback

logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["GET", "POST"])
def product_update(request, pk):
    """Update existing product"""
    product = get_object_or_404(
        Product.objects.select_related('brand', 'category').prefetch_related('photos'),
        pk=pk
    )
    
    if request.method == 'POST':
        try:
            category_id = request.POST.get('category_id')
            sku = request.POST.get('sku', '').strip()
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            price = request.POST.get('price', '0')
            cost = request.POST.get('cost', '0')
            printer_target = request.POST.get('printer_target', 'kitchen')
            track_stock = request.POST.get('track_stock') == 'on'
            stock_quantity = request.POST.get('stock_quantity', '0')
            sort_order = request.POST.get('sort_order', '0')
            is_active = request.POST.get('is_active') == 'on'
            
            if not all([category_id, sku, name, price]):
                return JsonResponse({
                    'success': False,
                    'message': 'Category, SKU, Name and Price are required'
                }, status=400)
            
            # Check unique constraint: brand + category + name + sku (exclude current product)
            if Product.objects.filter(
                brand=product.brand,
                category_id=category_id,
                name=name,
                sku=sku
            ).exclude(pk=pk).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Product with this combination already exists'
                }, status=400)
            
            product.category_id = category_id
            product.sku = sku
            product.name = name
            product.description = description
            product.price = float(price.replace(',', ''))
            product.cost = float(cost.replace(',', '')) if cost else 0
            product.printer_target = printer_target
            product.track_stock = track_stock
            product.stock_quantity = float(stock_quantity.replace(',', '')) if stock_quantity else 0
            product.sort_order = int(sort_order) if sort_order else 0
            product.is_active = is_active
            product.save()
            
            # Handle image uploads to MinIO (same as create)
            images = request.FILES.getlist('images')
            if images:
                from core.storage import minio_storage
                has_primary = product.photos.filter(is_primary=True).exists()
                
                for idx, image in enumerate(images):
                    try:
                        # Upload to MinIO
                        result = minio_storage.upload_product_image(
                            file=image,
                            product_id=str(product.id),
                            is_primary=(idx == 0 and not has_primary)
                        )
                        
                        # Save metadata to database
                        ProductPhoto.objects.create(
                            product=product,
                            object_key=result['object_key'],
                            filename=result['filename'],
                            size=result['size'],
                            content_type=result['content_type'],
                            checksum=result['checksum'],
                            version=result['version'],
                            is_primary=(idx == 0 and not has_primary),
                            sort_order=product.photos.count() + idx
                        )
                    except Exception as img_error:
                        logger.error(f"Image upload error during edit: {str(img_error)}")
                        # Continue with other images even if one fails
            
            messages.success(request, f'Product "{product.name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Product updated successfully',
                'redirect': '/products/'
            })
            
        except Exception as e:
            logger.error(f"Error updating product: {str(e)}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    brands = Brand.objects.filter(is_active=True).order_by('name')
    categories_qs = Category.objects.filter(brand=product.brand, is_active=True).select_related('parent')
    
    # Build tree structure: [parent1, child1, child2, parent2, child3, ...]
    parents = categories_qs.filter(parent__isnull=True).order_by('sort_order', 'name')
    category_tree = []
    for parent in parents:
        category_tree.append(parent)
        children = categories_qs.filter(parent=parent).order_by('sort_order', 'name')
        category_tree.extend(children)
    
    return render(request, 'products/product/_form.html', {
        'product': product,
        'brands': brands,
        'category_tree': category_tree
    })


@login_required
@require_http_methods(["POST", "DELETE"])
def product_delete(request, pk):
    """Delete product"""
    try:
        product = get_object_or_404(Product, pk=pk)
        product_name = product.name
        product.delete()
        
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Product deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def product_photo_delete(request, pk):
    """Delete product photo"""
    try:
        photo = get_object_or_404(ProductPhoto, pk=pk)
        photo.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Photo deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def product_modifier_assign(request, pk):
    """Assign/unassign modifiers to product"""
    product = get_object_or_404(Product.objects.select_related('brand'), pk=pk)
    
    if request.method == 'POST':
        try:
            modifier_ids = request.POST.getlist('modifier_ids')
            
            # Delete all existing assignments
            ProductModifier.objects.filter(product=product).delete()
            
            # Create new assignments
            for idx, modifier_id in enumerate(modifier_ids):
                ProductModifier.objects.create(
                    product=product,
                    modifier_id=modifier_id,
                    sort_order=idx
                )
            
            return JsonResponse({
                'success': True,
                'message': f'{len(modifier_ids)} modifier(s) assigned successfully'
            })
            
        except Exception as e:
            logger.error(f"Error assigning modifiers: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - show assignment form
    modifiers = Modifier.objects.filter(
        brand=product.brand,
        is_active=True
    ).prefetch_related('options').order_by('name')
    
    assigned_modifier_ids = list(
        product.product_modifiers.values_list('modifier_id', flat=True)
    )
    
    return render(request, 'products/product/_modifier_assign.html', {
        'product': product,
        'modifiers': modifiers,
        'assigned_modifier_ids': assigned_modifier_ids
    })
