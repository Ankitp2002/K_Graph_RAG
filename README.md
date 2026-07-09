[User App/UI]
     │
     ▼ (REST / WebSocket)
┌────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI APPLICATION LAYER                     │
└────────────┬───────────────────────────────────────────────────▲───────┘
             │                                                   │
             │ (Dispatches Heavy Job)                            │ (Hybrid Context Retrieval)
             ▼                                                   │
┌──────────────────────────────┐       ┌─────────────────────────┴───────┐
│  CELERY / TEMPORAL WORKERS   │       │     RETRIEVAL ROUTING ENGINE    │
├──────────────────────────────┤       ├─────────────────────────────────┤
│ • Parse docs (Unstructured)  │       │ 1. Direct Qdrant Vector Match   │
│ • Local NER (spaCy / GPU)    │       │ 2. Direct Cypher Graph Query    │
│ • Parallel Data Chunking     │       │ 3. Clean & Concatenate Arrays   │
└──────┬────────────────┬──────┘       └─────────────────────────▲───────┘
       │                │                                        │
       ▼ (Dense Vectors)▼ (Graph Triples)                        │ (Send final context)
┌──────────────┐┌──────────────┐                                 ▼
│    QDRANT    ││    NEO4J /   │                       ┌──────────────────┐
│  VECTOR DB   ││   MEMGRAPH   │                       │  NATIVE LLM API  │
└──────────────┘└──────────────┘                       │ (OpenAI/Anthropic│
                                                       │   Direct SDK)    │
                                                       └──────────────────┘