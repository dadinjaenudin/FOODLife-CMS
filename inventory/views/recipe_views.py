"""
Recipe (BOM) CRUD Views - Ultra Compact
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from inventory.models import Recipe
from core.models import Brand
from products.models import Product
from datetime import date


@login_required
def recipe_list(request):
    """List all recipes with search and brand filter"""
    search = request.GET.get('search', '').strip()
    brand_id = request.GET.get('brand_id', '').strip()
    page = request.GET.get('page', 1)
    
    # Base queryset
    recipes = Recipe.objects.select_related('brand__company', 'product')
    
    # Apply search
    if search:
        recipes = recipes.filter(
            Q(recipe_name__icontains=search) |
            Q(recipe_code__icontains=search) |
            Q(product__name__icontains=search)
        )
    
    # Apply brand filter
    if brand_id:
        recipes = recipes.filter(brand_id=brand_id)
    
    # Apply ordering
    recipes = recipes.order_by('-version', 'recipe_name')
    
    # Pagination
    paginator = Paginator(recipes, 10)
    recipes_page = paginator.get_page(page)
    
    # Get brands for filter
    brands = Brand.objects.filter(is_active=True).select_related('company').order_by('name')
    
    if request.headers.get('HX-Request'):
        return render(request, 'inventory/recipe/_table.html', {
            'recipes': recipes_page,
            'page_obj': recipes_page
        })
    
    return render(request, 'inventory/recipe/list.html', {
        'recipes': recipes_page,
        'page_obj': recipes_page,
        'search': search,
        'brand_id': brand_id,
        'brands': brands,
        'total_count': recipes.count()
    })


@login_required
@require_http_methods(["GET", "POST"])
def recipe_create(request):
    """Create new recipe"""
    if request.method == 'POST':
        try:
            brand_id = request.POST.get('brand_id', '').strip()
            product_id = request.POST.get('product_id', '').strip()
            recipe_code = request.POST.get('recipe_code', '').strip()
            recipe_name = request.POST.get('recipe_name', '').strip()
            version = request.POST.get('version', '1')
            yield_quantity = request.POST.get('yield_quantity', '1')
            yield_unit = request.POST.get('yield_unit', '').strip()
            preparation_type = request.POST.get('preparation_type', '').strip()
            effective_date = request.POST.get('effective_date', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            if not brand_id or not product_id or not recipe_code or not recipe_name or not yield_unit or not preparation_type:
                return JsonResponse({
                    'success': False,
                    'message': 'Brand, Product, Code, Name, Yield Unit and Preparation Type are required'
                }, status=400)
            
            # Check version uniqueness per brand+product
            if Recipe.objects.filter(brand_id=brand_id, product_id=product_id, version=version).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Recipe version {version} already exists for this product'
                }, status=400)
            
            # Create recipe
            recipe = Recipe.objects.create(
                brand_id=brand_id,
                product_id=product_id,
                recipe_code=recipe_code,
                recipe_name=recipe_name,
                version=version,
                yield_quantity=yield_quantity,
                yield_unit=yield_unit,
                preparation_type=preparation_type,
                effective_date=effective_date if effective_date else date.today(),
                is_active=is_active
            )
            
            messages.success(request, f'Recipe "{recipe.recipe_name}" created successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Recipe created successfully',
                'redirect': '/inventory/recipes/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    brands = Brand.objects.filter(is_active=True).select_related('company').order_by('name')
    products = Product.objects.filter(is_active=True).select_related('brand').order_by('name')
    return render(request, 'inventory/recipe/_form.html', {
        'brands': brands,
        'products': products
    })


@login_required
@require_http_methods(["GET", "POST"])
def recipe_update(request, pk):
    """Update existing recipe"""
    recipe = get_object_or_404(Recipe.objects.select_related('brand__company', 'product'), pk=pk)
    
    if request.method == 'POST':
        try:
            recipe_code = request.POST.get('recipe_code', '').strip()
            recipe_name = request.POST.get('recipe_name', '').strip()
            yield_quantity = request.POST.get('yield_quantity', '1')
            yield_unit = request.POST.get('yield_unit', '').strip()
            preparation_type = request.POST.get('preparation_type', '').strip()
            effective_date = request.POST.get('effective_date', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            if not recipe_code or not recipe_name or not yield_unit or not preparation_type:
                return JsonResponse({
                    'success': False,
                    'message': 'Code, Name, Yield Unit and Preparation Type are required'
                }, status=400)
            
            # Update recipe
            recipe.recipe_code = recipe_code
            recipe.recipe_name = recipe_name
            recipe.yield_quantity = yield_quantity
            recipe.yield_unit = yield_unit
            recipe.preparation_type = preparation_type
            recipe.effective_date = effective_date if effective_date else recipe.effective_date
            recipe.is_active = is_active
            recipe.save()
            
            messages.success(request, f'Recipe "{recipe.recipe_name}" updated successfully!')
            
            return JsonResponse({
                'success': True,
                'message': 'Recipe updated successfully',
                'redirect': '/inventory/recipes/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    # GET request - return form
    brands = Brand.objects.filter(is_active=True).select_related('company').order_by('name')
    products = Product.objects.filter(is_active=True).select_related('brand').order_by('name')
    return render(request, 'inventory/recipe/_form.html', {
        'recipe': recipe,
        'brands': brands,
        'products': products
    })


@login_required
@require_http_methods(["POST", "DELETE"])
def recipe_delete(request, pk):
    """Delete recipe"""
    try:
        recipe = get_object_or_404(Recipe, pk=pk)
        recipe_name = recipe.recipe_name
        recipe.delete()
        
        messages.success(request, f'Recipe "{recipe_name}" deleted successfully!')
        
        return JsonResponse({
            'success': True,
            'message': 'Recipe deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
