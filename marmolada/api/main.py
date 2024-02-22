from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi_pagination import add_pagination

from ..database import init_model
from . import artifacts, imports
from .base import API_PREFIX


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Database
    init_model()

    yield


app = FastAPI(lifespan=lifespan)

app.include_router(artifacts.router, prefix=API_PREFIX)
app.include_router(imports.router, prefix=API_PREFIX)

add_pagination(app)
