#!/usr/bin/env python
"""Test script for table position API endpoint"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIClient
import json

# Get or create test user
user, created = User.objects.get_or_create(username='testuser', defaults={'is_staff': True})
print(f"User: {user.username} (created={created})")

# Get a table to test with
from products.models import Tables
table = Tables.objects.first()
if table:
    print(f"Testing with Table ID: {table.id}")
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Test update_position endpoint
    url = f'/api/v1/tables/{table.id}/update-position/'
    data = {'pos_x': 250, 'pos_y': 300}
    response = client.post(url, data, format='json')
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {json.dumps(response.json(), indent=2)}")
    
    # Verify in DB
    table.refresh_from_db()
    print(f"DB Values - pos_x: {table.pos_x}, pos_y: {table.pos_y}")
else:
    print("No tables found in database")
