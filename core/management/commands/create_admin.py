"""
Management command to create admin user
Usage: python manage.py create_admin
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create or update admin user for FoodLife CMS'

    def handle(self, *args, **options):
        self.stdout.write('Creating admin user...')
        
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'role': 'admin',
                'role_scope': 'global'
            }
        )
        
        user.set_password('admin123')
        user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ User admin created successfully'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ Password updated to admin123'))
        
        self.stdout.write(f'User ID: {user.id}')
        self.stdout.write(f'Is Active: {user.is_active}')
        self.stdout.write(f'Is Staff: {user.is_staff}')
