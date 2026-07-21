from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langsmith import trace

from app.core.config import settings
from app.db.connections import qdrant_client, neo4j_driver

embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

class RetrievalRoutingEngine:
    
    @staticmethod
    def vector_search(query: str, top_k: int = 3) -> List[str]:
        """Direct Qdrant Vector Match"""
        query_vector = embeddings_model.embed_query(query)
        search_result = qdrant_client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k
        )
        return [hit.payload["text"] for hit in search_result]

    @staticmethod
    def graph_search(query: str) -> List[Dict[str, Any]]:
        """Direct Cypher Graph Query based on extracted query entities"""
        cypher = """
        MATCH (e:Entity)-[:MENTIONED_IN]->(c:Chunk)
        WHERE toLower(e.name) CONTAINS toLower($query) OR toLower(c.text) CONTAINS toLower($query)
        RETURN e.name as Entity, c.text as Context LIMIT 5
        """
        with neo4j_driver.session() as session:
            result = session.run(cypher, query=query)
            return [record.data() for record in result]

    @classmethod
    @trace(name="Hybrid RAG Pipeline")
    def run_pipeline(cls, query: str) -> Dict[str, Any]:
        """Hybrid Context Retrieval & Concatenation"""
        # Step 1: Execute Parallel Retrievals
        vector_results = cls.vector_search(query)
        graph_results = cls.graph_search(query)

        # Step 2: Clean & Concatenate Arrays
        combined_context = "\n--- Vector Context ---\n" + "\n".join(vector_results)
        combined_context += "\n--- Graph Context ---\n" + "\n".join([f"Entity: {r['Entity']} -> Text: {r['Context']}" for r in graph_results])

        # Step 3: Synthesize Answer using Native LLM with LangSmith Tracing
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an enterprise AI assistant using Knowledge Graph Augmented Retrieval. Answer strictly based on the context provided."),
            ("human", "Context:\n{context}\n\nQuestion: {question}")
        ])
        
        chain = prompt_template | llm | StrOutputParser()
        answer = chain.invoke({"context": combined_context, "question": query})

        return {
            "answer": answer,
            "vector_context": vector_results,
            "graph_context": graph_results
        }
