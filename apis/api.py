import sys

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from services.llm_manager import LLMManager
from .dependency import get_app_state
import uuid
from services.retrieval_engine import RetrievalRoutingEngine
from .schemas import QueryRequest, QueryResponse, IngestionResponse
import os
from constant import UPLOAD_DIR
import subprocess
import aiofiles

router = APIRouter()


@router.post("/health", response_model=IngestionResponse)
async def health_check(app_state=Depends(get_app_state)):
    """Health Check Endpoint"""
    try:
        return IngestionResponse(message="API is healthy and running.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest", response_model=IngestionResponse)
async def singal_file_base_ingest(
    file: UploadFile = File(...), app_state=Depends(get_app_state)
):
    """Dispatches Heavy Ingestion Job to Celery Workers"""
    try:
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

        async with aiofiles.open(file_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)

        subprocess.Popen(
            [
                "python",
                "-m",
                "workers.tasks",
                "--file-path",
                file_path,
                "--file-id",
                file_id,
            ],
            shell=sys.executable,
        )

        return IngestionResponse(
            message="Document ingestion job dispatched successfully.{} File ID: {}".format(
                file.filename, file_id
            )
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
