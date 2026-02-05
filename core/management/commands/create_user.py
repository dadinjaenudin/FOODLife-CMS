"""
Management command to create users with role selection
Usage: python manage.py create_user
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from core.models import Company, Brand, Store
import getpass
import re

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a new user with role selection'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== User Creation Form ===\n'))
        
        # Get username
        while True:
            username = input('Username: ').strip()
            if not username:
                self.stdout.write(self.style.ERROR('Username cannot be empty!'))
                continue
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.ERROR(f'Username "{username}" already exists!'))
                continue
            break
        
        # Get email
        while True:
            email = input('Email: ').strip()
            if not email:
                self.stdout.write(self.style.ERROR('Email cannot be empty!'))
                continue
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                self.stdout.write(self.style.ERROR('Invalid email format!'))
                continue
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.ERROR(f'Email "{email}" already exists!'))
                continue
            break
        
        # Get first name
        first_name = input('First Name (optional): ').strip()
        
        # Get last name
        last_name = input('Last Name (optional): ').strip()
        
        # Get password
        while True:
            password = getpass.getpass('Password: ')
            if not password:
                self.stdout.write(self.style.ERROR('Password cannot be empty!'))
                continue
            if len(password) < 8:
                self.stdout.write(self.style.ERROR('Password must be at least 8 characters!'))
                continue
            password_confirm = getpass.getpass('Confirm Password: ')
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match!'))
                continue
            break
        
        # Get PIN (optional)
        while True:
            pin = input('PIN (6 digits, optional - press Enter to skip): ').strip()
            if not pin:
                break
            if len(pin) != 6 or not pin.isdigit():
                self.stdout.write(self.style.ERROR('PIN must be exactly 6 digits!'))
                continue
            break
        
        # Select Role
        self.stdout.write('\nAvailable Roles:')
        role_choices = dict(User.ROLE_CHOICES)
        for i, (role_code, role_name) in enumerate(User.ROLE_CHOICES, 1):
            self.stdout.write(f'  {i}. {role_name} ({role_code})')
        
        while True:
            try:
                role_select = int(input('Select Role (enter number): '))
                if 1 <= role_select <= len(User.ROLE_CHOICES):
                    role = list(role_choices.keys())[role_select - 1]
                    break
                else:
                    self.stdout.write(self.style.ERROR(f'Please enter a number between 1 and {len(User.ROLE_CHOICES)}!'))
            except ValueError:
                self.stdout.write(self.style.ERROR('Please enter a valid number!'))
        
        # Select Role Scope
        self.stdout.write('\nAvailable Role Scopes:')
        scope_choices = dict(User.ROLE_SCOPE_CHOICES)
        for i, (scope_code, scope_name) in enumerate(User.ROLE_SCOPE_CHOICES, 1):
            self.stdout.write(f'  {i}. {scope_name} ({scope_code})')
        
        while True:
            try:
                scope_select = int(input('Select Role Scope (enter number): '))
                if 1 <= scope_select <= len(User.ROLE_SCOPE_CHOICES):
                    role_scope = list(scope_choices.keys())[scope_select - 1]
                    break
                else:
                    self.stdout.write(self.style.ERROR(f'Please enter a number between 1 and {len(User.ROLE_SCOPE_CHOICES)}!'))
            except ValueError:
                self.stdout.write(self.style.ERROR('Please enter a valid number!'))
        
        company = None
        brand = None
        store = None
        
        # Select Company based on role scope
        if role_scope in ['company', 'brand', 'store']:
            companies = Company.objects.filter(is_active=True)
            if not companies.exists():
                self.stdout.write(self.style.ERROR('No active companies found!'))
                return
            
            self.stdout.write(f'\nAvailable Companies:')
            companies_list = list(companies)
            for i, company_obj in enumerate(companies_list, 1):
                self.stdout.write(f'  {i}. {company_obj.name} ({company_obj.code})')
            
            while True:
                try:
                    company_select = int(input('Select Company (enter number): '))
                    if 1 <= company_select <= len(companies_list):
                        company = companies_list[company_select - 1]
                        break
                    else:
                        self.stdout.write(self.style.ERROR(f'Please enter a number between 1 and {len(companies_list)}!'))
                except ValueError:
                    self.stdout.write(self.style.ERROR('Please enter a valid number!'))
        
        # Select Brand if needed
        if role_scope in ['brand', 'store'] and company:
            brands = Brand.objects.filter(company=company, is_active=True)
            if not brands.exists():
                self.stdout.write(self.style.ERROR(f'No active brands found for {company.name}!'))
                return
            
            self.stdout.write(f'\nAvailable Brands:')
            brands_list = list(brands)
            for i, brand_obj in enumerate(brands_list, 1):
                self.stdout.write(f'  {i}. {brand_obj.name} ({brand_obj.code})')
            
            while True:
                try:
                    brand_select = int(input('Select Brand (enter number): '))
                    if 1 <= brand_select <= len(brands_list):
                        brand = brands_list[brand_select - 1]
                        break
                    else:
                        self.stdout.write(self.style.ERROR(f'Please enter a number between 1 and {len(brands_list)}!'))
                except ValueError:
                    self.stdout.write(self.style.ERROR('Please enter a valid number!'))
        
        # Select Store if needed
        if role_scope == 'store' and brand:
            stores = Store.objects.filter(brands=brand, is_active=True)
            if not stores.exists():
                self.stdout.write(self.style.ERROR(f'No active stores found for {brand.name}!'))
                return
            
            self.stdout.write(f'\nAvailable Stores:')
            stores_list = list(stores)
            for i, store_obj in enumerate(stores_list, 1):
                self.stdout.write(f'  {i}. {store_obj.name} ({store_obj.code})')
            
            while True:
                try:
                    store_select = int(input('Select Store (enter number): '))
                    if 1 <= store_select <= len(stores_list):
                        store = stores_list[store_select - 1]
                        break
                    else:
                        self.stdout.write(self.style.ERROR(f'Please enter a number between 1 and {len(stores_list)}!'))
                except ValueError:
                    self.stdout.write(self.style.ERROR('Please enter a valid number!'))
        
        # Confirm before creating
        self.stdout.write('\n=== User Summary ===')
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'First Name: {first_name or "(empty)"}')
        self.stdout.write(f'Last Name: {last_name or "(empty)"}')
        self.stdout.write(f'Role: {dict(User.ROLE_CHOICES).get(role)}')
        self.stdout.write(f'Role Scope: {dict(User.ROLE_SCOPE_CHOICES).get(role_scope)}')
        if company:
            self.stdout.write(f'Company: {company.name}')
        if brand:
            self.stdout.write(f'Brand: {brand.name}')
        if store:
            self.stdout.write(f'Store: {store.name}')
        self.stdout.write(f'PIN: {"Set" if pin else "Not set"}')
        
        confirm = input('\nCreate this user? (yes/no): ').strip().lower()
        if confirm != 'yes':
            self.stdout.write(self.style.WARNING('User creation cancelled.'))
            return
        
        # Create the user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                company=company,
                brand=brand,
                store=store,
                role=role,
                role_scope=role_scope,
                pin=pin,
                is_active=True
            )
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ User "{username}" created successfully!'))
            self.stdout.write(f'User ID: {user.id}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error creating user: {str(e)}'))
            raise CommandError(str(e))
