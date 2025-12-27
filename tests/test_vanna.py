"""
Tests for Vanna Text-to-SQL
"""
import pytest
from django.conf import settings
from vanna_config.setup import get_vanna_agent, setup_training_data, generate_sql, run_sql, ask


@pytest.mark.django_db
class TestVanna:
    """Test Vanna Text-to-SQL functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        if not settings.OPENAI_API_KEY:
            pytest.skip("OPENAI_API_KEY not set")
        # Setup training data once
        setup_training_data()
    
    def test_vanna_initialization(self):
        """Test Vanna initialization"""
        agent = get_vanna_agent()
        assert agent is not None
    
    def test_generate_sql(self):
        """Test SQL generation"""
        question = "Show me all leads from Lumina Grand"
        sql = generate_sql(question)
        
        assert sql is not None
        assert isinstance(sql, str)
        assert 'SELECT' in sql.upper()
        assert 'leads' in sql.lower()
    
    def test_run_sql(self):
        """Test SQL execution"""
        sql = "SELECT COUNT(*) as count FROM leads"
        results = run_sql(sql)
        
        assert results is not None
        assert isinstance(results, list)
        if results:
            assert 'count' in results[0]
    
    def test_ask_pipeline(self):
        """Test complete ask pipeline"""
        question = "How many leads are there?"
        answer = ask(question)
        
        assert answer is not None
        assert isinstance(answer, str)
        assert len(answer) > 0

