"""
Text chunking utilities for splitting documents into manageable chunks
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
import logging

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Chunk documents using recursive text splitting"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ):
        """
        Initialize document chunker
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            separators: List of separators to use for splitting
        """
        if separators is None:
            separators = ["\n\n", "\n", ". ", " ", ""]
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
        )
    
    def chunk_text(self, text: str, metadata: dict = None) -> List[dict]:
        """
        Split text into chunks with metadata
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach to each chunk
        
        Returns:
            List of chunk dictionaries with 'text' and 'metadata' keys
        """
        try:
            chunks = self.splitter.split_text(text)
            
            chunk_list = []
            for i, chunk in enumerate(chunks):
                chunk_dict = {
                    "text": chunk,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
                if metadata:
                    chunk_dict["metadata"] = metadata
                else:
                    chunk_dict["metadata"] = {}
                
                chunk_list.append(chunk_dict)
            
            logger.info(f"Created {len(chunk_list)} chunks from text")
            return chunk_list
            
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}")
            raise

