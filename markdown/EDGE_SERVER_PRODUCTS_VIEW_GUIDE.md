# Edge Server - Products View & HTML Implementation Guide

**Date**: February 3, 2026  
**System**: FoodLife F&B POS - Edge Server Product Display  
**URL**: `http://localhost:8002/products/`  
**Purpose**: Implementation guide untuk menampilkan product list dengan images dari Edge MinIO

---

## Overview

Halaman products di Edge Server menampilkan daftar produk yang tersedia di store dengan foto-foto yang sudah disync dari HO MinIO ke Edge MinIO. Implementation ini menggunakan Django views dan templates dengan JavaScript untuk efficient image loading.

---

## 1. Django View Implementation

### File: `products/views.py`

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from products.models import Product, ProductPhoto, Category
from django.conf import settings

@login_required
def product_list(request):
    """
    Display product list dengan images dari Edge MinIO
    URL: /products/
    """
    # Get filter parameters
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    show_inactive = request.GET.get('show_inactive', 'false') == 'true'
    
    # Base queryset dengan prefetch photos
    products = Product.objects.select_related(
        'category', 'brand', 'company'
    ).prefetch_related(
        Prefetch(
            'productphoto_set',
            queryset=ProductPhoto.objects.filter(is_primary=True),
            to_attr='primary_photos'
        )
    )
    
    # Filter by active status
    if not show_inactive:
        products = products.filter(is_active=True)
    
    # Search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Category filter
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Order by sort_order and name
    products = products.order_by('sort_order', 'name')
    
    # Pagination
    paginator = Paginator(products, 24)  # 24 products per page (4x6 grid)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = Category.objects.filter(
        is_active=True
    ).order_by('sort_order', 'name')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'show_inactive': show_inactive,
        'minio_endpoint': settings.EDGE_MINIO_ENDPOINT,  # e.g., "http://edge_minio:9000"
        'minio_bucket': 'product-images',
    }
    
    return render(request, 'products/product_list.html', context)


@login_required
def product_detail(request, product_id):
    """
    Display product detail dengan semua photos
    URL: /products/<uuid>/
    """
    product = Product.objects.select_related(
        'category', 'brand', 'company'
    ).prefetch_related(
        'productphoto_set',
        'productmodifier_set__modifier__modifieroption_set'
    ).get(id=product_id)
    
    # Get all photos ordered by sort_order
    photos = product.productphoto_set.all().order_by('sort_order')
    
    context = {
        'product': product,
        'photos': photos,
        'minio_endpoint': settings.EDGE_MINIO_ENDPOINT,
        'minio_bucket': 'product-images',
    }
    
    return render(request, 'products/product_detail.html', context)
```

### Product Model Helper Method

```python
# File: products/models.py

class ProductPhoto(models.Model):
    """Product photo model"""
    
    # ... existing fields ...
    
    @property
    def image_url(self):
        """
        Generate Edge MinIO URL dengan cache-busting
        """
        if self.object_key:
            base_url = f"{settings.EDGE_MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{self.object_key}"
            cache_param = self.checksum[:8] if self.checksum else str(self.version)
            return f"{base_url}?v={cache_param}"
        return None
    
    @property
    def thumbnail_url(self):
        """
        URL untuk thumbnail (bisa sama atau versi kecil)
        Untuk future optimization, bisa generate thumbnail saat sync
        """
        return self.image_url  # For now, same as main image
```

---

## 2. HTML Template - Product List

### File: `templates/products/product_list.html`

```django
{% extends "base.html" %}
{% load static %}

{% block title %}Products - {{ block.super }}{% endblock %}

{% block extra_css %}
<style>
    .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 1.5rem;
        padding: 1rem;
    }
    
    .product-card {
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
        background: white;
        cursor: pointer;
    }
    
    .product-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .product-image-container {
        position: relative;
        width: 100%;
        padding-top: 75%; /* 4:3 aspect ratio */
        background: #f7fafc;
        overflow: hidden;
    }
    
    .product-image {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: opacity 0.3s;
    }
    
    .product-image.loading {
        opacity: 0.3;
    }
    
    .product-image.loaded {
        opacity: 1;
    }
    
    .product-image.error {
        opacity: 0.5;
    }
    
    .image-placeholder {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
        color: #a0aec0;
    }
    
    .product-info {
        padding: 1rem;
    }
    
    .product-name {
        font-size: 1rem;
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 0.5rem;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    
    .product-sku {
        font-size: 0.875rem;
        color: #718096;
        margin-bottom: 0.5rem;
    }
    
    .product-price {
        font-size: 1.125rem;
        font-weight: 700;
        color: #2b6cb0;
    }
    
    .product-badge {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: 600;
        background: #48bb78;
        color: white;
    }
    
    .product-badge.inactive {
        background: #f56565;
    }
    
    .filter-bar {
        background: white;
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .filter-controls {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: center;
    }
    
    .search-box {
        flex: 1;
        min-width: 200px;
        max-width: 400px;
    }
    
    .pagination {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        margin-top: 2rem;
    }
    
    .no-image-icon {
        font-size: 3rem;
        color: #cbd5e0;
    }
    
    /* Loading skeleton */
    .skeleton {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
    }
    
    @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row mb-4">
        <div class="col">
            <h1 class="h3">Products</h1>
        </div>
        <div class="col-auto">
            <a href="{% url 'products:create' %}" class="btn btn-primary">
                <i class="fas fa-plus"></i> Add Product
            </a>
        </div>
    </div>
    
    <!-- Filter Bar -->
    <div class="filter-bar">
        <form method="get" class="filter-controls">
            <div class="search-box">
                <input type="text" 
                       name="search" 
                       class="form-control" 
                       placeholder="Search products..." 
                       value="{{ search_query }}"
                       id="searchInput">
            </div>
            
            <div>
                <select name="category" class="form-control" id="categorySelect">
                    <option value="">All Categories</option>
                    {% for category in categories %}
                    <option value="{{ category.id }}" 
                            {% if category.id|stringformat:"s" == selected_category %}selected{% endif %}>
                        {{ category.name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="form-check">
                <input type="checkbox" 
                       name="show_inactive" 
                       value="true" 
                       class="form-check-input" 
                       id="showInactive"
                       {% if show_inactive %}checked{% endif %}>
                <label class="form-check-label" for="showInactive">
                    Show Inactive
                </label>
            </div>
            
            <button type="submit" class="btn btn-secondary">
                <i class="fas fa-filter"></i> Filter
            </button>
            
            <a href="{% url 'products:list' %}" class="btn btn-outline-secondary">
                <i class="fas fa-times"></i> Clear
            </a>
        </form>
    </div>
    
    <!-- Product Grid -->
    <div class="product-grid">
        {% for product in page_obj %}
        <div class="product-card" onclick="location.href='{% url 'products:detail' product.id %}'">
            <div class="product-image-container">
                {% if product.primary_photos %}
                    {% with photo=product.primary_photos.0 %}
                    <img src="" 
                         data-src="{{ minio_endpoint }}/{{ minio_bucket }}/{{ photo.object_key }}?v={{ photo.checksum|slice:':8' }}"
                         alt="{{ product.name }}"
                         class="product-image loading"
                         data-product-id="{{ product.id }}"
                         loading="lazy"
                         onerror="handleImageError(this)">
                    {% endwith %}
                {% else %}
                    <div class="image-placeholder">
                        <i class="fas fa-image no-image-icon"></i>
                        <p class="mt-2">No Image</p>
                    </div>
                {% endif %}
                
                {% if not product.is_active %}
                <span class="product-badge inactive">Inactive</span>
                {% endif %}
            </div>
            
            <div class="product-info">
                <div class="product-name">{{ product.name }}</div>
                <div class="product-sku">SKU: {{ product.sku }}</div>
                <div class="product-price">Rp {{ product.price|floatformat:0|intcomma }}</div>
            </div>
        </div>
        {% empty %}
        <div class="col-12 text-center py-5">
            <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
            <p class="text-muted">No products found</p>
        </div>
        {% endfor %}
    </div>
    
    <!-- Pagination -->
    {% if page_obj.has_other_pages %}
    <div class="pagination">
        {% if page_obj.has_previous %}
        <a href="?page=1{% if search_query %}&search={{ search_query }}{% endif %}{% if selected_category %}&category={{ selected_category }}{% endif %}" 
           class="btn btn-outline-primary">First</a>
        <a href="?page={{ page_obj.previous_page_number }}{% if search_query %}&search={{ search_query }}{% endif %}{% if selected_category %}&category={{ selected_category }}{% endif %}" 
           class="btn btn-outline-primary">Previous</a>
        {% endif %}
        
        <span class="btn btn-primary disabled">
            Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}
        </span>
        
        {% if page_obj.has_next %}
        <a href="?page={{ page_obj.next_page_number }}{% if search_query %}&search={{ search_query }}{% endif %}{% if selected_category %}&category={{ selected_category }}{% endif %}" 
           class="btn btn-outline-primary">Next</a>
        <a href="?page={{ page_obj.paginator.num_pages }}{% if search_query %}&search={{ search_query }}{% endif %}{% if selected_category %}&category={{ selected_category }}{% endif %}" 
           class="btn btn-outline-primary">Last</a>
        {% endif %}
    </div>
    {% endif %}
</div>
{% endblock %}

{% block extra_js %}
<script>
// Lazy load images dengan Intersection Observer
document.addEventListener('DOMContentLoaded', function() {
    // Image loading handler
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const src = img.getAttribute('data-src');
                
                if (src) {
                    img.src = src;
                    img.onload = function() {
                        img.classList.remove('loading');
                        img.classList.add('loaded');
                    };
                    
                    observer.unobserve(img);
                }
            }
        });
    }, {
        rootMargin: '50px' // Load images 50px before they come into view
    });
    
    // Observe all product images
    document.querySelectorAll('.product-image[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
    
    // Auto-submit form on filter change
    document.getElementById('categorySelect')?.addEventListener('change', function() {
        this.form.submit();
    });
    
    document.getElementById('showInactive')?.addEventListener('change', function() {
        this.form.submit();
    });
});

// Handle image loading errors
function handleImageError(img) {
    img.classList.remove('loading');
    img.classList.add('error');
    
    // Replace with placeholder
    const container = img.parentElement;
    const placeholder = document.createElement('div');
    placeholder.className = 'image-placeholder';
    placeholder.innerHTML = `
        <i class="fas fa-exclamation-triangle no-image-icon text-warning"></i>
        <p class="mt-2">Image Failed to Load</p>
    `;
    
    img.style.display = 'none';
    container.appendChild(placeholder);
    
    console.error('Failed to load image:', img.getAttribute('data-src'));
}

// Retry failed images
function retryFailedImages() {
    document.querySelectorAll('.product-image.error').forEach(img => {
        const src = img.getAttribute('data-src');
        if (src) {
            img.classList.remove('error');
            img.classList.add('loading');
            img.style.display = 'block';
            img.src = src + '&retry=' + Date.now(); // Add cache buster
        }
    });
}
</script>
{% endblock %}
```

---

## 3. HTML Template - Product Detail

### File: `templates/products/product_detail.html`

```django
{% extends "base.html" %}
{% load static %}

{% block title %}{{ product.name }} - {{ block.super }}{% endblock %}

{% block extra_css %}
<style>
    .product-detail-container {
        background: white;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        padding: 2rem;
    }
    
    .product-gallery {
        margin-bottom: 2rem;
    }
    
    .main-image-container {
        position: relative;
        width: 100%;
        padding-top: 75%; /* 4:3 aspect ratio */
        background: #f7fafc;
        border-radius: 0.5rem;
        overflow: hidden;
        margin-bottom: 1rem;
    }
    
    .main-image {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: contain;
    }
    
    .thumbnail-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
        gap: 0.5rem;
    }
    
    .thumbnail {
        width: 100%;
        padding-top: 100%; /* Square aspect ratio */
        position: relative;
        border: 2px solid transparent;
        border-radius: 0.25rem;
        cursor: pointer;
        overflow: hidden;
        transition: border-color 0.2s;
    }
    
    .thumbnail:hover,
    .thumbnail.active {
        border-color: #4299e1;
    }
    
    .thumbnail img {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    .product-info {
        padding: 1rem 0;
    }
    
    .product-title {
        font-size: 2rem;
        font-weight: 700;
        color: #2d3748;
        margin-bottom: 1rem;
    }
    
    .product-price {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2b6cb0;
        margin-bottom: 1rem;
    }
    
    .product-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    .meta-item {
        padding: 1rem;
        background: #f7fafc;
        border-radius: 0.25rem;
    }
    
    .meta-label {
        font-size: 0.875rem;
        color: #718096;
        margin-bottom: 0.25rem;
    }
    
    .meta-value {
        font-size: 1rem;
        font-weight: 600;
        color: #2d3748;
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row mb-4">
        <div class="col">
            <a href="{% url 'products:list' %}" class="btn btn-outline-secondary">
                <i class="fas fa-arrow-left"></i> Back to Products
            </a>
        </div>
        <div class="col-auto">
            <a href="{% url 'products:edit' product.id %}" class="btn btn-primary">
                <i class="fas fa-edit"></i> Edit Product
            </a>
        </div>
    </div>
    
    <div class="product-detail-container">
        <div class="row">
            <!-- Product Gallery -->
            <div class="col-md-6">
                <div class="product-gallery">
                    <!-- Main Image -->
                    <div class="main-image-container">
                        {% if photos %}
                            {% with photo=photos.0 %}
                            <img id="mainImage"
                                 src="{{ minio_endpoint }}/{{ minio_bucket }}/{{ photo.object_key }}?v={{ photo.checksum|slice:':8' }}"
                                 alt="{{ product.name }}"
                                 class="main-image"
                                 onerror="handleImageError(this)">
                            {% endwith %}
                        {% else %}
                            <div class="image-placeholder">
                                <i class="fas fa-image no-image-icon"></i>
                                <p class="mt-2">No Image Available</p>
                            </div>
                        {% endif %}
                    </div>
                    
                    <!-- Thumbnail Gallery -->
                    {% if photos|length > 1 %}
                    <div class="thumbnail-gallery">
                        {% for photo in photos %}
                        <div class="thumbnail {% if forloop.first %}active{% endif %}"
                             onclick="changeMainImage('{{ minio_endpoint }}/{{ minio_bucket }}/{{ photo.object_key }}?v={{ photo.checksum|slice:':8' }}', this)">
                            <img src="{{ minio_endpoint }}/{{ minio_bucket }}/{{ photo.object_key }}?v={{ photo.checksum|slice:':8' }}"
                                 alt="{{ product.name }} - Image {{ forloop.counter }}"
                                 loading="lazy">
                        </div>
                        {% endfor %}
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <!-- Product Information -->
            <div class="col-md-6">
                <div class="product-info">
                    <h1 class="product-title">{{ product.name }}</h1>
                    
                    <div class="product-price">
                        Rp {{ product.price|floatformat:0|intcomma }}
                    </div>
                    
                    {% if not product.is_active %}
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle"></i>
                        This product is currently inactive
                    </div>
                    {% endif %}
                    
                    <!-- Product Meta Information -->
                    <div class="product-meta">
                        <div class="meta-item">
                            <div class="meta-label">SKU</div>
                            <div class="meta-value">{{ product.sku }}</div>
                        </div>
                        
                        <div class="meta-item">
                            <div class="meta-label">Category</div>
                            <div class="meta-value">{{ product.category.name|default:"-" }}</div>
                        </div>
                        
                        <div class="meta-item">
                            <div class="meta-label">Brand</div>
                            <div class="meta-value">{{ product.brand.name }}</div>
                        </div>
                        
                        <div class="meta-item">
                            <div class="meta-label">Cost</div>
                            <div class="meta-value">Rp {{ product.cost|floatformat:0|intcomma }}</div>
                        </div>
                        
                        {% if product.track_stock %}
                        <div class="meta-item">
                            <div class="meta-label">Stock</div>
                            <div class="meta-value">{{ product.stock_quantity }} units</div>
                        </div>
                        {% endif %}
                    </div>
                    
                    <!-- Description -->
                    {% if product.description %}
                    <div class="mt-4">
                        <h3 class="h5">Description</h3>
                        <p class="text-muted">{{ product.description }}</p>
                    </div>
                    {% endif %}
                    
                    <!-- Photo Information -->
                    {% if photos %}
                    <div class="mt-4">
                        <h3 class="h5">Product Images</h3>
                        <p class="text-muted">{{ photos|length }} image{{ photos|length|pluralize }} available</p>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
// Change main image when thumbnail clicked
function changeMainImage(imageUrl, thumbnailElement) {
    const mainImage = document.getElementById('mainImage');
    mainImage.src = imageUrl;
    
    // Update active thumbnail
    document.querySelectorAll('.thumbnail').forEach(thumb => {
        thumb.classList.remove('active');
    });
    thumbnailElement.classList.add('active');
}

// Handle image loading errors
function handleImageError(img) {
    const container = img.parentElement;
    const placeholder = document.createElement('div');
    placeholder.className = 'image-placeholder';
    placeholder.innerHTML = `
        <i class="fas fa-exclamation-triangle no-image-icon text-warning"></i>
        <p class="mt-2">Image Failed to Load</p>
    `;
    
    img.style.display = 'none';
    container.appendChild(placeholder);
}
</script>
{% endblock %}
```

---

## 4. URL Configuration

### File: `products/urls.py`

```python
from django.urls import path
from products import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='list'),
    path('<uuid:product_id>/', views.product_detail, name='detail'),
    path('create/', views.product_create, name='create'),
    path('<uuid:product_id>/edit/', views.product_edit, name='edit'),
]
```

### Main URL Configuration: `config/urls.py`

```python
urlpatterns = [
    # ... other paths ...
    path('products/', include('products.urls', namespace='products')),
]
```

---

## 5. Settings Configuration

### File: `config/settings.py`

```python
# MinIO Configuration for Edge Server
EDGE_MINIO_ENDPOINT = env('EDGE_MINIO_ENDPOINT', default='http://edge_minio:9000')
MINIO_BUCKET = 'product-images'

# For external access (browser)
EDGE_MINIO_EXTERNAL_ENDPOINT = env('EDGE_MINIO_EXTERNAL_ENDPOINT', default='http://localhost:9000')

# Template context processor
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'products.context_processors.minio_settings',  # Custom processor
            ],
        },
    },
]
```

### Context Processor: `products/context_processors.py`

```python
from django.conf import settings

def minio_settings(request):
    """
    Add MinIO settings to all template contexts
    """
    return {
        'EDGE_MINIO_ENDPOINT': settings.EDGE_MINIO_ENDPOINT,
        'EDGE_MINIO_EXTERNAL_ENDPOINT': settings.EDGE_MINIO_EXTERNAL_ENDPOINT,
        'MINIO_BUCKET': settings.MINIO_BUCKET,
    }
```

---

## 6. Base Template

### File: `templates/base.html`

```django
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Edge POS System{% endblock %}</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <!-- Custom CSS -->
    <link href="{% static 'css/main.css' %}" rel="stylesheet">
    
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                <i class="fas fa-store"></i> Edge POS
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'dashboard:index' %}">
                            <i class="fas fa-home"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'products:list' %}">
                            <i class="fas fa-box"></i> Products
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'transactions:pos' %}">
                            <i class="fas fa-cash-register"></i> POS
                        </a>
                    </li>
                </ul>
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="userDropdown" data-bs-toggle="dropdown">
                            <i class="fas fa-user"></i> {{ request.user.username }}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="{% url 'auth:profile' %}">Profile</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{% url 'auth:logout' %}">Logout</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    
    <!-- Main Content -->
    <main class="py-4">
        {% if messages %}
        <div class="container-fluid">
            {% for message in messages %}
            <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    <footer class="bg-light py-3 mt-5">
        <div class="container-fluid text-center text-muted">
            <small>&copy; 2026 FoodLife POS System - Edge Server</small>
        </div>
    </footer>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Custom JS -->
    <script src="{% static 'js/main.js' %}"></script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

---

## 7. JavaScript Utilities

### File: `static/js/image-loader.js`

```javascript
/**
 * Image loading utilities untuk Edge MinIO
 */

class ImageLoader {
    constructor(minioEndpoint, bucketName) {
        this.minioEndpoint = minioEndpoint;
        this.bucketName = bucketName;
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second
    }
    
    /**
     * Generate full image URL
     */
    getImageUrl(objectKey, checksum) {
        const cacheParam = checksum ? checksum.substring(0, 8) : Date.now();
        return `${this.minioEndpoint}/${this.bucketName}/${objectKey}?v=${cacheParam}`;
    }
    
    /**
     * Load image with retry logic
     */
    async loadImage(objectKey, checksum, retryCount = 0) {
        const url = this.getImageUrl(objectKey, checksum);
        
        return new Promise((resolve, reject) => {
            const img = new Image();
            
            img.onload = () => resolve(img);
            
            img.onerror = async () => {
                if (retryCount < this.retryAttempts) {
                    console.log(`Retry ${retryCount + 1}/${this.retryAttempts} for ${objectKey}`);
                    await this.delay(this.retryDelay * (retryCount + 1));
                    
                    try {
                        const result = await this.loadImage(objectKey, checksum, retryCount + 1);
                        resolve(result);
                    } catch (error) {
                        reject(error);
                    }
                } else {
                    reject(new Error(`Failed to load image after ${this.retryAttempts} attempts`));
                }
            };
            
            img.src = url;
        });
    }
    
    /**
     * Preload multiple images
     */
    async preloadImages(images) {
        const promises = images.map(img => 
            this.loadImage(img.objectKey, img.checksum)
        );
        
        return Promise.allSettled(promises);
    }
    
    /**
     * Delay utility
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize global image loader
if (typeof EDGE_MINIO_ENDPOINT !== 'undefined') {
    window.imageLoader = new ImageLoader(EDGE_MINIO_ENDPOINT, 'product-images');
}
```

---

## 8. Performance Optimization

### Lazy Loading with Intersection Observer

```javascript
// File: static/js/lazy-load.js

class LazyLoader {
    constructor(options = {}) {
        this.options = {
            rootMargin: options.rootMargin || '50px',
            threshold: options.threshold || 0.01,
            ...options
        };
        
        this.observer = new IntersectionObserver(
            this.handleIntersection.bind(this),
            this.options
        );
    }
    
    observe(elements) {
        elements.forEach(element => this.observer.observe(element));
    }
    
    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                this.loadImage(entry.target);
                this.observer.unobserve(entry.target);
            }
        });
    }
    
    loadImage(img) {
        const src = img.getAttribute('data-src');
        
        if (!src) return;
        
        img.classList.add('loading');
        
        img.onload = () => {
            img.classList.remove('loading');
            img.classList.add('loaded');
        };
        
        img.onerror = () => {
            img.classList.remove('loading');
            img.classList.add('error');
            this.handleError(img);
        };
        
        img.src = src;
    }
    
    handleError(img) {
        // Show error placeholder
        const placeholder = document.createElement('div');
        placeholder.className = 'image-error-placeholder';
        placeholder.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <p>Failed to load image</p>
        `;
        
        img.parentElement.appendChild(placeholder);
        img.style.display = 'none';
    }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const lazyLoader = new LazyLoader({
        rootMargin: '100px',
        threshold: 0.1
    });
    
    const lazyImages = document.querySelectorAll('img[data-src]');
    lazyLoader.observe(lazyImages);
});
```

---

## 9. Error Handling & Fallbacks

### Placeholder Images

```python
# File: products/models.py

class Product(models.Model):
    # ... existing fields ...
    
    def get_image_url(self):
        """Get product image URL with fallback"""
        try:
            photo = self.productphoto_set.filter(is_primary=True).first()
            if photo:
                return photo.image_url
        except Exception as e:
            logger.error(f"Error getting image for product {self.id}: {e}")
        
        # Return placeholder
        return '/static/images/product-placeholder.png'
    
    @property
    def has_image(self):
        """Check if product has any images"""
        return self.productphoto_set.exists()
```

---

## 10. Testing

### Manual Testing Checklist

```bash
# 1. Verify MinIO is accessible
curl http://localhost:9000/product-images/

# 2. Test product list page
curl -H "Cookie: sessionid=YOUR_SESSION" http://localhost:8002/products/

# 3. Test image URLs
curl -I http://localhost:9000/product-images/products/xxx/primary.jpg?v=checksum

# 4. Check Django logs for errors
docker compose logs web --tail=100 | grep -i error
```

### Automated Tests

```python
# File: products/tests/test_views.py

from django.test import TestCase, Client
from django.urls import reverse
from products.models import Product, ProductPhoto
from core.models import Company, Brand

class ProductViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test data
        self.company = Company.objects.create(name="Test Company")
        self.brand = Brand.objects.create(name="Test Brand", company=self.company)
        self.product = Product.objects.create(
            name="Test Product",
            sku="TEST001",
            price=10000,
            brand=self.brand,
            company=self.company
        )
    
    def test_product_list_view(self):
        """Test product list view loads correctly"""
        response = self.client.get(reverse('products:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")
    
    def test_product_detail_view(self):
        """Test product detail view loads correctly"""
        response = self.client.get(
            reverse('products:detail', kwargs={'product_id': self.product.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")
    
    def test_product_with_image(self):
        """Test product displays with image"""
        photo = ProductPhoto.objects.create(
            product=self.product,
            object_key="test/image.jpg",
            checksum="abc123",
            is_primary=True
        )
        
        response = self.client.get(reverse('products:list'))
        self.assertContains(response, photo.object_key)
```

---

## Summary

### Implementation Checklist

- ✅ Django views untuk product list dan detail
- ✅ HTML templates dengan responsive grid layout
- ✅ Lazy loading images dengan Intersection Observer
- ✅ Error handling dan fallback placeholders
- ✅ Cache-busting dengan checksum parameter
- ✅ Pagination support
- ✅ Search dan filter functionality
- ✅ Image gallery untuk product detail
- ✅ Performance optimization (lazy load, prefetch)
- ✅ Mobile responsive design

### Key Features

1. **Lazy Loading** - Images load hanya saat visible
2. **Cache-Busting** - URL include checksum untuk force refresh
3. **Error Handling** - Graceful fallback untuk failed images
4. **Performance** - Optimized dengan prefetch_related
5. **Responsive** - Mobile-friendly grid layout
6. **Accessibility** - Alt text dan ARIA labels

---

**Last Updated**: February 3, 2026  
**Version**: 1.0  
**Author**: System Integration Team
