"""
PDF processing utilities for extracting text from brochure PDFs
"""
import pdfplumber
from pypdf import PdfReader
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Process PDF files to extract text content"""
    
    def __init__(self):
        pass
    
    def extract_text(self, pdf_path: str, method: str = "pdfplumber") -> str:
        """
        Extract text from PDF file
        
        Args:
            pdf_path: Path to PDF file
            method: Extraction method ('pdfplumber' or 'pypdf')
        
        Returns:
            Extracted text content
        """
        try:
            if method == "pdfplumber":
                return self._extract_with_pdfplumber(pdf_path)
            else:
                return self._extract_with_pypdf(pdf_path)
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            raise
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber (better for complex layouts)"""
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n\n".join(text_parts)
    
    def _extract_with_pypdf(self, pdf_path: str) -> str:
        """Extract text using pypdf (faster, simpler)"""
        reader = PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
    
    def extract_metadata(self, pdf_path: str) -> dict:
        """
        Extract metadata from PDF
        
        Returns:
            Dictionary with PDF metadata
        """
        try:
            reader = PdfReader(pdf_path)
            metadata = reader.metadata or {}
            return {
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "pages": len(reader.pages),
                "filename": pdf_path.split("/")[-1]
            }
        except Exception as e:
            logger.error(f"Error extracting metadata from {pdf_path}: {str(e)}")
            return {"filename": pdf_path.split("/")[-1]}

