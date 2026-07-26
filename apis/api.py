from fastapi import APIRouter, HTTPException, UploadFile, File
import uuid

from .schemas import QueryRequest, QueryResponse, IngestionResponse
from workers.tasks import process_and_ingest_document
from services.retrieval_engine import RetrievalRoutingEngine

router = APIRouter()


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_document(file: UploadFile = File(...)):
    """Dispatches Heavy Ingestion Job to Celery Workers"""
    try:
        content = (await file.read()).decode("utf-8")
        doc_id = str(uuid.uuid4())

        # Async dispatch to Celery
        task = process_and_ingest_document.delay(content, doc_id)

        return IngestionResponse(
            task_id=task.id, message="Document ingestion job dispatched successfully."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Executes Hybrid Context Retrieval across Qdrant & Neo4j"""
    try:
        result = RetrievalRoutingEngine.run_pipeline(request.question)
        return QueryResponse(
            question=request.question,
            answer=result["answer"],
            vector_context=result["vector_context"],
            graph_context=result["graph_context"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
