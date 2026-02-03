"""
Analytics Report Views - UI for Sales & Business Reports
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, F, Q, FloatField
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek, Cast
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
from transactions.models import Bill, BillItem, Payment
from core.models import Store, Brand, Company
from products.models import Category


@login_required
def sales_report_dashboard(request):
    """Sales Report Dashboard - Main page with multiple reports"""
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    store_id = request.GET.get('store_id')
    
    # Default to last 30 days if no dates provided
    if not start_date or not end_date:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Build queryset
    bills = Bill.objects.filter(
        status='PAID',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    if store_id:
        bills = bills.filter(store_id=store_id)
    
    # Summary statistics
    summary = bills.aggregate(
        total_bills=Count('id'),
        total_sales=Sum('total'),
        total_tax=Sum('tax_amount'),
        total_discount=Sum('discount_amount'),
        total_service=Sum('service_charge'),
        avg_bill=Avg('total')
    )
    
    # Daily sales trend
    daily_sales = bills.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('date')
    
    # Payment method breakdown
    payment_breakdown = Payment.objects.filter(
        bill_id__in=bills.values_list('id', flat=True),
        status='SUCCESS'
    ).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Top selling products
    top_products = BillItem.objects.filter(
        bill_id__in=bills.values_list('id', flat=True),
        is_void=False
    ).values('product_name').annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total')
    ).order_by('-quantity')[:10]
    
    # Hourly sales distribution
    hourly_sales = bills.extra(
        select={'hour': 'EXTRACT(hour FROM created_at)'}
    ).values('hour').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('hour')
    
    # Get active stores for filter
    stores = Store.objects.filter(is_active=True).select_related('brand')
    
    # Prepare chart data for templates
    daily_labels = [d['date'].strftime('%Y-%m-%d') for d in daily_sales]
    daily_revenue = [float(d['total'] or 0) for d in daily_sales]
    
    payment_labels = [p['payment_method'] for p in payment_breakdown]
    payment_amounts = [float(p['total'] or 0) for p in payment_breakdown]
    
    hourly_labels = [f"{int(h['hour'])}:00" for h in hourly_sales]
    hourly_revenue = [float(h['total'] or 0) for h in hourly_sales]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'store_id': store_id,
        'summary': {
            'total_bills': summary['total_bills'] or 0,
            'total_sales': summary['total_sales'] or 0,
            'total_tax': summary['total_tax'] or 0,
            'total_discount': summary['total_discount'] or 0,
            'total_service': summary['total_service'] or 0,
            'avg_bill_value': summary['avg_bill'] or 0,
        },
        'daily_sales': list(daily_sales),
        'payment_breakdown': list(payment_breakdown),
        'top_products': list(top_products),
        'hourly_sales': list(hourly_sales),
        'stores': stores,
        # Chart data as JSON
        'daily_labels': json.dumps(daily_labels),
        'daily_revenue': json.dumps(daily_revenue),
        'payment_labels': json.dumps(payment_labels),
        'payment_amounts': json.dumps(payment_amounts),
        'hourly_labels': json.dumps(hourly_labels),
        'hourly_revenue': json.dumps(hourly_revenue),
    }
    
    return render(request, 'analytics/sales_report.html', context)


@login_required
def product_performance_report(request):
    """Product Performance Report"""
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category_id')
    
    if not start_date or not end_date:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Base queryset
    queryset = BillItem.objects.filter(
        bill_id__in=Bill.objects.filter(
            status='PAID',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values_list('id', flat=True),
        is_void=False
    )
    
    # Filter by category if specified
    if category_id:
        queryset = queryset.filter(product__category_id=category_id)
    
    # Product performance aggregation
    products_data = queryset.values(
        'product__id',
        'product__name',
        'product__category__name',
        'product_sku'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('subtotal'),
        total_cogs=Sum(F('quantity') * F('unit_cost')),
        avg_price=Avg('unit_price'),
        order_count=Count('bill', distinct=True)
    ).annotate(
        gross_margin=F('total_revenue') - F('total_cogs'),
        margin_percent=Cast(
            (F('total_revenue') - F('total_cogs')) * 100.0 / F('total_revenue'),
            FloatField()
        )
    ).order_by('-total_revenue')[:50]
    
    # Add performance stars (1-5 based on margin %)
    products_list = list(products_data)
    for product in products_list:
        margin = product.get('margin_percent', 0) or 0
        if margin >= 50:
            product['performance_stars'] = 5
        elif margin >= 40:
            product['performance_stars'] = 4
        elif margin >= 30:
            product['performance_stars'] = 3
        elif margin >= 20:
            product['performance_stars'] = 2
        else:
            product['performance_stars'] = 1
    
    # Top 10 for charts
    top_10_revenue = products_list[:10]
    top_10_quantity = sorted(products_list, key=lambda x: x['total_quantity'], reverse=True)[:10]
    
    # Prepare chart data
    top_revenue_labels = [p['product__name'][:20] for p in top_10_revenue]
    top_revenue_data = [float(p['total_revenue'] or 0) for p in top_10_revenue]
    
    top_quantity_labels = [p['product__name'][:20] for p in top_10_quantity]
    top_quantity_data = [float(p['total_quantity'] or 0) for p in top_10_quantity]
    
    # Scatter data for margin analysis (revenue vs margin %)
    margin_scatter_data = [
        {
            'x': float(p['total_revenue'] or 0),
            'y': float(p['margin_percent'] or 0)
        }
        for p in products_list[:30]  # Top 30 for scatter
    ]
    
    # Get categories for filter
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'category_id': category_id,
        'products': products_list,
        'categories': categories,
        # Chart data as JSON
        'top_revenue_labels': json.dumps(top_revenue_labels),
        'top_revenue_data': json.dumps(top_revenue_data),
        'top_quantity_labels': json.dumps(top_quantity_labels),
        'top_quantity_data': json.dumps(top_quantity_data),
        'margin_scatter_data': json.dumps(margin_scatter_data),
    }
    
    return render(request, 'analytics/product_performance.html', context)


@login_required
def hourly_sales_report(request):
    """Hourly Sales Analysis"""
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    store_id = request.GET.get('store_id')
    
    if not start_date or not end_date:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)  # Default to 7 days
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Hourly breakdown
    bills = Bill.objects.filter(
        status='PAID',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    if store_id:
        bills = bills.filter(store_id=store_id)
    
    hourly_data_raw = bills.extra(
        select={'hour': 'EXTRACT(hour FROM created_at)'}
    ).values('hour').annotate(
        bill_count=Count('id'),
        revenue=Sum('total'),
        avg_bill=Avg('total')
    ).order_by('hour')
    
    # Calculate total revenue for percentage
    total_revenue = sum(h['revenue'] or 0 for h in hourly_data_raw)
    
    # Enhance hourly data with percentages and status
    hourly_data_list = list(hourly_data_raw)
    if hourly_data_list:
        max_revenue = max(h['revenue'] or 0 for h in hourly_data_list)
        avg_revenue = total_revenue / len(hourly_data_list) if hourly_data_list else 0
        
        for hour_data in hourly_data_list:
            revenue = hour_data['revenue'] or 0
            hour_data['percentage'] = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            
            # Determine status
            if revenue >= max_revenue * 0.9:
                hour_data['status'] = 'peak'
            elif revenue >= avg_revenue:
                hour_data['status'] = 'high'
            elif revenue >= avg_revenue * 0.5:
                hour_data['status'] = 'normal'
            else:
                hour_data['status'] = 'low'
    
    # Find peak hour and revenue
    peak_hour_data = max(hourly_data_list, key=lambda x: x['revenue'] or 0) if hourly_data_list else None
    peak_hour = f"{int(peak_hour_data['hour'])}:00" if peak_hour_data else "N/A"
    peak_revenue = peak_hour_data['revenue'] if peak_hour_data else 0
    
    # Calculate averages
    avg_hourly_revenue = total_revenue / len(hourly_data_list) if hourly_data_list else 0
    operating_hours = len(hourly_data_list)
    
    # Identify peak and slow hours
    if hourly_data_list:
        sorted_by_revenue = sorted(hourly_data_list, key=lambda x: x['revenue'] or 0, reverse=True)
        peak_hours = [f"{int(h['hour'])}:00-{int(h['hour'])+1}:00" for h in sorted_by_revenue[:3]]
        slow_hours = [f"{int(h['hour'])}:00-{int(h['hour'])+1}:00" for h in sorted_by_revenue[-3:]]
    else:
        peak_hours = []
        slow_hours = []
    
    # Prepare chart data
    hourly_labels = [f"{int(h['hour'])}:00" for h in hourly_data_list]
    hourly_revenue = [float(h['revenue'] or 0) for h in hourly_data_list]
    hourly_bills = [int(h['bill_count'] or 0) for h in hourly_data_list]
    
    stores = Store.objects.filter(is_active=True)
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'store_id': store_id,
        'hourly_data': hourly_data_list,
        'peak_hour': peak_hour,
        'peak_revenue': peak_revenue,
        'avg_hourly_revenue': avg_hourly_revenue,
        'operating_hours': operating_hours,
        'peak_hours': peak_hours,
        'slow_hours': slow_hours,
        'avg_bill_trend': 'higher' if peak_hour_data and peak_hour_data['avg_bill'] > avg_hourly_revenue else 'lower',
        'stores': stores,
        # Chart data as JSON
        'hourly_labels': json.dumps(hourly_labels),
        'hourly_revenue': json.dumps(hourly_revenue),
        'hourly_bills': json.dumps(hourly_bills),
    }
    
    return render(request, 'analytics/hourly_sales.html', context)
