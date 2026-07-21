from qdrant_client import QdrantClient
from neo4j import GraphDatabase
from app.core.config import settings

# Qdrant Client Setup
qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)

# Neo4j Driver Setup
neo4j_driver = GraphDatabase.driver(
    settings.NEO4J_URI, 
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
)

def get_neo4j_session():
    with neo4j_driver.session() as session:
        yield session
