from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routers import chat, keys


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    try:
        yield
    finally:
        pass


app = FastAPI(lifespan=lifespan)

app.include_router(chat.router)
app.include_router(keys.router)
