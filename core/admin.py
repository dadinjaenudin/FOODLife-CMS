"""
Admin configuration for Core models
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import Company, Brand, Store, StoreBrand, User


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'timezone', 'point_expiry_months', 'points_per_currency', 'is_active', 'created_at']
    list_filter = ['is_active', 'timezone', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'code', 'name', 'logo', 'timezone', 'is_active')
        }),
        ('Loyalty Program Configuration', {
            'fields': ('point_expiry_months', 'points_per_currency'),
            'description': 'Configure company-wide loyalty program settings'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'tax_rate', 'service_charge', 'get_point_expiry', 'is_active']
    list_filter = ['company', 'is_active', 'created_at']
    search_fields = ['code', 'name', 'company__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['company']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'company', 'code', 'name', 'address', 'phone', 'tax_id', 'is_active')
        }),
        ('Financial Configuration', {
            'fields': ('tax_rate', 'service_charge')
        }),
        ('Loyalty Override', {
            'fields': ('point_expiry_months_override',),
            'description': 'Leave blank to use company default point expiry policy'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_point_expiry(self, obj):
        """Display effective point expiry months"""
        months = obj.get_point_expiry_months()
        if obj.point_expiry_months_override is not None:
            return format_html('<span style="color: blue;">{} months (override)</span>', months)
        return f'{months} months (company default)'
    get_point_expiry.short_description = 'Point Expiry'


class StoreBrandInline(admin.TabularInline):
    model = StoreBrand
    extra = 1
    autocomplete_fields = ['brand']
    fields = ['brand', 'is_active', 'start_date', 'end_date']


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['store_code', 'store_name', 'company', 'get_brands', 'phone', 'is_active']
    list_filter = ['company', 'is_active', 'created_at']
    search_fields = ['store_code', 'store_name', 'brands__name', 'address']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['company']
    inlines = [StoreBrandInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'company', 'store_code', 'store_name', 'address', 'phone', 'timezone', 'is_active')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_brands(self, obj):
        """Display all brands in this store"""
        brands = obj.brands.filter(is_active=True)
        if brands.exists():
            return ', '.join([b.name for b in brands])
        return '-'
    get_brands.short_description = 'Active Brands'
    get_brands.admin_order_field = 'brands__name'


@admin.register(StoreBrand)
class StoreBrandAdmin(admin.ModelAdmin):
    list_display = ['store', 'brand', 'is_active', 'start_date', 'end_date', 'created_at']
    list_filter = ['store__company', 'brand', 'is_active', 'start_date']
    search_fields = ['store__store_code', 'store__store_name', 'brand__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['store', 'brand']
    
    fieldsets = (
        ('Relationship', {
            'fields': ('id', 'store', 'brand', 'is_active')
        }),
        ('Operation Period', {
            'fields': ('start_date', 'end_date'),
            'description': 'When this brand started/ended operating in this store'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'get_full_name', 'company', 'brand', 'role', 'role_scope', 'is_active', 'is_staff']
    list_filter = ['company', 'brand', 'role', 'role_scope', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'company__name', 'brand__name']
    readonly_fields = ['id', 'date_joined', 'last_login', 'created_at', 'updated_at']
    autocomplete_fields = ['company', 'brand']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('id', 'username', 'password', 'pin')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'profile_photo')
        }),
        ('Multi-Tenant', {
            'fields': ('company', 'brand', 'role', 'role_scope'),
            'description': 'Company is required. Brand is optional for company-wide users.'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Authentication', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'pin'),
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email'),
        }),
        ('Multi-Tenant', {
            'fields': ('company', 'brand', 'role', 'role_scope'),
        }),
    )


# Customize admin site
admin.site.site_header = 'F&B HO Administration'
admin.site.site_title = 'F&B HO Admin'
admin.site.index_title = 'Master Data Management'
