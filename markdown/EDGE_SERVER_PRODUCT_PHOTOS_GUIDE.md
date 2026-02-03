# Edge Server - Product Photos Loading Guide

**Date**: February 3, 2026  
**System**: FoodLife F&B POS - Edge Server Implementation  
**Purpose**: Guide untuk mengimplementasikan product photos loading dari HO MinIO ke Edge MinIO

---

## Overview

Edge Server mendapatkan daftar product photos dari HO API (`/api/v1/sync/product-photos/`), kemudian mendownload image files langsung dari **HO MinIO** dan menyimpannya di **Edge MinIO** untuk akses lokal yang lebih cepat.

### Architecture Flow

```
Edge Server → HO API (get photo metadata + URLs)
            ↓
Edge Server → HO MinIO (download image files directly)
            ↓
Edge Server → Edge MinIO (upload to local storage)
            ↓
Edge PostgreSQL (save metadata with local object_key)
```

---

## Step 1: Get Product Photos List from HO API

### API Endpoint
```
POST http://HO_SERVER:8002/api/v1/sync/product-photos/
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

### Request Body
```json
{
  "company_id": "48917ccd-b3f6-4984-b6ed-a96d9d5c8d9b",
  "store_id": "fe2d2dbf-9616-48f5-bd5b-302c087d7181",
  "limit": 100,
  "offset": 0
}
```

### Response Example
```json
{
  "photos": [
    {
      "id": "73ce4e57-19f0-44f8-8e3d-ea1c27c0e21b",
      "product_id": "63ea9d40-47f2-4202-95b6-f9b9e798d762",
      "product_sku": "05018970",
      "product_name": "ASAHI SALMON BOWL",
      "object_key": "products/63ea9d40-47f2-4202-95b6-f9b9e798d762/primary.jpg",
      "filename": "Menu_Image_20250922025939.jpg",
      "size": 43111,
      "content_type": "image/jpeg",
      "checksum": "5cd6a73f49b355a6fd4347f5dd0a2338",
      "version": 1,
      "is_primary": true,
      "sort_order": 0,
      "updated_at": "2026-02-03T04:14:24.796133+00:00",
      "image_url": "http://HO_MINIO_HOST:9000/product-images/products/63ea9d40-47f2-4202-95b6-f9b9e798d762/primary.jpg?v=5cd6a73f"
    },
    {
      "id": "7067df8c-ef2b-40e0-9125-4617322d6d61",
      "product_id": "8fc95977-3e87-46e9-b911-c9d744f7e7ff",
      "product_sku": "05015917",
      "product_name": "ASIATIQUE SPAGHETTI VONGOLE",
      "object_key": "products/8fc95977-3e87-46e9-b911-c9d744f7e7ff/primary.webp",
      "filename": "Menu_Image_20250904021453.webp",
      "size": 49124,
      "content_type": "image/webp",
      "checksum": "42f666388fc03ee559c172ebb6132d6a",
      "version": 1,
      "is_primary": true,
      "sort_order": 0,
      "updated_at": "2026-02-03T04:14:35.015113+00:00",
      "image_url": "http://HO_MINIO_HOST:9000/product-images/products/8fc95977-3e87-46e9-b911-c9d744f7e7ff/primary.webp?v=42f66638"
    }
  ],
  "deleted_ids": [],
  "sync_timestamp": "2026-02-03T07:26:11.813339+00:00",
  "total": 2,
  "has_more": false,
  "next_offset": null,
  "filter": {
    "company_id": "48917ccd-b3f6-4984-b6ed-a96d9d5c8d9b",
    "store_id": "fe2d2dbf-9616-48f5-bd5b-302c087d7181"
  },
  "store": {
    "id": "fe2d2dbf-9616-48f5-bd5b-302c087d7181",
    "code": "AVRIL-001",
    "name": "AVR-SUNDA"
  }
}
```

---

## Step 2: Download Images from HO MinIO

### Important Fields dari Response

| Field | Purpose | Example |
|-------|---------|---------|
| `image_url` | **Direct download URL** dari HO MinIO | `http://HO:9000/product-images/products/xxx/primary.jpg?v=5cd6a73f` |
| `checksum` | MD5 hash untuk validasi integritas file | `5cd6a73f49b355a6fd4347f5dd0a2338` |
| `object_key` | Path object di MinIO | `products/63ea9d40-.../primary.jpg` |
| `size` | File size dalam bytes | `43111` |
| `content_type` | MIME type | `image/jpeg` atau `image/webp` |

### Cache-Busting Mechanism

URL **sudah include cache-busting parameter** `?v={checksum[:8]}`:
- Parameter `v` berisi 8 karakter pertama dari checksum
- Setiap kali image diupdate di HO, checksum berubah → URL berubah
- Browser/cache otomatis fetch versi terbaru

### Download Implementation (Python Example)

```python
import requests
import hashlib
from minio import Minio

def download_and_verify_image(photo_data):
    """
    Download image dari HO MinIO dan verify integrity
    
    Args:
        photo_data: Dict containing photo metadata from API
        
    Returns:
        bytes: Image content if valid, None if failed
    """
    image_url = photo_data['image_url']
    expected_checksum = photo_data['checksum']
    expected_size = photo_data['size']
    
    try:
        # Download image dari HO MinIO
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        image_bytes = response.content
        
        # Verify file size
        if len(image_bytes) != expected_size:
            print(f"Size mismatch: expected {expected_size}, got {len(image_bytes)}")
            return None
        
        # Verify checksum (MD5)
        actual_checksum = hashlib.md5(image_bytes).hexdigest()
        if actual_checksum != expected_checksum:
            print(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
            return None
        
        print(f"✓ Downloaded and verified: {photo_data['filename']}")
        return image_bytes
        
    except Exception as e:
        print(f"Failed to download {image_url}: {e}")
        return None
```

---

## Step 3: Upload to Edge MinIO

### Edge MinIO Configuration

```python
# Edge MinIO Client Setup
edge_minio = Minio(
    "edge_minio:9000",  # Edge MinIO host (dalam Docker network)
    access_key="edge_foodlife_admin",
    secret_key="edge_foodlife_secret_2026",
    secure=False  # Use True jika pakai HTTPS
)

# Ensure bucket exists
bucket_name = "product-images"
if not edge_minio.bucket_exists(bucket_name):
    edge_minio.make_bucket(bucket_name)
    # Set public read policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
            }
        ]
    }
    edge_minio.set_bucket_policy(bucket_name, json.dumps(policy))
```

### Upload Implementation

```python
from io import BytesIO

def upload_to_edge_minio(photo_data, image_bytes):
    """
    Upload image ke Edge MinIO
    
    Args:
        photo_data: Photo metadata from HO API
        image_bytes: Image content yang sudah didownload
        
    Returns:
        str: Object key di Edge MinIO, or None if failed
    """
    object_key = photo_data['object_key']  # Gunakan object_key yang sama
    content_type = photo_data['content_type']
    size = len(image_bytes)
    
    try:
        # Upload ke Edge MinIO
        edge_minio.put_object(
            bucket_name="product-images",
            object_name=object_key,
            data=BytesIO(image_bytes),
            length=size,
            content_type=content_type
        )
        
        print(f"✓ Uploaded to Edge MinIO: {object_key}")
        return object_key
        
    except Exception as e:
        print(f"Failed to upload {object_key}: {e}")
        return None
```

---

## Step 4: Save Metadata to Edge PostgreSQL

### Database Schema

```sql
CREATE TABLE product_photo (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL,
    object_key VARCHAR(500),
    filename VARCHAR(255),
    size INTEGER,
    content_type VARCHAR(100),
    checksum VARCHAR(32),
    version INTEGER DEFAULT 1,
    is_primary BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
);

CREATE INDEX idx_product_photo_product ON product_photo(product_id);
CREATE INDEX idx_product_photo_primary ON product_photo(product_id, is_primary);
```

### Save Implementation (Django Example)

```python
from django.db import transaction

def save_product_photo_to_edge(photo_data, edge_object_key):
    """
    Save product photo metadata ke Edge PostgreSQL
    
    Args:
        photo_data: Photo metadata from HO API
        edge_object_key: Object key di Edge MinIO (after upload)
    """
    from products.models import ProductPhoto, Product
    
    try:
        # Check if product exists di Edge
        product = Product.objects.get(id=photo_data['product_id'])
        
        # Create or update photo record
        photo, created = ProductPhoto.objects.update_or_create(
            id=photo_data['id'],
            defaults={
                'product': product,
                'object_key': edge_object_key,  # Local edge MinIO path
                'filename': photo_data['filename'],
                'size': photo_data['size'],
                'content_type': photo_data['content_type'],
                'checksum': photo_data['checksum'],
                'version': photo_data['version'],
                'is_primary': photo_data['is_primary'],
                'sort_order': photo_data['sort_order'],
            }
        )
        
        action = "Created" if created else "Updated"
        print(f"✓ {action} photo record: {photo.id}")
        return photo
        
    except Product.DoesNotExist:
        print(f"Product {photo_data['product_id']} not found in Edge database")
        return None
    except Exception as e:
        print(f"Failed to save photo metadata: {e}")
        return None
```

---

## Step 5: Complete Sync Process

### Full Sync Implementation

```python
def sync_product_photos(company_id, store_id):
    """
    Complete sync process: HO API → Download → Edge MinIO → Edge DB
    """
    # 1. Get JWT token
    token = get_jwt_token()
    
    # 2. Fetch photos from HO API
    offset = 0
    limit = 100
    has_more = True
    
    success_count = 0
    failed_count = 0
    
    while has_more:
        # Request to HO API
        response = requests.post(
            f"{HO_API_URL}/api/v1/sync/product-photos/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "company_id": company_id,
                "store_id": store_id,
                "limit": limit,
                "offset": offset
            }
        )
        
        data = response.json()
        photos = data['photos']
        has_more = data['has_more']
        
        # Process each photo
        for photo_data in photos:
            try:
                # 3. Download from HO MinIO
                image_bytes = download_and_verify_image(photo_data)
                if not image_bytes:
                    failed_count += 1
                    continue
                
                # 4. Upload to Edge MinIO
                edge_object_key = upload_to_edge_minio(photo_data, image_bytes)
                if not edge_object_key:
                    failed_count += 1
                    continue
                
                # 5. Save metadata to Edge DB
                photo_record = save_product_photo_to_edge(photo_data, edge_object_key)
                if photo_record:
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"Error processing photo {photo_data['id']}: {e}")
                failed_count += 1
        
        # Move to next page
        if has_more:
            offset = data['next_offset']
    
    print(f"\n=== Sync Complete ===")
    print(f"Success: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Total: {success_count + failed_count}")
    
    return success_count, failed_count
```

---

## Step 6: Accessing Images in Edge POS

### Generate Image URL for POS Display

```python
def get_product_image_url(product_id):
    """
    Get image URL untuk display di POS
    Returns URL dari Edge MinIO (local, cepat)
    """
    from products.models import ProductPhoto
    
    try:
        # Get primary photo
        photo = ProductPhoto.objects.get(
            product_id=product_id,
            is_primary=True
        )
        
        # Generate Edge MinIO URL
        edge_minio_url = f"http://edge_minio:9000/product-images/{photo.object_key}"
        
        # Add cache-busting
        cache_param = photo.checksum[:8] if photo.checksum else photo.version
        image_url = f"{edge_minio_url}?v={cache_param}"
        
        return image_url
        
    except ProductPhoto.DoesNotExist:
        # Return default placeholder image
        return "/static/images/no-image.png"
```

### Display in POS Frontend (JavaScript)

```javascript
// Load product image dengan error handling
function loadProductImage(productId, imgElement) {
    fetch(`/api/products/${productId}/image`)
        .then(response => response.json())
        .then(data => {
            imgElement.src = data.image_url;
            imgElement.alt = data.product_name;
        })
        .catch(error => {
            // Fallback to placeholder
            imgElement.src = '/static/images/no-image.png';
            console.error('Failed to load image:', error);
        });
}
```

---

## Performance Considerations

### 1. Parallel Downloads
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def sync_photos_parallel(photos, max_workers=10):
    """Download multiple images in parallel"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_photo, photo): photo 
            for photo in photos
        }
        
        for future in as_completed(futures):
            photo = futures[future]
            try:
                result = future.result()
                print(f"✓ Processed: {photo['filename']}")
            except Exception as e:
                print(f"✗ Failed: {photo['filename']} - {e}")
```

### 2. Incremental Sync
```python
# Gunakan updated_since untuk sync hanya foto yang berubah
last_sync = get_last_sync_timestamp()  # From local DB

response = requests.post(
    f"{HO_API_URL}/api/v1/sync/product-photos/",
    json={
        "company_id": company_id,
        "store_id": store_id,
        "updated_since": last_sync  # ISO format: "2026-02-03T00:00:00Z"
    }
)
```

### 3. Bandwidth Optimization
- Sync during off-peak hours (malam hari)
- Compress large images before storage
- Use resume capability for large files
- Monitor bandwidth usage

---

## Error Handling

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid/expired JWT token | Refresh token before sync |
| 404 Not Found | Invalid store_id | Verify store exists via `/sync/stores/` |
| Checksum mismatch | Corrupted download | Retry download up to 3 times |
| MinIO upload failed | Edge MinIO down/full | Check Edge MinIO status, disk space |
| Connection timeout | Network issues | Increase timeout, retry with backoff |

### Retry Logic

```python
import time

def download_with_retry(url, max_retries=3):
    """Download with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s...")
            time.sleep(wait_time)
```

---

## Monitoring & Logging

### Key Metrics to Track

```python
import logging

logger = logging.getLogger('product_photo_sync')

def log_sync_metrics(start_time, success_count, failed_count, total_bytes):
    """Log sync metrics for monitoring"""
    duration = time.time() - start_time
    
    logger.info(f"=== Photo Sync Metrics ===")
    logger.info(f"Duration: {duration:.2f}s")
    logger.info(f"Success: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Total bytes: {total_bytes / 1024 / 1024:.2f} MB")
    logger.info(f"Average speed: {(total_bytes / duration / 1024):.2f} KB/s")
```

---

## Testing

### Manual Test via curl

```bash
# 1. Get JWT token
TOKEN=$(curl -X POST http://HO_HOST:8002/api/v1/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | jq -r '.access')

# 2. Get product photos list
curl -X POST http://HO_HOST:8002/api/v1/sync/product-photos/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "48917ccd-b3f6-4984-b6ed-a96d9d5c8d9b",
    "store_id": "fe2d2dbf-9616-48f5-bd5b-302c087d7181"
  }' | jq .

# 3. Download image directly
curl -o test_image.jpg "http://HO_MINIO:9000/product-images/products/.../primary.jpg?v=5cd6a73f"

# 4. Verify checksum
md5sum test_image.jpg
# Should match checksum from API response
```

---

## Summary

### Key Points

1. **Image URL sudah include cache-busting** - Tidak perlu implement manual caching logic
2. **Download langsung dari HO MinIO** - Tidak ada proxy/intermediary API
3. **Verify integrity dengan checksum** - Setiap download harus diverify MD5
4. **Store di Edge MinIO** - Gunakan object_key yang sama untuk consistency
5. **Incremental sync supported** - Gunakan `updated_since` parameter

### Sync Schedule Recommendation

```python
# Celery Beat Schedule (config/settings.py)
CELERY_BEAT_SCHEDULE = {
    'sync-product-photos-hourly': {
        'task': 'sync_api.tasks.sync_product_photos',
        'schedule': crontab(minute=0),  # Every hour
    },
    'sync-product-photos-nightly-full': {
        'task': 'sync_api.tasks.sync_product_photos_full',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily full sync
    },
}
```

---

## Related Documentation

- [PRODUCT_PHOTO_SYNC_API_REFERENCE.md](./PRODUCT_PHOTO_SYNC_API_REFERENCE.md) - Detailed API documentation
- [EDGE_SERVER_IMAGE_SYNC_IMPLEMENTATION.md](./EDGE_SERVER_IMAGE_SYNC_IMPLEMENTATION.md) - Complete implementation guide
- [MINIO_SETUP.md](./MINIO_SETUP.md) - MinIO configuration guide

---

**Last Updated**: February 3, 2026  
**Version**: 1.0  
**Author**: System Integration Team
