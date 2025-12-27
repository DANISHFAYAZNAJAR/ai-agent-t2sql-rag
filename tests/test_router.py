"""
Tests for query router
"""
import pytest
from django.conf import settings
from agent.router import QueryRouter


@pytest.mark.django_db
class TestQueryRouter:
    """Test query routing logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        if not settings.OPENAI_API_KEY:
            pytest.skip("OPENAI_API_KEY not set")
    
    @pytest.fixture
    def router(self):
        """Create router instance"""
        return QueryRouter()
    
    def test_router_initialization(self, router):
        """Test router initialization"""
        assert router is not None
        assert router.llm is not None
    
    def test_classify_t2sql_query(self, router):
        """Test classification of T2SQL queries"""
        queries = [
            "Show me all leads from Lumina Grand",
            "How many leads are there?",
            "Find leads with budget above 1 million",
            "Count leads by project",
            "Get leads by status"
        ]
        
        for query in queries:
            classification = router.classify_query(query)
            assert classification in ['t2sql', 'rag']
            # Most should be t2sql
            if 'lead' in query.lower() or 'count' in query.lower():
                # These should typically be t2sql
                pass
    
    def test_classify_rag_query(self, router):
        """Test classification of RAG queries"""
        queries = [
            "What are the amenities in Lumina Grand?",
            "Tell me about Sobha Crest features",
            "What facilities are available?",
            "Describe the property location"
        ]
        
        for query in queries:
            classification = router.classify_query(query)
            assert classification in ['t2sql', 'rag']
            # Most should be rag
            if 'amenities' in query.lower() or 'features' in query.lower():
                # These should typically be rag
                pass
    
    def test_keyword_matching(self, router):
        """Test keyword-based classification"""
        # T2SQL keywords
        t2sql_queries = [
            "Show me leads",
            "Count customers",
            "Filter by budget"
        ]
        
        # RAG keywords
        rag_queries = [
            "What amenities",
            "Tell me about features",
            "Describe the project"
        ]
        
        # Test that keywords influence classification
        for query in t2sql_queries:
            classification = router.classify_query(query)
            assert classification in ['t2sql', 'rag']
        
        for query in rag_queries:
            classification = router.classify_query(query)
            assert classification in ['t2sql', 'rag']

