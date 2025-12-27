"""LangGraph nodes for agent execution"""
from typing import Dict, Any, Literal
import logging
import time
from .router import QueryRouter
from .tools.t2sql_tool import T2SQLTool
from .tools.rag_tool import DocumentRAGTool
from utils.query_logger import get_query_logger

logger = logging.getLogger(__name__)


class AgentNodes:
    """Nodes for the LangGraph agent"""
    
    def __init__(self):
        self.router = QueryRouter()
        self.t2sql_tool = T2SQLTool()
        self.rag_tool = DocumentRAGTool()
    
    def route_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Route the query to determine which tool to use"""
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
                "route": "rag",
                "error": str(e)
            }
    
    def execute_t2sql(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Text-to-SQL query"""
        query = state.get("query", "")
        start_time = time.time()
        
        try:
            result = self.t2sql_tool.execute(query)
            execution_time = time.time() - start_time
            
            query_logger = get_query_logger()
            query_logger.log_query(
                query=query,
                response=result.get("response", "I couldn't process your query."),
                task_type="t2sql",
                sql_query=result.get("sql"),
                sql_results=result.get("results"),
                execution_time=execution_time
            )
            
            return {
                **state,
                "task_type": "t2sql",
                "result": result,
                "response": result.get("response", "I couldn't process your query."),
                "metadata": {
                    "sql_query": result.get("sql"),
                    "sql_results_count": len(result.get("results", []))
                }
            }
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error in T2SQL execution: {str(e)}")
            
            query_logger = get_query_logger()
            query_logger.log_query(
                query=query,
                response=f"I encountered an error processing your database query: {str(e)}",
                task_type="t2sql",
                metadata={"error": str(e)},
                execution_time=execution_time
            )
            
            return {
                **state,
                "task_type": "t2sql",
                "error": str(e),
                "response": f"I encountered an error processing your database query: {str(e)}"
            }
    
    def execute_rag(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Document RAG query"""
        query = state.get("query", "")
        start_time = time.time()
        
        try:
            result = self.rag_tool.execute(query)
            execution_time = time.time() - start_time
            
            query_logger = get_query_logger()
            query_logger.log_query(
                query=query,
                response=result.get("response", "I couldn't find information to answer your question."),
                task_type="rag",
                rag_chunks=result.get("context", []),
                execution_time=execution_time
            )
            
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
            execution_time = time.time() - start_time
            logger.error(f"Error in RAG execution: {str(e)}")
            
            query_logger = get_query_logger()
            query_logger.log_query(
                query=query,
                response=f"I encountered an error retrieving information: {str(e)}",
                task_type="rag",
                metadata={"error": str(e)},
                execution_time=execution_time
            )
            
            return {
                **state,
                "task_type": "rag",
                "error": str(e),
                "response": f"I encountered an error retrieving information: {str(e)}"
            }
    
    def format_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format the final response"""
        return {
            "response": state.get("response", "I couldn't process your query."),
            "task_type": state.get("task_type", "unknown"),
            "metadata": state.get("metadata", {})
        }

