"""
Management command to generate sample transaction data for testing reports
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
import random
import uuid

from core.models import Company, Brand, Store, User
from products.models import Product, Category
from members.models import Member
from transactions.models import Bill, BillItem, Payment


class Command(BaseCommand):
    help = 'Generate sample transaction data for testing sales reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of transaction history to generate (default: 30)'
        )
        parser.add_argument(
            '--bills-per-day',
            type=int,
            default=50,
            help='Average number of bills per day (default: 50)'
        )

    def handle(self, *args, **options):
        days = options['days']
        bills_per_day = options['bills_per_day']
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('Generating Sample Transaction Data'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}\n'))
        
        # Get or create required data
        company = Company.objects.filter(is_active=True).first()
        if not company:
            self.stdout.write(self.style.ERROR('No active company found. Run generate_sample_data first.'))
            return
        
        brand = Brand.objects.filter(company=company, is_active=True).first()
        if not brand:
            self.stdout.write(self.style.ERROR('No active brand found. Run generate_sample_data first.'))
            return
        
        store = Store.objects.filter(brand=brand, is_active=True).first()
        if not store:
            self.stdout.write(self.style.ERROR('No active store found. Run generate_sample_data first.'))
            return
        
        user = User.objects.filter(is_active=True).first()
        if not user:
            self.stdout.write(self.style.ERROR('No active user found.'))
            return
        
        products = list(Product.objects.filter(brand=brand, is_active=True))
        if not products:
            self.stdout.write(self.style.ERROR('No active products found. Run generate_sample_data first.'))
            return
        
        members = list(Member.objects.filter(company=company, is_active=True))
        
        self.stdout.write(f'Using Store: {store.store_name}')
        self.stdout.write(f'Using Brand: {brand.brand_name}')
        self.stdout.write(f'Products available: {len(products)}')
        self.stdout.write(f'Members available: {len(members)}\n')
        
        # Payment methods with weights
        payment_methods = [
            ('CASH', 0.40),
            ('CARD', 0.25),
            ('QRIS', 0.20),
            ('GOPAY', 0.10),
            ('OVO', 0.05)
        ]
        
        # Generate transactions for each day
        total_bills_created = 0
        total_revenue = Decimal('0.00')
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        current_date = start_date
        
        while current_date <= end_date:
            # Randomize number of bills per day (±30%)
            daily_bills = int(bills_per_day * random.uniform(0.7, 1.3))
            
            for _ in range(daily_bills):
                # Generate random time within business hours (10:00-22:00)
                hour = random.randint(10, 21)
                minute = random.randint(0, 59)
                bill_datetime = current_date.replace(hour=hour, minute=minute, second=0)
                
                # Random customer count
                customer_count = random.randint(1, 6)
                
                # Create bill
                bill_number = f"BILL-{current_date.strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
                
                # Random member (30% chance)
                member = random.choice(members) if members and random.random() < 0.3 else None
                
                bill = Bill.objects.create(
                    company=company,
                    brand=brand,
                    store=store,
                    bill_number=bill_number,
                    bill_date=bill_datetime,
                    customer_count=customer_count,
                    member=member,
                    order_type='DINE_IN' if random.random() < 0.7 else random.choice(['TAKEAWAY', 'DELIVERY']),
                    table_number=f"T{random.randint(1, 20)}" if random.random() < 0.7 else None,
                    status='PAID',
                    subtotal=Decimal('0.00'),
                    tax_amount=Decimal('0.00'),
                    service_charge=Decimal('0.00'),
                    discount_amount=Decimal('0.00'),
                    total_amount=Decimal('0.00'),
                    created_by=user,
                    created_at=bill_datetime,
                    updated_at=bill_datetime
                )
                
                # Add 1-5 items per bill
                num_items = random.randint(1, 5)
                selected_products = random.sample(products, min(num_items, len(products)))
                
                subtotal = Decimal('0.00')
                
                for product in selected_products:
                    quantity = random.randint(1, 3)
                    unit_price = product.base_price
                    item_subtotal = unit_price * quantity
                    
                    # Random unit cost (60-80% of price)
                    unit_cost = unit_price * Decimal(str(random.uniform(0.6, 0.8)))
                    
                    BillItem.objects.create(
                        bill=bill,
                        company=company,
                        brand=brand,
                        product=product,
                        product_sku=product.product_code,
                        product_name=product.product_name,
                        category=product.category,
                        quantity=quantity,
                        unit_price=unit_price,
                        unit_cost=unit_cost,
                        subtotal=item_subtotal,
                        discount_amount=Decimal('0.00'),
                        total=item_subtotal,
                        is_void=False,
                        created_at=bill_datetime,
                        updated_at=bill_datetime
                    )
                    
                    subtotal += item_subtotal
                
                # Calculate totals
                tax_rate = Decimal('0.10')  # 10% tax
                service_rate = Decimal('0.05')  # 5% service
                
                tax_amount = subtotal * tax_rate
                service_charge = subtotal * service_rate
                
                # Random discount (10% chance)
                discount_amount = Decimal('0.00')
                if random.random() < 0.1:
                    discount_amount = subtotal * Decimal(str(random.uniform(0.05, 0.20)))
                
                total_amount = subtotal + tax_amount + service_charge - discount_amount
                
                # Update bill
                bill.subtotal = subtotal
                bill.tax_amount = tax_amount
                bill.service_charge = service_charge
                bill.discount_amount = discount_amount
                bill.total_amount = total_amount
                bill.save()
                
                # Create payment
                payment_method = random.choices(
                    [p[0] for p in payment_methods],
                    weights=[p[1] for p in payment_methods]
                )[0]
                
                Payment.objects.create(
                    bill=bill,
                    payment_method=payment_method,
                    amount=total_amount,
                    status='SUCCESS',
                    reference_no=f"PAY-{uuid.uuid4().hex[:12].upper()}",
                    created_at=bill_datetime,
                    updated_at=bill_datetime
                )
                
                total_bills_created += 1
                total_revenue += total_amount
            
            # Progress indicator
            if current_date.day == 1 or current_date == start_date:
                self.stdout.write(f'  Generating {current_date.strftime("%B %Y")}...')
            
            current_date += timedelta(days=1)
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✓ Sample Transaction Data Generated!'))
        self.stdout.write('='*60)
        self.stdout.write(f'Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
        self.stdout.write(f'Days: {days}')
        self.stdout.write(f'Total Bills: {total_bills_created:,}')
        self.stdout.write(f'Total Revenue: Rp {total_revenue:,.0f}')
        self.stdout.write(f'Avg Bills/Day: {total_bills_created/days:.1f}')
        self.stdout.write(f'Avg Bill Value: Rp {total_revenue/total_bills_created:,.0f}\n')
        
        # Show payment method distribution
        payment_dist = Payment.objects.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-count')
        
        self.stdout.write('Payment Method Distribution:')
        for pm in payment_dist:
            percentage = (pm['count'] / total_bills_created) * 100
            self.stdout.write(f"  {pm['payment_method']}: {pm['count']:,} ({percentage:.1f}%) - Rp {pm['total']:,.0f}")
        
        self.stdout.write('\n' + self.style.SUCCESS('All done! You can now view reports at /reports/sales-report/'))
