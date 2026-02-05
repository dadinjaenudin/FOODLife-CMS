"""
Create Sample Promotions for All Types

Usage:
    python manage.py create_promotion_samples
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from promotions.models import Promotion
from core.models import Company, Brand, Store, User


class Command(BaseCommand):
    help = 'Create sample promotions for all types'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting promotion sample data creation...'))
        self.stdout.write('=' * 60)
        
        # Get or create system user for created_by
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("❌ No user found. Please create a user first."))
            return
        
        self.stdout.write(f"✅ Using User: {user.username}")
        
        # Get entities
        company = Company.objects.first()
        if not company:
            self.stdout.write(self.style.ERROR("❌ No company found. Please create a company first."))
            return
        
        brand = Brand.objects.filter(company=company).first()
        if not brand:
            self.stdout.write(self.style.ERROR("❌ No brand found. Please create a brand first."))
            return
        
        stores = list(Store.objects.filter(brands=brand)[:3])
        if not stores:
            self.stdout.write(self.style.ERROR("❌ No stores found. Please create stores first."))
            return
        
        self.stdout.write(f"✅ Using Company: {company.name}")
        self.stdout.write(f"✅ Using Brand: {brand.name}")
        self.stdout.write(f"✅ Using Stores: {len(stores)} store(s)")
        self.stdout.write('=' * 60)
        
        # Date range
        today = timezone.now().date()
        start_date = today
        end_date = today + timedelta(days=30)
        
        promotions_created = 0
        
        # =================================================================
        # 1. PERCENT DISCOUNT - Basic 20% off
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='SAVE20',
            defaults={
                'name': 'Save 20% - Weekend Special',
                'description': 'Get 20% discount on all items during weekend',
                'promo_type': 'percent_discount',
                'discount_percent': Decimal('20.00'),
                'discount_amount': Decimal('0.00'),
                'max_discount_amount': Decimal('50000.00'),
                'min_purchase': Decimal('100000.00'),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': False,
                'member_only': False,
                'is_stackable': True,
                'priority': 100,
                'company': company,
                'brand': brand,
                'all_stores': True,
                'created_by': user,
            }
        )
        if created:
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: Percent Discount (20% off, max cap Rp50,000)")
        
        # =================================================================
        # 2. PERCENT DISCOUNT - High 60% (tests warning)
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='MEGA60',
            defaults={
                'name': 'Mega Sale 60% Off',
                'description': 'Massive 60% discount - Limited time only!',
                'promo_type': 'percent_discount',
                'discount_percent': Decimal('60.00'),
                'discount_amount': Decimal('0.00'),
                'max_discount_amount': Decimal('100000.00'),
                'min_purchase': Decimal('200000.00'),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': False,
                'member_only': True,
                'is_stackable': False,
                'priority': 150,
                'company': company,
                'brand': brand,
                'all_stores': False,
                'created_by': user,
            }
        )
        if created:
            promo.stores.set(stores[:2])
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: Percent (60% off - HIGH, 2 stores)")
        
        # =================================================================
        # 3. AMOUNT DISCOUNT - Flat Rp10,000 off
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='FLAT10K',
            defaults={
                'name': 'Flat Rp10,000 Off',
                'description': 'Get instant Rp10,000 discount',
                'promo_type': 'amount_discount',
                'discount_percent': Decimal('0.00'),
                'discount_amount': Decimal('10000.00'),
                'max_discount_amount': None,
                'min_purchase': Decimal('50000.00'),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': True,
                'member_only': False,
                'is_stackable': True,
                'priority': 50,
                'company': company,
                'brand': brand,
                'all_stores': True,
                'created_by': user,
            }
        )
        if created:
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: Amount (Rp10,000 off, auto-apply)")
        
        # =================================================================
        # 4. AMOUNT DISCOUNT - Cashback Rp50,000
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='CASHBACK50K',
            defaults={
                'name': 'Cashback Rp50,000',
                'description': 'Spend Rp300k get Rp50k cashback',
                'promo_type': 'amount_discount',
                'discount_percent': Decimal('0.00'),
                'discount_amount': Decimal('50000.00'),
                'max_discount_amount': None,
                'min_purchase': Decimal('300000.00'),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': False,
                'member_only': False,
                'is_stackable': False,
                'priority': 200,
                'max_uses': 100,
                'company': company,
                'brand': brand,
                'all_stores': True,
                'created_by': user,
            }
        )
        if created:
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: Amount (Rp50,000 off, max 100 uses)")
        
        # =================================================================
        # 5. HAPPY HOUR - Lunch 30% off
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='LUNCH30',
            defaults={
                'name': 'Happy Hour Lunch - 30% Off',
                'description': 'Get 30% off during lunch (11 AM - 2 PM)',
                'promo_type': 'happy_hour',
                'discount_percent': Decimal('30.00'),
                'discount_amount': Decimal('0.00'),
                'max_discount_amount': Decimal('30000.00'),
                'min_purchase': Decimal('0.00'),
                'valid_time_start': datetime.strptime('11:00', '%H:%M').time(),
                'valid_time_end': datetime.strptime('14:00', '%H:%M').time(),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': True,
                'member_only': False,
                'is_stackable': False,
                'priority': 120,
                'max_uses_per_day': 50,
                'company': company,
                'brand': brand,
                'all_stores': True,
                'created_by': user,
            }
        )
        if created:
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: Happy Hour (30% off, 11:00-14:00, max 50/day)")
        
        # =================================================================
        # 6. HAPPY HOUR - Dinner 25% off
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='DINNER25',
            defaults={
                'name': 'Dinner Special - 25% Off',
                'description': 'Evening discount 6 PM - 8 PM',
                'promo_type': 'happy_hour',
                'discount_percent': Decimal('25.00'),
                'discount_amount': Decimal('0.00'),
                'max_discount_amount': Decimal('40000.00'),
                'min_purchase': Decimal('100000.00'),
                'valid_time_start': datetime.strptime('18:00', '%H:%M').time(),
                'valid_time_end': datetime.strptime('20:00', '%H:%M').time(),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': False,
                'member_only': True,
                'is_stackable': False,
                'priority': 110,
                'company': company,
                'brand': brand,
                'all_stores': False,
                'created_by': user,
            }
        )
        if created:
            promo.stores.set(stores)
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: Happy Hour (25% off, 18:00-20:00, member only)")
        
        # =================================================================
        # 7. BOGO - Buy 2 Get 1
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='BOGO21',
            defaults={
                'name': 'Buy 2 Get 1 Free',
                'description': 'Purchase 2 items get 1 free',
                'promo_type': 'buy_x_get_y',
                'discount_percent': Decimal('0.00'),
                'discount_amount': Decimal('0.00'),
                'buy_quantity': 2,
                'get_quantity': 1,
                'max_discount_amount': Decimal('0.00'),
                'min_purchase': Decimal('0.00'),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': False,
                'member_only': False,
                'is_stackable': False,
                'priority': 80,
                'max_uses_per_customer': 3,
                'company': company,
                'brand': brand,
                'all_stores': True,
                'created_by': user,
            }
        )
        if created:
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: BOGO (Buy 2 Get 1, max 3/customer)")
        
        # =================================================================
        # 8. BOGO - Buy 3 Get 2
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='BOGO32',
            defaults={
                'name': 'Buy 3 Get 2 Free - Group Deal',
                'description': 'Buy 3 items get 2 free',
                'promo_type': 'buy_x_get_y',
                'discount_percent': Decimal('0.00'),
                'discount_amount': Decimal('0.00'),
                'buy_quantity': 3,
                'get_quantity': 2,
                'max_discount_amount': Decimal('0.00'),
                'min_purchase': Decimal('0.00'),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': False,
                'member_only': True,
                'is_stackable': False,
                'priority': 90,
                'max_uses': 50,
                'company': company,
                'brand': brand,
                'all_stores': False,
                'created_by': user,
            }
        )
        if created:
            promo.stores.set(stores[:1])
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: BOGO (Buy 3 Get 2, member only, 1 store)")
        
        # =================================================================
        # 9. THRESHOLD TIER
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='TIER100K',
            defaults={
                'name': 'Tiered Discount - Spend & Save',
                'description': 'Spend Rp500k get Rp100k off',
                'promo_type': 'threshold_tier',
                'discount_percent': Decimal('0.00'),
                'discount_amount': Decimal('100000.00'),
                'max_discount_amount': Decimal('0.00'),
                'min_purchase': Decimal('500000.00'),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': True,
                'member_only': False,
                'is_stackable': False,
                'priority': 70,
                'company': company,
                'brand': brand,
                'all_stores': True,
                'created_by': user,
            }
        )
        if created:
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: Tiered (Rp100k off for Rp500k)")
        
        # =================================================================
        # 10. PACKAGE DEAL
        # =================================================================
        promo, created = Promotion.objects.update_or_create(
            code='PACKAGE1',
            defaults={
                'name': 'Family Package Deal',
                'description': 'Special bundle price',
                'promo_type': 'package',
                'discount_percent': Decimal('0.00'),
                'discount_amount': Decimal('25000.00'),
                'max_discount_amount': Decimal('0.00'),
                'min_purchase': Decimal('0.00'),
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'is_auto_apply': False,
                'member_only': False,
                'is_stackable': False,
                'priority': 60,
                'company': company,
                'brand': brand,
                'all_stores': True,
                'created_by': user,
            }
        )
        if created:
            promotions_created += 1
        self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code})")
        self.stdout.write(f"   Type: Package (Rp25k off)")
        
        # =================================================================
        # CROSS-BRAND PROMOTIONS (NEW!)
        # =================================================================
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('🔄 CROSS-BRAND PROMOTIONS')
        self.stdout.write('=' * 60)
        
        # Get all brands for cross-brand
        all_brands = list(Brand.objects.filter(company=company, is_active=True))
        
        if len(all_brands) >= 2:
            # =================================================================
            # 11. CROSS-BRAND: Trigger-Benefit
            # =================================================================
            promo, created = Promotion.objects.update_or_create(
                code='XBRAND-COFFEE20',
                defaults={
                    'name': 'Cross-Brand Coffee Deal',
                    'description': 'Buy coffee Rp25k at Brand A, get 20% off at Brand B',
                    'promo_type': 'percent_discount',
                    'discount_percent': Decimal('20.00'),
                    'discount_amount': Decimal('0.00'),
                    'max_discount_amount': Decimal('30000.00'),
                    'min_purchase': Decimal('0.00'),
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_active': True,
                    'is_auto_apply': False,
                    'member_only': False,
                    'is_stackable': False,
                    'priority': 85,
                    'company': company,
                    'brand': brand,
                    'all_stores': True,
                    'is_cross_brand': True,
                    'cross_brand_type': 'trigger_benefit',
                    'trigger_min_amount': Decimal('25000.00'),
                    'created_by': user,
                }
            )
            if created:
                promo.trigger_brands.set([all_brands[0]])
                promo.benefit_brands.set([all_brands[1]])
                promotions_created += 1
            self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code}) 🔄")
            self.stdout.write(f"   Type: Cross-Brand Trigger-Benefit")
            self.stdout.write(f"   Trigger: {all_brands[0].name} (min Rp25k)")
            self.stdout.write(f"   Benefit: {all_brands[1].name} (20% off)")
            
            # =================================================================
            # 12. CROSS-BRAND: Multi-Brand Spend
            # =================================================================
            if len(all_brands) >= 3:
                promo, created = Promotion.objects.update_or_create(
                    code='XBRAND-MULTI50K',
                    defaults={
                        'name': 'Multi-Brand Loyalty Reward',
                        'description': 'Spend Rp100k at 2+ brands, get Rp50k voucher',
                        'promo_type': 'amount_discount',
                        'discount_percent': Decimal('0.00'),
                        'discount_amount': Decimal('50000.00'),
                        'max_discount_amount': None,
                        'min_purchase': Decimal('0.00'),
                        'start_date': start_date,
                        'end_date': end_date,
                        'is_active': True,
                        'is_auto_apply': False,
                        'member_only': True,
                        'is_stackable': False,
                        'priority': 95,
                        'max_uses_per_customer': 1,
                        'company': company,
                        'brand': brand,
                        'all_stores': True,
                        'is_cross_brand': True,
                        'cross_brand_type': 'multi_brand_spend',
                        'trigger_min_amount': Decimal('100000.00'),
                        'created_by': user,
                    }
                )
                if created:
                    promo.trigger_brands.set(all_brands[:3])
                    promo.benefit_brands.set(all_brands[:3])
                    promotions_created += 1
                self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code}) 🔄")
                self.stdout.write(f"   Type: Cross-Brand Multi-Spend")
                self.stdout.write(f"   Trigger: 3 brands (min Rp100k total)")
                self.stdout.write(f"   Benefit: Rp50k voucher")
            
            # =================================================================
            # 13. CROSS-BRAND: Same Receipt
            # =================================================================
            promo, created = Promotion.objects.update_or_create(
                code='XBRAND-SAME15',
                defaults={
                    'name': 'Same Receipt Multi-Brand',
                    'description': 'Buy from 2+ brands in one transaction, get 15% off',
                    'promo_type': 'percent_discount',
                    'discount_percent': Decimal('15.00'),
                    'discount_amount': Decimal('0.00'),
                    'max_discount_amount': Decimal('75000.00'),
                    'min_purchase': Decimal('150000.00'),
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_active': True,
                    'is_auto_apply': True,
                    'member_only': False,
                    'is_stackable': False,
                    'priority': 105,
                    'company': company,
                    'brand': brand,
                    'all_stores': True,
                    'is_cross_brand': True,
                    'cross_brand_type': 'same_receipt',
                    'trigger_min_amount': None,
                    'created_by': user,
                }
            )
            if created:
                promo.trigger_brands.set(all_brands)
                promo.benefit_brands.set(all_brands)
                promotions_created += 1
            self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Updated'}: {promo.name} ({promo.code}) 🔄")
            self.stdout.write(f"   Type: Cross-Brand Same Receipt")
            self.stdout.write(f"   Trigger: All {len(all_brands)} brands")
            self.stdout.write(f"   Benefit: 15% off entire bill")
            
            self.stdout.write(f"\n✨ Cross-Brand promotions showcase advanced marketing!")
        else:
            self.stdout.write(f"⚠️  Skipping cross-brand (need 2+ brands, found {len(all_brands)})")
        
        # Summary
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'\n🎉 Complete!'))
        self.stdout.write(f"✅ New promotions: {promotions_created}")
        self.stdout.write(f"✅ Total in system: {Promotion.objects.count()}")
        
        self.stdout.write("\n📊 By Type:")
        for promo_type, label in Promotion.PROMO_TYPE_CHOICES:
            count = Promotion.objects.filter(promo_type=promo_type).count()
            self.stdout.write(f"   - {label}: {count}")
        
        self.stdout.write("\n🔗 Access at: http://localhost:8002/promotions/")
        
        self.stdout.write("\n📋 All Promotions:")
        for promo in Promotion.objects.all().order_by('promo_type', 'code'):
            status = "✓" if promo.is_active else "✗"
            self.stdout.write(f"   [{status}] {promo.code:15s} - {promo.name}")
