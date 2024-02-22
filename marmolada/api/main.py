from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..database import init_model


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Database
    init_model()

    yield


app = FastAPI(lifespan=lifespan)
