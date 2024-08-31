import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from xdg import Mime

from ....database.model import Artifact

log = logging.getLogger(__name__)

scope = "artifact"
name = "file-type"


async def process(*, db_session: AsyncSession, uuid: UUID) -> None:
    log.debug("process(db_session=%s, uuid=%s)", db_session, uuid)
    artifact: Artifact = (
        await db_session.execute(select(Artifact).filter_by(uuid=uuid))
    ).scalar_one()

    artifact.content_type = str(Mime.get_type2(artifact.full_path))
    log.debug("-> %s", artifact.content_type)
