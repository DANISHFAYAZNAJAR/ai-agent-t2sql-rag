"""Document ingestion endpoints"""
from ninja import Router
from ninja import File
from ninja.files import UploadedFile
from ninja.responses import Response
from pydantic import BaseModel
from typing import Optional
from api.auth import AuthBearer
from data.ingestion.document_service import DocumentIngestionService
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

router = Router()
document_service = DocumentIngestionService()


class DocumentUploadResponse(BaseModel):
    message: str
    document_id: Optional[str] = None
    chunks_created: Optional[int] = None


@router.post("/upload", response=DocumentUploadResponse, auth=AuthBearer())
def upload_document(request, file: UploadedFile = File(...)):
    """Upload a brochure document for ingestion"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            result = document_service.ingest_document(
                file_path=tmp_file_path,
                document_metadata={"filename": file.name}
            )
            
            return DocumentUploadResponse(
                message="Document successfully ingested",
                document_id=result.get("document_id"),
                chunks_created=result.get("chunks_created", 0)
            )
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        return Response(
            DocumentUploadResponse(
                message=f"Error ingesting document: {str(e)}",
                document_id=None,
                chunks_created=0
            ),
            status=500
        )


@router.get("/list", auth=AuthBearer())
def list_documents(request):
    """List all ingested documents"""
    try:
        info = document_service.chromadb_manager.get_collection_info()
        return {
            "documents_count": info.get("count", 0),
            "collection_name": info.get("name", "brochures")
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return Response({"documents": [], "error": str(e)}, status=500)

