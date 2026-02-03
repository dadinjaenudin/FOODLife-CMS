@echo off
REM Fresh Migration Script - Rebuild database dari scratch
REM HATI-HATI: Script ini akan menghapus semua data!

echo ============================================
echo FRESH MIGRATION SCRIPT
echo ============================================
echo.
echo WARNING: This will DELETE ALL DATA and recreate migrations!
echo.
set /p confirm="Are you sure? Type 'YES' to continue: "
if not "%confirm%"=="YES" (
    echo Cancelled.
    exit /b 1
)

echo.
echo [1/6] Creating backup...
docker exec fnb_ho_db pg_dump -U postgres fnb_ho_db > backup_auto_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Backup failed!
    exit /b 1
)
echo Backup created successfully!

echo.
echo [2/6] Deleting old migration files...
for %%d in (core products transactions promotions analytics inventory members dashboard settings) do (
    if exist %%d\migrations (
        echo Cleaning %%d migrations...
        del /Q %%d\migrations\*.py 2>nul
        echo # Generated migrations > %%d\migrations\__init__.py
    )
)
echo Old migrations deleted!

echo.
echo [3/6] Stopping containers and removing volumes...
docker-compose down -v
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to stop containers!
    exit /b 1
)
echo Containers stopped and volumes removed!

echo.
echo [4/6] Generating fresh migrations...
REM Start database only first
docker-compose up -d db redis
timeout /t 10 /nobreak

REM Create migrations
docker-compose run --rm web python manage.py makemigrations core
docker-compose run --rm web python manage.py makemigrations products
docker-compose run --rm web python manage.py makemigrations transactions
docker-compose run --rm web python manage.py makemigrations promotions
docker-compose run --rm web python manage.py makemigrations analytics
docker-compose run --rm web python manage.py makemigrations inventory
docker-compose run --rm web python manage.py makemigrations members
docker-compose run --rm web python manage.py makemigrations dashboard
docker-compose run --rm web python manage.py makemigrations settings

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Migration generation failed!
    exit /b 1
)
echo Fresh migrations generated!

echo.
echo [5/6] Starting full application...
docker-compose down
docker-compose up -d

echo.
echo [6/6] Waiting for application to start...
timeout /t 15 /nobreak

echo.
echo ============================================
echo MIGRATION COMPLETE!
echo ============================================
echo.
echo Next steps:
echo 1. Check logs: docker-compose logs -f web
echo 2. Create superuser: docker-compose exec web python manage.py createsuperuser
echo 3. Test application: http://localhost:8002
echo.
echo Backup file saved for rollback if needed.
echo ============================================
