from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import taskiq_fastapi
from fastapi import FastAPI
from fastapi_pagination import add_pagination

from ..database import init_model
from ..tasks import configure_broker
from . import artifacts, imports, tags
from .base import API_PREFIX


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    broker = configure_broker()
    if not broker.is_worker_process:  # pragma: no branch
        await broker.startup()

    taskiq_fastapi.init(broker, app)

    # Database
    init_model()

    yield

    if not broker.is_worker_process:  # pragma: no branch
        await broker.shutdown()


app = FastAPI(lifespan=lifespan)

app.include_router(artifacts.router, prefix=API_PREFIX)
app.include_router(imports.router, prefix=API_PREFIX)
app.include_router(tags.router, prefix=API_PREFIX)

add_pagination(app)
