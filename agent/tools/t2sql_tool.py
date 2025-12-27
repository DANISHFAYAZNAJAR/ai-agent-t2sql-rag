"""Text-to-SQL tool using Vanna"""
from typing import Dict, Any
import logging
from vanna_config.setup import ask, generate_sql, run_sql, setup_training_data, get_vanna_agent

logger = logging.getLogger(__name__)

_training_done = False


def _ensure_trained():
    """Ensure Vanna is trained"""
    global _training_done
    if not _training_done:
        try:
            logger.info("Training Vanna on database schema...")
            setup_training_data()
            _training_done = True
            logger.info("Vanna training completed successfully")
        except Exception as e:
            logger.error(f"Vanna training failed: {str(e)}")


class T2SQLTool:
    """Tool for executing Text-to-SQL queries using Vanna"""
    
    def __init__(self):
        _ensure_trained()
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Execute a Text-to-SQL query"""
        _ensure_trained()
        
        try:
            sql = generate_sql(query)
            logger.info(f"Generated SQL: {sql}")
            
            results = run_sql(sql)
            logger.info(f"SQL executed, got {len(results)} results")
            
            response = self._generate_response_from_results(query, results, sql)
            
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
    
    def _generate_response_from_results(self, query: str, results: list, sql: str) -> str:
        """Generate natural language response from SQL results"""
        if not results:
            return "Query executed successfully, but no results were returned."
        
        query_lower = query.lower()
        
        if 'lead name' in query_lower and ('how many' in query_lower or 'count' in query_lower):
            if results and 'lead_name' in results[0]:
                count = len(results)
                names = [r.get('lead_name', 'N/A') for r in results]
                response = f"Found {count} leads for this query:\n" + "\n".join([f"- {name}" for name in names])
                return response
            elif results and 'count' in results[0]:
                count = results[0].get('count', 0)
                return f"There are {count} leads matching your criteria. (To see the lead names, please ask for 'lead names' separately.)"
        if 'count' in query_lower or 'how many' in query_lower:
            if len(results) == 1:
                count = results[0].get('total_leads') or results[0].get('count') or results[0].get('lead_count')
                if count is not None:
                    if 'unit type' in query_lower or 'unit_type' in query_lower:
                        unit_type = None
                        if '1 bed' in query_lower:
                            unit_type = '1 Bed'
                        elif '2 bed' in query_lower:
                            unit_type = '2 Bed'
                        elif '3 bed' in query_lower:
                            unit_type = '3 bed'
                        
                        project = None
                        if 'lumina' in query_lower:
                            project = 'Lumina Grand'
                        elif 'sobha' in query_lower:
                            project = 'Sobha Waves'
                        
                        if project and unit_type:
                            return f"There are {count} leads for {project} with unit type {unit_type}."
                        elif unit_type:
                            return f"There are {count} leads with unit type {unit_type}."
                        elif project:
                            return f"There are {count} leads for {project}."
                    return f"There are {count} leads in the database."
        
        if 'sobha' in query_lower or 'lumina' in query_lower or 'project' in query_lower:
            if 'budget' in query_lower and 'lead name' in query_lower:
                if len(results) > 1:
                    response_parts = [f"Found {len(results)} leads for this project:\n"]
                    for r in results[:10]:
                        name = r.get('lead_name', 'N/A')
                        min_b = r.get('min_budget')
                        max_b = r.get('max_budget')
                        budget_str = ""
                        if min_b and max_b:
                            budget_str = f"Budget: {min_b:,.0f} - {max_b:,.0f}"
                        elif min_b:
                            budget_str = f"Min budget: {min_b:,.0f}"
                        elif max_b:
                            budget_str = f"Max budget: {max_b:,.0f}"
                        else:
                            budget_str = "Budget: Not specified"
                        response_parts.append(f"- {name}: {budget_str}")
                    if len(results) > 10:
                        response_parts.append(f"\n... and {len(results) - 10} more leads")
                    return "\n".join(response_parts)
                elif len(results) == 1:
                    r = results[0]
                    name = r.get('lead_name', 'N/A')
                    min_b = r.get('min_budget')
                    max_b = r.get('max_budget')
                    if min_b and max_b:
                        return f"Lead name: {name}\nBudget: {min_b:,.0f} - {max_b:,.0f}"
                    elif min_b:
                        return f"Lead name: {name}\nMin budget: {min_b:,.0f}"
                    elif max_b:
                        return f"Lead name: {name}\nMax budget: {max_b:,.0f}"
                    else:
                        return f"Lead name: {name}\nBudget: Not specified"
        
        # Handle queries about specific person's project and conversations
        if 'works' in query_lower or ('which project' in query_lower and 'conversation' in query_lower):
            if results:
                response_parts = []
                # Group by lead name if multiple results
                if len(results) > 1:
                    response_parts.append(f"Found {len(results)} leads:\n")
                    for r in results[:10]:  # Limit to 10
                        name = r.get('lead_name', 'N/A')
                        project = r.get('project_name', 'N/A')
                        conv = r.get('last_conversation_summary', '')
                        conv_date = r.get('last_conversation_date', '')
                        
                        response_parts.append(f"\n{name}:")
                        response_parts.append(f"  Project: {project}")
                        if conv:
                            date_str = f" ({conv_date})" if conv_date else ""
                            response_parts.append(f"  Last Conversation{date_str}: {conv}")
                        else:
                            response_parts.append(f"  Last Conversation: No conversation recorded")
                    if len(results) > 10:
                        response_parts.append(f"\n... and {len(results) - 10} more leads")
                else:
                    r = results[0]
                    name = r.get('lead_name', 'N/A')
                    project = r.get('project_name', 'N/A')
                    conv = r.get('last_conversation_summary', '')
                    conv_date = r.get('last_conversation_date', '')
                    
                    response_parts.append(f"{name} works in: {project}")
                    if conv:
                        date_str = f" ({conv_date})" if conv_date else ""
                        response_parts.append(f"\nLast Conversation{date_str}: {conv}")
                    else:
                        response_parts.append(f"\nLast Conversation: No conversation recorded")
                
                return "\n".join(response_parts)
        
        if 'lead name' in query_lower:
            if len(results) == 1:
                name = results[0].get('lead_name', 'N/A')
                return f"The lead name is: {name}"
            else:
                names = [r.get('lead_name', 'N/A') for r in results[:10]]
                return f"Found {len(results)} leads:\n" + "\n".join([f"- {name}" for name in names])
        
        if 'budget' in query_lower:
            if len(results) == 1:
                r = results[0]
                min_b = r.get('min_budget')
                max_b = r.get('max_budget')
                if min_b and max_b:
                    return f"Budget range: {min_b:,.0f} - {max_b:,.0f}"
                elif min_b:
                    return f"Minimum budget: {min_b:,.0f}"
                elif max_b:
                    return f"Maximum budget: {max_b:,.0f}"
        
        if len(results) == 1:
            return f"Query result: {results[0]}"
        else:
            return f"Found {len(results)} results matching your query."
    
    def __call__(self, query: str) -> Dict[str, Any]:
        return self.execute(query)
