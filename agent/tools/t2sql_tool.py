"""
Text-to-SQL tool for LangGraph agent
Minimal implementation using Vanna directly
"""
from typing import Dict, Any
import logging
from vanna_config.setup import ask, generate_sql, run_sql, setup_training_data, get_vanna_agent

logger = logging.getLogger(__name__)

# Training flag
_training_done = False


class T2SQLTool:
    """Tool for executing Text-to-SQL queries using Vanna"""
    
    def __init__(self):
        """Initialize the T2SQL tool"""
        global _training_done
        if not _training_done:
            try:
                setup_training_data()
                _training_done = True
            except Exception as e:
                logger.warning(f"Vanna training may have failed: {str(e)}")
    
    def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute a Text-to-SQL query
        
        Args:
            query: Natural language query about the database
        
        Returns:
            Dictionary with SQL, results, and response
        """
        try:
            # Generate SQL from natural language
            sql = generate_sql(query)
            
            # Execute SQL
            results = run_sql(sql)
            
            # Get natural language answer from Vanna
            response = ask(query)
            
            # Clean response - remove tool execution noise
            if response:
                lines = [line.strip() for line in response.split('\n') 
                        if line.strip() and not any(noise in line.lower() for noise in [
                            'tool completed', 'tool failed', 'results saved', 
                            'csv', 'visualize', 'error executing', 'query_results_'
                        ])]
                response = '\n'.join(lines).strip()
            
            # If response is noisy or empty, create summary from results
            if not response or len(response) < 15:
                if results:
                    if len(results) == 1:
                        r = results[0]
                        if 'total_leads' in r:
                            response = f"There are {r['total_leads']} leads in the database."
                        elif 'lead_count' in r or 'count' in r:
                            response = f"Found {r.get('lead_count') or r.get('count')} leads."
                        else:
                            response = f"Query returned 1 result."
                    elif 'project_name' in results[0] and 'lead_count' in results[0]:
                        summary = "\n".join([f"- {r['project_name']}: {r.get('lead_count', r.get('count', 0))} leads" 
                                           for r in results])
                        response = f"Leads by project:\n{summary}"
                    else:
                        response = f"Found {len(results)} results."
                else:
                    response = "Query executed successfully, but no results were returned."
            
            return {
                "task_type": "t2sql",
                "sql": sql,
                "results": results,
                "response": response,
                "success": True
            }
        except Exception as e:
            logger.error(f"Error in T2SQL tool: {str(e)}")
            return {
                "task_type": "t2sql",
                "error": str(e),
                "success": False
            }
    
    def __call__(self, query: str) -> Dict[str, Any]:
        """Make the tool callable"""
        return self.execute(query)
