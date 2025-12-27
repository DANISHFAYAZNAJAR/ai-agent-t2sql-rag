"""
Tests for Django models
"""
import pytest
from django.utils import timezone
from datetime import date
from crm.models import Lead


@pytest.mark.django_db
class TestLeadModel:
    """Test Lead model"""
    
    def test_create_lead(self, sample_lead_data):
        """Test creating a lead"""
        lead = Lead.objects.create(**sample_lead_data)
        assert lead.lead_id == 'TEST_L1'
        assert lead.lead_name == 'Test Lead'
        assert lead.email == 'test@example.com'
        assert lead.project_name == 'Lumina Grand'
        assert lead.unit_type == '3 bed'
        assert lead.lead_status == 'connected'
    
    def test_lead_str_representation(self, sample_lead_data):
        """Test lead string representation"""
        lead = Lead.objects.create(**sample_lead_data)
        assert str(lead) == f"TEST_L1 - Test Lead"
    
    def test_lead_unique_constraint(self, sample_lead_data):
        """Test that lead_id must be unique"""
        Lead.objects.create(**sample_lead_data)
        
        # Try to create another lead with same lead_id
        with pytest.raises(Exception):  # IntegrityError
            Lead.objects.create(**sample_lead_data)
    
    def test_lead_status_choices(self):
        """Test lead status choices"""
        valid_statuses = [choice[0] for choice in Lead.LEAD_STATUS_CHOICES]
        assert 'not_connected' in valid_statuses
        assert 'connected' in valid_statuses
        assert 'visit_scheduled' in valid_statuses
        assert 'purchased' in valid_statuses
    
    def test_lead_budget_fields(self):
        """Test lead budget fields"""
        lead = Lead.objects.create(
            lead_id='TEST_L2',
            lead_name='Test Lead 2',
            email='test2@example.com',
            country_code='1',
            phone='1234567891',
            project_name='Sobha Crest',
            unit_type='2 bed',
            min_budget=500000.00,
            max_budget=1000000.00,
            lead_status='connected'
        )
        assert lead.min_budget == 500000.00
        assert lead.max_budget == 1000000.00
    
    def test_lead_date_fields(self):
        """Test lead date fields"""
        test_date = date(2024, 1, 15)
        lead = Lead.objects.create(
            lead_id='TEST_L3',
            lead_name='Test Lead 3',
            email='test3@example.com',
            country_code='1',
            phone='1234567892',
            project_name='Altura',
            unit_type='1 Bed',
            lead_status='visit_scheduled',
            last_conversation_date=test_date
        )
        assert lead.last_conversation_date == test_date

