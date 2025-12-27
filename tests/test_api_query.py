"""
Tests for query API endpoint
"""
import pytest
from django.test import Client
from django.conf import settings
import json
import os


@pytest.mark.django_db
class TestQueryEndpoint:
    """Test query endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        # Ensure OpenAI API key is set (or skip tests if not)
        if not settings.OPENAI_API_KEY:
            pytest.skip("OPENAI_API_KEY not set")
    
    def test_query_t2sql(self, authenticated_client):
        """Test T2SQL query"""
        response = authenticated_client.post(
            '/api/query',
            data=json.dumps({
                'query': 'How many leads are there?'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'response' in data
        assert 'task_type' in data
        assert data['task_type'] == 't2sql'
    
    def test_query_rag(self, authenticated_client):
        """Test RAG query"""
        response = authenticated_client.post(
            '/api/query',
            data=json.dumps({
                'query': 'What are the amenities in Lumina Grand?'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'response' in data
        assert 'task_type' in data
        # Could be rag or t2sql depending on routing
        assert data['task_type'] in ['rag', 't2sql']
    
    def test_query_unauthorized(self):
        """Test query without authentication"""
        client = Client()
        response = client.post(
            '/api/query',
            data=json.dumps({
                'query': 'Test query'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 401
    
    def test_query_missing_query(self, authenticated_client):
        """Test query with missing query parameter"""
        response = authenticated_client.post(
            '/api/query',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        # Should return validation error
        assert response.status_code in [400, 422]

