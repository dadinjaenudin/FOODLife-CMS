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
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='brands')
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
    Example: Cabang BSD, Cabang Senayan
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='stores')
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
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['store_code']),
        ]
    
    def __str__(self):
        return f"{self.store_code} - {self.store_name}"
    
    @property
    def company(self):
        """Access company through brand"""
        return self.brand.company


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
        ('store', 'Store Level'),    # Store manager - only 1 store
        ('brand', 'Brand Level'),    # Brand manager - all stores in 1 brand
        ('company', 'Company Level'), # HO admin - all brands & stores
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='users')
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
        help_text="Leave blank for company-wide users"
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
            return self.brand == store.brand  # Brand scope for stores in their brand
        return False  # Store scope cannot approve (or implement store-specific logic)
