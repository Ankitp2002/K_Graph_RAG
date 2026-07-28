from fastapi import FastAPI
from contextlib import asynccontextmanager
from apis.reg_routers import __routers__
from services.llm_manager import LLMManager
from services.retrieval_engine import RetrievalRoutingEngine
from core.config import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    llm_manager = LLMManager()
    llm_manager.initialize()
    app.state.llm_manager = llm_manager
    app.state.embedding_model = llm_manager.get_embeddings_model()

    app.state.retrieval_engine = RetrievalRoutingEngine(
        embeddings_model=app.state.embedding_model,
        qdrant_client=app.state.qdrant_client,
        neo4j_driver=app.state.neo4j_driver,
        settings=app.state.settings,
    )

    yield

    # Close DB connection


class Server:
    __slots__ = ["__app"]

    def __init__(self):

        self.__app = FastAPI(
            lifespan=lifespan, title="Knowledge Graph Server", debug=True
        )
        self.__app.state.settings = Settings()

        # configure routers
        self.include_routers(__routers__)

    @property
    def app(self) -> FastAPI:
        return self.__app

    def include_routers(self, routers: list):
        for router in routers:
            self.__app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    server = Server()
    uvicorn.run(server.app, port=8000)
