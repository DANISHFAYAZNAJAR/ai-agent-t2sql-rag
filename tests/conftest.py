"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys
import django
from django.conf import settings

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

# Django database setup is handled by pytest-django automatically

@pytest.fixture
def api_client():
    """Django test client"""
    from django.test import Client
    return Client()

@pytest.fixture
def authenticated_client(api_client):
    """Authenticated API client with JWT token"""
    from api.auth import router as auth_router
    from ninja import NinjaAPI
    
    # Create a test API instance
    api = NinjaAPI()
    api.add_router("/auth", auth_router)
    
    # Login to get token
    response = api_client.post(
        '/api/auth/login',
        data={'username': 'admin', 'password': 'admin123'},
        content_type='application/json'
    )
    
    if response.status_code == 200:
        token = response.json().get('access_token')
        api_client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    
    return api_client

@pytest.fixture
def sample_lead_data():
    """Sample lead data for testing"""
    return {
        'lead_id': 'TEST_L1',
        'lead_name': 'Test Lead',
        'email': 'test@example.com',
        'country_code': '1',
        'phone': '1234567890',
        'project_name': 'Lumina Grand',
        'unit_type': '3 bed',
        'min_budget': 1000000.00,
        'max_budget': 2000000.00,
        'lead_status': 'connected',
        'last_conversation_summary': 'Test conversation'
    }

