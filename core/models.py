"""
Core Multi-Tenant Models
Hierarchy: Company → Brand → Store → Terminal
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """
    Root Tenant - Top Level Organization
    Example: Yogya Group (YGY)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, help_text="Company code (e.g., YGY)")
    name = models.CharField(max_length=200, help_text="Company name")
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    timezone = models.CharField(max_length=50, default='Asia/Jakarta')
    is_active = models.BooleanField(default=True)
    
    # Loyalty Program Configuration
    point_expiry_months = models.IntegerField(
        default=12,
        validators=[MinValueValidator(0)],
        help_text="Points expire after X months (0 = never expire)"
    )
    points_per_currency = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0.01)],
        help_text="Points earned per currency unit (e.g., 1.00 = 1 point per Rp 1)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'company'
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_point_expiry_months(self):
        """Get point expiry months for this company"""
        return self.point_expiry_months


class Brand(models.Model):
    """
    Business Concept - Franchise Brand
    Example: Ayam Geprek Express, Bakso Boedjangan
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='brands')
    code = models.CharField(max_length=20, help_text="Brand code (e.g., YGY-001)")
    name = models.CharField(max_length=200, help_text="Brand name")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, help_text="NPWP")
    
    # Financial Configuration
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=11.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Tax rate in percentage (e.g., 11.00 for 11%)"
    )
    service_charge = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Service charge in percentage (e.g., 5.00 for 5%)"
    )
    
    # Loyalty Override (nullable = use company default)
    point_expiry_months_override = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Override company point expiry policy (leave blank to use company default)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'brand'
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        ordering = ['name']
        unique_together = [['company', 'code']]
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_point_expiry_months(self):
        """Get point expiry months for this brand (override or company default)"""
        if self.point_expiry_months_override is not None:
            return self.point_expiry_months_override
        return self.company.get_point_expiry_months()


class Store(models.Model):
    """
    Physical Location - Edge Server (SINGLETON per Edge)
    Can host multiple brands (Food Court scenario)
    Example: Cabang BSD, Cabang Senayan
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='stores',
                                help_text="Parent company that owns this store")
    brands = models.ManyToManyField(Brand, through='StoreBrand', related_name='stores',
                                    help_text="Brands/tenants operating in this store")
    store_code = models.CharField(max_length=20, unique=True, help_text="Store code (e.g., YGY-001-BSD)")
    store_name = models.CharField(max_length=200, help_text="Store name")
    address = models.TextField()
    phone = models.CharField(max_length=20)
    timezone = models.CharField(max_length=50, default='Asia/Jakarta')
    
    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'store'
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'
        ordering = ['store_name']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['store_code']),
        ]
    
    def __str__(self):
        return f"{self.store_code} - {self.store_name}"
    
    def get_active_brands(self):
        """Get all active brands in this store"""
        return self.brands.filter(is_active=True)
    
    def has_brand(self, brand):
        """Check if this store has a specific brand"""
        return self.brands.filter(id=brand.id).exists()


class StoreBrand(models.Model):
    """
    Junction Table: Store ↔ Brand (Many-to-Many)
    Represents which brands operate in which stores
    Food Court scenario: 1 Store can have multiple Brands (tenants)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='store_brands')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='brand_stores')
    
    # Operational status
    is_active = models.BooleanField(default=True, help_text="Is this brand currently active in this store?")
    
    # Dates
    start_date = models.DateField(null=True, blank=True, help_text="When this brand started operating in this store")
    end_date = models.DateField(null=True, blank=True, help_text="When this brand stopped operating (if applicable)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'store_brand'
        verbose_name = 'Store Brand'
        verbose_name_plural = 'Store Brands'
        unique_together = [['store', 'brand']]
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['store', 'brand', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.store.store_code} - {self.brand.name}"


class User(AbstractUser):
    """
    Custom User Model with Multi-Tenant Support and Role Scope
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('cashier', 'Cashier'),
        ('waiter', 'Waiter'),
        ('kitchen', 'Kitchen Staff'),
    ]
    
    ROLE_SCOPE_CHOICES = [
        ('global', 'Global Level'),  # Super Admin - all companies
        ('company', 'Company Level'), # HO admin - all brands & stores
        ('brand', 'Brand Level'),    # Brand manager - all stores in 1 brand
        ('store', 'Store Level'),    # Store manager - only 1 store
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, 
        on_delete=models.SET_NULL, 
        related_name='users',
        null=True,
        blank=True,
        help_text="Company affiliation (can be null if company is deleted)"
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        related_name='users',
        null=True,
        blank=True,
        help_text="Leave blank for company-wide users"
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        related_name='users',
        null=True,
        blank=True,
        help_text="Leave blank for brand/company-wide users"
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    role_scope = models.CharField(
        max_length=20,
        choices=ROLE_SCOPE_CHOICES,
        default='store',
        help_text="Authorization scope for this user"
    )
    
    pin = models.CharField(
        max_length=6,
        blank=True,
        help_text="6-digit PIN for POS login and approvals"
    )
    profile_photo = models.ImageField(upload_to='user_photos/', null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['username']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['role']),
            models.Index(fields=['role_scope']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def can_approve_for_brand(self, brand):
        """Check if user can approve for specific brand"""
        if self.role_scope == 'company':
            return True  # Company scope can approve for all brands
        if self.role_scope == 'brand':
            return self.brand == brand  # Brand scope only for their brand
        return False  # Store scope cannot approve
    
    def can_approve_for_store(self, store):
        """Check if user can approve for specific store"""
        if self.role_scope == 'company':
            return True  # Company scope can approve for all stores
        if self.role_scope == 'brand':
            # Brand scope can approve if their brand operates in this store
            return store.has_brand(self.brand) if self.brand else False
        if self.role_scope == 'store':
            return self.store == store  # Store scope only for their store
        return False
    
    def get_accessible_brands_in_store(self, store):
        """Get list of brands this user can access in a given store"""
        if self.role_scope == 'company':
            return store.get_active_brands()  # Company scope sees all brands
        if self.role_scope == 'brand' and self.brand:
            # Brand scope only sees their own brand if it's in the store
            if store.has_brand(self.brand):
                return [self.brand]
            return []
        if self.role_scope == 'store' and self.store == store:
            return store.get_active_brands()  # Store staff sees all brands in their store
        return []
