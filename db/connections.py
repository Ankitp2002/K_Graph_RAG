from qdrant_client import QdrantClient
from neo4j import GraphDatabase
from core.config import Settings


class VectorAndGraphDBConnections:

    __slots__ = ["qdrant_client", "neo4j_driver"]

    def __init__(self, settings: Settings):
        # Qdrant Client Setup
        self.qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT
        )
        # Neo4j Driver Setup
        self.neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    def get_neo4j_session(self):
        with self.neo4j_driver.session() as session:
            yield session

    def get_qdrant_client(self):
        return self.qdrant_client

    def get_neo4j_driver(self):
        return self.neo4j_driver
