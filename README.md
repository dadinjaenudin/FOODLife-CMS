# 🍽️ F&B POS HO System (Head Office / Cloud)

**Multi-Tenant Cloud-Based Head Office System for F&B POS**

---

## 📖 Overview

Head Office (HO) system untuk mengelola **master data**, menerima **data transaksional** dari Edge Server, dan menyediakan **reporting & analytics** untuk jaringan restoran multi-brand.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    HO (Cloud - Django)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Master Data Management                           │  │
│  │ - Company / Brand / Store                        │  │
│  │ - Products / Categories / Modifiers              │  │
│  │ - Members / Loyalty                              │  │
│  │ - Promotions (12+ types)                         │  │
│  │ - Inventory / Recipes (BOM)                      │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ REST API (JWT Auth)                              │  │
│  │ - HO → Edge: Master data pull (incremental)     │  │
│  │ - Edge → HO: Transaction data push (async)      │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Transaction Reception (Read-Only)                │  │
│  │ - Bills / Payments / Refunds                     │  │
│  │ - Kitchen Orders                                 │  │
│  │ - Cash Drops / EOD Sessions                      │  │
│  │ - Inventory Movements                            │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Reporting & Analytics                            │  │
│  │ - Multi-store sales reports                      │  │
│  │ - Promotion performance                          │  │
│  │ - Inventory COGS & margin                        │  │
│  │ - Member loyalty analytics                       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↕ REST API (HTTPS)
┌─────────────────────────────────────────────────────────┐
│               Edge Server (Per Store - Django)          │
│  - POS UI (HTMX)                                        │
│  - Offline-first (LAN only)                             │
│  - Single source of truth per store                     │
│  - Pull master data from HO (periodic)                  │
│  - Push transactions to HO (async queue)                │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

### 1. **Multi-Tenant Hierarchy**
- **Company** → **Brand** → **Store** → **Terminal**
- Company: Yogya Group (YGY)
- Brand: Ayam Geprek Express (YGY-001), Bakso Boedjangan (YGY-002), etc.
- Store: BSD, Senayan, Gading, etc.
- Role-based access control: `company` > `brand` > `store`

### 2. **Master Data Management**
- **Products**: Categories, Products, Modifiers, Photos
- **Tables**: Areas, Tables, Table Groups (dine-in)
- **Members**: Loyalty program with points & tiers
- **Promotions**: 12+ types (BOGO, Happy Hour, Member Tier, Package, etc.)
- **Inventory**: Items, Recipes (BOM), Yield factors
- **Users**: Multi-scope authorization (Admin, Manager, Cashier)

### 3. **Promotion Engine** ⭐
**12+ Promotion Types**:
- Percent/Amount Discount
- BOGO (Buy X Get Y)
- Package/Set Menu
- Combo/Bundle
- Mix & Match
- Threshold/Tiered Discount
- Happy Hour (Time-based)
- Payment Method Discount
- Member Tier Discount
- Upsell/Add-on
- Voucher-based
- Manual Discount (with approval)

**Features**:
- Multi-brand scope
- Stacking rules & conflict resolution
- Execution priority
- Usage limits (per customer)
- Manager approval workflow
- Explainability logs (applied/skipped with reasons)

### 4. **Inventory & Recipe Management** ⭐
- **Inventory Items**: Raw Material, Semi-Finished, Finished Goods, Packaging
- **Recipes (BOM)**: Multi-versioned, with ingredients
- **Yield Factor**: Handle cooking loss & waste
- **COGS Calculation**: Recipe cost → Product margin
- **Stock Deduction**: POS sale → Recipe explosion → Inventory movement

### 5. **Transaction Data Reception**
HO receives transaction data from Edge Servers (read-only):
- **Bills**: Complete transaction records
- **BillItems**: Line items with modifiers
- **Payments**: Multi-payment support (CASH, CARD, QRIS, EWALLET, etc.)
- **BillPromotions**: Applied promotions tracking
- **CashDrops**: Cash management
- **StoreSession**: EOD sessions with variance
- **KitchenOrders**: Kitchen operations tracking
- **BillRefunds**: Refund workflow (with approval)
- **InventoryMovements**: Stock movements from POS

### 6. **Sync API (HO ↔ Edge)**
**HO → Edge (Master Data Pull)**:
- `/api/v1/core/companies/sync/`
- `/api/v1/core/brands/sync/`
- `/api/v1/core/stores/sync/`
- `/api/v1/core/users/sync/`
- TODO: Products, Members, Promotions, Inventory

**Edge → HO (Transaction Push)**: TODO

**Features**:
- Incremental sync with `last_sync` parameter
- JWT authentication
- Brand/Store filtering for Edge
- Read-only ViewSets

### 7. **Management Commands**
- `python manage.py expire_member_points` - Expire member points (daily)
- `python manage.py generate_sample_data` - Generate test data

---

## 🛠️ Tech Stack

- **Backend**: Django 5.0.1 + Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development)
- **Cache**: Redis (via django-redis)
- **Task Queue**: Celery + Redis (scheduled jobs)
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Admin**: Django Admin (customized)
- **Deployment**: Docker Compose (HO), PyInstaller (Edge)

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ (production) or SQLite (dev)
- Redis (for caching & Celery)

### 1. Clone & Setup Virtual Environment

```bash
git clone <repository-url>
cd webapp
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 4. Database Setup

**Development (SQLite)**:
```bash
python manage.py migrate
python manage.py createsuperuser
```

**Production (PostgreSQL via Docker)**:
```bash
docker-compose up -d db redis
python manage.py migrate
python manage.py createsuperuser
```

### 5. Generate Sample Data (Optional)

```bash
python manage.py generate_sample_data

# Login credentials:
# - Admin: admin / admin123
# - Manager: manager_bsd / manager123
# - Cashier: cashier1 / cashier123 (PIN: 1234)
```

### 6. Run Development Server

```bash
python manage.py runserver
```

Access admin: http://localhost:8000/admin/

---

## 📁 Project Structure

```
webapp/
├── config/                 # Django project settings
│   ├── settings.py        # Production-ready settings
│   ├── urls.py            # Main URL config (includes API)
│   ├── celery.py          # Celery configuration
│   └── wsgi.py
├── core/                   # Multi-tenant core models
│   ├── models.py          # Company, Brand, Store, User
│   ├── admin.py           # Admin with multi-tenant filtering
│   ├── api/               # REST API endpoints
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   └── management/commands/
│       └── generate_sample_data.py
├── products/               # Product catalog
│   ├── models.py          # Category, Product, Modifier, Table, etc.
│   └── admin.py
├── members/                # Loyalty program
│   ├── models.py          # Member, MemberTransaction
│   ├── admin.py
│   └── management/commands/
│       └── expire_member_points.py
├── promotions/             # Promotion engine (12+ types)
│   ├── models.py          # Promotion, PackagePromotion, Voucher, etc.
│   └── admin.py
├── inventory/              # Inventory & Recipe (BOM)
│   ├── models.py          # InventoryItem, Recipe, RecipeIngredient
│   └── admin.py
├── transactions/           # Transaction data from Edge (read-only)
│   ├── models.py          # Bill, BillItem, Payment, etc.
│   └── admin.py
├── docker-compose.yml      # PostgreSQL + Redis
├── requirements.txt
├── .env.example
├── README.md              # This file
└── TESTING_CHECKLIST.md   # Comprehensive testing guide (350+ tests)
```

---

## 📊 Database Schema

**Total Tables**: 48+

**Core Models** (4):
- Company, Brand, Store, User

**Product Models** (12):
- Category, Product, ProductPhoto, Modifier, ModifierOption, ProductModifier
- TableArea, Table, TableGroup, TableGroupMember
- KitchenStation, PrinterConfig

**Member Models** (2):
- Member, MemberTransaction

**Promotion Models** (8):
- Promotion, PackagePromotion, PackageItem, PromotionTier
- Voucher, PromotionUsage, PromotionLog, PromotionApproval
- CustomerPromotionHistory

**Inventory Models** (3):
- InventoryItem, Recipe, RecipeIngredient

**Transaction Models** (10):
- Bill, BillItem, Payment, BillPromotion
- CashDrop, StoreSession, CashierShift
- KitchenOrder, BillRefund, InventoryMovement

See `TESTING_CHECKLIST.md` for detailed field descriptions.

---

## 🔐 Authentication & Permissions

### JWT Authentication

**Obtain Token**:
```bash
POST /api/token/
{
  "username": "admin",
  "password": "admin123"
}

# Response:
{
  "access": "eyJ0eXAiOiJKV1Q...",
  "refresh": "eyJ0eXAiOiJKV1Q..."
}
```

**Use Token**:
```bash
GET /api/v1/core/companies/sync/
Authorization: Bearer eyJ0eXAiOiJKV1Q...
```

**Refresh Token**:
```bash
POST /api/token/refresh/
{
  "refresh": "eyJ0eXAiOiJKV1Q..."
}
```

### Role-Based Access Control

| Role         | Scope    | Permissions                                      |
|--------------|----------|--------------------------------------------------|
| ADMIN        | Company  | Full access to all brands & stores              |
| MANAGER      | Brand    | Manage brand settings, users, products          |
| SUPERVISOR   | Store    | Store operations, shift management              |
| CASHIER      | Store    | POS operations only (Edge)                      |
| KITCHEN_STAFF| Store    | Kitchen display & order management (Edge)       |
| WAITER       | Store    | Table service, orders (Edge)                    |

---

## 🧪 Testing

See **`TESTING_CHECKLIST.md`** for comprehensive testing guide.

**350+ Test Cases** covering:
- Unit tests (models, business logic)
- Integration tests (API, multi-model operations)
- Admin tests (Django admin functionality)
- Command tests (management commands)
- End-to-end tests (complete workflows)
- Performance tests (query benchmarks)
- Security tests (authentication, authorization, input validation)

**Run Tests** (when implemented):
```bash
python manage.py test
```

---

## 📝 API Documentation

**Base URL**: `http://localhost:8000/api/v1/`

### Core Endpoints

| Endpoint                         | Method | Description                     | Auth Required |
|----------------------------------|--------|---------------------------------|---------------|
| `/api/token/`                    | POST   | Obtain JWT token                | No            |
| `/api/token/refresh/`            | POST   | Refresh JWT token               | No            |
| `/api/v1/core/companies/sync/`   | GET    | Sync companies (incremental)    | Yes           |
| `/api/v1/core/brands/sync/`      | GET    | Sync brands (by brand_id)       | Yes           |
| `/api/v1/core/stores/sync/`      | GET    | Sync stores (by store_id)       | Yes           |
| `/api/v1/core/users/sync/`       | GET    | Sync users (by brand_id)        | Yes           |

**Query Parameters**:
- `last_sync`: ISO datetime (e.g., `2024-01-22T10:30:00Z`) for incremental sync
- `brand_id`: UUID (filter by brand)
- `store_id`: UUID (filter by store)

**Response Format**:
```json
{
  "count": 5,
  "last_sync": "2024-01-22T12:00:00Z",
  "data": [...]
}
```

**TODO**: Add OpenAPI schema with drf-spectacular

---

## 🚀 Deployment

### Development

```bash
python manage.py runserver
```

### Production (Docker Compose)

```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic --noinput
```

### Environment Variables

See `.env.example` for required variables:
- `SECRET_KEY`: Django secret key
- `DEBUG`: True/False
- `DB_ENGINE`: postgresql / sqlite3
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `REDIS_URL`: redis://localhost:6379/0

---

## 📈 Roadmap

### ✅ Completed (Phase 1-8)
- [x] Phase 1: Foundation & Multi-Tenant Core
- [x] Phase 2: Product Catalog & Tables
- [x] Phase 3: Member & Loyalty Program
- [x] Phase 4: Promotion Engine (12+ types)
- [x] Phase 5: Inventory & Recipe Management
- [x] Phase 6: Transaction Data Reception
- [x] Phase 7: Sync API (Core endpoints)
- [x] Phase 8: Management Commands

### 🔄 In Progress
- [ ] Phase 7 (continued): Remaining API endpoints
  - [ ] Products API
  - [ ] Members API (bidirectional sync)
  - [ ] Promotions API
  - [ ] Inventory API
  - [ ] Transactions push API (Edge → HO)

### 📅 Upcoming
- [ ] Phase 9: Celery Beat (scheduled tasks)
- [ ] Phase 10: Reporting & Analytics UI
- [ ] Phase 11: API Documentation (drf-spectacular)
- [ ] Phase 12: Performance Optimization
- [ ] Phase 13: Security Audit
- [ ] Phase 14: Load Testing & Production Deployment

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'feat: Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

**Commit Message Convention**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

---

## 📄 License

Proprietary - Yogya Group © 2026

---

## 📞 Support

For questions or issues, contact:
- **Email**: info@yogyagroup.com
- **Slack**: #pos-development

---

## 🙏 Acknowledgments

- Django Framework
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- All open-source contributors

---

**Version**: 1.0  
**Last Updated**: 2026-01-22  
**Status**: Development (Phase 1-8 Complete) ✅
