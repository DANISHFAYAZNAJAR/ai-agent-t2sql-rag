"""Agent query endpoint"""
from ninja import Router
from ninja.responses import Response
from pydantic import BaseModel
from typing import Optional
from api.auth import AuthBearer
from agent.graph import get_agent
import logging

logger = logging.getLogger(__name__)

router = Router()


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    response: str
    task_type: str  # "t2sql" or "rag"
    metadata: Optional[dict] = None


@router.post("/query", response=QueryResponse, auth=AuthBearer())
def query_agent(request, query_data: QueryRequest):
    """Submit a query to the AI agent"""
    try:
        agent = get_agent()
        
        initial_state = {
            "query": query_data.query,
            "route": "unknown",
            "task_type": "unknown",
            "response": "",
            "result": {},
            "metadata": {},
            "error": ""
        }
        
        result = agent.invoke(initial_state)
        response = result.get("response", "I couldn't process your query.")
        task_type = result.get("task_type", "unknown")
        metadata = result.get("metadata", {})
        
        return QueryResponse(
            response=response,
            task_type=task_type,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Error in agent query: {str(e)}")
        return Response(
            QueryResponse(
                response=f"I encountered an error: {str(e)}",
                task_type="error",
                metadata={"error": str(e)}
            ),
            status=500
        )

