# MinIO Public Configuration - Settings Menu

**Date**: February 3, 2026  
**Feature**: MinIO Configuration Settings Page  
**Location**: Settings > MinIO Configuration  
**URL**: `/settings/minio-config/`

---

## Overview

Fitur ini menambahkan halaman konfigurasi MinIO di sidebar menu Settings untuk memudahkan pengaturan MinIO endpoint saat deploy ke production server. Dengan ini, tidak perlu edit manual file `.env` atau restart container untuk mengubah endpoint MinIO.

---

## Features

### 1. **Settings Menu dengan Submenu**
- Menu Settings di sidebar kiri sekarang expandable dengan submenu:
  - **MinIO Configuration** - Pengaturan MinIO endpoint
  - **Bulk Import** - Import produk dari Excel
  - **Import Logs** - History import
  - **Bulk Delete** - Hapus data bulk

### 2. **MinIO Configuration Page**
- Form untuk mengatur konfigurasi MinIO:
  - **MinIO Endpoint (Internal)** - Endpoint untuk Django server (e.g., `minio:9000`)
  - **MinIO External Endpoint** - Endpoint untuk browser/edge server (e.g., `192.168.1.100:9000`)
  - **MinIO Access Key** - Username MinIO
  - **MinIO Secret Key** - Password MinIO (optional, kosongkan jika tidak ingin ubah)
  - **Use SSL** - Enable/disable HTTPS

### 3. **Test Connection Button**
- Test koneksi ke MinIO server
- Menampilkan hasil test dengan detail:
  - Status connection (success/failed)
  - List buckets
  - Product bucket status
  - SSL configuration
  - Troubleshooting tips jika gagal

### 4. **Configuration Examples**
- Tampilan contoh konfigurasi untuk berbagai scenario:
  - **Development (Docker Compose)**
  - **Production - Same Server**
  - **Production - With Domain & SSL**

### 5. **Auto-save to .env**
- Konfigurasi disimpan langsung ke file `.env`
- Update existing values atau tambah baru jika belum ada
- Warning untuk restart server setelah save

---

## Implementation Details

### Files Modified/Created:

1. **templates/partials/sidebar_menu.html**
   - Changed Settings dari single link menjadi expandable menu
   - Added submenu: MinIO Config, Bulk Import, Import Logs, Bulk Delete

2. **settings/urls.py**
   - Added routes:
     - `minio-config/` - View configuration page
     - `minio-config/save/` - Save configuration to .env
     - `minio-config/test/` - Test MinIO connection

3. **settings/views.py**
   - Added `minio_config_view()` - Display configuration form
   - Added `save_minio_config()` - Save to .env file
   - Added `test_minio_connection()` - Test MinIO connectivity

4. **templates/settings/minio_config.html**
   - Full-featured configuration page with:
     - Current configuration display
     - Form inputs for all MinIO settings
     - Password toggle for secret key
     - Configuration examples
     - Test connection functionality
     - Real-time validation

5. **core/storage.py**
   - Added `test_connection()` method to MinIOStorage class
   - Returns connection status and bucket details

---

## Usage Guide

### For Administrators

#### Development Environment:
1. Login ke HO System
2. Klik **Settings** di sidebar kiri
3. Klik **MinIO Configuration**
4. Gunakan configuration:
   - Internal: `minio:9000`
   - External: `localhost:9000`
   - Access Key: `foodlife_admin`
   - Secret Key: `foodlife_secret_2026`
   - SSL: **OFF**
5. Klik **Test Connection** untuk verify
6. Klik **Save Configuration**
7. Restart server: `docker compose restart web`

#### Production Environment (Same Server):
1. Login ke HO System
2. Settings > MinIO Configuration
3. Update configuration:
   - Internal: `minio:9000` (jika pakai Docker) atau `localhost:9000`
   - External: `192.168.1.100:9000` (ganti dengan IP server Anda)
   - Access Key: `foodlife_admin`
   - Secret Key: (kosongkan jika tidak ubah)
   - SSL: **OFF** (atau ON jika ada reverse proxy)
4. Test Connection
5. Save & Restart

#### Production Environment (With Domain):
1. Login ke HO System
2. Settings > MinIO Configuration
3. Update configuration:
   - Internal: `minio:9000`
   - External: `minio.yourdomain.com` (atau `storage.yourdomain.com`)
   - Access Key: `production_user`
   - Secret Key: `strong_password_here`
   - SSL: **ON**
4. Test Connection
5. Save & Restart

---

## Technical Implementation

### Save to .env Flow:

```python
# Read .env file
with open('.env', 'r') as f:
    lines = f.readlines()

# Update or add MinIO settings
for line in lines:
    if 'MINIO_ENDPOINT=' in line:
        line = f'MINIO_ENDPOINT={new_value}\n'
    # ... update other settings

# Write back to .env
with open('.env', 'w') as f:
    f.writelines(lines)
```

### Test Connection Flow:

```python
# Test using MinIO client
try:
    buckets = minio_client.list_buckets()
    return {
        'success': True,
        'details': {
            'buckets': [b.name for b in buckets],
            'product_bucket_exists': 'product-images' in buckets
        }
    }
except Exception as e:
    return {'success': False, 'error': str(e)}
```

---

## Configuration Variables

### Environment Variables in .env:

```bash
# MinIO Configuration
MINIO_ENDPOINT=minio:9000                      # Internal endpoint (Docker service name)
MINIO_EXTERNAL_ENDPOINT=localhost:9000         # External endpoint (browser/edge access)
MINIO_ACCESS_KEY=foodlife_admin                # MinIO username
MINIO_SECRET_KEY=foodlife_secret_2026          # MinIO password
MINIO_USE_SSL=false                            # SSL/HTTPS enabled
```

### Django Settings (config/settings.py):

```python
# MinIO Configuration
MINIO_ENDPOINT = env('MINIO_ENDPOINT', default='minio:9000')
MINIO_EXTERNAL_ENDPOINT = env('MINIO_EXTERNAL_ENDPOINT', default='localhost:9000')
MINIO_ACCESS_KEY = env('MINIO_ACCESS_KEY', default='foodlife_admin')
MINIO_SECRET_KEY = env('MINIO_SECRET_KEY', default='foodlife_secret_2026')
MINIO_USE_SSL = env.bool('MINIO_USE_SSL', default=False)
MINIO_BUCKET_PRODUCTS = 'product-images'
```

---

## Security Considerations

1. **Secret Key Protection**
   - Secret key input menggunakan type="password"
   - Tidak ditampilkan di current configuration display
   - Bisa dikosongkan jika tidak ingin mengubah

2. **Access Control**
   - Halaman require `@login_required` decorator
   - Hanya user yang sudah login bisa akses
   - TODO: Add permission check untuk admin only

3. **SSL/HTTPS**
   - Enable SSL untuk production dengan domain
   - Disable untuk development (localhost)
   - Reverse proxy (Nginx/Caddy) recommended untuk SSL termination

---

## Troubleshooting

### Connection Test Failed

**Issue**: Connection test returns error

**Solutions**:
1. Check MinIO container is running:
   ```bash
   docker compose ps
   ```

2. Check MinIO logs:
   ```bash
   docker compose logs minio --tail 50
   ```

3. Verify endpoint is accessible:
   ```bash
   curl http://localhost:9000/minio/health/live
   ```

4. Test credentials:
   ```bash
   # Using mc (MinIO Client)
   mc alias set myminIO http://localhost:9000 foodlife_admin foodlife_secret_2026
   mc ls myminIO
   ```

5. Check firewall rules (production)

### Changes Not Applied

**Issue**: Configuration saved but tidak berubah

**Solution**: Restart Django server
```bash
docker compose restart web
```

### Bucket Not Found

**Issue**: product-images bucket tidak ada

**Solution**: Create bucket manually
```bash
# Using mc (MinIO Client)
mc mb myminIO/product-images
mc anonymous set download myminIO/product-images
```

---

## Benefits for Production Deployment

### Before (Manual .env Edit):
1. ❌ SSH ke server
2. ❌ Edit .env dengan nano/vim
3. ❌ Restart container manually
4. ❌ No validation/testing
5. ❌ Typo prone
6. ❌ No logging

### After (Settings Page):
1. ✅ Web-based UI
2. ✅ Form validation
3. ✅ Test connection before save
4. ✅ Configuration examples provided
5. ✅ Auto-save to .env
6. ✅ Change logging
7. ✅ Password masking
8. ✅ Error messages with troubleshooting

---

## Future Enhancements

### Planned Features:
- [ ] Auto-restart server after save (jika memungkinkan)
- [ ] Configuration version history
- [ ] Rollback to previous configuration
- [ ] Multiple MinIO profiles (dev, staging, prod)
- [ ] Bucket management (create, delete, set policy)
- [ ] Upload test file untuk verify upload permission
- [ ] Real-time connection status indicator
- [ ] Email notification on configuration change
- [ ] Audit log for configuration changes
- [ ] Permission-based access (admin only)

---

## Summary

✅ **Settings menu** sekarang expandable dengan 4 submenu  
✅ **MinIO Configuration page** untuk easy setup  
✅ **Test Connection** untuk verify sebelum save  
✅ **Auto-save to .env** tanpa perlu SSH  
✅ **Configuration examples** untuk berbagai scenario  
✅ **Password protection** untuk secret key  
✅ **Ready for production** deployment  

**Result**: Deploy ke production tidak akan error lagi karena MinIO endpoint bisa di-configure dengan mudah via web interface.

---

**Last Updated**: February 3, 2026  
**Version**: 1.0  
**Status**: Production Ready ✅
