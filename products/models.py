"""
Product Catalog Models
- Category (hierarchical, brand-scoped)
- Product (multi-tenant, SKU unique per brand)
- Modifier & ModifierOption (customization options)
- ProductPhoto (product images)
- Table Management (TableArea, Table, TableGroup)
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator
from core.models import Brand, User


class Category(models.Model):
    """
    Product Category - Hierarchical, Brand-scoped
    Example: Makanan → Ayam → Ayam Geprek
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='categories')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent category for hierarchical structure"
    )
    name = models.CharField(max_length=200)
    sort_order = models.IntegerField(default=0, help_text="Display order")
    icon = models.CharField(max_length=100, blank=True, help_text="Icon name or path")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'category'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name


class Product(models.Model):
    """
    Product/Menu Item - Multi-tenant, SKU unique per brand
    """
    PRINTER_TARGET_CHOICES = [
        ('kitchen', 'Kitchen'),
        ('bar', 'Bar'),
        ('dessert', 'Dessert'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    company = models.ForeignKey('core.Company', on_delete=models.PROTECT, related_name='company_products', null=True, blank=True, default=None)  # ← Nullable for migration
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    sku = models.CharField(max_length=50, help_text="SKU unique per brand")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True, help_text="Main product image")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Cost for margin calculation"
    )
    printer_target = models.CharField(
        max_length=20,
        choices=PRINTER_TARGET_CHOICES,
        default='kitchen',
        help_text="Target printer for this product"
    )
    track_stock = models.BooleanField(default=False, help_text="Track inventory for this product")
    stock_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Current stock quantity (managed by Edge)"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['sort_order', 'name']
        unique_together = [['brand', 'category', 'name', 'sku']]  # SOP: unique per brand+category+name+sku
        indexes = [
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['sku']),
        ]
    
    def __str__(self):
        return f"{self.sku} - {self.name}"

    def save(self, *args, **kwargs):
        if self.brand and not self.company:
            self.company = self.brand.company
        super().save(*args, **kwargs)
    
    @property
    def margin(self):
        """Calculate margin percentage"""
        if self.price > 0:
            return ((self.price - self.cost) / self.price) * 100
        return 0
    
    @property
    def primary_photo(self):
        """Get primary photo or first photo"""
        return self.photos.filter(is_primary=True).first() or self.photos.first()


class ProductPhoto(models.Model):
    """
    Product Photos - Multiple images per product
    Images stored in MinIO, only metadata in database
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='photos')
    
    # MinIO metadata (instead of ImageField)
    object_key = models.CharField(max_length=500, blank=True, default='', help_text="MinIO object key")
    filename = models.CharField(max_length=255, blank=True, default='', help_text="Original filename")
    size = models.IntegerField(default=0, help_text="File size in bytes")
    content_type = models.CharField(max_length=100, default='image/jpeg')
    checksum = models.CharField(max_length=64, blank=True, default='', help_text="MD5 checksum for integrity")
    version = models.IntegerField(default=1, help_text="Image version for sync")
    
    # Legacy field for backward compatibility (can be removed later)
    photo = models.ImageField(upload_to='product_photos/', blank=True, null=True)
    
    is_primary = models.BooleanField(default=False, help_text="Primary display photo")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_photo'
        verbose_name = 'Product Photo'
        verbose_name_plural = 'Product Photos'
        ordering = ['sort_order']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
            models.Index(fields=['object_key']),
            models.Index(fields=['checksum']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.filename}"
    
    @property
    def image_url(self):
        """Get presigned URL from MinIO with cache-busting (cached property for templates)"""
        if self.object_key:
            from core.storage import minio_storage
            from django.utils.http import urlencode
            import time
            
            base_url = minio_storage.get_image_url(self.object_key)
            # Add cache-busting parameter using checksum or timestamp
            cache_param = self.checksum[:8] if self.checksum else str(int(time.time()))
            separator = '&' if '?' in base_url else '?'
            return f"{base_url}{separator}v={cache_param}"
        elif self.photo:
            # Fallback to legacy photo field
            return self.photo.url
        return None
    
    def get_image_url(self):
        """Alias for backward compatibility"""
        return self.image_url


class Modifier(models.Model):
    """
    Modifier Group - Customization options (Size, Spice Level, Extras)
    Example: "Tingkat Kepedasan", "Ukuran", "Topping"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='modifiers')
    name = models.CharField(max_length=200, help_text="Modifier group name")
    is_required = models.BooleanField(
        default=False,
        help_text="Customer must select at least one option"
    )
    max_selections = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Maximum selections allowed (0 = unlimited)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'modifier'
        verbose_name = 'Modifier'
        verbose_name_plural = 'Modifiers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['brand', 'is_active']),
        ]
    
    def __str__(self):
        return self.name


class ModifierOption(models.Model):
    """
    Modifier Option - Individual choices within a modifier group
    Example: "Pedas Level 5", "Size Large", "Extra Cheese"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    modifier = models.ForeignKey(Modifier, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=200)
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Price adjustment (e.g., +5000 for Large)"
    )
    is_default = models.BooleanField(default=False, help_text="Default selection")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'modifier_option'
        verbose_name = 'Modifier Option'
        verbose_name_plural = 'Modifier Options'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['modifier', 'is_active']),
        ]
    
    def __str__(self):
        if self.price_adjustment != 0:
            return f"{self.name} (+{self.price_adjustment})"
        return self.name


class ProductModifier(models.Model):
    """
    M2M relationship between Product and Modifier
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_modifiers')
    modifier = models.ForeignKey(Modifier, on_delete=models.CASCADE, related_name='product_modifiers')
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'product_modifier'
        unique_together = [['product', 'modifier']]
        ordering = ['sort_order']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['modifier']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.modifier.name}"


# =============================================================================
# TABLE MANAGEMENT (Dine-In)
# =============================================================================

class TableArea(models.Model):
    """
    Dining Area - Sections in restaurant
    Example: Indoor, Outdoor, VIP Room
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey('core.Company', on_delete=models.PROTECT, related_name='table_areas', null=True, blank=True, help_text="Company for multi-tenant isolation")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='table_areas')
    store = models.ForeignKey('core.Store', on_delete=models.PROTECT, related_name='table_areas', null=True, blank=True, help_text="Store-specific areas (leave blank for brand-wide)")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Description of the area layout")
    sort_order = models.IntegerField(default=0)
    
    # Floor plan dimensions (optional)
    floor_width = models.IntegerField(null=True, blank=True, help_text="Floor width in pixels/units")
    floor_height = models.IntegerField(null=True, blank=True, help_text="Floor height in pixels/units")
    floor_image = models.ImageField(upload_to='floor_plans/', null=True, blank=True, help_text="Floor plan image")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'table_area'
        verbose_name = 'Table Area'
        verbose_name_plural = 'Table Areas'
        ordering = ['company', 'brand', 'store', 'sort_order', 'name']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['store', 'is_active']),
        ]
    
    def __str__(self):
        if self.store:
            return f"{self.store.store_name} - {self.name}"
        return f"{self.brand.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Auto-populate company from store or brand
        if not self.company:
            if self.store:
                self.company = self.store.brand.company
            elif self.brand:
                self.company = self.brand.company
        super().save(*args, **kwargs)


class Tables(models.Model):
    """
    Tables - Individual tables in restaurant
    Status managed by Edge, HO stores template only
    Note: Named 'Tables' (plural) to avoid SQL reserved keyword conflict
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.ForeignKey(TableArea, on_delete=models.PROTECT, related_name='tables')
    number = models.CharField(max_length=20, help_text="Table number (e.g., A1, B5)")
    capacity = models.IntegerField(validators=[MinValueValidator(1)], help_text="Maximum guests")
    qr_code = models.CharField(max_length=200, blank=True, help_text="QR code for ordering")
    
    # Floor plan positioning
    pos_x = models.IntegerField(null=True, blank=True, help_text="X position on floor plan")
    pos_y = models.IntegerField(null=True, blank=True, help_text="Y position on floor plan")
    
    # NOTE: status and table_group are managed by Edge, not synced from HO
    # These fields are for reference only at HO
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        help_text="Status managed by Edge"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tables'  # Changed from 'table' to 'tables' to avoid SQL keyword
        verbose_name = 'Table'
        verbose_name_plural = 'Tables'
        ordering = ['area', 'number']
        indexes = [
            models.Index(fields=['area', 'is_active']),
            models.Index(fields=['number']),
        ]
    
    def __str__(self):
        return f"{self.area.name} - Table {self.number}"


class TableGroup(models.Model):
    """
    Table Group - For joined tables (managed by Edge)
    HO stores for reference/reporting only
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='table_groups')
    main_table = models.ForeignKey(
        Tables,
        on_delete=models.PROTECT,
        related_name='main_table_groups',
        help_text="Primary table in group"
    )
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_table_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'table_group'
        verbose_name = 'Table Group'
        verbose_name_plural = 'Table Groups'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['brand', 'created_at']),
            models.Index(fields=['main_table']),
        ]
    
    def __str__(self):
        return f"Group {self.id} - {self.main_table}"


class TableGroupMember(models.Model):
    """
    Tables in a group (M2M)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_group = models.ForeignKey(TableGroup, on_delete=models.CASCADE, related_name='members')
    table = models.ForeignKey(Tables, on_delete=models.PROTECT, related_name='group_memberships')
    
    class Meta:
        db_table = 'table_group_member'
        unique_together = [['table_group', 'table']]
        indexes = [
            models.Index(fields=['table_group']),
            models.Index(fields=['table']),
        ]
    
    def __str__(self):
        return f"{self.table_group} - {self.table}"


# =============================================================================
# KITCHEN CONFIGURATION
# =============================================================================

class KitchenStation(models.Model):
    """
    Kitchen Station - Production areas per Store (Store-specific only)
    Example: Main Kitchen, Bar, Dessert Station
    Multi-company support with proper hierarchy: Company -> Brand -> Store -> Kitchen Station
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey('core.Company', on_delete=models.PROTECT, related_name='kitchen_stations', help_text="Company for multi-tenant isolation")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='kitchen_stations')
    store = models.ForeignKey('core.Store', on_delete=models.PROTECT, related_name='kitchen_stations', help_text="Kitchen stations are store-specific")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True, help_text="Description of the kitchen station")
    sort_order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'kitchen_station'
        verbose_name = 'Kitchen Station'
        verbose_name_plural = 'Kitchen Stations'
        ordering = ['company', 'brand', 'store', 'sort_order', 'name']
        unique_together = [['company', 'store', 'code']]  # Code unique per company+store combination
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['company', 'brand', 'store']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.store.store_name} - {self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Auto-populate company and brand from store
        if self.store and not self.company:
            self.company = self.store.brand.company
        if self.store and not self.brand_id:
            self.brand = self.store.brand
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate data consistency"""
        from django.core.exceptions import ValidationError
        
        if self.store:
            # Ensure store belongs to the specified brand
            if self.brand and self.store.brand != self.brand:
                raise ValidationError('Store must belong to the specified brand')
            
            # Ensure store belongs to the specified company
            if self.company and self.store.brand.company != self.company:
                raise ValidationError('Store must belong to the specified company')


class PrinterConfig(models.Model):
    """
    Printer Configuration
    Note: Might be better managed per Edge, not synced from HO
    """
    PAPER_WIDTH_CHOICES = [
        ('58mm', '58mm'),
        ('80mm', '80mm'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.ForeignKey(KitchenStation, on_delete=models.PROTECT, related_name='printers')
    printer_name = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField(help_text="Printer IP address")
    paper_width = models.CharField(max_length=10, choices=PAPER_WIDTH_CHOICES, default='80mm')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'printer_config'
        verbose_name = 'Printer Config'
        verbose_name_plural = 'Printer Configs'
        ordering = ['station', 'printer_name']
        indexes = [
            models.Index(fields=['station', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.station.name} - {self.printer_name} ({self.ip_address})"
