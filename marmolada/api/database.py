from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from ..database import session_maker


async def req_db_session() -> AsyncIterator[AsyncSession]:
    db_session = session_maker()
    try:
        yield db_session
    finally:
        await db_session.close()
