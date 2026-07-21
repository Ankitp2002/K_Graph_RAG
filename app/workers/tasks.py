import spacy
from celery import Celery
from qdrant_client.models import VectorParams, Distance, PointStruct
import uuid
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.db.connections import qdrant_client, neo4j_driver

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Load spaCy NLP model for Local Entity Recognition
nlp = spacy.load("en_core_web_sm")
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

@celery_app.task(name="process_and_ingest_document")
def process_and_ingest_document(document_text: str, doc_id: str):
    """
    1. Parse & Chunk Document
    2. Extract Entities & Triples using spaCy NER
    3. Push Vectors to Qdrant
    4. Push Knowledge Graph Triples to Neo4j
    """
    # Initialize Qdrant Collection if not exists
    collections = [c.name for c in qdrant_client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in collections:
        qdrant_client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )

    # Simple Parallellized/Chunking logic
    doc = nlp(document_text)
    chunks = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]

    points = []
    triples = []

    for idx, chunk in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        
        # 1. Embed and prepare Qdrant Point
        vector = embeddings_model.embed_query(chunk)
        points.append(PointStruct(
            id=chunk_id,
            vector=vector,
            payload={"doc_id": doc_id, "text": chunk, "chunk_index": idx}
        ))

        # 2. Extract Entities using spaCy for Neo4j Graph
        chunk_doc = nlp(chunk)
        entities = [ent.text.strip() for ent in chunk_doc.ents]
        
        # Build simple graph relationships (Entity -> CONTAINED_IN -> Chunk)
        for entity in entities:
            triples.append({
                "entity": entity,
                "label": chunk_doc.char_span(0, len(chunk)).text if len(entities) > 0 else "Concept",
                "chunk_id": chunk_id,
                "text": chunk
            })

    # Batch Insert Vectors into Qdrant
    if points:
        qdrant_client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)

    # Insert Triples into Neo4j
    cypher_query = """
    UNWIND $triples AS triple
    MERGE (e:Entity {name: triple.entity})
    MERGE (c:Chunk {id: triple.chunk_id})
    SET c.text = triple.text
    MERGE (e)-[:MENTIONED_IN]->(c)
    """
    with neo4j_driver.session() as session:
        session.run(cypher_query, triples=triples)

    return {"status": "SUCCESS", "chunks_processed": len(chunks), "entities_extracted": len(triples)}
