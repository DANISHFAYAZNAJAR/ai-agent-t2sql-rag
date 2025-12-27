"""Router for T2SQL or Document RAG"""
from typing import Literal
import logging
from langchain_openai import ChatOpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


class QueryRouter:
    """Route queries to appropriate tool (T2SQL or Document RAG)"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        self.t2sql_keywords = [
            "lead", "leads", "crm", "customer", "budget", "status",
            "count", "find", "show", "list", "filter", "query",
            "database", "table", "how many", "which leads"
        ]
        
        self.rag_keywords = [
            "amenities", "facilities", "features", "project", "property",
            "brochure", "location", "price", "pricing", "specifications",
            "what is", "tell me about", "describe", "information about"
        ]
    
    def classify_query(self, query: str) -> Literal["t2sql", "rag", "unknown"]:
        """Classify query to determine which tool to use"""
        query_lower = query.lower()
        t2sql_score = sum(1 for keyword in self.t2sql_keywords if keyword in query_lower)
        rag_score = sum(1 for keyword in self.rag_keywords if keyword in query_lower)
        if abs(t2sql_score - rag_score) < 2 or (t2sql_score == 0 and rag_score == 0):
            return self._llm_classify(query)
        if t2sql_score > rag_score:
            return "t2sql"
        elif rag_score > t2sql_score:
            return "rag"
        else:
            return self._llm_classify(query)
    
    def _llm_classify(self, query: str) -> Literal["t2sql", "rag"]:
        """Use LLM to classify the query"""
        try:
            prompt = f"""Classify the following query to determine which tool should handle it:

            Query: "{query}"

            Options:
            - "t2sql": Use if the query is about querying the CRM database, finding leads, filtering data, counting records, or asking about customer/lead information stored in the database.
            - "rag": Use if the query is about property features, amenities, project details, brochure information, or asking "what is" or "tell me about" a property/project.

            Respond with only "t2sql" or "rag" (no quotes, no explanation)."""

            response = self.llm.invoke(prompt)
            classification = response.content.strip().lower()
            
            if classification in ["t2sql", "rag"]:
                return classification
            else:
                logger.warning(f"Unexpected classification: {classification}, defaulting to rag")
                return "rag"
                
        except Exception as e:
            logger.error(f"Error in LLM classification: {str(e)}")
            return "rag"

