"""Vanna setup for Text-to-SQL"""
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
        return User(id="default", email="user@example.com", group_memberships=["user", "admin"])


def get_vanna_agent():
    """Get or create Vanna agent instance"""
    global _vanna_agent
    
    if _vanna_agent is None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in settings")
        
        chromadb_path = os.path.join(settings.CHROMADB_PATH, "vanna")
        os.makedirs(chromadb_path, exist_ok=True)
        
        llm_service = OpenAILlmService(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY
        )
        
        db_path = str(connection.settings_dict.get('NAME', ''))
        if not db_path:
            raise ValueError("Database path not found in Django settings")
        
        sql_runner = SqliteRunner(database_path=db_path)
        db_tool = RunSqlTool(sql_runner=sql_runner)
        
        model_name = getattr(settings, 'VANNA_MODEL', 'agent_vanna')
        agent_memory = ChromaAgentMemory(
            collection_name=f"{model_name}_training",
            persist_directory=chromadb_path
        )
        
        tools = ToolRegistry()
        tools.register_local_tool(db_tool, access_groups=['admin', 'user'])
        tools.register_local_tool(SaveTextMemoryTool(), access_groups=['admin', 'user'])
        
        user_resolver = SimpleUserResolver()
        
        _vanna_agent = Agent(
            llm_service=llm_service,
            tool_registry=tools,
            user_resolver=user_resolver,
            agent_memory=agent_memory
        )
        
        logger.info(f"Vanna 2.0 agent initialized")
    
    return _vanna_agent


async def ask_vanna(question: str) -> str:
    """Ask Vanna a question and get a natural language answer"""
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
    Generate SQL from natural language question using Vanna agent
    This is a fallback - primary method is intelligent column detection
    
    Args:
        question: Natural language question
        
    Returns:
        Generated SQL query or None if extraction fails
    """
    try:
        agent = get_vanna_agent()
        request_context = RequestContext()
        
        # Get SQL by asking agent and extracting from code blocks or text
        sql_query = None
        all_text = []
        
        async for component in agent.send_message(request_context=request_context, message=question):
            rich_comp = getattr(component, 'rich_component', None)
            simple_comp = getattr(component, 'simple_component', None)
            
            # Extract from rich component
            if rich_comp:
                comp_type = getattr(rich_comp, 'type', None)
                comp_data = getattr(rich_comp, 'data', {})
                
                # Look for code_block with SQL
                if comp_type == 'code_block':
                    code = comp_data.get('code', comp_data.get('content', ''))
                    if code and ('SELECT' in code.upper() or 'FROM' in code.upper()):
                        sql_query = code.strip()
                        logger.info(f"Found SQL in code_block: {sql_query}")
                        break
                elif comp_type == 'text':
                    text = comp_data.get('text', comp_data.get('content', ''))
                    if text:
                        all_text.append(str(text))
            
            # Extract from simple component
            if simple_comp:
                if isinstance(simple_comp, str):
                    all_text.append(simple_comp)
                elif hasattr(simple_comp, 'text'):
                    all_text.append(str(simple_comp.text))
        
        # If no SQL found in code blocks, try to extract from text
        if not sql_query:
            import re
            for text in all_text:
                # Look for SQL patterns in text
                sql_patterns = [
                    r'SELECT\s+.*?\s+FROM\s+\w+.*?;',  # SELECT ... FROM ... ;
                    r'SELECT\s+.*?\s+FROM\s+\w+',      # SELECT ... FROM ... (no semicolon)
                ]
                for pattern in sql_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
                    if matches:
                        sql_query = matches[0].strip()
                        # Clean up SQL - remove markdown code blocks if present
                        sql_query = re.sub(r'^```sql\s*', '', sql_query, flags=re.IGNORECASE)
                        sql_query = re.sub(r'^```\s*', '', sql_query)
                        sql_query = re.sub(r'\s*```\s*$', '', sql_query)
                        sql_query = sql_query.strip()
                        if sql_query and not sql_query.endswith(';'):
                            sql_query += ';'
                        logger.info(f"Extracted SQL from text: {sql_query}")
                        break
                if sql_query:
                    break
        
        return sql_query
    except Exception as e:
        logger.warning(f"Vanna agent SQL generation failed: {str(e)}")
        return None


def _get_table_schema():
    """Get the actual table schema from the database"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(leads)")
            columns = cursor.fetchall()
            # columns is a list of tuples: (cid, name, type, notnull, default_value, pk)
            schema = {
                'columns': [col[1] for col in columns],  # Column names
                'column_info': {col[1]: {'type': col[2], 'notnull': col[3]} for col in columns}
            }
            return schema
    except Exception as e:
        logger.error(f"Error getting table schema: {str(e)}")
        # Fallback to known schema
        return {
            'columns': ['id', 'lead_id', 'lead_name', 'email', 'country_code', 'phone', 
                       'project_name', 'unit_type', 'min_budget', 'max_budget', 
                       'lead_status', 'last_conversation_date', 'last_conversation_summary',
                       'created_at', 'updated_at'],
            'column_info': {}
        }


def _detect_columns_from_query(question: str, schema: dict) -> list:
    """
    Detect which columns are mentioned in the query by matching against schema
    
    Args:
        question: Natural language question
        schema: Table schema dictionary
        
    Returns:
        List of column names to select
    """
    question_lower = question.lower()
    detected_columns = []
    all_columns = schema['columns']
    
    # Mapping of common terms to column names
    column_mappings = {
        # Direct matches
        'lead name': 'lead_name',
        'lead_name': 'lead_name',
        'name': 'lead_name',
        'project': 'project_name',
        'project_name': 'project_name',
        'project name': 'project_name',
        'works in': 'project_name',
        'which project': 'project_name',
        'unit type': 'unit_type',
        'unit_type': 'unit_type',
        'bed': 'unit_type',
        'bedroom': 'unit_type',
        'budget': ['min_budget', 'max_budget'],
        'min budget': 'min_budget',
        'max budget': 'max_budget',
        'min_budget': 'min_budget',
        'max_budget': 'max_budget',
        'conversation': ['last_conversation_summary', 'last_conversation_date'],
        'last conversation': ['last_conversation_summary', 'last_conversation_date'],
        'conversation summary': 'last_conversation_summary',
        'conversation date': 'last_conversation_date',
        'status': 'lead_status',
        'lead status': 'lead_status',
        'email': 'email',
        'phone': 'phone',
        'count': 'COUNT(*)',
        'how many': 'COUNT(*)',
    }
    
    # Check for count queries first
    if 'count' in question_lower or 'how many' in question_lower:
        return ['COUNT(*)']
    
    # Check each mapping
    for term, column in column_mappings.items():
        if term in question_lower:
            if isinstance(column, list):
                detected_columns.extend(column)
            else:
                detected_columns.append(column)
    
    # Also check for direct column name mentions (case-insensitive)
    for col in all_columns:
        # Check if column name (with underscores replaced) appears in query
        col_variations = [
            col.lower(),
            col.lower().replace('_', ' '),
            col.lower().replace('_', ''),
        ]
        for variation in col_variations:
            if variation in question_lower and col not in detected_columns:
                detected_columns.append(col)
                break
    
    # Remove duplicates while preserving order
    seen = set()
    unique_columns = []
    for col in detected_columns:
        if col not in seen:
            seen.add(col)
            unique_columns.append(col)
    
    # If no columns detected, return common ones or all
    if not unique_columns:
        # Default: return commonly requested columns
        if 'lead name' in question_lower or any(name_word in question_lower for name_word in ['name', 'who']):
            unique_columns.append('lead_name')
        if 'project' in question_lower:
            unique_columns.append('project_name')
        if 'conversation' in question_lower:
            unique_columns.extend(['last_conversation_summary', 'last_conversation_date'])
        if 'budget' in question_lower:
            unique_columns.extend(['min_budget', 'max_budget'])
        
        # If still nothing, return all columns
        if not unique_columns:
            unique_columns = ['*']
    
    return unique_columns


def _build_where_clause(question: str, schema: dict) -> str:
    """
    Build WHERE clause from query by detecting filters
    
    Args:
        question: Natural language question
        schema: Table schema dictionary
        
    Returns:
        WHERE clause string (without WHERE keyword)
    """
    question_lower = question.lower()
    conditions = []
    
    # Project name detection
    project_match = None
    if 'sobha' in question_lower and 'waves' in question_lower:
        project_match = 'Sobha Waves'
    elif 'lumina' in question_lower and 'grand' in question_lower:
        project_match = 'Lumina Grand'
    elif 'beachgate' in question_lower:
        project_match = 'Beachgate by Address'
    elif 'damac' in question_lower:
        project_match = 'DAMAC Bay by Cavalli'
    elif 'godrej' in question_lower:
        project_match = 'Godrej Vistas'
    
    if project_match:
        conditions.append(f"project_name = '{project_match}'")
    
    # Unit type detection
    unit_type_match = None
    if '1 bed' in question_lower or '1bed' in question_lower or 'one bed' in question_lower:
        unit_type_match = '1 Bed'
    elif '2 bed' in question_lower or '2bed' in question_lower or 'two bed' in question_lower:
        if 'study' in question_lower:
            unit_type_match = '2 bed w study'
        else:
            unit_type_match = '2 Bed'
    elif '3 bed' in question_lower or '3bed' in question_lower or 'three bed' in question_lower:
        unit_type_match = '3 bed'
    
    if unit_type_match:
        conditions.append(f"unit_type = '{unit_type_match}'")
    
    # Lead name detection (for person names)
    import re
    lead_name_match = None
    # Pattern: Look for capitalized words that might be names
    name_patterns = [
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',  # "Rajan MK" or "John Smith"
    ]
    for pattern in name_patterns:
        matches = re.findall(pattern, question)
        if matches:
            potential_name = matches[0].strip()
            if len(potential_name.split()) <= 3:
                # Check if it's not a project name
                if not any(proj.lower() in potential_name.lower() for proj in ['Lumina', 'Sobha', 'Beachgate', 'DAMAC', 'Godrej']):
                    lead_name_match = potential_name
                    break
    
    # Also check for "works in" or "for" patterns
    if not lead_name_match:
        works_pattern = r'(\w+(?:\s+\w+){0,2})\s+(?:works|work|for|his|her)'
        works_match = re.search(works_pattern, question, re.IGNORECASE)
        if works_match:
            potential_name = works_match.group(1).strip()
            if len(potential_name.split()) <= 3 and potential_name[0].isupper():
                lead_name_match = potential_name
    
    if lead_name_match:
        conditions.append(f"lead_name LIKE '%{lead_name_match}%'")
    
    # Budget condition detection
    # Pattern for numbers - match longest number first (greedy)
    # This pattern matches: 1000000, 1,000,000, 1000000.50, etc.
    number_pattern = r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.?\d*)\b'
    
    budget_condition_added = False
    
    # Check for minimum budget conditions
    if 'min budget' in question_lower or 'minimum budget' in question_lower:
        budget_condition_added = True
        # Look for comparison operators
        if re.search(r'less\s+(?:than|then)', question_lower):
            # Extract all numbers and take the largest (most likely the budget value)
            numbers = re.findall(number_pattern, question)
            if numbers:
                # Convert to int/float and find the largest number (the budget value)
                numeric_values = [float(n.replace(',', '')) for n in numbers]
                value = str(int(max(numeric_values)))  # Use largest number
                conditions.append(f"min_budget < {value}")
        elif re.search(r'greater\s+(?:than|then)|more\s+than|above', question_lower):
            numbers = re.findall(number_pattern, question)
            if numbers:
                numeric_values = [float(n.replace(',', '')) for n in numbers]
                value = str(int(max(numeric_values)))
                conditions.append(f"min_budget > {value}")
        elif re.search(r'equal\s+to|exactly', question_lower):
            numbers = re.findall(number_pattern, question)
            if numbers:
                numeric_values = [float(n.replace(',', '')) for n in numbers]
                value = str(int(max(numeric_values)))
                conditions.append(f"min_budget = {value}")
        elif re.search(r'between', question_lower):
            numbers = re.findall(number_pattern, question)
            if len(numbers) >= 2:
                numeric_values = sorted([float(n.replace(',', '')) for n in numbers])
                value1 = str(int(numeric_values[0]))
                value2 = str(int(numeric_values[-1]))
                conditions.append(f"min_budget BETWEEN {value1} AND {value2}")
    
    # Check for maximum budget conditions
    elif 'max budget' in question_lower or 'maximum budget' in question_lower:
        budget_condition_added = True
        if re.search(r'less\s+(?:than|then)', question_lower):
            numbers = re.findall(number_pattern, question)
            if numbers:
                numeric_values = [float(n.replace(',', '')) for n in numbers]
                value = str(int(max(numeric_values)))
                conditions.append(f"max_budget < {value}")
        elif re.search(r'greater\s+(?:than|then)|more\s+than|above', question_lower):
            numbers = re.findall(number_pattern, question)
            if numbers:
                numeric_values = [float(n.replace(',', '')) for n in numbers]
                value = str(int(max(numeric_values)))
                conditions.append(f"max_budget > {value}")
    
    # Check for general budget conditions (without min/max specified) - only if not already added
    if not budget_condition_added and 'budget' in question_lower:
        # Look for patterns like "budget less than", "budget above", etc.
        if re.search(r'budget\s+(?:less\s+(?:than|then)|below)', question_lower):
            numbers = re.findall(number_pattern, question)
            if numbers:
                numeric_values = [float(n.replace(',', '')) for n in numbers]
                value = str(int(max(numeric_values)))
                # Check both min and max budget
                conditions.append(f"(min_budget < {value} OR max_budget < {value})")
        elif re.search(r'budget\s+(?:greater\s+(?:than|then)|more\s+than|above)', question_lower):
            numbers = re.findall(number_pattern, question)
            if numbers:
                numeric_values = [float(n.replace(',', '')) for n in numbers]
                value = str(int(max(numeric_values)))
                # Check both min and max budget
                conditions.append(f"(min_budget >= {value} OR max_budget >= {value})")
    
    if conditions:
        return " AND ".join(conditions)
    return ""


def generate_sql(question: str) -> str:
    """
    Generate SQL from natural language question using intelligent column detection
    Primary method: Schema-based column detection
    Fallback: Vanna agent
    """
    # Primary method: Build SQL intelligently from schema
    try:
        schema = _get_table_schema()
        columns = _detect_columns_from_query(question, schema)
        where_clause = _build_where_clause(question, schema)
        
        # If filtering by lead_name, ensure lead_name is in SELECT for response generation
        if where_clause and 'lead_name LIKE' in where_clause and 'lead_name' not in columns and 'COUNT(*)' not in columns:
            # Add lead_name to columns if not already present
            if columns == ['*']:
                # If selecting all, no need to add
                pass
            else:
                columns.insert(0, 'lead_name')  # Add at beginning for readability
        
        # Build SELECT clause
        if 'COUNT(*)' in columns:
            select_clause = "SELECT COUNT(*) as count"
        elif columns == ['*']:
            select_clause = "SELECT *"
        else:
            # Remove duplicates and maintain order
            unique_columns = []
            seen = set()
            for col in columns:
                if col not in seen:
                    seen.add(col)
                    unique_columns.append(col)
            select_clause = f"SELECT {', '.join(unique_columns)}"
        
        # Build WHERE clause
        where_str = ""
        if where_clause:
            where_str = f" WHERE {where_clause}"
        
        # Build SQL
        sql = f"{select_clause} FROM leads{where_str}"
        
        # Add LIMIT if selecting all columns (and not a count query)
        if columns == ['*'] and 'limit' not in question.lower() and 'COUNT(*)' not in columns:
            sql += " LIMIT 50"
        
        sql += ";"
        
        logger.info(f"Intelligently constructed SQL: {sql}")
        return sql
    except Exception as e:
        logger.error(f"Error constructing SQL from schema: {str(e)}")
        # Fallback: Try Vanna agent
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                sql = loop.run_until_complete(generate_sql_vanna(question))
                if sql and 'SELECT' in sql.upper():
                    logger.info(f"Using Vanna-generated SQL: {sql}")
                    return sql
            finally:
                loop.close()
        except Exception as e2:
            logger.error(f"Vanna fallback also failed: {str(e2)}")
        
        # Ultimate fallback
        logger.warning("Using ultimate fallback SQL")
        return "SELECT * FROM leads LIMIT 10;"


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
        DATABASE SCHEMA AND USAGE GUIDE
        
        CRITICAL INFORMATION:
        - There is ONLY ONE table in this database: 'leads'
        - There is NO table called 'projects', 'project', 'customers', or 'clients'
        - The 'project_name' is a COLUMN in the 'leads' table, NOT a separate table
        - Always query FROM 'leads' table, never from 'projects' or any other table name
        
        TABLE STRUCTURE: leads
        This table stores CRM lead information for real estate sales.
        
        COLUMNS AND THEIR MEANINGS:
        1. id: Primary key (auto-increment integer)
        2. lead_id: Unique identifier for each lead (VARCHAR, e.g., 'L1', 'L2', 'L123')
        3. lead_name: Full name of the lead/person (VARCHAR, e.g., 'Rajan MK', 'Aminah Ahmad')
        4. email: Email address of the lead (VARCHAR)
        5. country_code: Country code for phone (VARCHAR, e.g., '+971')
        6. phone: Phone number (VARCHAR)
        7. project_name: Property project name (VARCHAR, indexed)
           Common values: 'Lumina Grand', 'Sobha Waves', 'Beachgate by Address', 
           'DAMAC Bay by Cavalli', 'Godrej Vistas', 'Altura'
        8. unit_type: Type of unit/bedroom (VARCHAR, indexed)
           Common values: '1 Bed', '2 Bed', '3 bed', '2 bed w study'
        9. min_budget: Minimum budget in local currency (DECIMAL, can be NULL)
        10. max_budget: Maximum budget in local currency (DECIMAL, can be NULL)
        11. lead_status: Current status of the lead (VARCHAR, indexed)
            Values: 'not_connected', 'connected', 'visit_scheduled', 
            'visit_done_not_purchased', 'purchased', 'not_interested'
        12. last_conversation_date: Date of the last conversation (DATE, can be NULL)
        13. last_conversation_summary: Text summary of the last conversation (TEXT)
        14. created_at: Timestamp when record was created (DATETIME)
        15. updated_at: Timestamp when record was last updated (DATETIME)
        
        QUERY PATTERNS AND BEST PRACTICES:
        
        1. PROJECT NAME QUERIES:
           - Always use exact project name matching: WHERE project_name = 'Lumina Grand'
           - Project names are case-sensitive, use exact spelling
           - Example: "Show leads from Sobha Waves" → WHERE project_name = 'Sobha Waves'
        
        2. LEAD NAME QUERIES:
           - Use LIKE for partial name matching: WHERE lead_name LIKE '%Rajan%'
           - For exact match: WHERE lead_name = 'Rajan MK'
           - When filtering by lead name, always include lead_name in SELECT clause
        
        3. UNIT TYPE QUERIES:
           - Match exact unit type strings: WHERE unit_type = '1 Bed'
           - Common values: '1 Bed', '2 Bed', '3 bed', '2 bed w study'
           - Note: '1 Bed' has capital B, '3 bed' has lowercase b
        
        4. BUDGET QUERIES:
           - For budget ranges, check both min_budget and max_budget
           - Budget values are stored as DECIMAL numbers (no commas)
           - Example: "budget above 1 million" → WHERE (min_budget >= 1000000 OR max_budget >= 1000000)
           - Example: "budget less than 5000000" → WHERE (min_budget < 5000000 OR max_budget < 5000000)
           - When querying for specific budget, include both min_budget and max_budget in SELECT
        
        5. COUNT QUERIES:
           - Use COUNT(*) for counting records
           - Alias as 'count' or 'total_leads' for clarity
           - Example: SELECT COUNT(*) as count FROM leads WHERE project_name = 'Lumina Grand'
        
        6. MULTIPLE CONDITIONS:
           - Use AND to combine conditions: WHERE project_name = 'X' AND unit_type = 'Y'
           - Use OR for alternative conditions: WHERE project_name = 'X' OR project_name = 'Y'
        
        7. CONVERSATION QUERIES:
           - Use last_conversation_summary for conversation content
           - Use last_conversation_date for date filtering
           - When asking about conversations, include both columns in SELECT
        
        8. COLUMN SELECTION:
           - When filtering by a column, include that column in SELECT for clarity
           - Example: If filtering by lead_name, SELECT lead_name, project_name, ...
           - Use SELECT * only when user asks for "all" or "everything"
           - For count queries, use SELECT COUNT(*) as count
        
        COMMON MISTAKES TO AVOID:
        - DO NOT use table name 'projects' - it doesn't exist
        - DO NOT create JOINs - there's only one table
        - DO NOT use table aliases unnecessarily
        - DO use exact project name strings (case-sensitive)
        - DO include relevant columns in SELECT when filtering by them
        """
        
        # SQL examples - Comprehensive examples covering all query types
        sql_examples = [
            # Basic project queries
            "Question: Show me all leads from Lumina Grand\nSQL: SELECT * FROM leads WHERE project_name = 'Lumina Grand';",
            "Question: Get leads from Sobha Waves\nSQL: SELECT * FROM leads WHERE project_name = 'Sobha Waves';",
            "Question: What leads are in Beachgate by Address?\nSQL: SELECT * FROM leads WHERE project_name = 'Beachgate by Address';",
            
            # Lead name queries
            "Question: What is the lead name for Sobha Waves?\nSQL: SELECT lead_name FROM leads WHERE project_name = 'Sobha Waves';",
            "Question: Find lead name for Lumina Grand\nSQL: SELECT lead_name FROM leads WHERE project_name = 'Lumina Grand';",
            "Question: Who are the leads in Sobha Waves?\nSQL: SELECT lead_name FROM leads WHERE project_name = 'Sobha Waves';",
            "Question: Show me lead names from Lumina Grand\nSQL: SELECT lead_name FROM leads WHERE project_name = 'Lumina Grand';",
            
            # Budget queries
            "Question: What is the budget for Sobha Waves?\nSQL: SELECT lead_name, min_budget, max_budget FROM leads WHERE project_name = 'Sobha Waves';",
            "Question: Get lead name and budget details for Sobha Waves\nSQL: SELECT lead_name, min_budget, max_budget FROM leads WHERE project_name = 'Sobha Waves';",
            "Question: Show me budget for Lumina Grand leads\nSQL: SELECT lead_name, min_budget, max_budget FROM leads WHERE project_name = 'Lumina Grand';",
            "Question: Find leads with budget above 1 million\nSQL: SELECT * FROM leads WHERE (min_budget >= 1000000 OR max_budget >= 1000000);",
            "Question: Leads with budget less than 5000000\nSQL: SELECT * FROM leads WHERE (min_budget < 5000000 OR max_budget < 5000000);",
            
            # Unit type queries
            "Question: How many leads have unit type 1 bed?\nSQL: SELECT COUNT(*) as count FROM leads WHERE unit_type = '1 Bed';",
            "Question: Show leads with unit type 1 bed from Lumina Grand\nSQL: SELECT * FROM leads WHERE project_name = 'Lumina Grand' AND unit_type = '1 Bed';",
            "Question: What is lead name for Lumina Grand, and how many have unit type 1 bed?\nSQL: SELECT lead_name, COUNT(*) as count FROM leads WHERE project_name = 'Lumina Grand' AND unit_type = '1 Bed' GROUP BY lead_name;",
            "Question: Find leads with 2 bed w study\nSQL: SELECT * FROM leads WHERE unit_type = '2 bed w study';",
            "Question: Show me 3 bed units from Sobha Waves\nSQL: SELECT * FROM leads WHERE project_name = 'Sobha Waves' AND unit_type = '3 bed';",
            
            # Count queries
            "Question: How many leads are there?\nSQL: SELECT COUNT(*) as count FROM leads;",
            "Question: Count all leads\nSQL: SELECT COUNT(*) as count FROM leads;",
            "Question: How many leads are in Lumina Grand?\nSQL: SELECT COUNT(*) as count FROM leads WHERE project_name = 'Lumina Grand';",
            "Question: Count leads by project name\nSQL: SELECT project_name, COUNT(*) as count FROM leads GROUP BY project_name;",
            
            # Person/project relationship queries
            "Question: Rajan MK works in which project?\nSQL: SELECT project_name FROM leads WHERE lead_name LIKE '%Rajan MK%';",
            "Question: Which project does Rajan MK work in?\nSQL: SELECT project_name FROM leads WHERE lead_name LIKE '%Rajan MK%';",
            "Question: What project is Rajan MK in?\nSQL: SELECT project_name FROM leads WHERE lead_name LIKE '%Rajan MK%';",
            
            # Conversation queries
            "Question: What are the last conversations for Rajan MK's leads?\nSQL: SELECT lead_name, project_name, last_conversation_date, last_conversation_summary FROM leads WHERE lead_name LIKE '%Rajan MK%';",
            "Question: Show me last conversation for leads in Sobha Waves\nSQL: SELECT lead_name, last_conversation_date, last_conversation_summary FROM leads WHERE project_name = 'Sobha Waves';",
            "Question: What was the last conversation for Rajan MK?\nSQL: SELECT last_conversation_date, last_conversation_summary FROM leads WHERE lead_name LIKE '%Rajan MK%';",
            
            # Combined queries
            "Question: Rajan MK works in which project, what are few last conversations for his leads?\nSQL: SELECT lead_name, project_name, last_conversation_date, last_conversation_summary FROM leads WHERE lead_name LIKE '%Rajan MK%';",
            "Question: What is lead name for Sobha Waves, and what was its budget details?\nSQL: SELECT lead_name, min_budget, max_budget FROM leads WHERE project_name = 'Sobha Waves';",
            "Question: Show me lead names and budgets for Lumina Grand with unit type 1 bed\nSQL: SELECT lead_name, min_budget, max_budget FROM leads WHERE project_name = 'Lumina Grand' AND unit_type = '1 Bed';",
            
            # Status queries
            "Question: Show me all purchased leads\nSQL: SELECT * FROM leads WHERE lead_status = 'purchased';",
            "Question: How many connected leads are there?\nSQL: SELECT COUNT(*) as count FROM leads WHERE lead_status = 'connected';",
            
            # General queries
            "Question: Show me all leads\nSQL: SELECT * FROM leads LIMIT 50;",
            "Question: List all leads\nSQL: SELECT * FROM leads LIMIT 50;",
            "Question: Get all lead information\nSQL: SELECT * FROM leads LIMIT 50;",
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
