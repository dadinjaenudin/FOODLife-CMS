"""
Django settings for F&B HO (Head Office) Project.
Multi-Tenant POS System - Master Data Management
"""

from pathlib import Path
import environ
import os
from datetime import timedelta

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Application definition
INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'import_export',
    'django_extensions',
    'drf_spectacular',  # API Documentation
    'django_htmx',      # HTMX integration
    
    # Local apps
    'core',           # Multi-tenant core (Company, Brand, Store, User)
    'products',       # Product catalog (Category, Product, Modifier)
    'members',        # Member & Loyalty program
    'promotions',     # Promotion engine
    'inventory',      # Inventory & Recipe management
    'transactions',   # Transaction data from Edge
    'analytics',      # Reporting & Analytics
    'dashboard',      # Dashboard & UI
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files
    'corsheaders.middleware.CorsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',  # HTMX       # CORS
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DB_ENGINE = env('DB_ENGINE')

if DB_ENGINE == 'django.db.backends.sqlite3':
    # SQLite configuration (development)
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': BASE_DIR / env('DB_NAME'),
        }
    }
else:
    # PostgreSQL configuration (production)
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }

# Cache Configuration
REDIS_URL = env('REDIS_URL')

if 'locmem://' in REDIS_URL or 'memory://' in REDIS_URL:
    # Memory cache for development
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
else:
    # Redis cache for production
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'fnb_ho',
            'TIMEOUT': 300,
        }
    }

# Session Configuration (use Redis)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Internationalization
LANGUAGE_CODE = env('LANGUAGE_CODE')
TIME_ZONE = env('TIME_ZONE')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
    # API Documentation with drf-spectacular
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME', default=60)),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_REFRESH_TOKEN_LIFETIME', default=1440)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in development
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Celery Beat Schedule (for scheduled tasks)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'expire-member-points-daily': {
        'task': 'members.tasks.expire_member_points',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO' if not DEBUG else 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if not exists
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Email Configuration
EMAIL_BACKEND = env('EMAIL_BACKEND')
if EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend':
    EMAIL_HOST = env('EMAIL_HOST')
    EMAIL_PORT = env.int('EMAIL_PORT')
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')
    EMAIL_HOST_USER = env('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')

# Application Specific Settings
ENVIRONMENT = env('ENVIRONMENT', default='development')

# Multi-Tenant Settings
TENANT_MODEL = 'core.Company'
TENANT_FIELD = 'company'

# Member & Loyalty Defaults
DEFAULT_POINT_EXPIRY_MONTHS = 12
DEFAULT_POINTS_PER_CURRENCY = 1.00

# Promotion Engine Settings
MAX_PROMOTION_STACK = 5  # Maximum number of promotions that can be stacked
PROMOTION_EXECUTION_TIMEOUT = 10  # seconds

# Security Settings (Production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ===================================================================
# DRF-SPECTACULAR (API DOCUMENTATION) CONFIGURATION
# ===================================================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'F&B POS HO System API',
    'DESCRIPTION': '''
# F&B POS Head Office API Documentation

Multi-Tenant Cloud-Based Head Office System untuk F&B POS.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         HO (Cloud - Django)             │
│  ┌──────────────────────────────────┐  │
│  │ Master Data Management           │  │
│  │ - Company / Brand / Store        │  │
│  │ - Products / Categories          │  │
│  │ - Members / Loyalty              │  │
│  │ - Promotions (12+ types)         │  │
│  │ - Inventory / Recipes (BOM)      │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ REST API (JWT Auth)              │  │
│  │ - HO → Edge: Master data pull    │  │
│  │ - Edge → HO: Transaction push    │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ Analytics & Reporting            │  │
│  │ - Daily sales, product analysis  │  │
│  │ - Promotion performance          │  │
│  │ - Member analytics, COGS         │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
              ↕ REST API (HTTPS)
┌─────────────────────────────────────────┐
│   Edge Server (Per Store - Django)      │
│  - POS UI (HTMX)                        │
│  - Offline-first (LAN only)             │
│  - Pull master data from HO (periodic)  │
│  - Push transactions to HO (async)      │
└─────────────────────────────────────────┘
```

## Authentication

All API endpoints require JWT authentication:

1. **Obtain Token**: `POST /api/token/`
   ```json
   {
     "username": "your_username",
     "password": "your_password"
   }
   ```
   
2. **Use Token**: Add header to requests:
   ```
   Authorization: Bearer <access_token>
   ```

3. **Refresh Token**: `POST /api/token/refresh/`
   ```json
   {
     "refresh": "<refresh_token>"
   }
   ```

## API Categories

### 1. Core API - Multi-Tenant Master Data
- Company, Brand, Store, User management
- Base URL: `/api/v1/core/`

### 2. Products API - Product Catalog
- Categories, Products, Modifiers, Tables
- Base URL: `/api/v1/products/`

### 3. Members API - Loyalty Program (Bidirectional)
- Member registration, lookup, transactions
- Base URL: `/api/v1/members/`

### 4. Promotions API - Promotion Engine
- 12+ promotion types, vouchers, usage tracking
- Base URL: `/api/v1/promotions/`

### 5. Inventory API - Inventory & Recipe (BOM)
- Inventory items, recipes with ingredients
- Base URL: `/api/v1/inventory/`

### 6. Transactions API - Transaction Push (Edge → HO)
- Bills, payments, sessions, refunds
- Base URL: `/api/v1/transactions/`

### 7. Analytics API - Reporting & Analytics
- Sales reports, product analysis, member analytics
- Base URL: `/api/v1/analytics/`

## Sync Workflow

### Edge Startup Sync
1. Obtain JWT token
2. Pull company/brand/store data
3. Pull users for brand
4. Pull products, categories, modifiers
5. Pull promotions (active only)
6. Pull inventory items & recipes
7. Pull members (company-wide)

### Periodic Sync (Every 5 minutes)
Use `last_sync` parameter for incremental sync:
```
GET /api/v1/products/products/sync/?brand_id=xxx&last_sync=2024-01-22T10:30:00Z
```

### Transaction Push (After bill paid / EOD)
```
POST /api/v1/transactions/bills/push/
POST /api/v1/transactions/bulk-push/
```

## Response Format

Standard success response:
```json
{
  "count": 10,
  "last_sync": "2024-01-22T12:00:00Z",
  "data": [...]
}
```

Standard error response:
```json
{
  "error": "Error message",
  "detail": "Detailed error information"
}
```

## Common Query Parameters

- `brand_id`: Filter by brand (UUID)
- `store_id`: Filter by store (UUID)
- `company_id`: Filter by company (UUID)
- `last_sync`: ISO datetime for incremental sync
- `start_date`: Date range start (YYYY-MM-DD)
- `end_date`: Date range end (YYYY-MM-DD)

## Rate Limiting

- Default: 100 requests per minute per user
- Bulk operations: 10 requests per minute

## Support

- Repository: https://github.com/dadinjaenudin/FoodBeverages-CMS
- Documentation: See README.md
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'displayRequestDuration': True,
        'filter': True,
        'docExpansion': 'none',
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
    },
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': True,
    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': 'Development server'},
        {'url': 'https://api.yogyagroup.com', 'description': 'Production server'},
    ],
    'TAGS': [
        {'name': 'Authentication', 'description': 'JWT token management'},
        {'name': 'Core', 'description': 'Multi-tenant core (Company, Brand, Store, User)'},
        {'name': 'Products', 'description': 'Product catalog & table management'},
        {'name': 'Members', 'description': 'Loyalty program (bidirectional sync)'},
        {'name': 'Promotions', 'description': 'Promotion engine (12+ types)'},
        {'name': 'Inventory', 'description': 'Inventory & recipe (BOM) management'},
        {'name': 'Transactions', 'description': 'Transaction push (Edge → HO)'},
        {'name': 'Analytics', 'description': 'Reporting & analytics'},
    ],
    'EXTERNAL_DOCS': {
        'description': 'GitHub Repository',
        'url': 'https://github.com/dadinjaenudin/FoodBeverages-CMS',
    },
    'CONTACT': {
        'name': 'Yogya Group IT Team',
        'email': 'info@yogyagroup.com',
    },
    'LICENSE': {
        'name': 'Proprietary',
    },
    # Security schemes
    'SECURITY': [{'Bearer': []}],
    'COMPONENTS': {
        'securitySchemes': {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
            }
        }
    },
    # Preprocessing
    'PREPROCESSING_HOOKS': [],
    'POSTPROCESSING_HOOKS': [],
    'SCHEMA_PATH_PREFIX': r'/api/v1/',
    'ENUM_NAME_OVERRIDES': {},
}


# Authentication URLs
LOGIN_URL = 'auth:login'
LOGIN_REDIRECT_URL = 'dashboard:index'
LOGOUT_REDIRECT_URL = 'auth:login'


# CSRF Settings for HTMX
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF cookie
CSRF_TRUSTED_ORIGINS = [
    'https://8000-i56a4gtwdhxhy7tubdwem-583b4d74.sandbox.novita.ai',
    'https://*.sandbox.novita.ai',
]

