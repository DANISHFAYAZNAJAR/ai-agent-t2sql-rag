"""
Tests for LangGraph agent
"""
import pytest
from django.conf import settings
from agent.graph import get_agent


@pytest.mark.django_db
class TestLangGraphAgent:
    """Test LangGraph agent functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        if not settings.OPENAI_API_KEY:
            pytest.skip("OPENAI_API_KEY not set")
    
    @pytest.fixture
    def agent(self):
        """Get agent instance"""
        return get_agent()
    
    def test_agent_creation(self, agent):
        """Test agent graph creation"""
        assert agent is not None
    
    def test_agent_t2sql_query(self, agent):
        """Test agent with T2SQL query"""
        initial_state = {
            "query": "How many leads are there?",
            "route": "unknown",
            "task_type": "unknown",
            "response": "",
            "result": {},
            "metadata": {},
            "error": ""
        }
        
        result = agent.invoke(initial_state)
        
        assert result is not None
        assert 'response' in result
        assert 'task_type' in result
        assert result['task_type'] == 't2sql'
        assert len(result['response']) > 0
    
    def test_agent_rag_query(self, agent):
        """Test agent with RAG query"""
        initial_state = {
            "query": "What are the amenities in Lumina Grand?",
            "route": "unknown",
            "task_type": "unknown",
            "response": "",
            "result": {},
            "metadata": {},
            "error": ""
        }
        
        result = agent.invoke(initial_state)
        
        assert result is not None
        assert 'response' in result
        assert 'task_type' in result
        # Could be rag or t2sql depending on routing
        assert result['task_type'] in ['rag', 't2sql']
        assert len(result['response']) > 0
    
    def test_agent_routing(self, agent):
        """Test agent routing logic"""
        t2sql_state = {
            "query": "Count leads by project",
            "route": "unknown",
            "task_type": "unknown",
            "response": "",
            "result": {},
            "metadata": {},
            "error": ""
        }
        
        result = agent.invoke(t2sql_state)
        # Should route to t2sql
        assert result.get('task_type') == 't2sql'
    
    def test_agent_error_handling(self, agent):
        """Test agent error handling"""
        # Test with empty query
        initial_state = {
            "query": "",
            "route": "unknown",
            "task_type": "unknown",
            "response": "",
            "result": {},
            "metadata": {},
            "error": ""
        }
        
        # Should handle gracefully
        result = agent.invoke(initial_state)
        assert result is not None

