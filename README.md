# Knowladge Graph RAG

                [User App / UI]
                      |
                      | (REST / WebSocket)
                      |
        +-------------+----------------------------------------------------+
        |                    FASTAPI APPLICATION LAYER                     |
        +-------------+----------------------------------------------+-----+
                      |                                              |
                      | (Dispatches Heavy Job)                       | (Hybrid Context
                      |                                              |  Retrieval)
        +-------------+--------------+                +--------------+----------------+
        | CELERY / TEMPORAL WORKERS  |                |   RETRIEVAL ROUTING ENGINE    |
        +----------------------------+                +-------------------------------+
        | • Parse docs (Unstructured)|                | 1. Direct Qdrant Vector Match |
        | • Local NER (spaCy / GPU)  |                | 2. Direct Cypher Graph Query  |
        | • Parallel Data Chunking   |                | 3. Clean & Concatenate Arrays |
        +------+--------------+------+                +--------------+----------------+
               |              |                                      |
               | (Dense       | (Graph Triples)                      |
               |  Vectors)    |                                      | (Send final
               |              |                                      |  context)
        +------+-----+ +------+-----+                                |
        |   QDRANT   | |   NEO4J    |                         +------+-------+
        |  VECTOR DB | |            |                         |  NATIVE LLM  |
        +------------+ +------------+                         |     API      |
                                                              +--------------+

uv sync
.venv\Script\activate

uv run server.py
celery -A workers.tasks worker --loglevel=info --concurrency=1

======================================================================
.env:

# Application Config

PROJECT_NAME="Knowledge Graph RAG"
DEBUG=True

# LLM & Observability (LangSmith)

LANGCHAIN*TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="lsv2*..."
LANGCHAIN_PROJECT="kg-rag-..."

# Databases

QDRANT_HOST="localhost"
QDRANT_PORT=6333
QDRANT_COLLECTION="knowledge_chunks"

NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password123"

# Celery / Redis

CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/0"

# API Keys

GOOGLE*API_KEY="AQ..."
GROQ_API_KEY="gsk*..."
