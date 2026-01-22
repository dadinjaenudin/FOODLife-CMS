"""
Simple script to create test user for HO Dashboard
"""
from django.core.management.base import BaseCommand
from core.models import Company, Brand, Store, User


class Command(BaseCommand):
    help = 'Create test admin user for HO Dashboard'

    def handle(self, *args, **options):
        self.stdout.write('Creating test data...')
        
        # Create Company
        company, created = Company.objects.get_or_create(
            code='TEST',
            defaults={
                'name': 'Test Company',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Company created: {company.name}'))
        else:
            self.stdout.write(f'→ Company exists: {company.name}')
        
        # Create Brand
        brand, created = Brand.objects.get_or_create(
            code='TST-001',
            defaults={
                'company': company,
                'name': 'Test Brand',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Brand created: {brand.name}'))
        else:
            self.stdout.write(f'→ Brand exists: {brand.name}')
        
        # Create Store
        store, created = Store.objects.get_or_create(
            store_code='TST-HQ',
            defaults={
                'brand': brand,
                'store_name': 'Headquarters',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Store created: {store.store_name}'))
        else:
            self.stdout.write(f'→ Store exists: {store.store_name}')
        
        # Create Admin User
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'company': company,
                'brand': brand,
                'email': 'admin@test.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'admin',
                'role_scope': 'company',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Admin user created: {admin.username}'))
            self.stdout.write(self.style.WARNING(f'  Username: admin'))
            self.stdout.write(self.style.WARNING(f'  Password: admin123'))
        else:
            self.stdout.write(f'→ Admin user exists: {admin.username}')
        
        # Create Manager User
        manager, created = User.objects.get_or_create(
            username='manager',
            defaults={
                'company': company,
                'brand': brand,
                'email': 'manager@test.com',
                'first_name': 'Manager',
                'last_name': 'User',
                'role': 'manager',
                'role_scope': 'brand',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            manager.set_password('manager123')
            manager.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Manager user created: {manager.username}'))
        else:
            self.stdout.write(f'→ Manager user exists: {manager.username}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(self.style.SUCCESS('Test data created successfully!'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write('')
        self.stdout.write('Login credentials:')
        self.stdout.write('  Username: admin')
        self.stdout.write('  Password: admin123')
        self.stdout.write('')
        self.stdout.write('Access dashboard at: http://localhost:8000/')
