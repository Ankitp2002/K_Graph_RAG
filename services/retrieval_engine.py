from typing import Any, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable
from neo4j import Driver
from qdrant_client import QdrantClient
import numpy as np
from core.config import Settings


class RetrievalRoutingEngine:

    def __init__(
        self,
        embeddings_model: Any,
        nlp_model: Any,
        qdrant_client: QdrantClient,
        neo4j_driver: Driver,
        settings: Settings,
        llm: Optional[BaseChatModel] = None,
    ):
        self.llm = llm
        self.embeddings_model = embeddings_model
        self.nlp_model = nlp_model
        self.qdrant_client = qdrant_client
        self.neo4j_driver = neo4j_driver
        self.settings = settings

    def vector_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """1. Direct Vector Search via Qdrant.

        Retrieves top-k semantically relevant chunks.
        """
        query_vector = self.embeddings_model.embed_query(query)

        search_result = self.qdrant_client.query_points(
            collection_name=self.settings.QDRANT_COLLECTION,
            query=query_vector,
            limit=top_k,
        )

        return [
            {
                "chunk_id": str(hit.id),
                "text": hit.payload.get("text", ""),
                "score": hit.score,
                "entities": hit.payload.get("entities", []),
            }
            for hit in search_result.points
        ]

    def graph_search(
        self, query: str, seed_chunk_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """2. Direct Graph Search via Neo4j.

        Finds context linked to extracted query entities and traverses 1-hop
        relationships around seed vector chunks.
        """
        seed_chunk_ids = seed_chunk_ids or []

        # Extract entities from the user query
        query_doc = self.nlp_model(query)
        query_entities = [
            ent.text.strip().lower() for ent in query_doc.ents if ent.text.strip()
        ]

        cypher = """
       // A. Match query entities directly in the graph
        OPTIONAL MATCH (e_query:Entity)-[:MENTIONED_IN]->(c_entity:Chunk)
        WHERE toLower(e_query.name) IN $query_entities

        // B. Graph expansion: Traversal from seed chunks through shared entities to connected chunks
        OPTIONAL MATCH (c_seed:Chunk)
        WHERE c_seed.id IN $seed_ids
        
        OPTIONAL MATCH (c_seed)<-[:MENTIONED_IN]-(e_shared:Entity)-[:MENTIONED_IN]->(c_expanded:Chunk)
        WHERE NOT c_expanded.id IN $seed_ids

        RETURN 
            COLLECT(DISTINCT {
                chunk_id: c_entity.id, 
                text: c_entity.text, 
                via: e_query.name, 
                type: 'entity_match'
            }) AS entity_matched_chunks,
            
            COLLECT(DISTINCT {
                chunk_id: c_expanded.id, 
                text: c_expanded.text, 
                via: e_shared.name, 
                type: 'graph_expansion'
            }) AS expanded_chunks
        """

        with self.neo4j_driver.session() as session:
            result = session.run(
                cypher, seed_ids=seed_chunk_ids, query_entities=query_entities
            )
            record = result.single()
            data = record.data() if record else {}

        graph_results = []
        for key in ["entity_matched_chunks", "expanded_chunks"]:
            for item in data.get(key, []):
                if item and item.get("chunk_id"):
                    graph_results.append(item)

        graph_results = self.get_filtered_graph_by_compute_cosine_similarity(
            query_vector=self.embeddings_model.embed_query(query),
            graph_results=graph_results,
        )

        return graph_results

    def compute_cosine_similarity(self, vec1: list, vec2: list) -> float:
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def get_filtered_graph_by_compute_cosine_similarity(
        self, query_vector: List[float], graph_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Computes cosine similarity between two vectors."""
        filtered_graph_results = []
        for g in graph_results:
            # Option: Embed chunk text or compute score to check relevance
            chunk_vector = self.embeddings_model.embed_query(g["text"])
            similarity = self.compute_cosine_similarity(query_vector, chunk_vector)
            g["score"] = similarity

            # Keep only if it passes a relevance bar (e.g., > 0.70)
            if similarity > 0.75:
                filtered_graph_results.append(g)
        return filtered_graph_results

    @traceable(name="Hybrid RAG Pipeline")
    def run_pipeline(self, query: str, top_k_qdrant: int = 3) -> Dict[str, Any]:
        """Hybrid Context Retrieval, Deduplication, & Synthesis Pipeline."""
        if not self.llm:
            raise ValueError(
                "LLM model instance is required to run the synthesis pipeline."
            )

        # Step 1: Execute Vector Search
        vector_results = self.vector_search(query, top_k=top_k_qdrant)
        seed_chunk_ids = [v["chunk_id"] for v in vector_results]

        # Step 2: Execute Graph Search using Query Entities & Seed Chunk IDs
        graph_results = self.graph_search(query, seed_chunk_ids=seed_chunk_ids)

        # Step 3: Deduplicate Context Chunks across Vector and Graph sources
        context_map: Dict[str, Dict[str, Any]] = {}

        for v in vector_results:
            context_map[v["chunk_id"]] = {
                "text": v["text"],
                "source": "Vector Search",
                "score": v["score"],
            }

        for g in graph_results:
            chunk_id = g["chunk_id"]
            if chunk_id not in context_map:
                context_map[chunk_id] = {
                    "text": g["text"],
                    "source": f"Graph Search ({g['type']} via '{g['via']}')",
                    "score": None,
                }

        # Step 4: Construct Formatted Context Block
        formatted_context_blocks = [
            f"[Source: {c['source']}]\n{c['text']}" for c in context_map.values()
        ]
        combined_context = "\n\n---\n\n".join(formatted_context_blocks)

        # Step 5: Synthesize Answer using LangChain
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an enterprise AI assistant using Knowledge Graph Augmented Retrieval. "
                    "Answer the user's question strictly based on the provided context. "
                    "If the answer cannot be derived from the context, state that you do not have enough information.",
                ),
                ("human", "Context:\n{context}\n\nQuestion: {question}"),
            ]
        )

        chain = prompt_template | self.llm | StrOutputParser()
        answer = chain.invoke({"context": combined_context, "question": query})

        return {
            "query": query,
            "answer": answer,
            "vector_context": vector_results,
            "graph_context": graph_results,
            "deduplicated_contexts": list(context_map.values()),
            "formatted_context": combined_context,
        }
