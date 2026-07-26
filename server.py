from fastapi import FastAPI
from contextlib import asynccontextmanager
from apis.reg_routers import __routers__


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB connection

    yield

    # Close DB connection


class Server:
    __slots__ = ["__app"]

    def __init__(self):
        self.__app = FastAPI(lifespan=lifespan, title="Knowledge Graph Server")

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
