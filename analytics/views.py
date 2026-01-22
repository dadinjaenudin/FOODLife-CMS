"""
Analytics Views - Reporting & Analytics API
Generate various reports for HO management
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, Avg, F, Q, DecimalField
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from transactions.models import Bill, BillItem, Payment, BillPromotion, InventoryMovement


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_sales_report(request):
    """
    Daily Sales Report
    Query params: start_date, end_date, store_id (optional), brand_id (optional)
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    store_id = request.query_params.get('store_id')
    brand_id = request.query_params.get('brand_id')
    
    if not start_date or not end_date:
        return Response(
            {'error': 'start_date and end_date required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    queryset = Bill.objects.filter(
        status='PAID',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    if store_id:
        queryset = queryset.filter(store_id=store_id)
    if brand_id:
        queryset = queryset.filter(brand_id=brand_id)
    
    # Aggregate by date
    daily_data = queryset.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total_bills=Count('id'),
        total_sales=Sum('total'),
        total_discount=Sum('discount_amount'),
        total_tax=Sum('tax_amount'),
        total_service=Sum('service_charge'),
        avg_bill_value=Avg('total')
    ).order_by('date')
    
    # Summary
    summary = queryset.aggregate(
        total_bills=Count('id'),
        total_sales=Sum('total'),
        total_discount=Sum('discount_amount'),
        total_tax=Sum('tax_amount'),
        total_service=Sum('service_charge'),
        avg_bill_value=Avg('total')
    )
    
    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'summary': summary,
        'daily_breakdown': list(daily_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_sales_report(request):
    """
    Product Sales Analysis
    Query params: start_date, end_date, brand_id, category_id (optional)
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    brand_id = request.query_params.get('brand_id')
    category_id = request.query_params.get('category_id')
    
    if not start_date or not end_date or not brand_id:
        return Response(
            {'error': 'start_date, end_date, and brand_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    queryset = BillItem.objects.filter(
        brand_id=brand_id,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        is_void=False
    )
    
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    
    # Product analysis
    product_data = queryset.values(
        'product_id', 'product_sku', 'product_name', 'category_id'
    ).annotate(
        quantity_sold=Sum('quantity'),
        total_revenue=Sum('total'),
        total_cost=Sum(F('quantity') * F('unit_cost'), output_field=DecimalField()),
        total_discount=Sum('discount_amount'),
        gross_margin=Sum('total') - Sum(F('quantity') * F('unit_cost'), output_field=DecimalField()),
        order_count=Count('bill_id', distinct=True)
    ).annotate(
        margin_percent=F('gross_margin') * 100 / F('total_revenue')
    ).order_by('-quantity_sold')
    
    # Top 10 products
    top_products = list(product_data[:10])
    
    # Category summary
    category_data = queryset.values('category_id').annotate(
        quantity_sold=Sum('quantity'),
        total_revenue=Sum('total'),
        order_count=Count('bill_id', distinct=True)
    ).order_by('-total_revenue')
    
    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'top_products': top_products,
        'category_summary': list(category_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def promotion_performance_report(request):
    """
    Promotion Performance Report
    Query params: start_date, end_date, brand_id (optional)
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    brand_id = request.query_params.get('brand_id')
    
    if not start_date or not end_date:
        return Response(
            {'error': 'start_date and end_date required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    queryset = BillPromotion.objects.filter(
        applied_at__date__gte=start_date,
        applied_at__date__lte=end_date
    )
    
    # Filter by brand if provided (via bill)
    if brand_id:
        queryset = queryset.filter(bill_id__in=Bill.objects.filter(brand_id=brand_id).values('id'))
    
    # Promotion analysis
    promo_data = queryset.values(
        'promotion_id', 'promotion_name', 'promotion_code', 'execution_stage'
    ).annotate(
        usage_count=Count('id'),
        total_discount=Sum('discount_amount'),
        total_cashback=Sum('cashback_amount'),
        unique_bills=Count('bill_id', distinct=True),
        avg_discount_per_use=Avg('discount_amount')
    ).order_by('-usage_count')
    
    # Top promotions
    top_promos = list(promo_data[:20])
    
    # Stage breakdown
    stage_data = queryset.values('execution_stage').annotate(
        usage_count=Count('id'),
        total_discount=Sum('discount_amount')
    ).order_by('-usage_count')
    
    # Summary
    summary = queryset.aggregate(
        total_promotions_used=Count('promotion_id', distinct=True),
        total_usage_count=Count('id'),
        total_discount_given=Sum('discount_amount'),
        total_cashback_given=Sum('cashback_amount')
    )
    
    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'summary': summary,
        'top_promotions': top_promos,
        'stage_breakdown': list(stage_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def member_analytics_report(request):
    """
    Member Loyalty Analytics
    Query params: company_id, tier (optional)
    """
    from members.models import Member, MemberTransaction
    
    company_id = request.query_params.get('company_id')
    tier = request.query_params.get('tier')
    
    if not company_id:
        return Response(
            {'error': 'company_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    queryset = Member.objects.filter(company_id=company_id, is_active=True)
    
    if tier:
        queryset = queryset.filter(tier=tier)
    
    # Member summary
    summary = queryset.aggregate(
        total_members=Count('id'),
        total_points_balance=Sum('point_balance'),
        total_lifetime_points=Sum('points'),
        total_visits=Sum('total_visits'),
        total_spent=Sum('total_spent'),
        avg_spent_per_member=Avg('total_spent')
    )
    
    # Tier breakdown
    tier_data = Member.objects.filter(
        company_id=company_id, is_active=True
    ).values('tier').annotate(
        member_count=Count('id'),
        total_points=Sum('point_balance'),
        total_spent=Sum('total_spent'),
        avg_spent=Avg('total_spent')
    ).order_by('tier')
    
    # Top spenders
    top_spenders = list(queryset.order_by('-total_spent')[:20].values(
        'member_code', 'name', 'tier', 'total_spent', 'total_visits', 'point_balance'
    ))
    
    # Recent transaction activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_txns = MemberTransaction.objects.filter(
        member__company_id=company_id,
        created_at__gte=thirty_days_ago
    ).values('transaction_type').annotate(
        txn_count=Count('id'),
        total_points=Sum('points')
    )
    
    return Response({
        'summary': summary,
        'tier_breakdown': list(tier_data),
        'top_spenders': top_spenders,
        'recent_activity': list(recent_txns)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_cogs_report(request):
    """
    Inventory COGS & Margin Analysis
    Query params: start_date, end_date, brand_id
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    brand_id = request.query_params.get('brand_id')
    
    if not start_date or not end_date or not brand_id:
        return Response(
            {'error': 'start_date, end_date, and brand_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Sales with COGS
    sales_data = BillItem.objects.filter(
        brand_id=brand_id,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        is_void=False
    ).aggregate(
        total_revenue=Sum('total'),
        total_cogs=Sum(F('quantity') * F('unit_cost'), output_field=DecimalField()),
        total_quantity=Sum('quantity')
    )
    
    # Calculate gross margin
    if sales_data['total_revenue'] and sales_data['total_cogs']:
        gross_margin = sales_data['total_revenue'] - sales_data['total_cogs']
        margin_percent = (gross_margin / sales_data['total_revenue']) * 100
    else:
        gross_margin = 0
        margin_percent = 0
    
    sales_data['gross_margin'] = gross_margin
    sales_data['margin_percent'] = margin_percent
    
    # Inventory movements by type
    inv_movements = InventoryMovement.objects.filter(
        brand_id=brand_id,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).values('movement_type').annotate(
        movement_count=Count('id'),
        total_cost=Sum('total_cost')
    ).order_by('movement_type')
    
    # Product margin analysis
    product_margin = BillItem.objects.filter(
        brand_id=brand_id,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        is_void=False
    ).values('product_id', 'product_name').annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('total'),
        cogs=Sum(F('quantity') * F('unit_cost'), output_field=DecimalField()),
    ).annotate(
        margin=F('revenue') - F('cogs'),
        margin_percent=(F('revenue') - F('cogs')) * 100 / F('revenue')
    ).order_by('-margin')[:20]
    
    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'sales_summary': sales_data,
        'inventory_movements': list(inv_movements),
        'top_margin_products': list(product_margin)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cashier_performance_report(request):
    """
    Cashier Performance Report
    Query params: start_date, end_date, store_id (optional)
    """
    from transactions.models import CashierShift
    
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    store_id = request.query_params.get('store_id')
    
    if not start_date or not end_date:
        return Response(
            {'error': 'start_date and end_date required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Bills by cashier
    bill_queryset = Bill.objects.filter(
        status='PAID',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    if store_id:
        bill_queryset = bill_queryset.filter(store_id=store_id)
    
    cashier_data = bill_queryset.values('created_by').annotate(
        total_bills=Count('id'),
        total_sales=Sum('total'),
        avg_bill_value=Avg('total'),
        total_discount=Sum('discount_amount')
    ).order_by('-total_sales')
    
    # Cashier shift data
    shift_queryset = CashierShift.objects.filter(
        opened_at__date__gte=start_date,
        opened_at__date__lte=end_date
    )
    
    if store_id:
        shift_queryset = shift_queryset.filter(
            store_session_id__in=queryset.values('id')
        )
    
    shift_data = shift_queryset.values('cashier_id').annotate(
        total_shifts=Count('id'),
        total_variance=Sum('variance'),
        avg_variance=Avg('variance')
    )
    
    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'cashier_sales': list(cashier_data),
        'cashier_shifts': list(shift_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_method_report(request):
    """
    Payment Method Distribution Report
    Query params: start_date, end_date, store_id (optional), brand_id (optional)
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    store_id = request.query_params.get('store_id')
    brand_id = request.query_params.get('brand_id')
    
    if not start_date or not end_date:
        return Response(
            {'error': 'start_date and end_date required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get bills in period
    bills = Bill.objects.filter(
        status='PAID',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    if store_id:
        bills = bills.filter(store_id=store_id)
    if brand_id:
        bills = bills.filter(brand_id=brand_id)
    
    bill_ids = bills.values_list('id', flat=True)
    
    # Payment method breakdown
    payment_data = Payment.objects.filter(
        bill_id__in=bill_ids,
        status='SUCCESS'
    ).values('payment_method').annotate(
        payment_count=Count('id'),
        total_amount=Sum('amount'),
        avg_amount=Avg('amount')
    ).order_by('-total_amount')
    
    # Calculate percentages
    total_amount = Payment.objects.filter(
        bill_id__in=bill_ids, status='SUCCESS'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    payment_list = list(payment_data)
    for item in payment_list:
        if total_amount > 0:
            item['percentage'] = float((item['total_amount'] / total_amount) * 100)
        else:
            item['percentage'] = 0
    
    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'total_amount': total_amount,
        'payment_breakdown': payment_list
    })
