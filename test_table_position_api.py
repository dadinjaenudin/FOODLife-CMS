#!/usr/bin/env python
"""
Test script for table position update API endpoint
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User
from products.models import Tables, TableArea, Store, Brand, Company

# Create test client
client = APIClient()

# Get or create test data
try:
    company = Company.objects.first()
    brand = Brand.objects.filter(company=company).first()
    store = Store.objects.filter(company=company).first()
    
    if not (company and brand and store):
        print("❌ Test data missing (Company, Brand, Store)")
        exit(1)
    
    # Get or create tablearea
    tablearea = TableArea.objects.filter(store=store).first()
    if not tablearea:
        print("❌ No TableArea found for store")
        exit(1)
    
    # Get first table
    table = Tables.objects.filter(area=tablearea).first()
    if not table:
        print("❌ No Tables found for tablearea")
        exit(1)
    
    print(f"✓ Test data found:")
    print(f"  - Company: {company.name}")
    print(f"  - Brand: {brand.name}")
    print(f"  - Store: {store.name}")
    print(f"  - TableArea: {tablearea.name}")
    print(f"  - Table: {table.name} (ID: {table.id})")
    print()
    
    # Get or create test user
    user = User.objects.first()
    if not user:
        print("❌ No user found")
        exit(1)
    
    # Authenticate
    client.force_authenticate(user=user)
    print(f"✓ Authenticated as: {user.username}")
    print()
    
    # Test update position
    url = f'/api/v1/products/tables/{table.id}/update_position/'
    data = {
        'pos_x': 250,
        'pos_y': 150
    }
    
    print(f"POST {url}")
    print(f"Body: {data}")
    print()
    
    response = client.post(url, data, format='json')
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {response.json()}")
    print()
    
    # Verify position saved
    table.refresh_from_db()
    print(f"✓ Table position in DB:")
    print(f"  - pos_x: {table.pos_x}")
    print(f"  - pos_y: {table.pos_y}")
    
    if table.pos_x == 250 and table.pos_y == 150:
        print()
        print("✅ API endpoint working correctly!")
    else:
        print()
        print("❌ Position not saved correctly")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
