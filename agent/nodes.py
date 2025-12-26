"""
LangGraph nodes for agent execution
"""
from typing import Dict, Any, Literal
import logging
from .router import QueryRouter
from .tools.t2sql_tool import T2SQLTool
from .tools.rag_tool import DocumentRAGTool

logger = logging.getLogger(__name__)


class AgentNodes:
    """Nodes for the LangGraph agent"""
    
    def __init__(self):
        """Initialize agent nodes"""
        self.router = QueryRouter()
        self.t2sql_tool = T2SQLTool()
        self.rag_tool = DocumentRAGTool()
    
    def route_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route the query to determine which tool to use
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state with route decision
        """
        query = state.get("query", "")
        
        try:
            route = self.router.classify_query(query)
            logger.info(f"Query routed to: {route}")
            
            return {
                **state,
                "route": route
            }
        except Exception as e:
            logger.error(f"Error in routing: {str(e)}")
            return {
                **state,
                "route": "rag",  # Default fallback
                "error": str(e)
            }
    
    def execute_t2sql(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Text-to-SQL query
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state with T2SQL results
        """
        query = state.get("query", "")
        
        try:
            result = self.t2sql_tool.execute(query)
            
            return {
                **state,
                "task_type": "t2sql",
                "result": result,
                "response": result.get("response", "I couldn't process your query."),
                "metadata": {}
            }
        except Exception as e:
            logger.error(f"Error in T2SQL execution: {str(e)}")
            return {
                **state,
                "task_type": "t2sql",
                "error": str(e),
                "response": f"I encountered an error processing your database query: {str(e)}"
            }
    
    def execute_rag(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Document RAG query
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state with RAG results
        """
        query = state.get("query", "")
        
        try:
            result = self.rag_tool.execute(query)
            
            return {
                **state,
                "task_type": "rag",
                "result": result,
                "response": result.get("response", "I couldn't find information to answer your question."),
                "metadata": {
                    "sources": result.get("sources", []),
                    "context_chunks": len(result.get("context", []))
                }
            }
        except Exception as e:
            logger.error(f"Error in RAG execution: {str(e)}")
            return {
                **state,
                "task_type": "rag",
                "error": str(e),
                "response": f"I encountered an error retrieving information: {str(e)}"
            }
    
    def format_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the final response
        
        Args:
            state: Current agent state
        
        Returns:
            Final formatted state
        """
        return {
            "response": state.get("response", "I couldn't process your query."),
            "task_type": state.get("task_type", "unknown"),
            "metadata": state.get("metadata", {})
        }

