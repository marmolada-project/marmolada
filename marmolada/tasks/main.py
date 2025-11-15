from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from taskiq.brokers.shared_broker import async_shared_broker

if TYPE_CHECKING:
    from .plugins import TaskPluginManager

log = logging.getLogger(__name__)
plugin_mgr: TaskPluginManager | None = None


@async_shared_broker.task
async def process_artifact(uuid: UUID) -> None:
    print(f"process_artifact({uuid=!s}) => …")
    await plugin_mgr.process_scope(scope="artifact", uuid=uuid)
    print(f"process_artifact({uuid=!s}) done")


@async_shared_broker.task
async def process_import(uuid: UUID) -> None:
    log.debug(f"process_import({uuid=!s}) => …")
    await plugin_mgr.process_scope(scope="import", uuid=uuid)
    log.debug(f"process_import({uuid=!s}) done")
