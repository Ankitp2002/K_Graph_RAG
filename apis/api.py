from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from services.llm_manager import LLMManager
from .dependency import get_app_state
import uuid
from services.retrieval_engine import RetrievalRoutingEngine
from .schemas import QueryRequest, QueryResponse, IngestionResponse
from workers.tasks import process_and_ingest_document
import shutil
import os
from constant import UPLOAD_DIR

router = APIRouter()


@router.post("/ingest", response_model=IngestionResponse)
async def singal_file_base_ingest(
    file: UploadFile = File(...), app_state=Depends(get_app_state)
):
    """Dispatches Heavy Ingestion Job to Celery Workers"""
    try:
        file_id = str(uuid.uuid4())
        extension = os.path.splitext(file.filename)[1].lower()
        saved_filename = f"{file_id}.{extension}"
        file_path = os.path.join(UPLOAD_DIR, saved_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        task = process_and_ingest_document(file_path, extension, file_id)

        return IngestionResponse(
            task_id=task.id, message="Document ingestion job dispatched successfully."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest, app_state=Depends(get_app_state)):
    """Executes Hybrid Context Retrieval across Qdrant & Neo4j"""
    try:
        retrievel_eng: RetrievalRoutingEngine = app_state.retrieval_engine
        llm_manager: LLMManager = app_state.llm_manager
        retrievel_eng.llm = llm_manager.get_client("llm_gpt_oss_120")

        result = retrievel_eng.run_pipeline(request.question)
        return QueryResponse(
            question=request.question,
            answer=result["answer"],
            vector_context=result["vector_context"],
            graph_context=result["graph_context"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
