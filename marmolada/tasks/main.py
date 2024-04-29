import logging
from uuid import UUID

from .typing import Context

log = logging.getLogger(__name__)


async def process_artifact(ctx: Context, uuid: UUID) -> None: ...


async def process_import(ctx: Context, uuid: UUID) -> None: ...
