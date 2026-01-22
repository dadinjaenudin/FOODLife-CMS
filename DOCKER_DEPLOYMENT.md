# 🐳 Docker Deployment Guide
# F&B POS HO System

**Version**: 1.0  
**Last Updated**: 2026-01-22

---

## 📑 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Development)](#quick-start-development)
3. [Production Deployment](#production-deployment)
4. [Configuration](#configuration)
5. [Services Overview](#services-overview)
6. [Common Commands](#common-commands)
7. [Troubleshooting](#troubleshooting)
8. [Backup & Restore](#backup--restore)
9. [Scaling & Performance](#scaling--performance)
10. [Security Best Practices](#security-best-practices)

---

## 🔧 Prerequisites

### Required Software
- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+
- **Git**: 2.30+

### System Requirements

#### Development
- **CPU**: 2 cores minimum
- **RAM**: 4 GB minimum
- **Disk**: 10 GB free space

#### Production
- **CPU**: 4 cores minimum (8+ recommended)
- **RAM**: 8 GB minimum (16+ recommended)
- **Disk**: 50 GB free space (SSD recommended)

### Install Docker

#### Ubuntu/Debian
```bash
# Update package index
sudo apt-get update

# Install dependencies
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up stable repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
```

#### macOS
```bash
# Install via Homebrew
brew install --cask docker

# Or download Docker Desktop
# https://www.docker.com/products/docker-desktop
```

#### Windows
Download and install Docker Desktop:
https://www.docker.com/products/docker-desktop

### Verify Installation
```bash
docker --version
docker compose version
```

Expected output:
```
Docker version 24.0.0+
Docker Compose version v2.20.0+
```

---

## 🚀 Quick Start (Development)

### Step 1: Clone Repository
```bash
git clone https://github.com/dadinjaenudin/FoodBeverages-CMS.git
cd FoodBeverages-CMS
```

### Step 2: Setup Environment
```bash
# Copy environment file
cp .env.docker .env

# (Optional) Edit environment variables
nano .env
```

### Step 3: Build and Start Services
```bash
# Build images
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f web
```

### Step 4: Access Application

- **Web Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/docs/
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/

**Default Credentials**:
- Username: `admin`
- Password: `admin123`

### Step 5: Verify Services
```bash
# Check running containers
docker compose ps

# Expected output:
# NAME                    STATUS
# fnb_ho_web              Up
# fnb_ho_db               Up (healthy)
# fnb_ho_redis            Up (healthy)
# fnb_ho_celery_worker    Up
# fnb_ho_celery_beat      Up
```

---

## 🏭 Production Deployment

### Step 1: Prepare Server

#### Recommended Server Specs
- **Cloud Provider**: AWS, Google Cloud, Digital Ocean, or Azure
- **OS**: Ubuntu 22.04 LTS
- **Instance Type**: 
  - Development: t3.medium (2 vCPU, 4 GB RAM)
  - Production: t3.large+ (2+ vCPU, 8+ GB RAM)

#### Server Setup
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker (see Prerequisites section)

# Install additional tools
sudo apt-get install -y git ufw fail2ban
```

### Step 2: Clone and Configure
```bash
# Clone repository
git clone https://github.com/dadinjaenudin/FoodBeverages-CMS.git
cd FoodBeverages-CMS

# Copy production environment template
cp .env.prod.example .env.prod

# Edit with production values
nano .env.prod
```

**Critical Settings to Change**:
```bash
SECRET_KEY=<generate-strong-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_PASSWORD=<strong-database-password>
REDIS_PASSWORD=<strong-redis-password>
```

### Step 3: SSL Certificates

#### Option A: Let's Encrypt (Free)
```bash
# Install Certbot
sudo apt-get install -y certbot

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

#### Option B: Self-Signed (Testing)
```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=ID/ST=Jakarta/L=Jakarta/O=YogyaGroup/CN=yourdomain.com"
```

### Step 4: Update Nginx Configuration
```bash
# Edit nginx configuration
nano nginx/conf.d/django.conf

# Replace 'yourdomain.com' with your actual domain
sed -i 's/yourdomain.com/your-actual-domain.com/g' nginx/conf.d/django.conf
```

### Step 5: Build and Deploy
```bash
# Build production images
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### Step 6: Firewall Configuration
```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH (if not already allowed)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

### Step 7: Verify Deployment
```bash
# Check container health
docker compose -f docker-compose.prod.yml ps

# Test endpoints
curl -I https://yourdomain.com
curl https://yourdomain.com/health/
```

---

## ⚙️ Configuration

### Environment Files

| File | Purpose | Usage |
|------|---------|-------|
| `.env.docker` | Development (Docker) | `docker compose up` |
| `.env.prod` | Production | `docker compose -f docker-compose.prod.yml up` |
| `.env.example` | Template | Copy to create new environment |

### Key Environment Variables

#### Django Settings
```bash
SECRET_KEY=<random-50-char-string>
DEBUG=False  # ALWAYS False in production
ALLOWED_HOSTS=domain1.com,domain2.com
```

#### Database Settings
```bash
DB_ENGINE=django.db.backends.postgresql
DB_NAME=fnb_ho_db
DB_USER=postgres
DB_PASSWORD=<strong-password>
DB_HOST=db  # Docker service name
DB_PORT=5432
```

#### Redis Settings
```bash
REDIS_URL=redis://:password@redis:6379/0
```

#### Gunicorn Settings (Production)
```bash
GUNICORN_WORKERS=4  # (CPU cores * 2) + 1
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120
```

---

## 🔍 Services Overview

### 1. PostgreSQL (db)
**Purpose**: Primary database  
**Port**: 5432  
**Data Volume**: `postgres_data`

```bash
# Connect to database
docker compose exec db psql -U postgres -d fnb_ho_db

# Backup database
docker compose exec db pg_dump -U postgres fnb_ho_db > backup.sql

# Restore database
cat backup.sql | docker compose exec -T db psql -U postgres fnb_ho_db
```

### 2. Redis (redis)
**Purpose**: Cache & message broker  
**Port**: 6379  
**Data Volume**: `redis_data` (production)

```bash
# Connect to Redis
docker compose exec redis redis-cli

# Monitor Redis
docker compose exec redis redis-cli MONITOR

# Check memory usage
docker compose exec redis redis-cli INFO memory
```

### 3. Django Web (web)
**Purpose**: Main application server  
**Port**: 8000  
**Command**: 
- Dev: `python manage.py runserver`
- Prod: `gunicorn config.wsgi:application`

```bash
# View logs
docker compose logs -f web

# Execute Django commands
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# Access shell
docker compose exec web python manage.py shell
```

### 4. Celery Worker (celery_worker)
**Purpose**: Async task processing  
**No exposed ports**

```bash
# View worker logs
docker compose logs -f celery_worker

# Check active tasks
docker compose exec celery_worker celery -A config inspect active
```

### 5. Celery Beat (celery_beat)
**Purpose**: Scheduled tasks  
**No exposed ports**

```bash
# View beat logs
docker compose logs -f celery_beat

# List scheduled tasks
docker compose exec web python manage.py shell
>>> from django_celery_beat.models import PeriodicTask
>>> PeriodicTask.objects.all()
```

### 6. Nginx (nginx) - Production Only
**Purpose**: Reverse proxy & static file serving  
**Ports**: 80, 443

```bash
# Reload nginx
docker compose exec nginx nginx -s reload

# Test configuration
docker compose exec nginx nginx -t

# View access logs
docker compose logs -f nginx
```

### 7. Flower (flower) - Production Only
**Purpose**: Celery monitoring  
**Port**: 5555  
**URL**: http://yourdomain.com:5555

---

## 🛠️ Common Commands

### Docker Compose Commands

#### Start Services
```bash
# Development
docker compose up -d

# Production
docker compose -f docker-compose.prod.yml up -d

# Start specific service
docker compose up -d web
```

#### Stop Services
```bash
# Stop all
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v

# Stop specific service
docker compose stop web
```

#### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f web

# Last 100 lines
docker compose logs --tail=100 web
```

#### Restart Services
```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart web
```

#### Rebuild Images
```bash
# Rebuild all
docker compose build

# Rebuild specific service
docker compose build web

# Force rebuild (no cache)
docker compose build --no-cache
```

### Django Management Commands

#### Migrations
```bash
# Run migrations
docker compose exec web python manage.py migrate

# Create migrations
docker compose exec web python manage.py makemigrations

# Show migrations
docker compose exec web python manage.py showmigrations
```

#### User Management
```bash
# Create superuser
docker compose exec web python manage.py createsuperuser

# Change password
docker compose exec web python manage.py changepassword admin
```

#### Data Management
```bash
# Generate sample data
docker compose exec web python manage.py generate_sample_data

# Flush database (⚠️ deletes all data)
docker compose exec web python manage.py flush

# Load fixtures
docker compose exec web python manage.py loaddata fixtures/initial_data.json
```

#### Static Files
```bash
# Collect static files
docker compose exec web python manage.py collectstatic --noinput

# Clear cache
docker compose exec web python manage.py clear_cache
```

### Database Commands

#### Backup
```bash
# PostgreSQL backup
docker compose exec db pg_dump -U postgres fnb_ho_db > backup_$(date +%Y%m%d).sql

# With compression
docker compose exec db pg_dump -U postgres fnb_ho_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

#### Restore
```bash
# PostgreSQL restore
cat backup.sql | docker compose exec -T db psql -U postgres fnb_ho_db

# From compressed backup
gunzip -c backup.sql.gz | docker compose exec -T db psql -U postgres fnb_ho_db
```

#### Database Shell
```bash
# PostgreSQL shell
docker compose exec db psql -U postgres -d fnb_ho_db

# Django dbshell
docker compose exec web python manage.py dbshell
```

---

## 🔧 Troubleshooting

### Container Won't Start

#### Check Logs
```bash
docker compose logs web
```

#### Check Container Status
```bash
docker compose ps
```

#### Verify Environment
```bash
docker compose exec web env | grep DB_
```

### Database Connection Issues

#### Symptom
```
django.db.utils.OperationalError: could not connect to server
```

#### Solution
```bash
# Check database health
docker compose exec db pg_isready -U postgres

# Restart database
docker compose restart db

# Check database logs
docker compose logs db
```

### Port Already in Use

#### Symptom
```
Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use
```

#### Solution
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>

# Or use different port
# Edit docker-compose.yml: "8001:8000"
```

### Out of Memory

#### Symptom
```
Killed
```

#### Solution
```bash
# Check container resources
docker stats

# Increase Docker memory limit (Docker Desktop)
# Docker Desktop > Settings > Resources > Memory

# Or reduce worker count in .env
GUNICORN_WORKERS=2
CELERY_WORKERS=2
```

### Permission Issues

#### Symptom
```
PermissionError: [Errno 13] Permission denied
```

#### Solution
```bash
# Fix volume permissions
docker compose exec web chown -R appuser:appuser /app

# Or run as root (temporary, not recommended)
docker compose exec -u root web chown -R appuser:appuser /app
```

---

## 💾 Backup & Restore

### Automated Backup Script

Create `backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker compose exec -T db pg_dump -U postgres fnb_ho_db | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Media files backup
docker compose exec -T web tar -czf - /app/media | cat > "$BACKUP_DIR/media_$DATE.tar.gz"

# Keep only last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Make executable and add to cron:
```bash
chmod +x backup.sh

# Add to crontab (daily at 2 AM)
0 2 * * * /path/to/backup.sh
```

### Manual Backup

#### Full Backup
```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup database
docker compose exec db pg_dump -U postgres fnb_ho_db > backups/$(date +%Y%m%d)/database.sql

# Backup media files
docker cp fnb_ho_web:/app/media backups/$(date +%Y%m%d)/media

# Backup .env file
cp .env backups/$(date +%Y%m%d)/.env
```

### Restore from Backup

```bash
# Stop services
docker compose down

# Restore database
cat backups/20260122/database.sql | docker compose exec -T db psql -U postgres fnb_ho_db

# Restore media files
docker cp backups/20260122/media fnb_ho_web:/app/

# Start services
docker compose up -d
```

---

## 📈 Scaling & Performance

### Horizontal Scaling

#### Scale Celery Workers
```bash
# Scale to 4 workers
docker compose up -d --scale celery_worker=4

# Check running workers
docker compose ps celery_worker
```

#### Load Balancing (Production)
For production, use multiple web instances behind a load balancer:

```yaml
# docker-compose.prod.yml
services:
  web:
    deploy:
      replicas: 3
```

### Vertical Scaling

#### Increase Resources
```yaml
# docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Performance Optimization

#### Database Connection Pooling
```python
# config/settings.py
DATABASES = {
    'default': {
        # ...
        'CONN_MAX_AGE': 600,  # 10 minutes
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

#### Redis Cache Configuration
```python
# config/settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}
```

---

## 🔒 Security Best Practices

### 1. Environment Variables
```bash
# Never commit .env files
echo ".env" >> .gitignore
echo ".env.prod" >> .gitignore

# Use strong passwords
openssl rand -base64 32  # Generate random password
```

### 2. SSL/TLS
```bash
# Always use HTTPS in production
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 3. Database Security
```bash
# Use strong database password
DB_PASSWORD=$(openssl rand -base64 24)

# Limit database access
# Only allow connections from web container
```

### 4. Docker Security
```bash
# Run containers as non-root user
USER appuser

# Scan images for vulnerabilities
docker scan fnb_ho_web:latest

# Keep images updated
docker compose pull
docker compose up -d
```

### 5. Firewall
```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 6. Regular Updates
```bash
# Update Docker images monthly
docker compose pull
docker compose up -d

# Update system packages
sudo apt-get update && sudo apt-get upgrade -y
```

---

## 📊 Monitoring

### Health Checks

#### Application Health
```bash
curl http://localhost:8000/health/
```

#### Container Health
```bash
docker compose ps
docker inspect fnb_ho_web | grep -A 10 Health
```

### Resource Monitoring
```bash
# Real-time stats
docker stats

# Disk usage
docker system df

# Container logs size
docker compose logs --tail=0 | wc -l
```

### Celery Monitoring (Flower)
```
http://yourdomain.com:5555

Username: admin
Password: (from .env FLOWER_PASSWORD)
```

---

## 🆘 Support

### Documentation
- **Main README**: [README.md](README.md)
- **API Documentation**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Docker Hub**: https://hub.docker.com

### Community
- **GitHub Issues**: https://github.com/dadinjaenudin/FoodBeverages-CMS/issues
- **Email**: support@yogyagroup.com
- **Slack**: #devops-support

---

## 📝 Appendix

### A. Generate Strong Secret Key
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### B. Check Docker Installation
```bash
docker run hello-world
docker compose version
```

### C. Clean Up Docker
```bash
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Remove everything (⚠️ dangerous)
docker system prune -a --volumes -f
```

---

**Version**: 1.0  
**Last Updated**: 2026-01-22  
**Maintainer**: DevOps Team @ Yogya Group  
**Status**: Production Ready ✅
