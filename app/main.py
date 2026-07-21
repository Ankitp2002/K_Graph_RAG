from fastapi import FastAPI
from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Production-grade Knowledge Graph RAG with FastAPI, Qdrant, Neo4j, Celery, and LangSmith"
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "online", "system": settings.PROJECT_NAME}
