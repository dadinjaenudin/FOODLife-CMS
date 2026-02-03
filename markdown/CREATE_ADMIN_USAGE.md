# Admin User Creation - Documentation

Script ini digunakan untuk membuat admin user secara otomatis.

## Fitur

✓ Quick admin user creation
✓ Default credentials: admin / admin123
✓ Support Docker dan local development
✓ Auto-start Docker containers jika belum running
✓ Error handling dan validation

## Cara Menggunakan

### 1. Docker (Recommended)

#### Windows
```bash
create_admin_docker.bat
```

#### Linux/Mac
```bash
chmod +x create_admin_docker.sh
./create_admin_docker.sh
```

#### Manual Docker Command
```bash
docker-compose exec fnb_ho_web python create_admin_user.py
```

### 2. Local Development (Tanpa Docker)

#### Windows
```bash
create_admin_local.bat
```

#### Linux/Mac
```bash
chmod +x create_admin_local.sh
./create_admin_local.sh
```

#### Manual Command
```bash
python create_admin_user.py
```

## Credentials

Setelah script berhasil dijalankan, Anda bisa login dengan:

- **URL**: http://localhost:8002/auth/login/
- **Username**: admin
- **Password**: admin123

## Script Details

### create_admin_user.py
- Python script yang membuat/update admin user
- Menggunakan Django ORM
- Membuat user dengan role='admin' dan role_scope='global'
- Set is_active=True, is_staff=True, is_superuser=True

### create_admin_docker.bat / create_admin_docker.sh
- Wrapper untuk menjalankan script dalam Docker container
- Otomatis check dan start containers jika belum running
- Gunakan untuk Docker deployment

### create_admin_local.bat / create_admin_local.sh
- Wrapper untuk menjalankan script di local environment
- Gunakan untuk local development
- Pastikan environment variables sudah benar

## Troubleshooting

### Error: "Docker containers not running"
```bash
# Start containers manually
docker-compose up -d

# Verify status
docker-compose ps
```

### Error: "Database connection refused"
```bash
# Wait a moment for database to start
sleep 10

# Check database logs
docker-compose logs db
```

### Error: "User admin already exists"
Script akan otomatis update password ke admin123 jika user sudah ada.

### Error: "manage.py not found"
- Pastikan Anda menjalankan script dari root directory FoodLife-CMS
- Cek path ke manage.py

## File Structure

```
FoodLife-CMS/
├── create_admin_user.py         # Python script untuk create admin
├── create_admin_docker.bat      # Windows Docker wrapper
├── create_admin_docker.sh       # Linux/Mac Docker wrapper
├── create_admin_local.bat       # Windows local wrapper
├── create_admin_local.sh        # Linux/Mac local wrapper
├── docker-compose.yml           # Docker configuration
└── markdown/
    └── CREATE_ADMIN_USAGE.md    # Dokumentasi ini
```

## Notes

- Script akan overwrite password jika user admin sudah ada
- User dibuat dengan global scope (akses semua)
- User set sebagai superuser dan staff
- Recommended untuk development/testing purpose
- Untuk production, ubah password setelah login pertama

## Next Steps

1. Jalankan script untuk create admin user
2. Login dengan credentials: admin / admin123
3. Buat company/brand/store di dashboard
4. Create users lain dengan role yang lebih spesifik menggunakan `create_user.bat`
