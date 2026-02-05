"""
Admin configuration for Products app
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Product, ProductPhoto, Modifier, ModifierOption,
    ProductModifier, TableArea, Tables, TableGroup, TableGroupMember,
    KitchenStation, PrinterConfig
)


class ProductPhotoInline(admin.TabularInline):
    model = ProductPhoto
    extra = 1
    fields = ['photo', 'is_primary', 'sort_order']


class ProductModifierInline(admin.TabularInline):
    model = ProductModifier
    extra = 1
    autocomplete_fields = ['modifier']
    fields = ['modifier', 'sort_order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'parent', 'sort_order', 'is_active', 'created_at']
    list_filter = ['brand', 'is_active', 'created_at']
    search_fields = ['name', 'brand__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['brand', 'parent']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'brand', 'parent', 'name', 'icon', 'sort_order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'brand', 'category', 'price', 'cost', 'get_margin', 'printer_target', 'is_active']
    list_filter = ['brand', 'category', 'printer_target', 'track_stock', 'is_active', 'created_at']
    search_fields = ['sku', 'name', 'brand__name', 'category__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'get_margin']
    autocomplete_fields = ['brand', 'category']
    inlines = [ProductPhotoInline, ProductModifierInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'brand', 'category', 'sku', 'name', 'description', 'is_active')
        }),
        ('Pricing', {
            'fields': ('price', 'cost', 'get_margin')
        }),
        ('Kitchen & Stock', {
            'fields': ('printer_target', 'track_stock', 'stock_quantity')
        }),
        ('Display', {
            'fields': ('sort_order',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_margin(self, obj):
        """Display margin percentage"""
        margin = obj.margin
        if margin > 50:
            color = 'green'
        elif margin > 30:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.2f}%</span>', color, margin)
    get_margin.short_description = 'Margin'


@admin.register(ProductPhoto)
class ProductPhotoAdmin(admin.ModelAdmin):
    list_display = ['product', 'photo', 'is_primary', 'sort_order', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['product__name']
    readonly_fields = ['id', 'created_at']
    autocomplete_fields = ['product']


class ModifierOptionInline(admin.TabularInline):
    model = ModifierOption
    extra = 1
    fields = ['name', 'price_adjustment', 'is_default', 'sort_order', 'is_active']


@admin.register(Modifier)
class ModifierAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'is_required', 'max_selections', 'get_option_count', 'is_active']
    list_filter = ['brand', 'is_required', 'is_active', 'created_at']
    search_fields = ['name', 'brand__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['brand']
    inlines = [ModifierOptionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'brand', 'name', 'is_active')
        }),
        ('Rules', {
            'fields': ('is_required', 'max_selections')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_option_count(self, obj):
        """Count modifier options"""
        return obj.options.count()
    get_option_count.short_description = 'Options'


@admin.register(ModifierOption)
class ModifierOptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'modifier', 'price_adjustment', 'is_default', 'sort_order', 'is_active']
    list_filter = ['modifier__brand', 'modifier', 'is_default', 'is_active']
    search_fields = ['name', 'modifier__name']
    readonly_fields = ['id', 'created_at']
    autocomplete_fields = ['modifier']


# =============================================================================
# TABLE MANAGEMENT
# =============================================================================

class TableInline(admin.TabularInline):
    model = Tables
    extra = 1
    fields = ['number', 'capacity', 'qr_code', 'pos_x', 'pos_y', 'is_active']


@admin.register(TableArea)
class TableAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'get_brand_name', 'get_table_count', 'sort_order', 'is_active']
    list_filter = ['store__company', 'store', 'brand', 'is_active', 'created_at']
    search_fields = ['name', 'store__store_name', 'brand__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['store', 'brand']
    inlines = [TableInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'brand', 'store', 'name', 'description', 'sort_order', 'is_active')
        }),
        ('Floor Plan', {
            'fields': ('floor_width', 'floor_height', 'floor_image'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_brand_name(self, obj):
        """Get brand name"""
        return obj.brand.name if obj.brand else '-'
    get_brand_name.short_description = 'Brand'
    
    def get_table_count(self, obj):
        """Count tables in area"""
        return obj.tables.count()
    get_table_count.short_description = 'Tables'


@admin.register(Tables)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'area', 'get_store', 'get_brand', 'capacity', 'status', 'is_active']
    list_filter = ['area__store__company', 'area__brand', 'area__store', 'area', 'status', 'is_active']
    search_fields = ['number', 'area__name', 'area__store__store_name', 'qr_code']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['area']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'area', 'number', 'capacity', 'qr_code', 'is_active')
        }),
        ('Floor Plan', {
            'fields': ('pos_x', 'pos_y')
        }),
        ('Status (Managed by Edge)', {
            'fields': ('status',),
            'description': 'Status is managed by Edge Server, not synced from HO'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_store(self, obj):
        """Get store through area"""
        return obj.area.store.store_name
    get_store.short_description = 'Store'
    get_store.admin_order_field = 'area__store'
    
    def get_brand(self, obj):
        """Get brand through area and store"""
        return obj.area.store.brand.name
    get_brand.short_description = 'Brand'
    get_brand.admin_order_field = 'area__store__brand'


class TableGroupMemberInline(admin.TabularInline):
    model = TableGroupMember
    extra = 1
    autocomplete_fields = ['table']


@admin.register(TableGroup)
class TableGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'brand', 'main_table', 'get_member_count', 'created_by', 'created_at']
    list_filter = ['brand', 'created_at']
    search_fields = ['main_table__number', 'brand__name']
    readonly_fields = ['id', 'created_at']
    autocomplete_fields = ['brand', 'main_table', 'created_by']
    inlines = [TableGroupMemberInline]
    
    def get_member_count(self, obj):
        """Count tables in group"""
        return obj.members.count()
    get_member_count.short_description = 'Tables'


# =============================================================================
# KITCHEN
# =============================================================================

class PrinterConfigInline(admin.TabularInline):
    model = PrinterConfig
    extra = 1
    fields = ['printer_name', 'ip_address', 'paper_width', 'is_active']


@admin.register(KitchenStation)
class KitchenStationAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'get_printer_count', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [PrinterConfigInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'code', 'name', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_printer_count(self, obj):
        """Count printers"""
        return obj.printers.count()
    get_printer_count.short_description = 'Printers'


@admin.register(PrinterConfig)
class PrinterConfigAdmin(admin.ModelAdmin):
    list_display = ['printer_name', 'station', 'ip_address', 'paper_width', 'is_active']
    list_filter = ['station', 'paper_width', 'is_active']
    search_fields = ['printer_name', 'ip_address', 'station__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['station']
