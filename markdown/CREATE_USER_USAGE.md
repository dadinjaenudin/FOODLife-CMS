# User Creation Script - Documentation

Script ini digunakan untuk membuat user baru dengan memilih role dan scope secara interaktif.

## Fitur

✓ Interactive user creation dengan validasi input
✓ Pilihan role (Admin, Manager, Cashier, Waiter, Kitchen Staff)
✓ Pilihan role scope (Global, Company, Brand, Store)
✓ Dynamic selection komponen (Company, Brand, Store) berdasarkan scope
✓ PIN validation (6 digit)
✓ Password confirmation
✓ User summary sebelum creating
✓ Error handling dan validasi lengkap

## Cara Menggunakan

### 1. Menggunakan Docker (Recommended)

#### Windows - Dengan docker-compose
```bash
create_user_docker.bat
```

#### Windows - Direct Docker exec
```bash
create_user_docker_direct.bat
```

#### Linux/Mac - Dengan docker-compose
```bash
chmod +x create_user_docker.sh
./create_user_docker.sh
```

#### Linux/Mac - Direct Docker exec
```bash
chmod +x create_user_docker_direct.sh
./create_user_docker_direct.sh
```

#### Manual Docker command
```bash
# Dengan docker-compose
docker-compose exec fnb_ho_web python manage.py create_user

# Dengan docker exec (jika container sedang running)
docker exec -it fnb_ho_web python manage.py create_user
```

### 2. Local Development (Tanpa Docker)

#### Windows (Batch File)
```bash
create_user.bat
```

#### Linux/Mac (Shell Script)
```bash
chmod +x create_user.sh
./create_user.sh
```

#### Manual (Django Management Command)
```bash
python manage.py create_user
```

## Role dan Role Scope

### Roles (Peran Pengguna)
- **Admin**: Administrator system
- **Manager**: Manajer outlet
- **Cashier**: Kasir/Operator mesin
- **Waiter**: Pelayan/Waiter
- **Kitchen**: Kitchen Staff/Koki

### Role Scopes (Ruang Lingkup Akses)
1. **Global Level**: Super Admin - akses semua companies
2. **Company Level**: HO Admin - akses semua brands & stores dalam 1 perusahaan
3. **Brand Level**: Brand Manager - akses semua stores dalam 1 brand
4. **Store Level**: Store Manager - hanya akses 1 store

## Contoh Input

```
=== User Creation Form ===

Username: john_cashier
Email: john@example.com
First Name: John
Last Name: Doe
Password: ******* (min 8 chars)
Confirm Password: *******
PIN (6 digits, optional): 123456

Available Roles:
  1. Admin (admin)
  2. Manager (manager)
  3. Cashier (cashier)
  4. Waiter (waiter)
  5. Kitchen Staff (kitchen)
Select Role (enter number): 3

Available Role Scopes:
  1. Global Level (global)
  2. Company Level (company)
  3. Brand Level (brand)
  4. Store Level (store)
Select Role Scope (enter number): 4

Available Companies:
  1. Yogya Group (YGY)
Select Company (enter number): 1

Available Brands:
  1. Ayam Geprek Express (YGY-001)
  2. Bakso Boedjangan (YGY-002)
Select Brand (enter number): 1

Available Stores:
  1. Yogya Store 01 (YGY-001-01)
  2. Yogya Store 02 (YGY-001-02)
Select Store (enter number): 1

=== User Summary ===
Username: john_cashier
Email: john@example.com
First Name: John
Last Name: Doe
Role: Cashier (cashier)
Role Scope: Store Level (store)
Company: Yogya Group
Brand: Ayam Geprek Express
Store: Yogya Store 01
PIN: Set

Create this user? (yes/no): yes

✓ User "john_cashier" created successfully!
User ID: a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

## Validasi Input

- **Username**: Harus unik, tidak boleh kosong
- **Email**: Format valid, harus unik, tidak boleh kosong
- **Password**: Minimal 8 karakter, harus confirm match
- **PIN**: Opsional, jika diisi harus 6 digit
- **Role**: Harus dipilih dari list yang tersedia
- **Role Scope**: Harus dipilih dari list yang tersedia
- **Company/Brand/Store**: Otomatis muncul berdasarkan scope, harus dipilih

## Troubleshooting

### Error: "Python is not installed"
- Install Python dari https://www.python.org/downloads/
- Pastikan Python sudah di-add ke PATH environment variable

### Error: "manage.py not found"
- Jalankan script dari root directory FoodLife-CMS
- Pastikan Anda di folder yang tepat sebelum menjalankan script

### Error: "No active companies found"
- Pastikan ada company yang sudah dibuat dan is_active=True
- Gunakan Django admin atau management command lain untuk membuat company

### Username/Email already exists
- Gunakan username atau email yang berbeda
- Script akan memberitahu jika ada konflik

## File Structure

```
FoodLife-CMS/
├── create_user.bat                  # Windows batch file (local)
├── create_user.sh                   # Linux/Mac shell script (local)
├── create_user_docker.bat           # Windows batch file (docker-compose)
├── create_user_docker.sh            # Linux/Mac shell script (docker-compose)
├── create_user_docker_direct.bat    # Windows batch file (docker exec)
├── create_user_docker_direct.sh     # Linux/Mac shell script (docker exec)
├── docker-compose.yml               # Docker compose configuration
├── core/
│   └── management/
│       └── commands/
│           └── create_user.py       # Django management command
└── markdown/
    └── CREATE_USER_USAGE.md         # Dokumentasi ini
```

## Notes

- Script ini menggunakan interactive input, jangan gunakan untuk automation/scripting
- Password tidak akan ditampilkan di layar saat input
- Semua user yang dibuat akan is_active=True secara default
- Jika terjadi error saat create, transaction akan rollback otomatis

## Docker Environment

### Prasyarat
- Docker installed
- docker-compose installed
- Container image sudah di-build

### Container Information
- **Container Name**: `fnb_ho_web`
- **Service Name**: `web`
- **Docker Image**: Built from Dockerfile in project root
- **Database**: PostgreSQL (`fnb_ho_db`)
- **Cache/Broker**: Redis (`fnb_ho_redis`)

### Startup Docker Containers

```bash
# Start all containers (db, redis, web)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f web
```

### Shutdown Docker Containers

```bash
# Stop containers
docker-compose down

# Stop dan remove volumes
docker-compose down -v
```

### Script Behavior

#### `create_user_docker.bat` / `create_user_docker.sh`
- Menggunakan `docker-compose`
- Otomatis check dan start containers jika belum running
- Recommended untuk development
- Lebih mudah untuk multi-service setup

#### `create_user_docker_direct.bat` / `create_user_docker_direct.sh`
- Menggunakan `docker exec`
- Direct akses ke container
- Memerlukan container sudah running
- Lebih cepat jika container sudah aktif
- Optional: bisa pass container ID sebagai argument

### Troubleshooting Docker

**Error: No such service: web**
```bash
# Pastikan docker-compose.yml ada di current directory
# atau jalankan dari project root
cd /path/to/FoodLife-CMS
docker-compose up -d
```

**Error: Cannot connect to Docker daemon**
```bash
# Start Docker Desktop atau Docker service
# Windows: Start Docker Desktop
# Linux: sudo systemctl start docker
```

**Error: Container fnb_ho_web not running**
```bash
# Start containers
docker-compose up -d

# Check if container started
docker-compose ps
```

**Error: Database connection refused**
```bash
# Wait for database to be ready
docker-compose logs db

# Restart services
docker-compose restart
```
