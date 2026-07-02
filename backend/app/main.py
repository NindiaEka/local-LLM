from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import init_db
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import chat, keys
from app.routers.v1 import analytics as v1_analytics
from app.routers.v1 import chat as v1_chat
from app.routers.v1 import models as v1_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    try:
        yield
    finally:
        pass


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print("\n========== VALIDATION ERROR ==========")
    print(exc.errors())
    print("======================================\n")

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# app.add_middleware(RequestLoggingMiddleware)

app.include_router(chat.router)
app.include_router(keys.router)
app.include_router(v1_chat.router)
app.include_router(v1_models.router)
app.include_router(v1_analytics.router)