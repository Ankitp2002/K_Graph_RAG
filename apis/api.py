from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from services.llm_manager import LLMManager
from .dependency import get_app_state
import uuid
from services.retrieval_engine import RetrievalRoutingEngine
from .schemas import QueryRequest, QueryResponse, IngestionResponse
from workers.tasks import process_and_ingest_document

router = APIRouter()


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...), app_state=Depends(get_app_state)
):
    """Dispatches Heavy Ingestion Job to Celery Workers"""
    try:
        content = (await file.read()).decode("utf-8")
        doc_id = str(uuid.uuid4())

        # Async dispatch to Celery
        nlp = app_state.nlp_model
        embeddings_model = app_state.embedding_model
        qdrant_client = app_state.qdrant_client
        neo4j_driver = app_state.neo4j_driver

        task = process_and_ingest_document.delay(
            content, doc_id, nlp, embeddings_model, qdrant_client, neo4j_driver
        )

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
