"""
LangGraph agent definition
"""
from typing import Dict, Any, Literal, TypedDict
from langgraph.graph import StateGraph, END
from .nodes import AgentNodes


# Define the state schema as TypedDict
class AgentState(TypedDict):
    """State schema for the agent"""
    query: str
    route: str
    task_type: str
    response: str
    result: Dict[str, Any]
    metadata: Dict[str, Any]
    error: str


def create_agent_graph() -> StateGraph:
    """
    Create and configure the LangGraph agent
    
    Returns:
        Configured StateGraph instance
    """
    nodes = AgentNodes()
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("route", nodes.route_query)
    workflow.add_node("t2sql", nodes.execute_t2sql)
    workflow.add_node("rag", nodes.execute_rag)
    workflow.add_node("format", nodes.format_response)
    
    # Set entry point
    workflow.set_entry_point("route")
    
    # Define routing function
    def route_decision(state: AgentState) -> str:
        route = state.get("route", "rag")
        if route == "t2sql":
            return "t2sql"
        else:
            return "rag"
    
    # Add conditional edges based on routing decision
    workflow.add_conditional_edges(
        "route",
        route_decision,
        {
            "t2sql": "t2sql",
            "rag": "rag"
        }
    )
    
    # Connect tool execution to formatting
    workflow.add_edge("t2sql", "format")
    workflow.add_edge("rag", "format")
    
    # End after formatting
    workflow.add_edge("format", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


# Create a singleton instance
_agent_app = None

def get_agent():
    """
    Get or create the agent graph instance
    
    Returns:
        Agent graph instance
    """
    global _agent_app
    if _agent_app is None:
        _agent_app = create_agent_graph()
    return _agent_app

