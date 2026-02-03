# Edge Server Image Synchronization Implementation

## Overview
Dokumentasi implementasi sinkronisasi product images dari MinIO (HO Server) ke Edge Server PostgreSQL, memungkinkan edge server menggunakan image lokal tanpa koneksi ke MinIO pusat.

---

## Architecture

### Current Flow
```
HO Server (MinIO) → Edge Server (Request from MinIO) → Display
```

### New Flow with Sync
```
HO Server (MinIO) → Sync API → Edge Server PostgreSQL (binary storage) → Display
```

---

## Database Schema Changes

### Edge Server: `product_photo` Table
```sql
ALTER TABLE product_photo ADD COLUMN image_binary BYTEA;
ALTER TABLE product_photo ADD COLUMN last_sync_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE product_photo ADD COLUMN sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE product_photo ADD COLUMN sync_error TEXT;

CREATE INDEX idx_product_photo_sync_status ON product_photo(sync_status);
CREATE INDEX idx_product_photo_last_sync ON product_photo(last_sync_at);
```

### HO Server: Tracking Changes
```sql
-- Already exists in current schema
-- product_photo.updated_at will be used for incremental sync
-- product_photo.checksum will be used to detect changes
```

---

## ProductPhoto Model Fields

### Fields to Sync from HO to Edge

| Field | Type | Purpose | Sync Priority |
|-------|------|---------|---------------|
| `id` | UUID | Primary key | ✅ Required |
| `product_id` | UUID | Foreign key to product | ✅ Required |
| `object_key` | VARCHAR(500) | MinIO path reference | ✅ Required |
| `filename` | VARCHAR(255) | Original filename | ✅ Required |
| `size` | INTEGER | File size in bytes | ✅ Required |
| `content_type` | VARCHAR(100) | MIME type | ✅ Required |
| `checksum` | VARCHAR(64) | MD5 checksum | ✅ Required |
| `version` | INTEGER | Image version | ✅ Required |
| `is_primary` | BOOLEAN | Primary display photo | ✅ Required |
| `sort_order` | INTEGER | Display order | ✅ Required |
| `created_at` | TIMESTAMP | Creation time | ⚠️ Optional |
| `updated_at` | TIMESTAMP | Last update time | ⚠️ Optional |

### Edge Server Additional Fields

| Field | Type | Purpose |
|-------|------|---------|
| `image_binary` | BYTEA | Actual image binary data |
| `last_sync_at` | TIMESTAMP | Last successful sync |
| `sync_status` | VARCHAR(20) | `pending`, `syncing`, `synced`, `failed` |
| `sync_error` | TEXT | Error message if sync failed |

---

## API Implementation

### 1. Sync Product Photos API (Edge Server Pulls)

**Endpoint:** `GET /api/sync/product-photos/`

**Query Parameters:**
- `since` (optional): ISO 8601 timestamp for incremental sync
- `store_id` (required): UUID of requesting store
- `limit` (optional): Max records per request (default: 100)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "status": "success",
  "data": {
    "photos": [
      {
        "id": "uuid",
        "product_id": "uuid",
        "object_key": "products/uuid/primary.jpg",
        "filename": "product.jpg",
        "size": 123456,
        "content_type": "image/jpeg",
        "checksum": "md5hash",
        "version": 1,
        "is_primary": true,
        "sort_order": 0,
        "updated_at": "2026-02-03T10:00:00Z",
        "image_url": "http://ho-server:9000/product-images/..."
      }
    ],
    "total": 150,
    "has_more": true,
    "next_offset": 100
  }
}
```

**Implementation Location:** `sync_api/views.py`

---

### 2. Download Image Binary API (Edge Server Downloads)

**Endpoint:** `GET /api/sync/product-photos/<photo_id>/download/`

**Query Parameters:**
- `store_id` (required): UUID of requesting store

**Response:** Binary image data with headers
```
Content-Type: image/jpeg
Content-Length: 123456
Content-Disposition: attachment; filename="product.jpg"
X-Checksum: md5hash
X-Version: 1
```

**Implementation Location:** `sync_api/views.py`

---

### 3. Sync Status Report API (Edge Reports to HO)

**Endpoint:** `POST /api/sync/product-photos/status/`

**Request Body:**
```json
{
  "store_id": "uuid",
  "sync_batch": [
    {
      "photo_id": "uuid",
      "status": "synced",
      "synced_at": "2026-02-03T10:05:00Z",
      "error": null
    },
    {
      "photo_id": "uuid",
      "status": "failed",
      "synced_at": null,
      "error": "Network timeout"
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Sync status updated for 2 photos"
}
```

---

## Sync Strategies

### Strategy 1: Full Sync (Initial Setup)
1. Edge server requests all photos: `GET /api/sync/product-photos/`
2. For each photo, download binary: `GET /api/sync/product-photos/{id}/download/`
3. Store in PostgreSQL `image_binary` field
4. Update `sync_status = 'synced'` and `last_sync_at`

### Strategy 2: Incremental Sync (Daily/Hourly)
1. Edge server tracks last sync time
2. Request only updated photos: `GET /api/sync/product-photos/?since=2026-02-03T00:00:00Z`
3. Download changed images
4. Update local records

### Strategy 3: Change Detection (Checksum-based)
1. Compare local checksum with HO checksum
2. If different, download new version
3. Replace `image_binary` with new data
4. Increment `version` field

---

## Implementation Code

### HO Server: Sync API Views

**File:** `sync_api/views.py`

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import FileResponse, HttpResponse
from products.models import ProductPhoto
from core.storage import minio_storage
import io

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_product_photos(request):
    """
    Get list of product photos for synchronization
    Query params: since, store_id, limit, offset
    """
    since = request.GET.get('since')
    store_id = request.GET.get('store_id')
    limit = int(request.GET.get('limit', 100))
    offset = int(request.GET.get('offset', 0))
    
    if not store_id:
        return Response({
            'status': 'error',
            'message': 'store_id is required'
        }, status=400)
    
    # Query photos, optionally filtered by updated_at
    queryset = ProductPhoto.objects.select_related('product').all()
    
    if since:
        from dateutil import parser
        since_dt = parser.isoparse(since)
        queryset = queryset.filter(updated_at__gte=since_dt)
    
    total = queryset.count()
    photos = queryset[offset:offset + limit]
    
    data = []
    for photo in photos:
        data.append({
            'id': str(photo.id),
            'product_id': str(photo.product_id),
            'object_key': photo.object_key,
            'filename': photo.filename,
            'size': photo.size,
            'content_type': photo.content_type,
            'checksum': photo.checksum,
            'version': photo.version,
            'is_primary': photo.is_primary,
            'sort_order': photo.sort_order,
            'updated_at': photo.updated_at.isoformat(),
            'image_url': photo.image_url
        })
    
    return Response({
        'status': 'success',
        'data': {
            'photos': data,
            'total': total,
            'has_more': (offset + limit) < total,
            'next_offset': offset + limit if (offset + limit) < total else None
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_product_photo(request, photo_id):
    """
    Download binary image data from MinIO
    """
    store_id = request.GET.get('store_id')
    if not store_id:
        return Response({
            'status': 'error',
            'message': 'store_id is required'
        }, status=400)
    
    try:
        photo = ProductPhoto.objects.get(id=photo_id)
        
        # Download from MinIO
        if photo.object_key:
            image_data = minio_storage.download_image(photo.object_key)
            
            response = HttpResponse(image_data, content_type=photo.content_type)
            response['Content-Disposition'] = f'attachment; filename="{photo.filename}"'
            response['Content-Length'] = photo.size
            response['X-Checksum'] = photo.checksum
            response['X-Version'] = photo.version
            
            return response
        else:
            return Response({
                'status': 'error',
                'message': 'No image data available'
            }, status=404)
            
    except ProductPhoto.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Photo not found'
        }, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_sync_status(request):
    """
    Edge server reports sync status back to HO
    """
    store_id = request.data.get('store_id')
    sync_batch = request.data.get('sync_batch', [])
    
    if not store_id:
        return Response({
            'status': 'error',
            'message': 'store_id is required'
        }, status=400)
    
    # Log sync status (optional: store in sync history table)
    for item in sync_batch:
        photo_id = item.get('photo_id')
        status = item.get('status')
        error = item.get('error')
        
        # You can log this to a SyncHistory model
        print(f"Photo {photo_id} - Status: {status}, Error: {error}")
    
    return Response({
        'status': 'success',
        'message': f'Sync status updated for {len(sync_batch)} photos'
    })
```

---

### HO Server: MinIO Download Helper

**File:** `core/storage.py`

Add method to `MinIOStorage` class:

```python
def download_image(self, object_key):
    """
    Download image binary data from MinIO
    Returns: bytes
    """
    try:
        response = self.client.get_object(
            bucket_name=self.bucket_products,
            object_name=object_key
        )
        
        # Read all data
        image_data = response.read()
        response.close()
        response.release_conn()
        
        return image_data
        
    except S3Error as e:
        print(f"✗ MinIO download error: {e}")
        raise Exception(f"Failed to download image: {str(e)}")
```

---

### HO Server: URL Configuration

**File:** `sync_api/urls.py`

```python
from django.urls import path
from . import views

app_name = 'sync_api'

urlpatterns = [
    # Existing sync endpoints...
    
    # Product Photo Sync
    path('product-photos/', views.sync_product_photos, name='sync_product_photos'),
    path('product-photos/<uuid:photo_id>/download/', views.download_product_photo, name='download_product_photo'),
    path('product-photos/status/', views.report_sync_status, name='report_sync_status'),
]
```

---

## Edge Server Implementation

### Edge Server: Sync Service

**File:** `edge_sync_service.py` (new file on edge server)

```python
import requests
import psycopg2
from datetime import datetime, timezone
import hashlib
import time

class ProductPhotoSyncService:
    def __init__(self, ho_base_url, store_id, auth_token, db_config):
        self.ho_base_url = ho_base_url
        self.store_id = store_id
        self.auth_token = auth_token
        self.db_config = db_config
        self.headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
    
    def get_last_sync_time(self):
        """Get last successful sync timestamp from database"""
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        cur.execute("""
            SELECT MAX(last_sync_at) FROM product_photo 
            WHERE sync_status = 'synced'
        """)
        result = cur.fetchone()[0]
        cur.close()
        conn.close()
        return result
    
    def fetch_photo_list(self, since=None, limit=100, offset=0):
        """Fetch list of photos from HO server"""
        params = {
            'store_id': self.store_id,
            'limit': limit,
            'offset': offset
        }
        if since:
            params['since'] = since.isoformat()
        
        url = f"{self.ho_base_url}/api/sync/product-photos/"
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def download_photo_binary(self, photo_id):
        """Download binary image data"""
        url = f"{self.ho_base_url}/api/sync/product-photos/{photo_id}/download/"
        params = {'store_id': self.store_id}
        
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        
        return {
            'data': response.content,
            'checksum': response.headers.get('X-Checksum'),
            'version': response.headers.get('X-Version')
        }
    
    def verify_checksum(self, data, expected_checksum):
        """Verify downloaded data integrity"""
        actual_checksum = hashlib.md5(data).hexdigest()
        return actual_checksum == expected_checksum
    
    def save_photo_to_db(self, photo_meta, image_data):
        """Save or update photo in edge database"""
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        
        try:
            # Check if photo exists
            cur.execute("SELECT id, checksum FROM product_photo WHERE id = %s", 
                       (photo_meta['id'],))
            existing = cur.fetchone()
            
            if existing:
                # Update existing record
                cur.execute("""
                    UPDATE product_photo 
                    SET object_key = %s,
                        filename = %s,
                        size = %s,
                        content_type = %s,
                        checksum = %s,
                        version = %s,
                        is_primary = %s,
                        sort_order = %s,
                        image_binary = %s,
                        last_sync_at = %s,
                        sync_status = %s,
                        sync_error = NULL
                    WHERE id = %s
                """, (
                    photo_meta['object_key'],
                    photo_meta['filename'],
                    photo_meta['size'],
                    photo_meta['content_type'],
                    photo_meta['checksum'],
                    photo_meta['version'],
                    photo_meta['is_primary'],
                    photo_meta['sort_order'],
                    psycopg2.Binary(image_data),
                    datetime.now(timezone.utc),
                    'synced',
                    photo_meta['id']
                ))
            else:
                # Insert new record
                cur.execute("""
                    INSERT INTO product_photo 
                    (id, product_id, object_key, filename, size, content_type, 
                     checksum, version, is_primary, sort_order, image_binary, 
                     last_sync_at, sync_status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    photo_meta['id'],
                    photo_meta['product_id'],
                    photo_meta['object_key'],
                    photo_meta['filename'],
                    photo_meta['size'],
                    photo_meta['content_type'],
                    photo_meta['checksum'],
                    photo_meta['version'],
                    photo_meta['is_primary'],
                    photo_meta['sort_order'],
                    psycopg2.Binary(image_data),
                    datetime.now(timezone.utc),
                    'synced',
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc)
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"Error saving photo {photo_meta['id']}: {e}")
            
            # Mark as failed
            cur.execute("""
                UPDATE product_photo 
                SET sync_status = %s, sync_error = %s 
                WHERE id = %s
            """, ('failed', str(e), photo_meta['id']))
            conn.commit()
            
            return False
        finally:
            cur.close()
            conn.close()
    
    def sync_incremental(self):
        """Perform incremental sync"""
        print("Starting incremental sync...")
        
        since = self.get_last_sync_time()
        offset = 0
        limit = 100
        total_synced = 0
        total_failed = 0
        
        sync_report = []
        
        while True:
            # Fetch batch of photos
            result = self.fetch_photo_list(since=since, limit=limit, offset=offset)
            photos = result['data']['photos']
            
            if not photos:
                break
            
            print(f"Processing batch: {len(photos)} photos (offset: {offset})")
            
            for photo_meta in photos:
                photo_id = photo_meta['id']
                
                try:
                    # Download binary data
                    download_result = self.download_photo_binary(photo_id)
                    
                    # Verify checksum
                    if not self.verify_checksum(download_result['data'], 
                                                photo_meta['checksum']):
                        raise Exception("Checksum mismatch")
                    
                    # Save to database
                    if self.save_photo_to_db(photo_meta, download_result['data']):
                        total_synced += 1
                        sync_report.append({
                            'photo_id': photo_id,
                            'status': 'synced',
                            'synced_at': datetime.now(timezone.utc).isoformat(),
                            'error': None
                        })
                    else:
                        total_failed += 1
                        sync_report.append({
                            'photo_id': photo_id,
                            'status': 'failed',
                            'synced_at': None,
                            'error': 'Database save failed'
                        })
                    
                except Exception as e:
                    print(f"Failed to sync photo {photo_id}: {e}")
                    total_failed += 1
                    sync_report.append({
                        'photo_id': photo_id,
                        'status': 'failed',
                        'synced_at': None,
                        'error': str(e)
                    })
                
                # Rate limiting
                time.sleep(0.1)
            
            # Check if there are more photos
            if not result['data']['has_more']:
                break
            
            offset = result['data']['next_offset']
        
        # Report sync status back to HO
        self.report_sync_status(sync_report)
        
        print(f"Sync completed. Synced: {total_synced}, Failed: {total_failed}")
        return {
            'synced': total_synced,
            'failed': total_failed
        }
    
    def report_sync_status(self, sync_batch):
        """Report sync status to HO server"""
        if not sync_batch:
            return
        
        url = f"{self.ho_base_url}/api/sync/product-photos/status/"
        payload = {
            'store_id': self.store_id,
            'sync_batch': sync_batch
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            print("Sync status reported successfully")
        except Exception as e:
            print(f"Failed to report sync status: {e}")


# Usage Example
if __name__ == '__main__':
    service = ProductPhotoSyncService(
        ho_base_url='http://ho-server:8000',
        store_id='your-store-uuid',
        auth_token='your-auth-token',
        db_config={
            'host': 'localhost',
            'database': 'edge_db',
            'user': 'postgres',
            'password': 'password'
        }
    )
    
    service.sync_incremental()
```

---

### Edge Server: Serving Images from Database

**File:** `edge_api_views.py`

```python
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from products.models import ProductPhoto

def serve_product_photo(request, photo_id):
    """
    Serve image from PostgreSQL binary storage
    """
    photo = get_object_or_404(ProductPhoto, id=photo_id)
    
    if photo.image_binary:
        response = HttpResponse(bytes(photo.image_binary), 
                              content_type=photo.content_type)
        response['Content-Disposition'] = f'inline; filename="{photo.filename}"'
        response['Content-Length'] = len(photo.image_binary)
        response['Cache-Control'] = 'public, max-age=86400'  # Cache for 1 day
        
        return response
    else:
        return HttpResponse('Image not found', status=404)
```

---

## Deployment Steps

### Step 1: HO Server Setup
1. Add download method to `core/storage.py`
2. Create sync API views in `sync_api/views.py`
3. Add URL routes in `sync_api/urls.py`
4. Test endpoints with Postman/curl

### Step 2: Edge Server Database Migration
```bash
# On edge server
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Edge Server Sync Service
1. Create `edge_sync_service.py`
2. Configure cron job for periodic sync
3. Test initial sync with small dataset

### Step 4: Monitoring Setup
1. Add logging for sync operations
2. Create dashboard for sync status
3. Set up alerts for sync failures

---

## Cron Job Configuration

**File:** `/etc/cron.d/product-photo-sync`

```bash
# Sync every hour
0 * * * * cd /path/to/edge-server && python edge_sync_service.py >> /var/log/photo-sync.log 2>&1

# Full sync daily at 2 AM
0 2 * * * cd /path/to/edge-server && python edge_sync_service.py --full >> /var/log/photo-sync-full.log 2>&1
```

---

## Performance Considerations

1. **Batch Size**: Limit to 100 photos per request to avoid memory issues
2. **Rate Limiting**: Add 100ms delay between downloads
3. **Compression**: Consider compressing binary data during transfer
4. **Retry Logic**: Implement exponential backoff for failed downloads
5. **Parallel Downloads**: Use threading for faster sync (max 5 concurrent)
6. **Database Indexing**: Ensure indexes on `sync_status` and `last_sync_at`

---

## Monitoring & Alerts

### Metrics to Track
- Sync duration
- Success/failure rate
- Data transfer volume
- Database size growth
- Sync lag (time difference between HO and Edge)

### Alert Triggers
- Sync failure rate > 10%
- Sync not completed in 1 hour
- Database storage > 80% capacity
- Checksum mismatch errors

---

## Security Considerations

1. **Authentication**: Use JWT tokens with expiry
2. **Authorization**: Verify store_id permissions
3. **Data Integrity**: Always verify checksums
4. **Network**: Use HTTPS/SSL for transfers
5. **Access Control**: Limit API access to authorized edge servers only

---

## Testing Checklist

- [ ] Test full sync with 1000 products
- [ ] Test incremental sync with updated photos
- [ ] Test checksum verification
- [ ] Test retry on network failure
- [ ] Test database storage limits
- [ ] Test concurrent sync requests
- [ ] Test image serving from edge database
- [ ] Test sync status reporting
- [ ] Load test with 10,000 products

---

## Rollback Plan

If sync causes issues:
1. Stop cron job
2. Keep existing MinIO URLs as fallback
3. Edge server can still fetch from HO MinIO directly
4. Investigate and fix sync service
5. Clear failed records: `UPDATE product_photo SET sync_status = 'pending'`
6. Resume sync

---

## Future Enhancements

1. **Compression**: Compress images before transfer (WebP format)
2. **CDN Integration**: Use CDN for faster delivery
3. **Selective Sync**: Sync only active products
4. **Webhook Notifications**: Real-time sync on image update
5. **Multi-region Sync**: Sync to multiple edge servers simultaneously

---

## Contact & Support

For issues or questions:
- Technical Lead: [Your Name]
- Documentation: See `EDGE_SERVER_MASTER_INDEX.md`
- API Reference: See `API_DOCUMENTATION.md`
