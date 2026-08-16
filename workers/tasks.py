def process_and_ingest_document(file_path, file_id):
    from qdrant_client.models import VectorParams, Distance, PointStruct
    import uuid
    from core.config import Settings
    from db.connections import VectorAndGraphDBConnections
    from services.llm_manager import LLMManager
    from services.docling_engine import DoclingEngine
    from doc_converter.base_converter import BaseConverter

    settings = Settings()

    db_connection = VectorAndGraphDBConnections(settings)
    qdrant_client = db_connection.get_qdrant_client()
    neo4j_driver = db_connection.get_neo4j_driver()

    llm_manager = LLMManager()
    embeddings_model = llm_manager.get_embeddings_model()
    nlp_model = llm_manager.get_nlp_model()

    docling_engine = DoclingEngine()
    docling_engine.initialize()

    markdown_converter = BaseConverter(
        llm_instance=llm_manager,
        docling_converter=docling_engine,
        file_path="",
        extention="",
    )

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
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

    extension = f".{file_path.split('.')[-1]}"

    # get document_text base on requested expention
    markdown_converter.file_path = file_path
    markdown_converter.extention = extension
    document_text, _ = markdown_converter.parse_and_enrich_document()

    # Simple Parallellized/Chunking logic
    doc = nlp_model(document_text)
    chunks = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]

    points = []
    triples = []

    for idx, chunk in enumerate(chunks):
        chunk_id = str(uuid.uuid4())

        # 1. Extract Entities using spaCy
        chunk_doc = nlp_model(chunk)
        # Store entity text and label (e.g., PERSON, ORG)
        entities_data = [
            {"name": ent.text.strip(), "type": ent.label_}
            for ent in chunk_doc.ents
            if ent.text.strip()
        ]
        entity_names = [e["name"] for e in entities_data]

        # 2. Embed Chunk Text
        vector = embeddings_model.embed_query(chunk)

        # 3. Prepare Qdrant Point (Payload includes entity metadata for payload filtering)
        points.append(
            PointStruct(
                id=chunk_id,
                vector=vector,
                payload={
                    "doc_id": file_id,
                    "text": chunk,
                    "chunk_index": idx,
                    "entities": entity_names,
                },
            )
        )

        # 4. Prepare Neo4j Triples
        for ent in entities_data:
            triples.append(
                {
                    "entity": ent["name"],
                    "type": ent["type"],
                    "chunk_id": chunk_id,
                    "text": chunk,
                }
            )

    # Batch Insert Vectors into Qdrant
    if points:
        qdrant_client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)

    # Optimized Dynamic Cypher Insert into Neo4j
    cypher_query = """
    UNWIND $triples AS triple
    MERGE (c:Chunk {id: triple.chunk_id})
    ON CREATE SET c.text = triple.text

    MERGE (e:Entity {name: triple.entity})
    ON CREATE SET e.type = triple.type

    MERGE (e)-[:MENTIONED_IN]->(c)
    """

    if triples:
        with neo4j_driver.session() as session:
            session.run(cypher_query, triples=triples)

    print(
        {
            "status": "SUCCESS",
            "chunks_processed": len(chunks),
            "entities_extracted": len(triples),
        }
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process and ingest a document.")
    parser.add_argument("--file-path", required=True, help="Path to the document file.")
    parser.add_argument("--file-id", required=True, help="ID for the document.")
    args = parser.parse_args()

    print(f"Processing file: {args.file_path} with ID: {args.file_id}")
    process_and_ingest_document(args.file_path, args.file_id)
