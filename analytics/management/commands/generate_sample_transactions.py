"""
Management command to generate sample transaction data for testing reports
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random
import uuid

from core.models import Company, Brand, Store, User
from products.models import Product
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
        
        store = Store.objects.filter(brands=brand, is_active=True).first()
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
        self.stdout.write(f'Using Brand: {brand.name}')
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
        day_count = 0
        
        while current_date <= end_date:
            day_count += 1
            # Randomize number of bills per day (±30%)
            daily_bills = int(bills_per_day * random.uniform(0.7, 1.3))
            
            daily_revenue = Decimal('0.00')
            
            for _ in range(daily_bills):
                # Generate random time within business hours (10:00-22:00)
                hour = random.randint(10, 21)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                
                bill_datetime = current_date.replace(
                    hour=hour,
                    minute=minute,
                    second=second,
                    microsecond=0
                )
                
                # Random member (30% chance)
                member = random.choice(members) if members and random.random() < 0.3 else None
                
                # Random number of items (1-5)
                num_items = random.randint(1, 5)
                selected_products = random.sample(products, min(num_items, len(products)))
                
                # Calculate bill totals
                subtotal = Decimal('0.00')
                for product in selected_products:
                    quantity = random.randint(1, 3)
                    subtotal += product.price * quantity
                
                # Apply random discount (0-20%)
                discount_percent = random.choice([0, 0, 0, 5, 10, 15, 20])  # More likely to have no discount
                discount_amount = subtotal * Decimal(discount_percent) / Decimal(100)
                
                after_discount = subtotal - discount_amount
                
                # Tax (10%)
                tax_rate = Decimal('10.00')
                tax_amount = after_discount * tax_rate / Decimal(100)
                
                # Service charge (5%)
                service_charge_rate = Decimal('5.00')
                service_charge = after_discount * service_charge_rate / Decimal(100)
                
                total = after_discount + tax_amount + service_charge
                
                # Create Bill
                bill_number = f'TRX-{day_count:04d}-{total_bills_created:05d}'
                terminal_uuid = str(uuid.uuid4())  # Generate UUID for terminal
                
                try:
                    bill = Bill.objects.create(
                        company_id=company.id,
                        brand_id=brand.id,
                        store_id=store.id,
                        terminal_id=terminal_uuid,
                        bill_number=bill_number,
                        bill_type='DINE_IN' if random.random() < 0.7 else 'TAKEAWAY',
                        status='PAID',
                        pax=random.randint(1, 6),
                        member_id=member.id if member else None,
                        member_code=member.member_code if member else None,
                        subtotal=subtotal,
                        tax_rate=tax_rate,
                        tax_amount=tax_amount,
                        service_charge_rate=service_charge_rate,
                        service_charge=service_charge,
                        discount_amount=discount_amount,
                        total=total,
                        created_by=user.id,
                        created_at=bill_datetime,
                        closed_by=user.id,
                        closed_at=bill_datetime
                    )
                    
                    # Create Bill Items
                    for product in selected_products:
                        quantity = random.randint(1, 3)
                        unit_price = product.price
                        item_subtotal = unit_price * quantity
                        
                        BillItem.objects.create(
                            bill=bill,
                            product_id=product.id,
                            product_sku=product.sku,
                            product_name=product.name,
                            quantity=quantity,
                            unit_price=unit_price,
                            unit_cost=product.cost,
                            subtotal=item_subtotal,
                            is_void=False,
                            created_by=user.id
                        )
                    
                    # Create Payment
                    payment_method = random.choices(
                        [pm[0] for pm in payment_methods],
                        weights=[pm[1] for pm in payment_methods]
                    )[0]
                    
                    Payment.objects.create(
                        bill=bill,
                        payment_method=payment_method,
                        amount=total,
                        status='SUCCESS',
                        created_by=user.id
                    )
                    
                    total_bills_created += 1
                    daily_revenue += total
                    total_revenue += total
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error creating bill: {e}'))
                    continue
            
            # Progress indicator
            if day_count % 5 == 0:
                self.stdout.write(
                    f'Day {day_count}/{days} - Generated {daily_bills} bills - '
                    f'Daily Revenue: Rp {daily_revenue:,.0f}'
                )
            
            current_date += timedelta(days=1)
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('Generation Complete!'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'Total Bills Created: {total_bills_created}'))
        self.stdout.write(self.style.SUCCESS(f'Total Revenue: Rp {total_revenue:,.0f}'))
        self.stdout.write(self.style.SUCCESS(f'Average Bill Value: Rp {total_revenue/total_bills_created if total_bills_created > 0 else 0:,.0f}'))
        self.stdout.write(self.style.SUCCESS(f'Date Range: {start_date.date()} to {end_date.date()}\n'))
