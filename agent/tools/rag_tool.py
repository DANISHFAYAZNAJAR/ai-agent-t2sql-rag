"""Document RAG tool"""
from typing import Dict, Any, List
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from data.ingestion.document_service import DocumentIngestionService
from django.conf import settings

logger = logging.getLogger(__name__)


class DocumentRAGTool:
    """Tool for retrieving information from brochure documents using RAG"""
    
    def __init__(self):
        self.document_service = DocumentIngestionService()
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful real estate assistant. 
            Answer questions about property projects based on the provided brochure information.
            Be accurate, concise, and helpful. If the information is not available in the provided context, say so."""),
            ("human", """Based on the following information from property brochures, answer the question.

Context from brochures:
{context}

Question: {question}

Provide a clear and helpful answer:""")
        ])
    
    def execute(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Execute a Document RAG query"""
        try:
            search_results = self.document_service.search_documents(
                query=query,
                n_results=n_results
            )
            
            if not search_results:
                return {
                    "task_type": "rag",
                    "response": "I couldn't find any relevant information in the brochures to answer your question.",
                    "context": [],
                    "success": False
                }
            
            context_texts = [result["text"] for result in search_results]
            context = "\n\n---\n\n".join(context_texts)
            prompt = self.prompt_template.format_messages(
                context=context,
                question=query
            )
            
            response = self.llm.invoke(prompt)
            answer = response.content
            
            return {
                "task_type": "rag",
                "response": answer,
                "context": search_results,
                "sources": [r.get("metadata", {}).get("filename", "Unknown") for r in search_results],
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in Document RAG tool: {str(e)}")
            return {
                "task_type": "rag",
                "error": str(e),
                "success": False
            }
    
    def __call__(self, query: str) -> Dict[str, Any]:
        return self.execute(query)

