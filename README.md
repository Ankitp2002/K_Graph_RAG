        [User App / UI]
              |
              | (REST / WebSocket)
              v
+------------------------------------------------------------------+
|                    FASTAPI APPLICATION LAYER                     |
+-------------+----------------------------------------------+-----+
              |                                              |
              | (Dispatches Heavy Job)                       | (Hybrid Context
              v                                              |  Retrieval)
+----------------------------+                +--------------+----------------+
| CELERY / TEMPORAL WORKERS  |                |   RETRIEVAL ROUTING ENGINE    |
+----------------------------+                +-------------------------------+
| • Parse docs (Unstructured)|                | 1. Direct Qdrant Vector Match |
| • Local NER (spaCy / GPU)  |                | 2. Direct Cypher Graph Query  |
| • Parallel Data Chunking   |                | 3. Clean & Concatenate Arrays |
+------+--------------+------+                +--------------+----------------+
       |              |                                      |
       | (Dense       | (Graph Triples)                      |
       |  Vectors)    |                                      | (Send final
       v              v                                      |  context)
+------+-----+ +------+-----+                                v
|   QDRANT   | |   NEO4J /  |                         +------+-------+
|  VECTOR DB | |  MEMGRAPH  |                         |  NATIVE LLM  |
+------------+ +------------+                         |     API      |
                                                      +--------------+