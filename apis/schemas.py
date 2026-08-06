from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    vector_context: List[str]
    graph_context: List[Dict[str, Any]]


class IngestionResponse(BaseModel):
    # task_id: str
    message: str
