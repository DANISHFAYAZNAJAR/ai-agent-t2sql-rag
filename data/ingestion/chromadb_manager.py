"""
ChromaDB manager for storing and retrieving document embeddings
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging
from django.conf import settings
import os

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Manage ChromaDB collections for document storage"""
    
    def __init__(self, collection_name: str = "brochures"):
        """
        Initialize ChromaDB manager
        
        Args:
            collection_name: Name of the collection to use
        """
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=settings.CHROMADB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Get or create the collection"""
        try:
            collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Brochure document embeddings"}
            )
            logger.info(f"Connected to collection: {self.collection_name}")
            return collection
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise
    
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        ids: Optional[List[str]] = None
    ):
        """
        Add documents to ChromaDB
        
        Args:
            texts: List of text chunks
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
            ids: Optional list of IDs for documents
        """
        try:
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(texts))]
            
            # ChromaDB can generate embeddings automatically, but we'll use our own
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(texts)} documents to collection")
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        """
        Search for similar documents
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter
        
        Returns:
            Dictionary with results
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
            return results
        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            raise
    
    def get_collection_info(self) -> Dict:
        """Get information about the collection"""
        try:
            count = self.collection.count()
            return {
                "name": self.collection_name,
                "count": count
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {"name": self.collection_name, "count": 0}

