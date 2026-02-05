from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

# Import models - handle missing imports gracefully
try:
    from core.models import Company, Brand, Store
except ImportError:
    Company = Brand = Store = None

try:
    from products.models import Product, Category
except ImportError:
    Product = Category = None

try:
    from members.models import Member
except ImportError:
    Member = None

try:
    from transactions.models import Bill, Payment
except ImportError:
    Bill = Payment = None

try:
    from promotions.models import Promotion
except ImportError:
    Promotion = None


@login_required
def index(request):
    """
    Main dashboard view with key metrics and charts
    """
    # Date range for statistics (last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Get user's company context
    user_company = request.user.company if hasattr(request.user, 'company') else None
    
    # Key metrics with safe checks
    context = {
        'total_stores': 0,
        'total_products': 0,
        'total_members': 0,
        'active_promotions': 0,
        'recent_sales': {'total': 0, 'count': 0, 'avg': 0},
        'recent_bills': [],
        'recent_members': [],
    }
    
    # Safe query execution
    if Store:
        try:
            context['total_stores'] = Store.objects.filter(
                company=user_company
            ).count() if user_company else Store.objects.count()
        except:
            pass
    
    if Product:
        try:
            context['total_products'] = Product.objects.filter(
                company=user_company
            ).count() if user_company else Product.objects.count()
        except:
            pass
    
    if Member:
        try:
            context['total_members'] = Member.objects.filter(
                company=user_company
            ).count() if user_company else Member.objects.count()
            
            context['recent_members'] = Member.objects.filter(
                created_at__gte=start_date
            ).select_related('company').order_by('-created_at')[:10]
        except:
            pass
    
    if Promotion:
        try:
            context['active_promotions'] = Promotion.objects.filter(
                company=user_company,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            ).count() if user_company else Promotion.objects.filter(
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            ).count()
        except:
            pass
    
    if Bill:
        try:
            # Sales metrics (last 30 days)
            context['recent_sales'] = Bill.objects.filter(
                created_at__gte=start_date,
                status='PAID'
            ).aggregate(
                total=Sum('final_total'),
                count=Count('id'),
                avg=Avg('final_total')
            )
            
            # Recent activities
            context['recent_bills'] = Bill.objects.filter(
                created_at__gte=start_date
            ).select_related('store', 'cashier').order_by('-created_at')[:10]
        except:
            pass
    
    return render(request, 'dashboard/index.html', context)


@login_required
def reports_dashboard(request):
    """
    Detailed reports and analytics dashboard
    """
    context = {}
    return render(request, 'dashboard/reports.html', context)
