"""
Complete document ingestion service
"""
import os
import uuid
from typing import Dict, List
import logging
from .pdf_processor import PDFProcessor
from .chunking import DocumentChunker
from .embeddings import EmbeddingGenerator
from .chromadb_manager import ChromaDBManager

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Service for ingesting documents into the system"""
    
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.chunker = DocumentChunker(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.embedding_generator = EmbeddingGenerator()
        self.chromadb_manager = ChromaDBManager(collection_name="brochures")
    
    def ingest_document(self, file_path: str, document_metadata: Dict = None) -> Dict:
        """
        Ingest a document: extract, chunk, embed, and store
        
        Args:
            file_path: Path to the document file
            document_metadata: Additional metadata for the document
        
        Returns:
            Dictionary with ingestion results
        """
        try:
            logger.info(f"Starting ingestion for: {file_path}")
            
            # Step 1: Extract text from PDF
            text = self.pdf_processor.extract_text(file_path)
            if not text.strip():
                raise ValueError("No text extracted from PDF")
            
            # Step 2: Extract PDF metadata
            pdf_metadata = self.pdf_processor.extract_metadata(file_path)
            
            # Step 3: Combine metadata
            metadata = {
                **(document_metadata or {}),
                **pdf_metadata,
                "source": file_path,
                "document_id": str(uuid.uuid4())
            }
            
            # Step 4: Chunk the text
            chunks = self.chunker.chunk_text(text, metadata=metadata)
            
            # Step 5: Generate embeddings
            texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embedding_generator.generate_embeddings(texts)
            
            # Step 6: Prepare data for ChromaDB
            chunk_metadatas = [chunk.get("metadata", {}) for chunk in chunks]
            chunk_ids = [f"{metadata['document_id']}_chunk_{i}" for i in range(len(chunks))]
            
            # Step 7: Store in ChromaDB
            self.chromadb_manager.add_documents(
                texts=texts,
                embeddings=embeddings,
                metadatas=chunk_metadatas,
                ids=chunk_ids
            )
            
            result = {
                "document_id": metadata["document_id"],
                "filename": pdf_metadata.get("filename", os.path.basename(file_path)),
                "chunks_created": len(chunks),
                "status": "success"
            }
            
            logger.info(f"Successfully ingested document: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error ingesting document {file_path}: {str(e)}")
            raise
    
    def search_documents(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Search documents using semantic search
        
        Args:
            query: Search query
            n_results: Number of results to return
        
        Returns:
            List of relevant document chunks
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_generator.generate_embedding(query)
            
            # Search ChromaDB
            results = self.chromadb_manager.search(
                query_embedding=query_embedding,
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results.get("documents") and len(results["documents"]) > 0:
                for i in range(len(results["documents"][0])):
                    formatted_results.append({
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "distance": results["distances"][0][i] if results.get("distances") else None
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise

