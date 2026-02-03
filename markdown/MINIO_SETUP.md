# MinIO Setup Guide - Public Bucket Policy

## Problem
MinIO presigned URLs menggunakan signature yang dikalkulasi berdasarkan hostname. Ketika:
- Django (dalam container) mengakses MinIO via `minio:9000` 
- Browser mengakses MinIO via `localhost:9000`

Signature menjadi invalid karena hostname berbeda → **SignatureDoesNotMatch error**

## Solution
Gunakan **public bucket policy** untuk anonymous read access. Dengan ini:
- ✅ Tidak perlu presigned URL signature
- ✅ Direct URL: `http://localhost:9000/product-images/object-key`
- ✅ Browser bisa langsung load images tanpa authentication

## Setup Steps

### 1. Set Bucket Policy (One Time Setup)
Jalankan script untuk membuat bucket publicly readable:

```bash
docker compose exec web python set_minio_public.py
```

**Script: `set_minio_public.py`**
```python
#!/usr/bin/env python
import json
from minio import Minio

client = Minio(
    "minio:9000",
    access_key="foodlife_admin",
    secret_key="foodlife_secret_2026",
    secure=False
)

bucket_name = "product-images"

# Anonymous read-only policy (download access only)
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
        }
    ]
}

client.set_bucket_policy(bucket_name, json.dumps(policy))
print(f"✓ Bucket '{bucket_name}' is now publicly readable")
```

### 2. Update Storage Service
**File: `core/storage.py`**

```python
def get_image_url(self, object_key, expires=3600):
    """Get direct URL for image access (no presigning - requires public bucket)"""
    return f"http://{self.external_endpoint}/{self.bucket_products}/{object_key}"
```

Tidak perlu presigned URL signature lagi!

### 3. Restart Container
```bash
docker compose restart web
```

## What Changed

| Before (Presigned URLs) | After (Public Bucket) |
|------------------------|----------------------|
| `http://localhost:9000/product-images/key?signature=...` | `http://localhost:9000/product-images/key` |
| ❌ Signature mismatch error | ✅ Direct access |
| ⏱️ URL expires (default 1 hour) | ✅ Permanent URL |
| 🔒 Requires authentication | 🌐 Anonymous read access |

## Security Note
- ✅ **Upload**: Masih butuh authentication (foodlife_admin credentials)
- ✅ **Read/Download**: Public anonymous access
- ✅ **Write/Delete**: Masih terproteksi authentication

Bucket hanya readable, tidak bisa di-write tanpa credentials.

## Verification

### Test via Browser
```
http://localhost:9000/product-images/products/uuid/filename.jpg
```

### Test via Python Shell
```python
from core.storage import minio_storage
url = minio_storage.get_image_url("products/uuid/test.jpg")
print(url)  # Output: http://localhost:9000/product-images/products/uuid/test.jpg
```

### Check Policy via MinIO Console
1. Buka http://localhost:9001
2. Login: `foodlife_admin` / `foodlife_secret_2026`
3. Buckets → `product-images` → Access Policy
4. Should show: **Public (Custom Policy)**

## Troubleshooting

### Images tidak load?
1. Check bucket policy:
   ```bash
   docker compose exec web python set_minio_public.py
   ```

2. Check MinIO container running:
   ```bash
   docker compose ps minio
   ```

3. Check file exists in bucket:
   ```bash
   docker compose exec web python manage.py shell
   >>> from core.storage import minio_storage
   >>> list(minio_storage.client.list_objects("product-images", prefix="products/"))
   ```

### CORS Error?
Tambahkan CORS configuration di MinIO (jika perlu):
```bash
docker compose exec minio mc alias set local http://localhost:9000 foodlife_admin foodlife_secret_2026
docker compose exec minio mc anonymous set download local/product-images
```

## Production Considerations

Untuk production environment:
1. **Option A**: Keep public bucket, gunakan CDN (CloudFlare, CloudFront) untuk caching
2. **Option B**: Gunakan reverse proxy (Nginx) untuk handle hostname translation
3. **Option C**: Set MinIO dengan domain name (bukan localhost)

Untuk development: **Public bucket sudah cukup** ✅
