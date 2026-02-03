@echo off
REM Script untuk membuat admin user menggunakan Docker
REM Usage: create_admin_docker.bat

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if docker-compose exists
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] docker-compose is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if docker-compose.yml exists
if not exist "docker-compose.yml" (
    echo [ERROR] docker-compose.yml not found. Please run this script from the project root directory
    pause
    exit /b 1
)

echo.
echo ============================================
echo  FoodLife CMS - Create Admin User (Docker)
echo ============================================
echo.

REM Check if containers are running
docker-compose ps web >nul 2>&1
if errorlevel 1 (
    echo [INFO] Docker containers not running. Starting them...
    docker-compose up -d
    if errorlevel 1 (
        echo [ERROR] Failed to start Docker containers
        pause
        exit /b 1
    )
    echo [INFO] Waiting for containers to be ready...
    ping -n 11 localhost >nul
)

REM Run the create admin user script
echo [INFO] Creating admin user...
echo.

REM Get container ID of fnb_ho_web
for /f "tokens=1" %%A in ('docker ps -q --filter "name=fnb_ho_web"') do set CONTAINER_ID=%%A

if "!CONTAINER_ID!"=="" (
    echo [ERROR] Container fnb_ho_web not running
    pause
    exit /b 1
)

docker exec !CONTAINER_ID! python manage.py create_admin

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to create admin user
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Admin user creation completed
echo.
echo You can now login with:
echo   Username: admin
echo   Password: admin123
echo.
echo URL: http://localhost:8002/auth/login/
echo.
pause
