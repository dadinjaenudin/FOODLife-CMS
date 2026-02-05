"""
Promotion Compiler Service
Converts Django Promotion models to Edge-compatible JSON format

This compiler transforms database promotion records into JSON structures
that can be consumed by POS/Edge devices for offline promotion evaluation.

Author: Rovo Dev
Date: 2026-01-27
Version: 1.0
"""

from typing import Dict, List, Optional
from decimal import Decimal
from django.db.models import Q
from django.utils import timezone
from promotions.models import Promotion, PromotionTier, PackagePromotion
from products.models import Product, Category
from core.models import Store
import logging
import json

logger = logging.getLogger(__name__)


class PromotionCompiler:
    """
    Main compiler class - converts Promotion model to JSON
    
    Usage:
        compiler = PromotionCompiler()
        json_data = compiler.compile_promotion(promotion)
    """
    
    def __init__(self):
        self.version = "1.0"
        self.compiler_name = "PromotionCompiler"
    
    def compile_promotion(self, promotion: Promotion) -> Dict:
        """
        Main entry point - compile single promotion
        
        Args:
            promotion: Promotion model instance
            
        Returns:
            Dict: JSON-serializable promotion data
            
        Example:
            >>> compiler = PromotionCompiler()
            >>> result = compiler.compile_promotion(my_promotion)
            >>> print(result['code'])
            'WEEKEND20'
        """
        if not promotion.is_active:
            logger.warning(f"Compiling inactive promotion: {promotion.code}")
        
        try:
            compiled = {
                # Basic Info
                "id": str(promotion.id),
                "code": promotion.code,
                "name": promotion.name,
                "description": promotion.description,
                "terms_conditions": promotion.terms_conditions,
                
                # Multi-tenant Context (REQUIRED for Edge Server)
                "company_id": str(promotion.company_id) if promotion.company_id else None,
                "brand_id": str(promotion.brand_id) if promotion.brand_id else None,
                
                # Type & Configuration
                "promo_type": promotion.promo_type,
                "apply_to": promotion.apply_to,
                "execution_stage": promotion.execution_stage,
                "execution_priority": promotion.execution_priority,
                
                # Flags
                "is_active": promotion.is_active,
                "is_auto_apply": promotion.is_auto_apply,
                "require_voucher": promotion.require_voucher,
                "member_only": promotion.member_only,
                "is_stackable": promotion.is_stackable,
                
                # Compiled Sections
                "validity": self.compile_time_rules(promotion),
                "scope": self.compile_scope(promotion),
                "targeting": self.compile_targeting(promotion),
                "rules": self.compile_rules(promotion),
                "limits": self.compile_limits(promotion),
                
                # Metadata
                "compiled_at": timezone.now().isoformat(),
                "compiler_version": self.version,
            }
            
            # Cross-brand handling
            if promotion.is_cross_brand:
                compiled["cross_brand"] = self.compile_cross_brand(promotion)
            
            logger.info(f"Successfully compiled promotion: {promotion.code}")
            return compiled
            
        except Exception as e:
            logger.error(f"Error compiling promotion {promotion.id}: {str(e)}")
            raise
    
    def compile_time_rules(self, promotion: Promotion) -> Dict:
        """
        Compile validity time rules
        
        Returns:
            Dict with date/time validity rules
        """
        return {
            "start_date": promotion.start_date.isoformat(),
            "end_date": promotion.end_date.isoformat(),
            "time_start": promotion.valid_time_start.isoformat() if promotion.valid_time_start else None,
            "time_end": promotion.valid_time_end.isoformat() if promotion.valid_time_end else None,
            "days_of_week": promotion.valid_days if promotion.valid_days else [],
            "exclude_holidays": promotion.exclude_holidays,
        }
    
    def compile_scope(self, promotion: Promotion) -> Dict:
        """
        Compile product/category scope
        
        Determines which products this promotion applies to:
        - All products
        - Specific categories
        - Specific products
        - With exclusions
        """
        scope = {
            "apply_to": promotion.apply_to,
        }
        
        # Categories
        if promotion.apply_to == 'category':
            scope["categories"] = [str(cat_id) for cat_id in promotion.categories.values_list('id', flat=True)]
            scope["exclude_categories"] = [str(cat_id) for cat_id in promotion.exclude_categories.values_list('id', flat=True)]
        
        # Products
        if promotion.apply_to == 'product':
            scope["products"] = [str(prod_id) for prod_id in promotion.products.values_list('id', flat=True)]
            scope["exclude_products"] = [str(prod_id) for prod_id in promotion.exclude_products.values_list('id', flat=True)]
        
        # For 'all' - still need exclusions
        if promotion.apply_to == 'all':
            scope["exclude_categories"] = [str(cat_id) for cat_id in promotion.exclude_categories.values_list('id', flat=True)]
            scope["exclude_products"] = [str(prod_id) for prod_id in promotion.exclude_products.values_list('id', flat=True)]
        
        return scope
    
    def compile_targeting(self, promotion: Promotion) -> Dict:
        """
        Compile store/brand/customer targeting
        
        Determines:
        - Which stores can use this
        - Which brands are included
        - Which customers are eligible
        - Which sales channels
        """
        targeting = {}
        
        # Store targeting
        if promotion.all_stores:
            targeting["stores"] = "all"
        else:
            targeting["stores"] = [str(store_id) for store_id in promotion.stores.values_list('id', flat=True)]
        
        # Brand targeting
        if promotion.scope == 'company':
            targeting["brands"] = "all"
        elif promotion.scope == 'brands':
            targeting["brands"] = [str(brand_id) for brand_id in promotion.brands.values_list('id', flat=True)]
        elif promotion.scope == 'single' and promotion.brand:
            targeting["brands"] = [str(promotion.brand.id)]
        
        # Exclude brands
        if promotion.exclude_brands.exists():
            targeting["exclude_brands"] = [str(brand_id) for brand_id in promotion.exclude_brands.values_list('id', flat=True)]
        
        # Customer targeting
        targeting["member_only"] = promotion.member_only
        if promotion.member_tiers:
            targeting["member_tiers"] = promotion.member_tiers
        
        # Customer type
        targeting["customer_type"] = promotion.customer_type
        
        # Sales channels
        if promotion.sales_channels:
            targeting["sales_channels"] = promotion.sales_channels
        if promotion.exclude_channels:
            targeting["exclude_channels"] = promotion.exclude_channels
        
        return targeting
    
    def compile_rules(self, promotion: Promotion) -> Dict:
        """
        Compile type-specific rules
        Routes to appropriate compiler based on promo_type
        
        This is the main dispatcher that calls the correct
        compilation method for each promotion type.
        """
        compiler_map = {
            'percent_discount': self._compile_percent_discount,
            'amount_discount': self._compile_amount_discount,
            'buy_x_get_y': self._compile_bogo,
            'combo': self._compile_combo,
            'free_item': self._compile_free_item,
            'happy_hour': self._compile_happy_hour,
            'cashback': self._compile_cashback,
            'payment_discount': self._compile_payment_discount,
            'package': self._compile_package,
            'mix_match': self._compile_mix_match,
            'upsell': self._compile_upsell,
            'threshold_tier': self._compile_threshold,
        }
        
        compiler_func = compiler_map.get(promotion.promo_type)
        if not compiler_func:
            logger.error(f"No compiler for promo_type: {promotion.promo_type}")
            return {"error": f"Unsupported promo_type: {promotion.promo_type}"}
        
        return compiler_func(promotion)
    
    # ============================================================================
    # TYPE-SPECIFIC COMPILERS (12 Types)
    # ============================================================================
    
    def _compile_percent_discount(self, promotion: Promotion) -> Dict:
        """
        Type 1: Percent Discount
        Example: 20% off all beverages
        """
        return {
            "type": "percent",
            "discount_percent": float(promotion.discount_percent),
            "max_discount_amount": float(promotion.max_discount_amount) if promotion.max_discount_amount else None,
            "min_purchase": float(promotion.min_purchase),
        }
    
    def _compile_amount_discount(self, promotion: Promotion) -> Dict:
        """
        Type 2: Amount Discount
        Example: Rp 10,000 off
        """
        return {
            "type": "amount",
            "discount_amount": float(promotion.discount_amount),
            "min_purchase": float(promotion.min_purchase),
        }
    
    def _compile_bogo(self, promotion: Promotion) -> Dict:
        """
        Type 3: Buy X Get Y (BOGO)
        Example: Buy 2 Get 1 Free
        """
        rules = {
            "type": "bogo",
            "buy_quantity": promotion.buy_quantity,
            "get_quantity": promotion.get_quantity,
            "get_discount_percent": float(promotion.discount_percent) if promotion.discount_percent else 100.0,
        }
        
        # If specific get_product is defined
        if promotion.get_product:
            rules["get_product_id"] = str(promotion.get_product.id)
            rules["same_product_only"] = False
        else:
            rules["same_product_only"] = True
        
        return rules
    
    def _compile_combo(self, promotion: Promotion) -> Dict:
        """
        Type 4: Combo Deal
        Example: Burger + Fries + Drink = Rp 45,000
        """
        combo_products = list(
            promotion.combo_products.values('id', 'name', 'price')
        )
        
        return {
            "type": "combo",
            "combo_price": float(promotion.combo_price),
            "products": [
                {
                    "product_id": str(p['id']),
                    "quantity": 1,  # Default, can be enhanced
                }
                for p in combo_products
            ],
            "all_required": True,
        }
    
    def _compile_free_item(self, promotion: Promotion) -> Dict:
        """
        Type 5: Free Item
        Example: Buy main course, get free dessert
        """
        rules = {
            "type": "free_item",
            "min_purchase": float(promotion.min_purchase),
        }
        
        if promotion.required_product:
            rules["trigger_product_id"] = str(promotion.required_product.id)
            rules["trigger_min_qty"] = promotion.buy_quantity or 1
        
        if promotion.get_product:
            rules["free_product_id"] = str(promotion.get_product.id)
            rules["free_quantity"] = promotion.get_quantity or 1
        
        return rules
    
    def _compile_happy_hour(self, promotion: Promotion) -> Dict:
        """
        Type 6: Happy Hour
        Example: 50% off coffee 2PM-5PM
        """
        return {
            "type": "happy_hour",
            "discount_percent": float(promotion.discount_percent) if promotion.discount_percent else None,
            "discount_amount": float(promotion.discount_amount) if promotion.discount_amount else None,
            "special_price": float(promotion.happy_hour_price) if promotion.happy_hour_price else None,
            "time_start": promotion.valid_time_start.isoformat() if promotion.valid_time_start else None,
            "time_end": promotion.valid_time_end.isoformat() if promotion.valid_time_end else None,
            "days_of_week": promotion.valid_days if promotion.valid_days else [],
        }
    
    def _compile_cashback(self, promotion: Promotion) -> Dict:
        """
        Type 7: Cashback
        Example: 10% cashback via GoPay
        """
        return {
            "type": "cashback",
            "cashback_type": "percent" if promotion.discount_percent else "amount",
            "cashback_value": float(promotion.discount_percent or promotion.discount_amount),
            "cashback_max": float(promotion.max_discount_amount) if promotion.max_discount_amount else None,
            "min_purchase": float(promotion.min_purchase),
            "payment_methods": promotion.payment_methods if promotion.payment_methods else [],
            "cashback_method": "points",  # Default
        }
    
    def _compile_payment_discount(self, promotion: Promotion) -> Dict:
        """
        Type 8: Payment Method Discount
        Example: 5% off with BCA Card
        """
        return {
            "type": "payment_discount",
            "payment_methods": promotion.payment_methods if promotion.payment_methods else [],
            "discount_type": "percent" if promotion.discount_percent else "amount",
            "discount_value": float(promotion.discount_percent or promotion.discount_amount),
            "max_discount": float(promotion.max_discount_amount) if promotion.max_discount_amount else None,
            "min_purchase": float(promotion.payment_min_amount),
        }
    
    def _compile_package(self, promotion: Promotion) -> Dict:
        """
        Type 9: Package/Set Menu
        Example: Family Package - 2 mains + 2 sides + 4 drinks = Rp 200k
        """
        try:
            package = promotion.package
            items = []
            
            for item in package.items.all():
                item_data = {
                    "item_type": item.item_type,
                    "quantity": float(item.quantity),
                    "is_required": item.is_required,
                }
                
                if item.product:
                    item_data["product_id"] = str(item.product.id)
                elif item.category:
                    item_data["category_id"] = str(item.category.id)
                    item_data["min_selection"] = item.min_selection
                    item_data["max_selection"] = item.max_selection
                
                items.append(item_data)
            
            return {
                "type": "package",
                "package_name": package.package_name,
                "package_price": float(package.package_price),
                "items": items,
                "allow_modification": package.allow_modification,
            }
        except PackagePromotion.DoesNotExist:
            logger.error(f"Package promotion {promotion.id} missing package details")
            return {"type": "package", "error": "Package details not configured"}
    
    def _compile_mix_match(self, promotion: Promotion) -> Dict:
        """
        Type 10: Mix & Match
        Example: Any 3 drinks for Rp 50,000
        """
        rules = promotion.mix_match_rules or {}
        
        return {
            "type": "mix_match",
            "category_id": rules.get('category_id'),
            "required_quantity": rules.get('required_quantity', 3),
            "special_price": float(rules.get('special_price', 0)),
            "allow_same_product": rules.get('allow_same_product', True),
        }
    
    def _compile_upsell(self, promotion: Promotion) -> Dict:
        """
        Type 11: Upsell/Add-on
        Example: Add fries for only Rp 10,000 with burger
        """
        rules = {
            "type": "upsell",
            "upsell_message": promotion.upsell_message,
        }
        
        if promotion.required_product:
            rules["required_product_id"] = str(promotion.required_product.id)
            rules["required_min_qty"] = promotion.buy_quantity or 1
        
        if promotion.upsell_product:
            rules["upsell_product_id"] = str(promotion.upsell_product.id)
            rules["special_price"] = float(promotion.upsell_special_price)
        
        return rules
    
    def _compile_threshold(self, promotion: Promotion) -> Dict:
        """
        Type 12: Threshold/Tiered
        Example: Spend Rp 100k get 10% off, Rp 200k get 15% off
        """
        tiers = []
        
        for tier in promotion.tiers.filter(is_active=True).order_by('tier_order'):
            tier_data = {
                "tier_name": tier.tier_name,
                "min_amount": float(tier.min_amount),
                "max_amount": float(tier.max_amount) if tier.max_amount else None,
                "discount_type": tier.discount_type,
                "discount_value": float(tier.discount_value),
            }
            
            if tier.free_product:
                tier_data["free_product_id"] = str(tier.free_product.id)
            
            if tier.discount_type == 'points_multiplier':
                tier_data["points_multiplier"] = float(tier.points_multiplier)
            
            tiers.append(tier_data)
        
        return {
            "type": "threshold_tier",
            "tiers": tiers,
        }
    
    # ============================================================================
    # ADDITIONAL COMPILATION METHODS
    # ============================================================================
    
    def compile_limits(self, promotion: Promotion) -> Dict:
        """
        Compile usage limits
        
        Returns limits on how many times promotion can be used
        """
        return {
            "max_uses": promotion.max_uses,
            "max_uses_per_customer": promotion.max_uses_per_customer,
            "max_uses_per_day": promotion.max_uses_per_day,
            "current_uses": promotion.current_uses,
        }
    
    def compile_cross_brand(self, promotion: Promotion) -> Dict:
        """
        Compile cross-brand specific rules
        
        For promotions that span multiple brands
        Example: Buy at Brand A, get discount at Brand B
        """
        cross_brand = {
            "enabled": True,
            "type": promotion.cross_brand_type,
        }
        
        if promotion.cross_brand_type == 'trigger_benefit':
            cross_brand["trigger_brands"] = [str(brand_id) for brand_id in promotion.trigger_brands.values_list('id', flat=True)]
            cross_brand["trigger_min_amount"] = float(promotion.trigger_min_amount or 0)
            cross_brand["benefit_brands"] = [str(brand_id) for brand_id in promotion.benefit_brands.values_list('id', flat=True)]
        
        # Add custom rules from JSON field
        if promotion.cross_brand_rules:
            cross_brand["rules"] = promotion.cross_brand_rules
        
        return cross_brand
    
    # ============================================================================
    # BATCH OPERATIONS
    # ============================================================================
    
    def compile_multiple(self, promotions: List[Promotion]) -> List[Dict]:
        """
        Compile multiple promotions (batch operation)
        
        Args:
            promotions: List of Promotion instances
            
        Returns:
            List of compiled promotion dicts
        """
        compiled = []
        for promotion in promotions:
            try:
                compiled.append(self.compile_promotion(promotion))
            except Exception as e:
                logger.error(f"Error compiling promotion {promotion.id}: {str(e)}")
                continue
        
        logger.info(f"Batch compiled {len(compiled)} promotions")
        return compiled
    
    def compile_for_store(self, store_id: str) -> List[Dict]:
        """
        Compile all active promotions for a specific store
        
        This is the main method POS will call to get all promotions
        
        Args:
            store_id: Store UUID
            
        Returns:
            List of compiled promotions applicable to this store
        """
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            logger.error(f"Store {store_id} not found")
            return []
        
        # Get promotions applicable to this store
        now = timezone.now()
        promotions = Promotion.objects.filter(
            Q(all_stores=True) | Q(stores=store),
            is_active=True,
            start_date__lte=now.date(),
            end_date__gte=now.date(),
            company=store.company
        ).distinct()
        
        # Filter by brand
        if store.brand:
            promotions = promotions.filter(
                Q(scope='company') |
                Q(scope='brands', brands=store.brand) |
                Q(scope='single', brand=store.brand)
            )
        
        logger.info(f"Found {promotions.count()} promotions for store {store.store_name}")
        
        # Compile promotions and add store_id context
        compiled = self.compile_multiple(promotions)
        
        # Add store_id to each compiled promotion for context
        for promo in compiled:
            promo['store_id'] = str(store_id)
        
        return compiled
    
    def compile_for_company(self, company_id: str) -> Dict:
        """
        Compile all active promotions for ALL stores in a company
        
        This is the main method for HO to compile promotions for entire company.
        Generates promotion JSON for every store and brand combination.
        
        Args:
            company_id: Company UUID
            
        Returns:
            Dict with structure:
            {
                "company_id": "uuid",
                "compiled_at": "timestamp",
                "stores": {
                    "store-uuid-1": [promotions...],
                    "store-uuid-2": [promotions...],
                },
                "summary": {
                    "total_stores": 10,
                    "total_promotions": 50,
                    "stores_with_promotions": 8
                }
            }
        """
        from core.models import Company
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            logger.error(f"Company {company_id} not found")
            return {
                "error": "Company not found",
                "company_id": company_id
            }
        
        # Get all active stores for this company
        stores = Store.objects.filter(
            company=company,
            is_active=True
        ).select_related('company').prefetch_related('brands').order_by('company__name', 'store_name')
        
        logger.info(f"Compiling promotions for company {company.name} ({stores.count()} stores)")
        
        result = {
            "company_id": str(company_id),
            "company_name": company.name,
            "compiled_at": timezone.now().isoformat(),
            "stores": {},
            "summary": {
                "total_stores": stores.count(),
                "total_promotions": 0,
                "stores_with_promotions": 0,
                "by_brand": {}
            }
        }
        
        # Compile for each store
        for store in stores:
            store_promotions = self.compile_for_store(str(store.id))
            
            result["stores"][str(store.id)] = {
                "store_id": str(store.id),
                "store_code": store.store_code,
                "store_name": store.store_name,
                "brand_id": str(store.brand_id),
                "brand_name": store.brand.name,
                "promotions": store_promotions,
                "count": len(store_promotions)
            }
            
            # Update summary
            result["summary"]["total_promotions"] += len(store_promotions)
            if len(store_promotions) > 0:
                result["summary"]["stores_with_promotions"] += 1
            
            # Track by brand
            brand_name = store.brand.name
            if brand_name not in result["summary"]["by_brand"]:
                result["summary"]["by_brand"][brand_name] = {
                    "stores": 0,
                    "promotions": 0
                }
            result["summary"]["by_brand"][brand_name]["stores"] += 1
            result["summary"]["by_brand"][brand_name]["promotions"] += len(store_promotions)
        
        logger.info(
            f"Company compilation complete: {result['summary']['total_promotions']} promotions "
            f"across {result['summary']['stores_with_promotions']}/{result['summary']['total_stores']} stores"
        )
        
        return result


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def compile_promotion(promotion: Promotion) -> Dict:
    """
    Convenience function for quick compilation
    
    Usage:
        from promotions.services.compiler import compile_promotion
        json_data = compile_promotion(my_promotion)
    """
    compiler = PromotionCompiler()
    return compiler.compile_promotion(promotion)


def compile_promotions_for_store(store_id: str) -> List[Dict]:
    """
    Convenience function for store sync
    
    Usage:
        from promotions.services.compiler import compile_promotions_for_store
        promotions_json = compile_promotions_for_store('store-uuid')
    """
    compiler = PromotionCompiler()
    return compiler.compile_for_store(store_id)
