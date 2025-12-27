"""Query logger for agent queries and responses"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from django.conf import settings
import os

logger = logging.getLogger(__name__)


class QueryLogger:
    """Logger for agent queries and responses"""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize query logger"""
        if log_file is None:
            log_dir = Path(settings.BASE_DIR) / 'logs'
            log_dir.mkdir(exist_ok=True)
            log_file = str(log_dir / 'query_log.jsonl')
        
        self.log_file = log_file
        self.ensure_log_file()
    
    def ensure_log_file(self):
        """Ensure log file and directory exist"""
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if not log_path.exists():
            log_path.touch()
    
    def log_query(
        self,
        query: str,
        response: str,
        task_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        sql_query: Optional[str] = None,
        sql_results: Optional[List[Dict]] = None,
        rag_chunks: Optional[List[Dict]] = None,
        execution_time: Optional[float] = None
    ):
        """Log a query and its response"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'response': response,
            'task_type': task_type,
            'execution_time_seconds': execution_time,
        }
        
        # Add task-specific information
        if task_type == 't2sql':
            log_entry['sql_query'] = sql_query
            if sql_results is not None:
                log_entry['sql_results_count'] = len(sql_results)
                # Store first few results as sample (to avoid huge logs)
                log_entry['sql_results_sample'] = sql_results[:5] if len(sql_results) > 5 else sql_results
                log_entry['sql_results_full_count'] = len(sql_results)
        
        elif task_type == 'rag':
            if rag_chunks is not None:
                log_entry['rag_chunks_count'] = len(rag_chunks)
                log_entry['rag_chunks'] = []
                for chunk in rag_chunks:
                    chunk_info = {
                        'content': chunk.get('content', chunk.get('text', ''))[:200] + '...' if len(str(chunk.get('content', chunk.get('text', '')))) > 200 else chunk.get('content', chunk.get('text', '')),
                        'metadata': chunk.get('metadata', {}),
                        'score': chunk.get('score', chunk.get('distance', None))
                    }
                    log_entry['rag_chunks'].append(chunk_info)
        
        # Add any additional metadata
        if metadata:
            log_entry['metadata'] = metadata
        
        # Write to log file (JSONL format - one JSON object per line)
        try:
            def json_serializer(obj):
                """JSON serializer for dates/datetimes"""
                from datetime import date, datetime
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False, default=json_serializer) + '\n')
            logger.debug(f"Logged query: {query[:50]}...")
        except Exception as e:
            logger.error(f"Error writing to log file: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent log entries"""
        try:
            logs = []
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
            return logs
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Error reading log file: {str(e)}")
            return []


# Global logger instance
_query_logger = None


def get_query_logger() -> QueryLogger:
    """Get or create global query logger instance"""
    global _query_logger
    if _query_logger is None:
        _query_logger = QueryLogger()
    return _query_logger

