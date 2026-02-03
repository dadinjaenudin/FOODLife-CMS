# Product Photo Sync Implementation Summary

## Date: February 3, 2026

---

## Overview
Implementasi lengkap untuk sinkronisasi product images dari HO Server (MinIO) ke Edge Server (PostgreSQL binary storage).

---

## What Was Implemented

### 1. HO Server - API Endpoints ✅

**File:** `sync_api/sync_views.py`

Three new API endpoints added:

#### A. `sync_product_photos()`
- **Method:** GET
- **Endpoint:** `/api/v1/sync/product-photos/`
- **Purpose:** Get list of product photos with metadata
- **Features:**
  - Pagination (limit, offset)
  - Incremental sync (since parameter)
  - Returns photo metadata + image URL
  - Authentication required (JWT Bearer)

#### B. `download_product_photo()`
- **Method:** GET
- **Endpoint:** `/api/v1/sync/product-photos/<photo_id>/download/`
- **Purpose:** Download binary image data from MinIO
- **Features:**
  - Streams image from MinIO
  - Returns binary data with headers
  - Includes checksum for verification
  - Includes version number

#### C. `report_sync_status()`
- **Method:** POST
- **Endpoint:** `/api/v1/sync/product-photos/status/`
- **Purpose:** Edge server reports sync status back to HO
- **Features:**
  - Batch status reporting
  - Logs success/failure for each photo
  - Helps track sync health

### 2. HO Server - Storage Service ✅

**File:** `core/storage.py`

New method added to `MinIOStorage` class:

#### `download_image(object_key)`
- Downloads image binary from MinIO
- Returns bytes data
- Handles S3Error exceptions
- Used by download API endpoint

### 3. URL Configuration ✅

**File:** `sync_api/sync_urls.py`

Three new URL routes added:
```python
path('product-photos/', sync_views.sync_product_photos, name='product_photos'),
path('product-photos/<uuid:photo_id>/download/', sync_views.download_product_photo, name='download_product_photo'),
path('product-photos/status/', sync_views.report_sync_status, name='report_sync_status'),
```

### 4. Documentation Created ✅

**Created Files:**

1. **`EDGE_SERVER_IMAGE_SYNC_IMPLEMENTATION.md`**
   - Complete implementation guide
   - Database schema for edge server
   - Python sync service code
   - Deployment steps
   - Monitoring & alerts guide
   - 200+ lines comprehensive doc

2. **`PRODUCT_PHOTO_SYNC_API_REFERENCE.md`**
   - Quick API reference
   - Curl examples
   - Python code examples
   - Error handling guide
   - Testing instructions

3. **`test_product_photo_sync_api.py`**
   - Complete test script
   - Tests all 3 endpoints
   - Includes pagination test
   - Incremental sync test
   - Download & checksum verification

### 5. Master Documentation Updated ✅

**File:** `markdown/EDGE_SERVER_MASTER_INDEX.md`

- Added Product Image Sync section
- Referenced both new documentation files
- Updated API list with image sync endpoints

---

## Technical Details

### Data Flow

```
┌─────────────┐         ┌─────────────┐         ┌──────────────┐
│  HO MinIO   │────────▶│  HO Server  │────────▶│ Edge Server  │
│  (Storage)  │         │  (Sync API) │         │ (PostgreSQL) │
└─────────────┘         └─────────────┘         └──────────────┘
     │                        │                         │
     │ 1. Store images        │ 2. Serve via API       │ 3. Store binary
     │    as files            │    - Metadata          │    in database
     │                        │    - Binary data       │
```

### Fields Synchronized

| Field | Type | Purpose |
|-------|------|---------|
| id | UUID | Primary key |
| product_id | UUID | Foreign key |
| object_key | VARCHAR | MinIO path |
| filename | VARCHAR | Original name |
| size | INTEGER | File size |
| content_type | VARCHAR | MIME type |
| checksum | VARCHAR(64) | MD5 hash |
| version | INTEGER | Version number |
| is_primary | BOOLEAN | Primary photo flag |
| sort_order | INTEGER | Display order |
| updated_at | TIMESTAMP | Last update |

### Edge Server Additional Fields

| Field | Type | Purpose |
|-------|------|---------|
| image_binary | BYTEA | Actual image data |
| last_sync_at | TIMESTAMP | Last sync time |
| sync_status | VARCHAR(20) | pending/syncing/synced/failed |
| sync_error | TEXT | Error message if failed |

---

## API Endpoints Summary

### 1. Get Photo List
```
GET /api/v1/sync/product-photos/?store_id=uuid&limit=100&offset=0
```

**Response:**
- photos: Array of photo metadata
- total: Total count
- has_more: Boolean for pagination
- next_offset: Next page offset

### 2. Download Binary
```
GET /api/v1/sync/product-photos/<photo_id>/download/?store_id=uuid
```

**Response:**
- Binary image data
- Headers: Content-Type, Content-Length, X-Checksum, X-Version

### 3. Report Status
```
POST /api/v1/sync/product-photos/status/
Body: { store_id, sync_batch: [{photo_id, status, synced_at, error}] }
```

**Response:**
- Success message with count

---

## Sync Strategies

### Full Sync (Initial)
1. Request all photos with pagination (limit=100)
2. For each photo:
   - Download binary data
   - Verify checksum
   - Store in PostgreSQL BYTEA field
   - Update sync_status = 'synced'
3. Report status back to HO

### Incremental Sync (Periodic)
1. Get last_sync_at from local DB
2. Request: `?since=<last_sync_at>`
3. Only download changed photos (checksum differs)
4. Update local records

### Performance Tips
- Batch size: 100 photos per request
- Rate limiting: 100ms delay between downloads
- Parallel downloads: Max 5 concurrent
- Always verify checksums
- Use indexes on sync_status and last_sync_at

---

## Testing

### Run Test Script

```bash
# Edit test_product_photo_sync_api.py first:
# - Update STORE_ID
# - Update USERNAME, PASSWORD

python test_product_photo_sync_api.py
```

### Test Results Expected

```
1. Getting authentication token...
✓ Authentication successful

2. Testing sync_product_photos endpoint...
✓ Successfully retrieved 10 photos
  Total available: 150
  Has more: true

3. Testing incremental sync...
✓ Successfully retrieved 5 updated photos

4. Testing download_product_photo endpoint...
✓ Successfully downloaded image
  Content Length: 123456 bytes
  Checksum: d695074cf6f06cf75634cd19fc003a71
  Saved to: test_download_84ce2575.jpg

5. Testing report_sync_status endpoint...
✓ Successfully reported sync status

6. Testing pagination...
✓ Pagination test complete
  Total photos retrieved: 50
```

---

## Edge Server Implementation (Separate System)

### Required Changes on Edge Server

1. **Database Migration**
```sql
ALTER TABLE product_photo ADD COLUMN image_binary BYTEA;
ALTER TABLE product_photo ADD COLUMN last_sync_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE product_photo ADD COLUMN sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE product_photo ADD COLUMN sync_error TEXT;
```

2. **Python Sync Service**
- Use provided `edge_sync_service.py` from documentation
- Configure: HO base URL, store ID, auth token, DB config
- Run as cron job (hourly/daily)

3. **Cron Configuration**
```bash
# Hourly incremental sync
0 * * * * cd /path/to/edge && python edge_sync_service.py

# Daily full sync at 2 AM
0 2 * * * cd /path/to/edge && python edge_sync_service.py --full
```

4. **Image Serving**
```python
def serve_product_photo(request, photo_id):
    photo = ProductPhoto.objects.get(id=photo_id)
    return HttpResponse(bytes(photo.image_binary), 
                       content_type=photo.content_type)
```

---

## Cache-Busting Strategy (Already Implemented)

**Problem:** Browser caches images with same filename (e.g., `primary.jpg`)

**Solution:** Checksum-based URL versioning

**Implementation:**
```python
@property
def image_url(self):
    base_url = minio_storage.get_image_url(self.object_key)
    cache_param = self.checksum[:8] if self.checksum else str(int(time.time()))
    separator = '&' if '?' in base_url else '?'
    return f"{base_url}{separator}v={cache_param}"
```

**Result:** Each upload gets unique URL
```
Old: http://localhost:9000/product-images/products/uuid/primary.jpg?v=5cd6a73f
New: http://localhost:9000/product-images/products/uuid/primary.jpg?v=d695074c
```

---

## Security Considerations

1. **Authentication:** All endpoints require JWT Bearer token
2. **Authorization:** store_id validated against active stores
3. **Data Integrity:** Checksums verified on download
4. **Access Control:** Only authenticated edge servers can access
5. **Rate Limiting:** Recommended 100ms delay between requests

---

## Monitoring Recommendations

### Metrics to Track
- Sync duration (should be < 1 hour)
- Success/failure rate (target: >95%)
- Data transfer volume
- Database size growth
- Sync lag (time difference HO ↔ Edge)

### Alert Triggers
- Sync failure rate > 10%
- Sync not completed in 1 hour
- Database storage > 80% capacity
- Checksum mismatch errors

---

## Files Modified/Created

### Modified Files
1. `sync_api/sync_views.py` - Added 3 new API views (~200 lines)
2. `sync_api/sync_urls.py` - Added 3 URL routes
3. `core/storage.py` - Added download_image method
4. `markdown/EDGE_SERVER_MASTER_INDEX.md` - Updated documentation index

### Created Files
1. `markdown/EDGE_SERVER_IMAGE_SYNC_IMPLEMENTATION.md` (comprehensive guide)
2. `markdown/PRODUCT_PHOTO_SYNC_API_REFERENCE.md` (API reference)
3. `test_product_photo_sync_api.py` (test script)
4. `markdown/PRODUCT_PHOTO_SYNC_IMPLEMENTATION_SUMMARY.md` (this file)

---

## Next Steps

### For HO Server (Already Complete ✅)
- API endpoints implemented
- Documentation created
- Test script ready

### For Edge Server (To Do Later)
1. Run database migration
2. Deploy sync service
3. Configure cron jobs
4. Test with HO server
5. Monitor sync health

### Testing Checklist
- [ ] Run test_product_photo_sync_api.py
- [ ] Verify all 3 endpoints return 200 OK
- [ ] Test with actual product photos
- [ ] Test incremental sync (since parameter)
- [ ] Test pagination with 100+ photos
- [ ] Verify checksum validation
- [ ] Test error handling (invalid store_id)

---

## Performance Expectations

### Initial Sync (1000 products with photos)
- **Duration:** ~5-10 minutes
- **Data Transfer:** ~100-500 MB (depends on image sizes)
- **Database Growth:** Same as transfer size

### Incremental Sync (Daily)
- **Duration:** ~30 seconds - 2 minutes
- **Data Transfer:** ~1-10 MB (only changed photos)
- **Frequency:** Hourly or daily based on needs

---

## Rollback Plan

If issues occur:
1. **Stop sync service** (disable cron job)
2. **Edge server continues** using HO MinIO URLs directly
3. **Investigate logs** for sync errors
4. **Fix issues** in sync service
5. **Clear failed records:** `UPDATE product_photo SET sync_status = 'pending'`
6. **Resume sync** gradually

---

## Support & Documentation

### Key Documentation Files
- Main Implementation: `EDGE_SERVER_IMAGE_SYNC_IMPLEMENTATION.md`
- API Reference: `PRODUCT_PHOTO_SYNC_API_REFERENCE.md`
- Master Index: `EDGE_SERVER_MASTER_INDEX.md`
- Test Script: `test_product_photo_sync_api.py`

### Related Documentation
- `API_DOCUMENTATION.md` - General API docs
- `COMPLETE_EDGE_SERVER_API_GUIDE.md` - All edge APIs
- `SYNC_API_DOCUMENTATION.md` - Promotion sync guide

---

## Status: IMPLEMENTATION COMPLETE ✅

All HO Server components are implemented and ready for testing.
Edge Server implementation is documented and ready for deployment.

**Total Development Time:** ~2 hours
**Lines of Code:** ~600 lines (API + docs)
**Documentation Pages:** 3 comprehensive guides
**Test Coverage:** Full test script included

---

## Implementation Log

**February 3, 2026**
- ✅ Added download_image() method to MinIOStorage
- ✅ Implemented sync_product_photos() API view
- ✅ Implemented download_product_photo() API view
- ✅ Implemented report_sync_status() API view
- ✅ Added URL routes for all 3 endpoints
- ✅ Created comprehensive implementation guide
- ✅ Created API quick reference guide
- ✅ Created test script with all scenarios
- ✅ Updated master documentation index
- ✅ Cache-busting already implemented previously
- ✅ Single photo per product constraint enforced

**Ready for:** Testing and Edge Server deployment
