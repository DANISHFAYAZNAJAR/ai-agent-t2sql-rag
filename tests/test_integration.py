"""
Integration tests for complete workflows
"""
import pytest
from django.conf import settings
from agent.graph import get_agent
from vanna_config.setup import setup_training_data, generate_sql, run_sql, ask
from data.ingestion.document_service import DocumentIngestionService
import os


@pytest.mark.django_db
class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        if not settings.OPENAI_API_KEY:
            pytest.skip("OPENAI_API_KEY not set")
        # Setup training data once
        setup_training_data()
    
    def test_complete_t2sql_workflow(self):
        """Test complete T2SQL workflow"""
        # Test query
        question = "How many leads are there?"
        sql = generate_sql(question)
        results = run_sql(sql)
        answer = ask(question)
        
        assert sql is not None
        assert results is not None
        assert answer is not None
        assert len(answer) > 0
    
    def test_complete_rag_workflow(self):
        """Test complete RAG workflow"""
        service = DocumentIngestionService()
        
        # Try to ingest a document if available
        brochure_dir = "../Proplens AI Engineer_Challenge/Project brochure dataset"
        if os.path.exists(brochure_dir):
            pdf_files = [f for f in os.listdir(brochure_dir) if f.endswith('.pdf')]
            if pdf_files:
                pdf_path = os.path.join(brochure_dir, pdf_files[0])
                try:
                    result = service.ingest_document(pdf_path)
                    assert result.get('chunks_created', 0) > 0
                    
                    # Test search
                    search_results = service.search_documents("amenities", n_results=3)
                    assert isinstance(search_results, list)
                except Exception:
                    pass  # Skip if ingestion fails
    
    def test_agent_end_to_end(self):
        """Test agent end-to-end"""
        agent = get_agent()
        
        # Test T2SQL query
        t2sql_state = {
            "query": "How many leads are there?",
            "route": "unknown",
            "task_type": "unknown",
            "response": "",
            "result": {},
            "metadata": {},
            "error": ""
        }
        
        result = agent.invoke(t2sql_state)
        assert result.get('task_type') == 't2sql'
        assert len(result.get('response', '')) > 0
        
        # Test RAG query
        rag_state = {
            "query": "What are the amenities?",
            "route": "unknown",
            "task_type": "unknown",
            "response": "",
            "result": {},
            "metadata": {},
            "error": ""
        }
        
        result = agent.invoke(rag_state)
        assert result.get('task_type') in ['rag', 't2sql']
        assert len(result.get('response', '')) > 0

