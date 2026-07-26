from typing import List, Dict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langsmith import traceable
from core.config import Settings
from qdrant_client import QdrantClient
from neo4j import GraphDatabase


class RetrievalRoutingEngine:

    def __init__(
        self,
        embeddings_model,
        qdrant_client=QdrantClient,
        neo4j_driver=GraphDatabase,
        settings=Settings,
        llm: Optional[BaseChatModel] = None,
    ):
        self.llm = llm
        self.embeddings_model = embeddings_model
        self.qdrant_client = qdrant_client
        self.neo4j_driver = neo4j_driver
        self.settings = settings

    def vector_search(self, query: str, top_k: int = 3) -> List[str]:
        """Direct Qdrant Vector Match"""
        query_vector = self.embeddings_model.embed_query(query)

        # Modern Qdrant API call
        search_result = self.qdrant_client.query_points(
            collection_name=self.settings.QDRANT_COLLECTION,
            query=query_vector,
            limit=top_k,
        )
        return [hit.payload.get("text", "") for hit in search_result.points]

    def graph_search(self, query: str) -> List[Dict[str, Any]]:
        """Direct Cypher Graph Query based on extracted query entities"""
        cypher = """
        MATCH (e:Entity)-[:MENTIONED_IN]->(c:Chunk)
        WHERE toLower(e.name) CONTAINS toLower($query) OR toLower(c.text) CONTAINS toLower($query)
        RETURN e.name as Entity, c.text as Context LIMIT 5
        """
        with self.neo4j_driver.session() as session:
            result = session.run(cypher, query=query)
            return [record.data() for record in result]

    @traceable(name="Hybrid RAG Pipeline")  # Fixed decorator
    def run_pipeline(self, query: str) -> Dict[str, Any]:
        """Hybrid Context Retrieval & Concatenation"""
        # Step 1: Execute Parallel/Sequential Retrievals
        vector_results = self.vector_search(query)
        graph_results = self.graph_search(query)

        # Step 2: Clean & Concatenate Arrays
        combined_context = "\n--- Vector Context ---\n" + "\n".join(vector_results)

        graph_context_str = "\n".join(
            [
                f"Entity: {r.get('Entity', 'Unknown')} -> Text: {r.get('Context', '')}"
                for r in graph_results
            ]
        )
        combined_context += "\n--- Graph Context ---\n" + graph_context_str

        # Step 3: Synthesize Answer using Native LLM with LangSmith Tracing
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an enterprise AI assistant using Knowledge Graph Augmented Retrieval. Answer strictly based on the context provided.",
                ),
                ("human", "Context:\n{context}\n\nQuestion: {question}"),
            ]
        )

        chain = prompt_template | self.llm | StrOutputParser()
        answer = chain.invoke({"context": combined_context, "question": query})

        return {
            "answer": answer,
            "vector_context": vector_results,
            "graph_context": graph_results,
        }
