"""
Generate Sample Kitchen Station and Printer Configuration Data
Based on Product printer_target choices and real kitchen setup scenarios
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import KitchenStation, PrinterConfig, Product
from core.models import Company, Brand, Store
import random


class Command(BaseCommand):
    help = 'Create sample kitchen stations and printer configurations'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing kitchen stations first')
        parser.add_argument('--company', type=str, help='Company name to create data for')
        parser.add_argument('--brand', type=str, help='Brand name to create data for')

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                if options['reset']:
                    self.stdout.write('🗑️  Deleting existing kitchen stations and printers...')
                    PrinterConfig.objects.all().delete()
                    KitchenStation.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS('   Deleted existing data'))

                # Get target company/brand or use all
                companies = Company.objects.filter(is_active=True)
                if options['company']:
                    companies = companies.filter(name__icontains=options['company'])

                brands = Brand.objects.filter(is_active=True, company__in=companies)
                if options['brand']:
                    brands = brands.filter(name__icontains=options['brand'])

                if not brands.exists():
                    self.stdout.write(self.style.ERROR('❌ No brands found'))
                    return

                self.stdout.write(f'🏢 Creating kitchen stations for {brands.count()} brands...')

                total_stations = 0
                total_printers = 0

                for brand in brands:
                    stations_created, printers_created = self.create_brand_kitchen_data(brand)
                    total_stations += stations_created
                    total_printers += printers_created

                self.stdout.write(self.style.SUCCESS(f'✅ Created {total_stations} kitchen stations and {total_printers} printers'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            raise

    def create_brand_kitchen_data(self, brand):
        """Create kitchen stations and printers for a brand"""
        self.stdout.write(f'📍 Processing {brand.name} ({brand.company.name})')
        
        stations_created = 0
        printers_created = 0
        
        # Get stores for this brand
        stores = Store.objects.filter(brands=brand, is_active=True)
        
        # Create brand-wide kitchen stations (available to all stores)
        brand_stations = self.create_brand_wide_stations(brand)
        stations_created += len(brand_stations)
        
        # Create printers for brand-wide stations  
        for station in brand_stations:
            printers = self.create_station_printers(station, is_brand_wide=True)
            printers_created += len(printers)
        
        # Create store-specific stations for each store
        for store in stores:
            store_stations = self.create_store_specific_stations(brand, store)
            stations_created += len(store_stations)
            
            # Create printers for store-specific stations
            for station in store_stations:
                printers = self.create_station_printers(station, is_brand_wide=False)
                printers_created += len(printers)
        
        self.stdout.write(f'   ✅ {brand.name}: {stations_created} stations, {printers_created} printers')
        return stations_created, printers_created

    def create_brand_wide_stations(self, brand):
        """Create brand-wide kitchen stations based on product printer targets"""
        stations = []
        
        # Standard kitchen stations based on Product.PRINTER_TARGET_CHOICES
        station_configs = [
            {
                'code': 'KITCHEN',
                'name': 'Main Kitchen',
                'description': 'Primary cooking station for hot food items, main courses, and cooked dishes',
                'sort_order': 1
            },
            {
                'code': 'BAR',
                'name': 'Bar Station',
                'description': 'Beverage preparation station for drinks, cocktails, and cold beverages',
                'sort_order': 2
            },
            {
                'code': 'DESSERT',
                'name': 'Dessert Station',
                'description': 'Dessert and pastry preparation station for sweets and cold desserts',
                'sort_order': 3
            }
        ]
        
        for config in station_configs:
            station, created = KitchenStation.objects.get_or_create(
                brand=brand,
                store=None,  # Brand-wide
                code=config['code'],
                defaults={
                    'name': config['name'],
                    'description': config['description'],
                    'sort_order': config['sort_order'],
                    'is_active': True
                }
            )
            if created:
                stations.append(station)
                self.stdout.write(f'   📋 Created brand-wide station: {station.code} - {station.name}')
        
        return stations

    def create_store_specific_stations(self, brand, store):
        """Create store-specific kitchen stations based on store type/concept"""
        stations = []
        
        # Determine store-specific stations based on store name patterns
        store_name_lower = store.store_name.lower()
        
        # Additional stations for specific store types
        additional_stations = []
        
        if any(keyword in store_name_lower for keyword in ['drive', 'auto', 'car']):
            additional_stations.extend([
                {
                    'code': 'DRIVE_THRU',
                    'name': 'Drive Thru Kitchen',
                    'description': 'Dedicated kitchen for drive-thru orders with faster preparation',
                    'sort_order': 10
                },
                {
                    'code': 'EXPEDITE',
                    'name': 'Expedite Station',
                    'description': 'Order assembly and quality check station for drive-thru',
                    'sort_order': 11
                }
            ])
        
        if any(keyword in store_name_lower for keyword in ['mall', 'plaza', 'center']):
            additional_stations.extend([
                {
                    'code': 'DISPLAY',
                    'name': 'Display Kitchen',
                    'description': 'Open kitchen for customer viewing in mall locations',
                    'sort_order': 12
                },
                {
                    'code': 'GRAB_GO',
                    'name': 'Grab & Go Station',
                    'description': 'Pre-made items and quick service station',
                    'sort_order': 13
                }
            ])
        
        if any(keyword in store_name_lower for keyword in ['airport', 'station', 'terminal']):
            additional_stations.extend([
                {
                    'code': 'EXPRESS',
                    'name': 'Express Kitchen',
                    'description': 'Fast preparation station for transit locations',
                    'sort_order': 14
                }
            ])
        
        if any(keyword in store_name_lower for keyword in ['premium', 'vip', 'deluxe']):
            additional_stations.extend([
                {
                    'code': 'SPECIALTY',
                    'name': 'Specialty Kitchen',
                    'description': 'Premium and custom order preparation station',
                    'sort_order': 15
                },
                {
                    'code': 'CHEF_TABLE',
                    'name': 'Chef Table Station',
                    'description': 'Interactive cooking station for premium experience',
                    'sort_order': 16
                }
            ])
        
        # Create the additional stations
        for config in additional_stations:
            station, created = KitchenStation.objects.get_or_create(
                brand=brand,
                store=store,
                code=config['code'],
                defaults={
                    'name': config['name'],
                    'description': config['description'],
                    'sort_order': config['sort_order'],
                    'is_active': True
                }
            )
            if created:
                stations.append(station)
                self.stdout.write(f'   🏪 Created store-specific station: {store.store_name} - {station.code}')
        
        return stations

    def create_station_printers(self, station, is_brand_wide=False):
        """Create printer configurations for a kitchen station"""
        printers = []
        
        # Base IP for demonstration (use private IP ranges)
        base_ip = "192.168.1"
        
        # Printer configurations based on station type
        printer_configs = []
        
        if station.code == 'KITCHEN':
            printer_configs = [
                {'name': 'Kitchen Printer Main', 'ip_suffix': '101', 'paper_width': '80mm'},
                {'name': 'Kitchen Printer Backup', 'ip_suffix': '102', 'paper_width': '80mm'},
            ]
        elif station.code == 'BAR':
            printer_configs = [
                {'name': 'Bar Receipt Printer', 'ip_suffix': '201', 'paper_width': '58mm'},
            ]
        elif station.code == 'DESSERT':
            printer_configs = [
                {'name': 'Dessert Station Printer', 'ip_suffix': '301', 'paper_width': '58mm'},
            ]
        elif station.code == 'DRIVE_THRU':
            printer_configs = [
                {'name': 'Drive Thru Kitchen', 'ip_suffix': '401', 'paper_width': '80mm'},
                {'name': 'Drive Thru Expedite', 'ip_suffix': '402', 'paper_width': '58mm'},
            ]
        elif station.code == 'EXPRESS':
            printer_configs = [
                {'name': 'Express Kitchen Printer', 'ip_suffix': '501', 'paper_width': '80mm'},
            ]
        else:
            # Default printer for other stations
            printer_configs = [
                {'name': f'{station.name} Printer', 'ip_suffix': str(random.randint(150, 199)), 'paper_width': '58mm'},
            ]
        
        # Create printers
        for config in printer_configs:
            # Adjust IP based on store for store-specific stations
            if not is_brand_wide and station.store:
                store_id_suffix = str(abs(hash(str(station.store.id))) % 100).zfill(2)
                ip_address = f"{base_ip}.{store_id_suffix}{config['ip_suffix'][-1]}"
            else:
                ip_address = f"{base_ip}.{config['ip_suffix']}"
            
            printer, created = PrinterConfig.objects.get_or_create(
                station=station,
                printer_name=config['name'],
                defaults={
                    'ip_address': ip_address,
                    'paper_width': config['paper_width'],
                    'is_active': True
                }
            )
            if created:
                printers.append(printer)
        
        return printers

    def get_sample_products_by_printer_target(self, brand):
        """Get sample of existing products grouped by printer_target"""
        products_by_target = {}
        
        for choice_value, choice_label in Product.PRINTER_TARGET_CHOICES:
            products = Product.objects.filter(
                brand=brand,
                printer_target=choice_value,
                is_active=True
            )[:3]  # Get up to 3 products per category
            
            if products.exists():
                products_by_target[choice_value] = {
                    'label': choice_label,
                    'products': list(products)
                }
        
        return products_by_target