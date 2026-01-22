# 🧪 COMPREHENSIVE TESTING CHECKLIST
## F&B POS HO System - Phase by Phase Testing Guide

**Testing Strategy**: Option A (All phases implemented) dengan testing breakdown per file per phase.

**Testing Approach**:
- ✅ **Unit Tests**: Model validation, business logic
- ✅ **Integration Tests**: API endpoints, multi-model operations
- ✅ **Admin Tests**: Django admin interface functionality
- ✅ **Command Tests**: Management command execution
- ✅ **End-to-End Tests**: Complete workflow scenarios

---

## 📋 PHASE 1: FOUNDATION & MULTI-TENANT CORE

### **File: `core/models.py`**

#### Model: Company
- [ ] ✅ Create company with valid data
- [ ] ✅ Unique code constraint (duplicate should fail)
- [ ] ✅ Unique name constraint
- [ ] ✅ Default is_active=True
- [ ] ✅ Point expiry validation (>= 0)
- [ ] ✅ Points per currency validation (>= 0)
- [ ] ✅ Auto timestamps (created_at, updated_at)
- [ ] ❌ Create company with negative point_expiry_months (should fail)
- [ ] ❌ Create company without code (should fail)

#### Model: Brand
- [ ] ✅ Create brand with valid company FK
- [ ] ✅ Unique (company_id, code) constraint
- [ ] ✅ Tax rate validation (0-100)
- [ ] ✅ Service charge validation (0-100)
- [ ] ✅ Loyalty override (nullable)
- [ ] ✅ Cascade behavior when company deleted
- [ ] ❌ Create brand with duplicate code in same company (should fail)
- [ ] ✅ Create brand with same code in different company (should succeed)
- [ ] ❌ Tax rate > 100 (should fail)
- [ ] ❌ Service charge < 0 (should fail)

#### Model: Store
- [ ] ✅ Create store with valid brand FK
- [ ] ✅ Unique store_code constraint
- [ ] ✅ Timezone field populated
- [ ] ✅ Latitude/longitude (nullable)
- [ ] ✅ Cascade when brand deleted
- [ ] ❌ Duplicate store_code (should fail)
- [ ] ✅ Query stores by brand
- [ ] ✅ Query active stores only

#### Model: User (Custom)
- [ ] ✅ Create user with username/password
- [ ] ✅ Create user with company_id
- [ ] ✅ Create user with brand_id (nullable)
- [ ] ✅ Role validation (ADMIN, MANAGER, CASHIER, etc.)
- [ ] ✅ Role scope validation (company, brand, store)
- [ ] ✅ PIN field (4-6 digits for cashier)
- [ ] ✅ Password hashing (never plaintext)
- [ ] ✅ is_active default True
- [ ] ❌ Invalid role choice (should fail)
- [ ] ❌ Invalid role_scope (should fail)
- [ ] ✅ User authentication (login)
- [ ] ✅ User permissions based on role_scope

### **File: `core/admin.py`**
- [ ] ✅ CompanyAdmin accessible
- [ ] ✅ BrandAdmin with company filter
- [ ] ✅ StoreAdmin with brand filter
- [ ] ✅ UserAdmin with role/scope filters
- [ ] ✅ Multi-tenant filtering works (user sees only their scope)
- [ ] ✅ Search functionality
- [ ] ✅ Inline editing where applicable
- [ ] ✅ Audit log entries created on changes

### **Integration Tests**
- [ ] ✅ Create complete hierarchy: Company → Brand → Store
- [ ] ✅ Create users at different scopes
- [ ] ✅ User cannot access data outside their scope
- [ ] ✅ Admin user can access all scopes

---

## 📦 PHASE 2: PRODUCT CATALOG & TABLES

### **File: `products/models.py`**

#### Model: Category
- [ ] ✅ Create root category (parent=None)
- [ ] ✅ Create child category with parent
- [ ] ✅ Unique (brand_id, name, parent_id) constraint
- [ ] ✅ Self-referencing FK (parent) works
- [ ] ✅ Recursive delete protection (if has children)
- [ ] ✅ Sort order functionality
- [ ] ❌ Circular parent reference (should fail)
- [ ] ✅ Query category tree

#### Model: Product
- [ ] ✅ Create product with valid brand & category
- [ ] ✅ Unique (brand_id, sku) constraint
- [ ] ✅ Price validation (>= 0)
- [ ] ✅ Cost validation (>= 0)
- [ ] ✅ track_stock boolean
- [ ] ✅ stock_quantity updated correctly
- [ ] ✅ printer_target choices validation
- [ ] ❌ Duplicate SKU in same brand (should fail)
- [ ] ✅ Same SKU in different brands (should succeed)
- [ ] ✅ Product soft delete (is_active=False)

#### Model: ProductPhoto
- [ ] ✅ Create photo with product FK
- [ ] ✅ Multiple photos per product
- [ ] ✅ is_primary flag (only one per product)
- [ ] ✅ Sort order
- [ ] ✅ Cascade delete when product deleted

#### Model: Modifier & ModifierOption
- [ ] ✅ Create modifier with brand
- [ ] ✅ Create options for modifier
- [ ] ✅ is_required flag
- [ ] ✅ max_selections validation
- [ ] ✅ price_adjustment (can be negative)
- [ ] ✅ is_default flag (only one per modifier)
- [ ] ✅ Cascade delete options when modifier deleted

#### Model: ProductModifier (M2M)
- [ ] ✅ Link product to modifier
- [ ] ✅ Multiple modifiers per product
- [ ] ✅ Unique (product, modifier) constraint
- [ ] ❌ Duplicate link (should fail)
- [ ] ✅ Query products by modifier
- [ ] ✅ Query modifiers by product

#### Model: Table & TableArea
- [ ] ✅ Create table area for brand
- [ ] ✅ Create table in area
- [ ] ✅ Unique table number per area
- [ ] ✅ QR code generation
- [ ] ✅ Capacity validation (> 0)
- [ ] ✅ Status choices (AVAILABLE, OCCUPIED, RESERVED, CLEANING)
- [ ] ✅ Position (pos_x, pos_y) for floor plan
- [ ] ❌ Duplicate table number in same area (should fail)

#### Model: TableGroup & TableGroupMember
- [ ] ✅ Create table group for brand
- [ ] ✅ Add tables to group
- [ ] ✅ Main table designation
- [ ] ✅ Group status updates all member tables
- [ ] ✅ Unique table per group constraint

#### Model: KitchenStation & PrinterConfig
- [ ] ✅ Create kitchen station
- [ ] ✅ Create printer config for station
- [ ] ✅ Printer IP validation
- [ ] ✅ Paper width choices
- [ ] ✅ is_active flag

### **File: `products/admin.py`**
- [ ] ✅ All product admins accessible
- [ ] ✅ Brand filtering works
- [ ] ✅ Inline editing (photos, modifiers)
- [ ] ✅ Search products by SKU/name
- [ ] ✅ Filter by category
- [ ] ✅ Table floor plan view (future)

### **Integration Tests**
- [ ] ✅ Create product with photos & modifiers
- [ ] ✅ Calculate product final price with modifiers
- [ ] ✅ Table group merge scenario
- [ ] ✅ Kitchen printer routing based on product.printer_target

---

## 👥 PHASE 3: MEMBER & LOYALTY PROGRAM

### **File: `members/models.py`**

#### Model: Member
- [ ] ✅ Create member with company_id
- [ ] ✅ Auto-generate member_code (MB-COMPANYCODE-YYYYMM-XXXX)
- [ ] ✅ Unique member_code
- [ ] ✅ Unique card_number per company
- [ ] ✅ Phone validation (unique per company)
- [ ] ✅ Tier choices (BRONZE, SILVER, GOLD, PLATINUM)
- [ ] ✅ Default tier = BRONZE
- [ ] ✅ points >= point_balance (invariant)
- [ ] ✅ total_visits counter
- [ ] ✅ total_spent accumulation
- [ ] ✅ last_visit timestamp
- [ ] ✅ expire_date calculation
- [ ] ❌ Duplicate member_code (should fail)
- [ ] ❌ point_balance < 0 (should fail)

#### Model: MemberTransaction
- [ ] ✅ Create EARN transaction
- [ ] ✅ Create REDEEM transaction
- [ ] ✅ Create ADJUSTMENT transaction
- [ ] ✅ Create EXPIRED transaction
- [ ] ✅ balance_after calculation
- [ ] ✅ bill_id reference (nullable)
- [ ] ✅ created_by audit trail
- [ ] ✅ is_expired flag
- [ ] ✅ expired_at timestamp
- [ ] ❌ points inconsistency (should fail validation)
- [ ] ✅ Query member transaction history
- [ ] ✅ Calculate point balance from transactions

### **File: `members/admin.py`**
- [ ] ✅ MemberAdmin with company filter
- [ ] ✅ Search by member_code, phone, name
- [ ] ✅ Filter by tier, status
- [ ] ✅ Inline transaction view
- [ ] ✅ Points balance display
- [ ] ✅ Last visit display

### **Integration Tests**
- [ ] ✅ Member registration flow
- [ ] ✅ Earn points on purchase (Bill → MemberTransaction)
- [ ] ✅ Redeem points for discount
- [ ] ✅ Points expiry job (see Phase 8 command test)
- [ ] ✅ Tier upgrade based on total_spent
- [ ] ✅ Member statistics (visits, spent) accurate

---

## 🎁 PHASE 4: PROMOTION ENGINE (CRITICAL & COMPLEX)

### **File: `promotions/models.py`**

#### Model: Promotion (12+ types)
- [ ] ✅ Create PERCENT_DISCOUNT promotion
- [ ] ✅ Create AMOUNT_DISCOUNT promotion
- [ ] ✅ Create BOGO (Buy X Get Y) promotion
- [ ] ✅ Create FREE_ITEM promotion
- [ ] ✅ Create COMBO promotion
- [ ] ✅ Create MIX_MATCH promotion
- [ ] ✅ Create THRESHOLD_TIER promotion
- [ ] ✅ Create HAPPY_HOUR promotion
- [ ] ✅ Create PAYMENT_DISCOUNT promotion
- [ ] ✅ Create MEMBER_TIER promotion
- [ ] ✅ Create CASHBACK promotion
- [ ] ✅ Create PACKAGE promotion
- [ ] ✅ Create UPSELL promotion
- [ ] ✅ Unique code per company
- [ ] ✅ Date range validation (start_date <= end_date)
- [ ] ✅ Time rules (JSON) validation
- [ ] ✅ Scope validation (company, brand, multi-brand)
- [ ] ✅ Multi-brand M2M relationship
- [ ] ✅ Product M2M relationship
- [ ] ✅ Category M2M relationship
- [ ] ✅ Channel filter (DINE_IN, TAKEAWAY, DELIVERY, QR_ORDER)
- [ ] ✅ Customer type filter (ALL, NEW, EXISTING, INACTIVE)
- [ ] ✅ Member tier filter
- [ ] ✅ Payment method filter
- [ ] ✅ Usage limits (max_usage, max_usage_per_customer)
- [ ] ✅ Min purchase validation
- [ ] ✅ Min quantity/item count
- [ ] ✅ Stacking rules (can_stack_with, cannot_stack_with)
- [ ] ✅ Execution priority (integer)
- [ ] ✅ Max discount cap
- [ ] ✅ require_employee_activation
- [ ] ✅ require_manager_approval
- [ ] ✅ Conflict resolution strategy
- [ ] ❌ Invalid promo_type (should fail)
- [ ] ❌ end_date < start_date (should fail)
- [ ] ❌ Negative discount_value (should fail for most types)

#### Model: PackagePromotion & PackageItem
- [ ] ✅ Create package with promotion (OneToOne)
- [ ] ✅ Add items to package
- [ ] ✅ Required items
- [ ] ✅ Optional items (is_required=False)
- [ ] ✅ Min/max selection per item
- [ ] ✅ Upsell options (price upgrade)
- [ ] ✅ Package SKU unique
- [ ] ✅ Package price calculation
- [ ] ✅ allow_modification flag
- [ ] ✅ track_as_virtual_product
- [ ] ✅ auto_deduct_components
- [ ] ✅ Cascade delete items when package deleted

#### Model: PromotionTier
- [ ] ✅ Create tiers for threshold promotion
- [ ] ✅ Tier ordering (tier_order)
- [ ] ✅ Min/max amount per tier
- [ ] ✅ Discount type per tier
- [ ] ✅ Points multiplier per tier
- [ ] ✅ Free product per tier
- [ ] ❌ Overlapping tier ranges (should fail validation)
- [ ] ✅ Query applicable tier for given amount

#### Model: Voucher
- [ ] ✅ Create voucher linked to promotion
- [ ] ✅ Unique code per voucher
- [ ] ✅ Status (ACTIVE, USED, EXPIRED, CANCELLED)
- [ ] ✅ Customer assignment (phone/name)
- [ ] ✅ QR code generation
- [ ] ✅ Expires_at validation
- [ ] ✅ used_at, used_by, used_bill tracking
- [ ] ❌ Use expired voucher (should fail)
- [ ] ❌ Use already-used voucher (should fail)
- [ ] ✅ Mark voucher as used (atomic operation)

#### Model: PromotionUsage
- [ ] ✅ Record usage per promotion
- [ ] ✅ Track member usage
- [ ] ✅ Track customer_phone usage (non-member)
- [ ] ✅ Usage count enforcement (max_usage_per_customer)
- [ ] ✅ bill_id reference
- [ ] ❌ Exceed usage limit (should fail)
- [ ] ✅ Query usage history per promotion
- [ ] ✅ Query usage per member

#### Model: PromotionLog
- [ ] ✅ Create log for applied promotion
- [ ] ✅ Create log for skipped promotion (with reason)
- [ ] ✅ Create log for failed promotion
- [ ] ✅ Status choices (APPLIED, SKIPPED, FAILED)
- [ ] ✅ Calculation detail (JSON explainability)
- [ ] ✅ discount_amount tracking
- [ ] ✅ cashback_amount tracking
- [ ] ✅ bill_id reference
- [ ] ✅ Query logs per bill
- [ ] ✅ Query logs per promotion

#### Model: PromotionApproval
- [ ] ✅ Create approval request (PENDING)
- [ ] ✅ Approve request (APPROVED)
- [ ] ✅ Reject request (REJECTED)
- [ ] ✅ bill_id reference
- [ ] ✅ discount_amount
- [ ] ✅ requested_by, approved_by tracking
- [ ] ✅ approval_notes
- [ ] ❌ Non-manager cannot approve (should fail permission check)
- [ ] ✅ Approval flow integration with bill

#### Model: CustomerPromotionHistory
- [ ] ✅ Track first_order_date per customer per brand
- [ ] ✅ Track last_order_date
- [ ] ✅ Track total_orders
- [ ] ✅ Track total_spent
- [ ] ✅ Member FK (nullable for guests)
- [ ] ✅ customer_phone for non-members
- [ ] ✅ inactive_days calculation
- [ ] ✅ Query by customer & brand
- [ ] ✅ Upsert on new order

### **File: `promotions/admin.py`**
- [ ] ✅ PromotionAdmin accessible
- [ ] ✅ Filter by promo_type, scope, status
- [ ] ✅ Search by code, name
- [ ] ✅ Inline package items
- [ ] ✅ Inline promotion tiers
- [ ] ✅ Date range filter
- [ ] ✅ Brand filter
- [ ] ✅ Stacking rules display
- [ ] ✅ Usage stats display
- [ ] ✅ VoucherAdmin with status filter
- [ ] ✅ PromotionUsageAdmin read-only
- [ ] ✅ PromotionLogAdmin for explainability review
- [ ] ✅ PromotionApprovalAdmin for approval workflow

### **Integration Tests (PROMOTION ENGINE - CRITICAL)**
- [ ] ✅ **Scenario 1**: Apply single percent discount
- [ ] ✅ **Scenario 2**: Apply BOGO (Buy 2 Ayam Geprek, Get 1 Free)
- [ ] ✅ **Scenario 3**: Apply package promotion (Paket Hemat 30k)
- [ ] ✅ **Scenario 4**: Happy hour discount (16:00-18:00)
- [ ] ✅ **Scenario 5**: Member tier discount (GOLD member 15% off)
- [ ] ✅ **Scenario 6**: Payment method discount (QRIS 10% off)
- [ ] ✅ **Scenario 7**: Threshold tier (spend 100k → 10% off, 200k → 20% off)
- [ ] ✅ **Scenario 8**: Mix & match (Buy 3 from category Drinks → 15% off)
- [ ] ✅ **Scenario 9**: First order promo (new customer 50% off)
- [ ] ✅ **Scenario 10**: Stacking (allow 2 promos to stack)
- [ ] ✅ **Scenario 11**: Conflict resolution (non-stackable promos → highest discount wins)
- [ ] ✅ **Scenario 12**: Voucher redemption
- [ ] ✅ **Scenario 13**: Cashback promotion (pay → earn cashback points)
- [ ] ✅ **Scenario 14**: Upsell promotion (add item X → get Y 50% off)
- [ ] ✅ **Scenario 15**: Manager approval required promotion
- [ ] ✅ **Scenario 16**: Employee-only promotion activation
- [ ] ✅ **Scenario 17**: Multi-brand promotion (promo berlaku untuk 2 brand)
- [ ] ✅ **Scenario 18**: Usage limit enforcement (max 5x per customer)
- [ ] ✅ **Scenario 19**: Expired voucher rejection
- [ ] ✅ **Scenario 20**: Explainability logs (all applied/skipped promos logged)
- [ ] ✅ **Edge Case**: Multiple promos on same item
- [ ] ✅ **Edge Case**: Promo with circular stacking dependency
- [ ] ✅ **Edge Case**: Total discount > subtotal (should cap at subtotal)
- [ ] ✅ **Edge Case**: Cashback > paid amount (should cap)
- [ ] ✅ **Edge Case**: Member tier downgrade mid-transaction
- [ ] ✅ **Edge Case**: Package with optional choices (partial selection)

---

## 📦 PHASE 5: INVENTORY & RECIPE MANAGEMENT (BOM)

### **File: `inventory/models.py`**

#### Model: InventoryItem
- [ ] ✅ Create raw material item
- [ ] ✅ Create semi-finished item
- [ ] ✅ Create finished goods item
- [ ] ✅ Create packaging item
- [ ] ✅ Unique (brand_id, item_code)
- [ ] ✅ item_type choices validation
- [ ] ✅ base_unit
- [ ] ✅ conversion_factor (> 0)
- [ ] ✅ cost_per_unit validation (>= 0)
- [ ] ✅ track_stock boolean
- [ ] ✅ min_stock, max_stock
- [ ] ❌ Duplicate item_code in same brand (should fail)
- [ ] ✅ Same item_code in different brands (should succeed)

#### Model: Recipe (BOM)
- [ ] ✅ Create recipe for product
- [ ] ✅ Unique (brand_id, product_id, version)
- [ ] ✅ Recipe versioning (multiple versions per product)
- [ ] ✅ yield_quantity, yield_unit
- [ ] ✅ preparation_type choices
- [ ] ✅ effective_date, end_date
- [ ] ✅ is_active flag (only one active per product)
- [ ] ❌ Multiple active recipes for same product (should fail validation)
- [ ] ✅ Recipe version rollback scenario

#### Model: RecipeIngredient
- [ ] ✅ Add ingredient to recipe
- [ ] ✅ quantity, unit
- [ ] ✅ yield_factor (0-1) validation
- [ ] ✅ is_critical flag
- [ ] ✅ sort_order
- [ ] ✅ Cascade delete when recipe deleted
- [ ] ✅ Calculate recipe cost from ingredients
- [ ] ✅ Calculate expected vs actual yield

### **File: `inventory/admin.py`**
- [ ] ✅ InventoryItemAdmin accessible
- [ ] ✅ RecipeAdmin with inline ingredients
- [ ] ✅ Filter by brand, item_type
- [ ] ✅ Search by item_code, name
- [ ] ✅ Cost calculation display
- [ ] ✅ Version management UI

### **Integration Tests**
- [ ] ✅ Create recipe with ingredients
- [ ] ✅ Calculate recipe cost (sum of ingredient costs)
- [ ] ✅ Stock deduction on sale (BillItem → Recipe explosion → InventoryMovement)
- [ ] ✅ Yield loss handling (ingredient quantity * yield_factor)
- [ ] ✅ Recipe versioning (switch to new recipe version)
- [ ] ✅ COGS calculation per product
- [ ] ✅ Theoretical vs actual usage variance
- [ ] ✅ Substitution ingredient scenario
- [ ] ✅ Partial batch failure (manufacturing)
- [ ] ✅ Central kitchen → store transfer

---

## 💰 PHASE 6: TRANSACTION DATA RECEPTION (Edge → HO)

### **File: `transactions/models.py`**

#### Model: Bill
- [ ] ✅ Receive bill from Edge (OPEN status)
- [ ] ✅ Receive bill (PAID status)
- [ ] ✅ Receive bill (VOID status)
- [ ] ✅ Receive bill (REFUND status)
- [ ] ✅ Unique bill_number
- [ ] ✅ Denormalized company_id, brand_id, store_id
- [ ] ✅ Bill type choices (DINE_IN, TAKEAWAY, DELIVERY, QRORDER)
- [ ] ✅ Member info (nullable)
- [ ] ✅ Table info (nullable)
- [ ] ✅ Amounts: subtotal, tax, service, discount, total
- [ ] ✅ Rounding adjustment
- [ ] ✅ Audit trail (created_by, closed_by, voided_by)
- [ ] ✅ synced_at timestamp
- [ ] ❌ Duplicate bill_number (should fail)
- [ ] ✅ Query bills by date range
- [ ] ✅ Query bills by store
- [ ] ✅ Query bills by status

#### Model: BillItem
- [ ] ✅ Receive bill items linked to bill
- [ ] ✅ Denormalized company/brand/store
- [ ] ✅ Product snapshot (sku, name, category)
- [ ] ✅ Modifiers snapshot (JSON)
- [ ] ✅ Quantity, unit_price, unit_cost
- [ ] ✅ Discount amount per item
- [ ] ✅ Status choices (PENDING, SENT_TO_KITCHEN, PREPARING, READY, SERVED, VOID)
- [ ] ✅ is_void flag
- [ ] ✅ Kitchen tracking (sent_to_kitchen_at, prepared_at)
- [ ] ✅ void_reason
- [ ] ✅ Query items by bill
- [ ] ✅ Query items by product
- [ ] ✅ Calculate margin (unit_price - unit_cost)

#### Model: Payment
- [ ] ✅ Receive payment records (multi-payment support)
- [ ] ✅ Payment method choices (CASH, CARD, QRIS, EWALLET, TRANSFER, VOUCHER, MEMBER_POINTS)
- [ ] ✅ Amount validation (>= 0)
- [ ] ✅ Status (PENDING, SUCCESS, FAILED, REFUND)
- [ ] ✅ Cash: cash_received, change
- [ ] ✅ External reference (for gateway)
- [ ] ✅ payment_gateway_response (JSON)
- [ ] ✅ Query payments by bill
- [ ] ✅ Calculate total paid for bill

#### Model: BillPromotion
- [ ] ✅ Receive applied promotion records
- [ ] ✅ Execution stage (ITEM_LEVEL, SUBTOTAL, PAYMENT, CASHBACK)
- [ ] ✅ Discount amount, cashback amount
- [ ] ✅ Affected items (JSON array)
- [ ] ✅ calculation_detail (explainability JSON)
- [ ] ✅ Query promotions applied to bill
- [ ] ✅ Query promotion performance

#### Model: CashDrop
- [ ] ✅ Receive cash drop records
- [ ] ✅ Transaction type (DROP, PICKUP)
- [ ] ✅ Denormalized multi-tenant fields
- [ ] ✅ Amount validation
- [ ] ✅ Query by store & date

#### Model: StoreSession (EOD)
- [ ] ✅ Receive store session (EOD)
- [ ] ✅ Unique (store_id, session_date)
- [ ] ✅ Status (OPEN, CLOSED)
- [ ] ✅ Opening/closing cash
- [ ] ✅ Expected vs actual cash
- [ ] ✅ Variance calculation
- [ ] ✅ Sales summary (total_sales, total_discount, total_refund)
- [ ] ❌ Duplicate session for same store & date (should fail)
- [ ] ✅ Query sessions by store
- [ ] ✅ Calculate daily revenue

#### Model: CashierShift
- [ ] ✅ Receive cashier shift records
- [ ] ✅ Link to store_session
- [ ] ✅ Status (OPEN, CLOSED)
- [ ] ✅ Cash variance per cashier
- [ ] ✅ Query shifts by cashier
- [ ] ✅ Query shifts by terminal

#### Model: KitchenOrder
- [ ] ✅ Receive kitchen order records
- [ ] ✅ Status tracking (PENDING, PREPARING, READY, SERVED, CANCELLED)
- [ ] ✅ Print timestamp
- [ ] ✅ Prepared/served timestamps
- [ ] ✅ Query orders by station
- [ ] ✅ Calculate preparation time

#### Model: BillRefund
- [ ] ✅ Receive refund records
- [ ] ✅ Refund type (FULL, PARTIAL)
- [ ] ✅ Status (PENDING, APPROVED, REJECTED, COMPLETED)
- [ ] ✅ Refunded items (JSON)
- [ ] ✅ Approval workflow tracking
- [ ] ✅ Query refunds by status
- [ ] ✅ Calculate refund impact on revenue

#### Model: InventoryMovement
- [ ] ✅ Receive inventory movement from Edge
- [ ] ✅ Movement type (SALE, REFUND, WASTE, ADJUSTMENT, TRANSFER, MANUFACTURING)
- [ ] ✅ Quantity, unit, unit_cost, total_cost
- [ ] ✅ Bill reference (nullable)
- [ ] ✅ Recipe reference (nullable)
- [ ] ✅ Query movements by item
- [ ] ✅ Calculate COGS from movements

### **File: `transactions/admin.py`**
- [ ] ✅ All transaction admins are READ-ONLY
- [ ] ✅ No add/delete permissions
- [ ] ✅ Date hierarchy navigation
- [ ] ✅ Multi-tenant filtering
- [ ] ✅ Search functionality
- [ ] ✅ Status filters
- [ ] ✅ Export to CSV/Excel (future)

### **Integration Tests**
- [ ] ✅ Receive complete bill from Edge (bill + items + payments + promotions)
- [ ] ✅ Receive bill with multiple payments (split payment)
- [ ] ✅ Receive void bill scenario
- [ ] ✅ Receive refund scenario (full & partial)
- [ ] ✅ Receive EOD session data
- [ ] ✅ Data integrity (denormalized fields match FK lookups)
- [ ] ✅ Idempotency (duplicate sync doesn't create duplicates)
- [ ] ✅ Query reporting: daily sales by store
- [ ] ✅ Query reporting: product sales analysis
- [ ] ✅ Query reporting: promotion performance
- [ ] ✅ Query reporting: cashier performance
- [ ] ✅ Query reporting: payment method distribution
- [ ] ✅ Query reporting: margin analysis

---

## 🔄 PHASE 7: SYNC API (HO ↔ Edge)

### **File: `core/api/serializers.py`**
- [ ] ✅ CompanySerializer serialization
- [ ] ✅ BrandSerializer serialization
- [ ] ✅ StoreSerializer serialization
- [ ] ✅ UserSerializer serialization (exclude password)
- [ ] ✅ Read-only fields enforcement
- [ ] ✅ Nested serialization (e.g., brand includes company)

### **File: `core/api/views.py`**
- [ ] ✅ CompanyViewSet /sync endpoint
- [ ] ✅ BrandViewSet /sync endpoint with brand_id filter
- [ ] ✅ StoreViewSet /sync endpoint with store_id filter
- [ ] ✅ UserViewSet /sync endpoint with brand_id filter
- [ ] ✅ last_sync parameter (incremental sync)
- [ ] ✅ JWT authentication required
- [ ] ✅ ReadOnlyViewSet (GET only)
- [ ] ❌ POST/PUT/DELETE should return 405 Method Not Allowed
- [ ] ✅ Response format: {count, last_sync, data[]}
- [ ] ✅ Filter Edge-specific data (user scope)

### **File: `config/urls.py`**
- [ ] ✅ JWT token obtain endpoint (/api/token/)
- [ ] ✅ JWT token refresh endpoint (/api/token/refresh/)
- [ ] ✅ Core API routes registered
- [ ] ✅ URL namespacing

### **Integration Tests**
- [ ] ✅ Obtain JWT token with valid credentials
- [ ] ✅ Refresh JWT token
- [ ] ❌ Access API without token (should return 401)
- [ ] ❌ Access API with expired token (should return 401)
- [ ] ✅ Sync companies (full)
- [ ] ✅ Sync brands (incremental with last_sync)
- [ ] ✅ Sync stores (filter by store_id)
- [ ] ✅ Sync users (filter by brand_id & role_scope)
- [ ] ✅ Edge pulls only authorized data (no cross-brand leakage)
- [ ] ✅ Sync products (TODO)
- [ ] ✅ Sync members (TODO - bidirectional)
- [ ] ✅ Sync promotions (TODO)
- [ ] ✅ Sync inventory (TODO)
- [ ] ✅ Push transactions from Edge to HO (TODO)

---

## ⚙️ PHASE 8: MANAGEMENT COMMANDS & AUTOMATION

### **File: `members/management/commands/expire_member_points.py`**
- [ ] ✅ Command executes without errors
- [ ] ✅ --dry-run mode (preview only)
- [ ] ✅ Process all active companies
- [ ] ✅ Calculate expiry date correctly (point_expiry_months)
- [ ] ✅ Identify transactions to expire
- [ ] ✅ Mark transactions as is_expired=True
- [ ] ✅ Create EXPIRED transaction records
- [ ] ✅ Update member.point_balance
- [ ] ✅ Audit trail (expired_at timestamp)
- [ ] ✅ Output summary (total points expired, members affected)
- [ ] ❌ Process inactive companies (should skip)
- [ ] ❌ Process companies with point_expiry_months=0 (should skip)
- [ ] ✅ Idempotency (running twice doesn't double-expire)

### **File: `core/management/commands/generate_sample_data.py`**
- [ ] ✅ Command executes without errors
- [ ] ✅ Create company (Yogya Group)
- [ ] ✅ Create brand (Ayam Geprek Express)
- [ ] ✅ Create stores (BSD, Senayan)
- [ ] ✅ Create users (admin, manager, cashier) with correct credentials
- [ ] ✅ Create categories
- [ ] ✅ Create products
- [ ] ✅ Create modifiers & options
- [ ] ✅ Link products to modifiers (M2M)
- [ ] ✅ Create sample members
- [ ] ✅ --clear flag (delete existing data)
- [ ] ✅ Data integrity (all FK relationships valid)
- [ ] ✅ Login with generated credentials
- [ ] ✅ Output summary with credentials

### **Celery Integration (Future)**
- [ ] ⏳ Setup Celery Beat scheduler
- [ ] ⏳ Schedule expire_member_points (daily)
- [ ] ⏳ Schedule sync health check (hourly)
- [ ] ⏳ Schedule report generation (daily)
- [ ] ⏳ Monitor Celery workers
- [ ] ⏳ Handle failed tasks

---

## 📊 END-TO-END WORKFLOW TESTS

### **Workflow 1: Complete Bill Flow (Edge → HO)**
1. [ ] ✅ Edge creates bill (OPEN)
2. [ ] ✅ Edge adds items to bill
3. [ ] ✅ Edge applies promotions
4. [ ] ✅ Edge processes payment
5. [ ] ✅ Edge closes bill (PAID)
6. [ ] ✅ Edge pushes bill to HO
7. [ ] ✅ HO receives and stores bill
8. [ ] ✅ HO denormalizes data correctly
9. [ ] ✅ HO generates reports

### **Workflow 2: Member Loyalty Flow**
1. [ ] ✅ Member registered at Edge
2. [ ] ✅ Member synced to HO
3. [ ] ✅ Member makes purchase
4. [ ] ✅ Points earned and recorded
5. [ ] ✅ MemberTransaction created
6. [ ] ✅ Member balance updated
7. [ ] ✅ Points synced to HO
8. [ ] ✅ Points expire after N months (automated)
9. [ ] ✅ Member redeems points
10. [ ] ✅ Points deducted and bill discounted

### **Workflow 3: Product & Inventory Flow**
1. [ ] ✅ HO creates product
2. [ ] ✅ HO creates recipe for product
3. [ ] ✅ HO adds ingredients to recipe
4. [ ] ✅ Edge pulls product & recipe
5. [ ] ✅ Edge sells product
6. [ ] ✅ Edge deducts inventory (recipe explosion)
7. [ ] ✅ Edge pushes inventory movement to HO
8. [ ] ✅ HO calculates COGS
9. [ ] ✅ HO generates margin report

### **Workflow 4: Promotion Application Flow**
1. [ ] ✅ HO creates promotion
2. [ ] ✅ Edge pulls promotion
3. [ ] ✅ Cashier creates bill at Edge
4. [ ] ✅ Promotion engine evaluates eligibility
5. [ ] ✅ Promotion applied (discount calculated)
6. [ ] ✅ Explainability log created
7. [ ] ✅ Bill total updated
8. [ ] ✅ PromotionUsage recorded
9. [ ] ✅ Data pushed to HO
10. [ ] ✅ HO reports promotion performance

### **Workflow 5: Refund Flow**
1. [ ] ✅ Customer requests refund
2. [ ] ✅ Cashier creates refund request (PENDING)
3. [ ] ✅ Manager approves refund
4. [ ] ✅ Refund bill created
5. [ ] ✅ Inventory reversed (if applicable)
6. [ ] ✅ Member points reversed (if applicable)
7. [ ] ✅ Refund synced to HO
8. [ ] ✅ HO updates revenue reports

### **Workflow 6: EOD (End of Day) Flow**
1. [ ] ✅ All shifts closed
2. [ ] ✅ Store session closed
3. [ ] ✅ Cash variance calculated
4. [ ] ✅ Sales summary generated
5. [ ] ✅ EOD data pushed to HO
6. [ ] ✅ HO aggregates multi-store reports
7. [ ] ✅ HO sends EOD summary email (future)

---

## 🔬 PERFORMANCE & SCALABILITY TESTS

### **Database Performance**
- [ ] ✅ Query bills by date range (< 100ms for 10k records)
- [ ] ✅ Query bills with items (N+1 issue resolved)
- [ ] ✅ Aggregate sales by store (indexed queries)
- [ ] ✅ Member lookup by phone (< 50ms)
- [ ] ✅ Product search by SKU (< 50ms)
- [ ] ✅ Promotion eligibility check (< 200ms for complex promo)
- [ ] ✅ Recipe explosion (< 100ms for 10 ingredients)
- [ ] ⚠️ Bulk insert 1000 bills (< 5s)
- [ ] ⚠️ Sync 10k products (< 10s)

### **API Performance**
- [ ] ✅ /api/v1/core/companies/sync/ (< 200ms)
- [ ] ✅ /api/v1/core/brands/sync/ (< 200ms)
- [ ] ✅ /api/v1/core/users/sync/ (< 300ms for 100 users)
- [ ] ⚠️ Concurrent sync requests (100 req/s)

### **Scalability Scenarios**
- [ ] ✅ 100 stores syncing simultaneously
- [ ] ✅ 10,000 members per company
- [ ] ✅ 50,000 products across all brands
- [ ] ✅ 1 million transactions per month
- [ ] ✅ 10,000 active promotions (filtered efficiently)

---

## 🛡️ SECURITY & PERMISSIONS TESTS

### **Authentication & Authorization**
- [ ] ✅ JWT token expiry enforced
- [ ] ✅ Refresh token rotation
- [ ] ❌ Replay attack (expired token should fail)
- [ ] ❌ Cross-tenant data access (should fail)
- [ ] ✅ Role-based access control (ADMIN > MANAGER > CASHIER)
- [ ] ✅ Role scope enforcement (company > brand > store)
- [ ] ❌ Cashier cannot access manager endpoints (should fail)
- [ ] ❌ Store user cannot access other store data (should fail)

### **Data Integrity**
- [ ] ✅ Foreign key constraints enforced
- [ ] ✅ Unique constraints enforced
- [ ] ✅ Check constraints (e.g., price >= 0)
- [ ] ✅ Atomic transactions (all-or-nothing)
- [ ] ✅ Audit trail integrity (created_by, updated_at)

### **Input Validation**
- [ ] ❌ SQL injection attempts (should fail)
- [ ] ❌ XSS attempts in text fields (should sanitize)
- [ ] ❌ Invalid JSON payloads (should return 400)
- [ ] ❌ Negative prices (should fail validation)
- [ ] ❌ Future dates in invalid contexts (should fail)

---

## 📖 DOCUMENTATION & USABILITY

### **Admin Interface**
- [ ] ✅ All models registered
- [ ] ✅ Intuitive list displays
- [ ] ✅ Effective search fields
- [ ] ✅ Useful filters
- [ ] ✅ Inline editing where appropriate
- [ ] ✅ Readable verbose names
- [ ] ✅ Help text on complex fields

### **API Documentation**
- [ ] ⏳ Install drf-spectacular
- [ ] ⏳ Generate OpenAPI schema
- [ ] ⏳ Interactive API docs (Swagger UI)
- [ ] ⏳ Example requests/responses
- [ ] ⏳ Authentication guide

### **Code Quality**
- [ ] ✅ Models have docstrings
- [ ] ✅ Views have docstrings
- [ ] ✅ Complex logic has comments
- [ ] ✅ Consistent naming conventions
- [ ] ✅ No hardcoded values (use settings)

---

## 🚀 DEPLOYMENT READINESS

### **Environment Configuration**
- [ ] ✅ .env.example provided
- [ ] ✅ Environment-specific settings (dev/prod)
- [ ] ✅ Secret key management
- [ ] ✅ Database URL configuration
- [ ] ✅ Redis URL configuration

### **Docker Setup**
- [ ] ✅ docker-compose.yml provided
- [ ] ✅ PostgreSQL service
- [ ] ✅ Redis service
- [ ] ⏳ Celery worker service (future)
- [ ] ⏳ Celery beat service (future)

### **Migrations**
- [ ] ✅ All migrations applied
- [ ] ✅ No migration conflicts
- [ ] ✅ Migrations reversible (where possible)

### **Static Files & Media**
- [ ] ✅ STATIC_ROOT configured
- [ ] ✅ MEDIA_ROOT configured
- [ ] ⏳ collectstatic command works
- [ ] ⏳ Media files served correctly

---

## 📝 TEST EXECUTION SUMMARY

**Total Test Cases**: ~350+

**Breakdown by Phase**:
- Phase 1 (Foundation): ~40 tests
- Phase 2 (Products): ~60 tests
- Phase 3 (Members): ~35 tests
- Phase 4 (Promotions): ~90 tests ⚠️ CRITICAL
- Phase 5 (Inventory): ~40 tests
- Phase 6 (Transactions): ~60 tests
- Phase 7 (Sync API): ~25 tests
- Phase 8 (Commands): ~15 tests
- End-to-End: ~30 tests
- Performance: ~15 tests
- Security: ~15 tests

**Legend**:
- ✅ = Must pass (blocking)
- ⚠️ = Performance benchmark (warning if fails)
- ❌ = Expected to fail (negative test)
- ⏳ = Future implementation (not blocking)

---

## 🎯 TESTING PRIORITY

### **P0 - Critical (Must Pass Before Production)**
1. Core multi-tenant isolation
2. User authentication & authorization
3. Bill creation & payment flow
4. Promotion engine accuracy
5. Inventory deduction correctness
6. Data sync integrity
7. Security & permissions

### **P1 - High (Should Pass)**
1. All CRUD operations
2. Admin interface usability
3. API endpoints functionality
4. Management commands
5. Member loyalty program
6. Refund workflows

### **P2 - Medium (Nice to Have)**
1. Performance benchmarks
2. Edge case handling
3. Explainability logs
4. Reporting queries

### **P3 - Low (Future)**
1. UI/UX enhancements
2. Advanced reporting
3. Export features
4. Email notifications

---

## 🏁 NEXT STEPS AFTER TESTING

1. **Fix all P0 failures** (blocking deployment)
2. **Document test coverage** (aim for >80%)
3. **Setup CI/CD pipeline** (run tests automatically)
4. **Implement remaining API endpoints** (products, members, promotions, inventory, transactions push)
5. **Add API documentation** (drf-spectacular)
6. **Setup Celery for automation**
7. **Performance optimization** (query optimization, caching)
8. **Security audit** (penetration testing)
9. **Load testing** (simulate production traffic)
10. **User acceptance testing** (UAT with real cashiers/managers)

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-22  
**Author**: AI Assistant (GenSpark)  
**Status**: Ready for Execution 🚀
