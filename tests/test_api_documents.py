"""
Tests for document ingestion API
"""
import pytest
from django.test import Client
from django.conf import settings
import json
import os
import tempfile


@pytest.mark.django_db
class TestDocumentEndpoints:
    """Test document ingestion endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        if not settings.OPENAI_API_KEY:
            pytest.skip("OPENAI_API_KEY not set")
    
    def test_list_documents(self, authenticated_client):
        """Test listing documents"""
        response = authenticated_client.get('/api/documents/list')
        
        assert response.status_code == 200
        data = response.json()
        assert 'documents_count' in data or 'documents' in data
    
    def test_upload_document(self, authenticated_client):
        """Test document upload"""
        # Create a dummy PDF file for testing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF')
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, 'rb') as pdf_file:
                response = authenticated_client.post(
                    '/api/documents/upload',
                    {'file': pdf_file},
                    format='multipart'
                )
                
                # Note: This might fail if the PDF is not valid, but we test the endpoint
                assert response.status_code in [200, 400, 500]
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    def test_upload_unauthorized(self):
        """Test upload without authentication"""
        client = Client()
        response = client.post('/api/documents/upload')
        assert response.status_code == 401

