# Product Photo Sync API - Quick Reference

## Overview
API endpoints untuk sinkronisasi product images dari HO Server ke Edge Server.

---

## Authentication
Semua endpoint memerlukan JWT Bearer token:
```
Authorization: Bearer <your-token>
```

---

## Endpoints

### 1. Get Product Photos List

**Endpoint:** `GET /api/v1/sync/product-photos/`

**Query Parameters:**
- `store_id` (required): Store UUID
- `since` (optional): ISO 8601 timestamp untuk incremental sync
- `limit` (optional): Max records per request (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/sync/product-photos/?store_id=uuid&limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "photos": [
      {
        "id": "84ce2575-284b-421d-b2d4-70842d3d993b",
        "product_id": "63ea9d40-...",
        "product_sku": "05018970",
        "product_name": "ASAHI SALMON BOWL",
        "object_key": "products/63ea9d40.../primary.jpg",
        "filename": "Menu_Image_20250922025828.jpg",
        "size": 123456,
        "content_type": "image/jpeg",
        "checksum": "d695074cf6f06cf75634cd19fc003a71",
        "version": 1,
        "is_primary": true,
        "sort_order": 0,
        "updated_at": "2026-02-03T10:00:00Z",
        "image_url": "http://localhost:9000/product-images/..."
      }
    ],
    "total": 150,
    "has_more": true,
    "next_offset": 10
  }
}
```

---

### 2. Download Image Binary

**Endpoint:** `GET /api/v1/sync/product-photos/<photo_id>/download/`

**Query Parameters:**
- `store_id` (required): Store UUID

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/sync/product-photos/84ce2575-284b-421d-b2d4-70842d3d993b/download/?store_id=uuid" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o product_image.jpg
```

**Response Headers:**
```
Content-Type: image/jpeg
Content-Length: 123456
Content-Disposition: attachment; filename="product.jpg"
X-Checksum: d695074cf6f06cf75634cd19fc003a71
X-Version: 1
```

**Response Body:** Binary image data

---

### 3. Report Sync Status

**Endpoint:** `POST /api/v1/sync/product-photos/status/`

**Request Body:**
```json
{
  "store_id": "uuid",
  "sync_batch": [
    {
      "photo_id": "84ce2575-284b-421d-b2d4-70842d3d993b",
      "status": "synced",
      "synced_at": "2026-02-03T10:05:00Z",
      "error": null
    },
    {
      "photo_id": "another-uuid",
      "status": "failed",
      "synced_at": null,
      "error": "Network timeout"
    }
  ]
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/sync/product-photos/status/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": "uuid",
    "sync_batch": [
      {
        "photo_id": "uuid",
        "status": "synced",
        "synced_at": "2026-02-03T10:05:00Z",
        "error": null
      }
    ]
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Sync status updated for 2 photos"
}
```

---

## Python Example - Full Sync Flow

```python
import requests
import hashlib

BASE_URL = "http://localhost:8000"
STORE_ID = "your-store-uuid"
TOKEN = "your-jwt-token"

headers = {
    'Authorization': f'Bearer {TOKEN}'
}

# 1. Get list of photos
response = requests.get(
    f"{BASE_URL}/api/v1/sync/product-photos/",
    params={'store_id': STORE_ID, 'limit': 100, 'offset': 0},
    headers=headers
)

photos = response.json()['data']['photos']

# 2. Download each photo
for photo in photos:
    photo_id = photo['id']
    expected_checksum = photo['checksum']
    
    # Download binary
    response = requests.get(
        f"{BASE_URL}/api/v1/sync/product-photos/{photo_id}/download/",
        params={'store_id': STORE_ID},
        headers=headers
    )
    
    image_data = response.content
    
    # Verify checksum
    actual_checksum = hashlib.md5(image_data).hexdigest()
    if actual_checksum == expected_checksum:
        print(f"✓ {photo['filename']} - Checksum OK")
        # Save to database...
    else:
        print(f"✗ {photo['filename']} - Checksum mismatch!")
```

---

## Python Example - Incremental Sync

```python
from datetime import datetime

# Get last sync time from local database
last_sync = "2026-02-03T00:00:00Z"

response = requests.get(
    f"{BASE_URL}/api/v1/sync/product-photos/",
    params={
        'store_id': STORE_ID,
        'since': last_sync,
        'limit': 100
    },
    headers=headers
)

data = response.json()
updated_photos = data['data']['photos']

print(f"Found {len(updated_photos)} updated photos since {last_sync}")

# Download only changed photos
for photo in updated_photos:
    # Check if checksum differs from local version
    # If different, download new version
    pass
```

---

## Error Responses

### 400 Bad Request
```json
{
  "status": "error",
  "message": "store_id is required"
}
```

### 404 Not Found
```json
{
  "status": "error",
  "message": "Store not found"
}
```

### 500 Internal Server Error
```json
{
  "status": "error",
  "message": "Internal server error",
  "detail": "Failed to download image: S3Error..."
}
```

---

## Sync Strategy Recommendations

### Initial Sync (Full)
1. Request all photos with `limit=100`
2. Use pagination (`offset`) to fetch all pages
3. Download binary data for each photo
4. Verify checksums before storing
5. Report sync status back to HO

### Incremental Sync (Daily/Hourly)
1. Store `last_sync_at` timestamp locally
2. Request only updated photos: `?since=<last_sync_at>`
3. Compare checksums with local version
4. Download only if checksum differs
5. Update `last_sync_at` after successful sync

### Performance Tips
- Use batch size of 100 photos per request
- Add 100ms delay between downloads
- Use parallel downloads (max 5 concurrent)
- Compress data during transfer if possible
- Always verify checksums

---

## Testing

Run the test script:
```bash
python test_product_photo_sync_api.py
```

Before running, update these variables:
- `STORE_ID`: Your store UUID
- `USERNAME`: Admin username
- `PASSWORD`: Admin password

---

## Related Documentation

- [Edge Server Image Sync Implementation](EDGE_SERVER_IMAGE_SYNC_IMPLEMENTATION.md)
- [API Documentation](API_DOCUMENTATION.md)
- [Edge Server Master Index](EDGE_SERVER_MASTER_INDEX.md)
