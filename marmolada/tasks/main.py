from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from .typing import Context

if TYPE_CHECKING:
    from .plugins import TaskPluginManager

log = logging.getLogger(__name__)
plugin_mgr: TaskPluginManager | None = None


async def process_artifact(ctx: Context, uuid: UUID) -> None:
    await plugin_mgr.process_scope(scope="artifact", uuid=uuid)


async def process_import(ctx: Context, uuid: UUID) -> None:
    await plugin_mgr.process_scope(scope="import", uuid=uuid)
