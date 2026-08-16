from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    answer: Any
    vector_context: List[Any]
    graph_context: List[Any]


class IngestionResponse(BaseModel):
    # task_id: str
    message: str
