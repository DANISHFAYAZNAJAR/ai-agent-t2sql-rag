"""
Minimal Vanna setup for Text-to-SQL capability
Using Vanna 2.0 framework directly
"""
from vanna import Agent
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.tools import RunSqlTool
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.tools.agent_memory import SaveTextMemoryTool
from django.conf import settings
from django.db import connection
from asgiref.sync import sync_to_async
import logging
import os
import uuid

logger = logging.getLogger(__name__)

# Global agent instance
_vanna_agent = None


class SimpleUserResolver(UserResolver):
    """Simple user resolver for Vanna agent"""
    
    async def resolve_user(self, request_context: RequestContext) -> User:
        """Resolve user from request context"""
        return User(id="default", email="user@example.com", group_memberships=["user", "admin"])


def get_vanna_agent():
    """Get or create Vanna agent instance"""
    global _vanna_agent
    
    if _vanna_agent is None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in settings")
        
        # Setup ChromaDB path
        chromadb_path = os.path.join(settings.CHROMADB_PATH, "vanna")
        os.makedirs(chromadb_path, exist_ok=True)
        
        # 1. Configure LLM Service
        llm_service = OpenAILlmService(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY
        )
        
        # 2. Configure Database Runner (SQLite)
        db_path = str(connection.settings_dict.get('NAME', ''))
        if not db_path:
            raise ValueError("Database path not found in Django settings")
        
        sql_runner = SqliteRunner(database_path=db_path)
        db_tool = RunSqlTool(sql_runner=sql_runner)
        
        # 3. Configure Agent Memory (ChromaDB)
        model_name = getattr(settings, 'VANNA_MODEL', 'proplens_vanna')
        agent_memory = ChromaAgentMemory(
            collection_name=f"{model_name}_training",
            persist_directory=chromadb_path
        )
        
        # 4. Create Tool Registry
        tools = ToolRegistry()
        tools.register_local_tool(db_tool, access_groups=['admin', 'user'])
        tools.register_local_tool(SaveTextMemoryTool(), access_groups=['admin', 'user'])
        
        # 5. User Resolver
        user_resolver = SimpleUserResolver()
        
        # 6. Create Vanna Agent
        _vanna_agent = Agent(
            llm_service=llm_service,
            tool_registry=tools,
            user_resolver=user_resolver,
            agent_memory=agent_memory
        )
        
        logger.info(f"Vanna 2.0 agent initialized")
    
    return _vanna_agent


async def ask_vanna(question: str) -> str:
    """
    Ask Vanna a question and get a natural language answer
    
    Args:
        question: Natural language question
        
    Returns:
        Natural language answer (cleaned)
    """
    agent = get_vanna_agent()
    request_context = RequestContext()
    
    # Collect all text components from agent response
    answer_parts = []
    all_text = []
    
    async for component in agent.send_message(request_context=request_context, message=question):
        rich_comp = getattr(component, 'rich_component', None)
        simple_comp = getattr(component, 'simple_component', None)
        
        # Extract from rich component
        if rich_comp:
            comp_type = getattr(rich_comp, 'type', None)
            comp_data = getattr(rich_comp, 'data', {})
            
            if comp_type == 'text':
                text = comp_data.get('text', comp_data.get('content', ''))
                if text:
                    all_text.append(str(text))
            elif comp_data:
                # Try to get any text from data
                for key in ['text', 'content', 'message', 'answer']:
                    if key in comp_data:
                        all_text.append(str(comp_data[key]))
                        break
        
        # Extract from simple component
        if simple_comp:
            if isinstance(simple_comp, str):
                all_text.append(simple_comp)
            elif hasattr(simple_comp, 'text'):
                all_text.append(str(simple_comp.text))
    
    # Filter and clean text
    for text in all_text:
        text_lower = text.lower()
        # Skip tool execution messages
        if any(noise in text_lower for noise in [
            'tool completed successfully', 'tool failed', 'results saved to file',
            'important: for visualize_data', 'error executing query', 'query_results_',
            '.csv', 'no such column'
        ]):
            continue
        # Skip CSV headers
        if text.strip().startswith('id,') or text.strip().startswith('project_name,'):
            continue
        # Add meaningful text
        if text.strip() and len(text.strip()) > 5:
            answer_parts.append(text.strip())
    
    # Join and clean response
    answer = '\n'.join(answer_parts).strip()
    
    # If answer is empty, try to extract from all_text (last meaningful message)
    if not answer or len(answer) < 10:
        # Look for the last meaningful message
        for text in reversed(all_text):
            text_clean = text.strip()
            if len(text_clean) > 20 and not any(noise in text_clean.lower() for noise in [
                'tool', 'csv', 'file', 'saved', 'visualize'
            ]):
                answer = text_clean
                break
    
    # Final fallback
    if not answer or len(answer) < 10:
        answer = "I couldn't generate a clear response. Please try rephrasing your question."
    
    return answer


def ask(question: str) -> str:
    """Sync wrapper for ask_vanna"""
    import asyncio
    
    # Always create a new event loop for sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(ask_vanna(question))
    finally:
        loop.close()


async def generate_sql_vanna(question: str) -> str:
    """
    Generate SQL from natural language question
    
    Args:
        question: Natural language question
        
    Returns:
        Generated SQL query
    """
    agent = get_vanna_agent()
    request_context = RequestContext()
    
    # Get SQL by asking agent and extracting from code blocks
    sql_query = None
    async for component in agent.send_message(request_context=request_context, message=question):
        rich_comp = getattr(component, 'rich_component', None)
        
        if rich_comp:
            comp_type = getattr(rich_comp, 'type', None)
            comp_data = getattr(rich_comp, 'data', {})
            
            # Look for code_block with SQL
            if comp_type == 'code_block':
                code = comp_data.get('code', comp_data.get('content', ''))
                if code and ('SELECT' in code.upper() or 'FROM' in code.upper()):
                    sql_query = code
                    break
    
    if not sql_query:
        # Fallback: simple query
        logger.warning("Could not extract SQL from agent response")
        sql_query = f"SELECT * FROM leads LIMIT 10;"
    
    return sql_query


def generate_sql(question: str) -> str:
    """Sync wrapper for generate_sql_vanna"""
    import asyncio
    
    # Always create a new event loop for sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(generate_sql_vanna(question))
    finally:
        loop.close()


def run_sql(sql: str) -> list:
    """
    Execute SQL query and return results
    
    Args:
        sql: SQL query to execute
        
    Returns:
        Query results as list of dictionaries
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
        return results
    except Exception as e:
        logger.error(f"Error running SQL: {str(e)}")
        raise


async def train_vanna_on_text(content: str):
    """Train Vanna on text content (DDL, docs, SQL examples)"""
    agent = get_vanna_agent()
    from vanna.core.tool import ToolContext
    
    user = User(id="system", email="system@example.com", group_memberships=["admin"])
    context = ToolContext(
        user=user,
        conversation_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        agent_memory=agent.agent_memory
    )
    
    save_tool = SaveTextMemoryTool()
    from vanna.tools.agent_memory import SaveTextMemoryParams
    
    await save_tool.execute(
        context=context,
        args=SaveTextMemoryParams(content=content)
    )


def setup_training_data():
    """Set up training data for Vanna (DDL, docs, SQL examples)"""
    import asyncio
    
    try:
        # Get DDL
        with connection.cursor() as cursor:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='leads'")
            result = cursor.fetchone()
            ddl = result[0] if result else """
            CREATE TABLE leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id VARCHAR(50) UNIQUE NOT NULL,
                lead_name VARCHAR(200) NOT NULL,
                email VARCHAR(255) NOT NULL,
                country_code VARCHAR(10) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                project_name VARCHAR(200) NOT NULL,
                unit_type VARCHAR(50) NOT NULL,
                min_budget DECIMAL(15, 2),
                max_budget DECIMAL(15, 2),
                lead_status VARCHAR(50) NOT NULL,
                last_conversation_date DATE,
                last_conversation_summary TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );
            """
        
        # Documentation
        documentation = """
        The CRM database contains lead information for real estate sales.
        
        Table: leads
        - lead_id: Unique identifier (e.g., L1, L2)
        - project_name: Property project name (e.g., 'Lumina Grand', 'Beachgate by Address')
        - unit_type: Unit type (e.g., '1 Bed', '2 Bed', '3 bed')
        - min_budget, max_budget: Budget range
        - lead_status: Status ('not_connected', 'connected', 'visit_scheduled', 'purchased', etc.)
        """
        
        # SQL examples
        sql_examples = [
            "Question: Show me all leads from Lumina Grand\nSQL: SELECT * FROM leads WHERE project_name = 'Lumina Grand';",
            "Question: Count leads by project name\nSQL: SELECT project_name, COUNT(*) as count FROM leads GROUP BY project_name;",
            "Question: Find leads with budget above 1 million\nSQL: SELECT * FROM leads WHERE (min_budget >= 1000000 OR max_budget >= 1000000);"
        ]
        
        # Run training
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(train_vanna_on_text(f"DDL Schema:\n{ddl}"))
            loop.run_until_complete(train_vanna_on_text(f"Documentation:\n{documentation}"))
            for example in sql_examples:
                loop.run_until_complete(train_vanna_on_text(example))
            
            logger.info("Vanna training completed")
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error setting up training data: {str(e)}")
        raise
