"""
Analytics Report Views - UI for Sales & Business Reports
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from transactions.models import Bill, BillItem, Payment
from core.models import Store, Brand, Company


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
        bill_date__gte=start_date,
        bill_date__lte=end_date
    )
    
    if store_id:
        bills = bills.filter(store_id=store_id)
    
    # Summary statistics
    summary = bills.aggregate(
        total_bills=Count('id'),
        total_sales=Sum('total_amount'),
        total_tax=Sum('tax_amount'),
        total_discount=Sum('discount_amount'),
        total_service=Sum('service_charge'),
        avg_bill=Avg('total_amount')
    )
    
    # Daily sales trend
    daily_sales = bills.annotate(
        date=TruncDate('bill_date')
    ).values('date').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('date')
    
    # Payment method breakdown
    payment_breakdown = Payment.objects.filter(
        bill__in=bills,
        status='SUCCESS'
    ).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Top selling products
    top_products = BillItem.objects.filter(
        bill__in=bills,
        is_void=False
    ).values('product_name').annotate(
        quantity=Sum('quantity'),
        revenue=Sum('subtotal')
    ).order_by('-quantity')[:10]
    
    # Hourly sales distribution
    hourly_sales = bills.extra(
        select={'hour': 'EXTRACT(hour FROM bill_date)'}
    ).values('hour').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('hour')
    
    # Get active stores for filter
    stores = Store.objects.filter(is_active=True).select_related('brand')
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'store_id': store_id,
        'summary': summary,
        'daily_sales': list(daily_sales),
        'payment_breakdown': list(payment_breakdown),
        'top_products': list(top_products),
        'hourly_sales': list(hourly_sales),
        'stores': stores,
        'total_count': summary['total_bills'] or 0,
    }
    
    return render(request, 'analytics/sales_report.html', context)


@login_required
def product_performance_report(request):
    """Product Performance Report"""
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Product performance
    products = BillItem.objects.filter(
        bill__status='PAID',
        bill__bill_date__gte=start_date,
        bill__bill_date__lte=end_date,
        is_void=False
    ).values('product_name', 'product_sku').annotate(
        quantity_sold=Sum('quantity'),
        total_revenue=Sum('subtotal'),
        total_cost=Sum(F('quantity') * F('unit_cost')),
        avg_price=Avg('unit_price'),
        order_count=Count('bill', distinct=True)
    ).annotate(
        gross_margin=F('total_revenue') - F('total_cost'),
        margin_percent=(F('total_revenue') - F('total_cost')) * 100 / F('total_revenue')
    ).order_by('-total_revenue')[:50]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'products': list(products),
        'total_products': products.count()
    }
    
    return render(request, 'analytics/product_report.html', context)


@login_required
def hourly_sales_report(request):
    """Hourly Sales Analysis"""
    
    date = request.GET.get('date')
    store_id = request.GET.get('store_id')
    
    if not date:
        date = timezone.now().date()
    else:
        date = datetime.strptime(date, '%Y-%m-%d').date()
    
    # Hourly breakdown
    bills = Bill.objects.filter(
        status='PAID',
        bill_date__date=date
    )
    
    if store_id:
        bills = bills.filter(store_id=store_id)
    
    hourly_data = bills.extra(
        select={'hour': 'EXTRACT(hour FROM bill_date)'}
    ).values('hour').annotate(
        total_bills=Count('id'),
        total_sales=Sum('total_amount'),
        avg_bill=Avg('total_amount'),
        total_customers=Sum('customer_count')
    ).order_by('hour')
    
    # Summary
    summary = bills.aggregate(
        total_bills=Count('id'),
        total_sales=Sum('total_amount'),
        avg_bill=Avg('total_amount')
    )
    
    stores = Store.objects.filter(is_active=True)
    
    context = {
        'date': date,
        'store_id': store_id,
        'hourly_data': list(hourly_data),
        'summary': summary,
        'stores': stores
    }
    
    return render(request, 'analytics/hourly_report.html', context)
