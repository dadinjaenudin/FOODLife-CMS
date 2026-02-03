#!/bin/bash
# Script untuk membuat admin user menggunakan Docker
# Usage: ./create_admin_docker.sh

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "[ERROR] docker-compose is not installed"
    exit 1
fi

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "[ERROR] docker-compose.yml not found. Please run this script from the project root directory"
    exit 1
fi

echo ""
echo "============================================"
echo "  FoodLife CMS - Create Admin User (Docker)"
echo "============================================"
echo ""

# Check if containers are running
if ! docker-compose ps fnb_ho_web 2>/dev/null | grep -q "Up"; then
    echo "[INFO] Docker containers not running. Starting them..."
    docker-compose up -d
    echo "[INFO] Waiting for containers to be ready..."
    sleep 10
fi

# Run the create admin user script
echo "[INFO] Creating admin user..."
echo ""

docker-compose exec -T fnb_ho_web python manage.py create_admin

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to create admin user"
    exit 1
fi

echo ""
echo "[SUCCESS] Admin user creation completed"
echo ""
echo "You can now login with:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "URL: http://localhost:8002/auth/login/"
echo ""
