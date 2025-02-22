from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination.cursor import CursorPage
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.model import Import
from ..tasks.base import ArqRedis, get_task_pool
from . import schemas
from .database import req_db_session

router = APIRouter(prefix="/imports")


@router.get("")
async def get_imports(
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
) -> CursorPage[schemas.ImportResult]:
    return await paginate(
        db_session,
        select(Import).order_by(Import.created_at).options(selectinload(Import.artifacts)),
    )


@router.get("/{uuid}", response_model=schemas.ImportResult)
async def get_import(
    uuid: UUID, db_session: Annotated[AsyncSession, Depends(req_db_session)]
) -> Import:
    import_ = (
        await db_session.execute(
            select(Import).filter_by(uuid=uuid).options(selectinload(Import.artifacts))
        )
    ).scalar_one()
    return import_


@router.post("", response_model=schemas.ImportResult, status_code=status.HTTP_201_CREATED)
async def post_import(
    data: schemas.ImportPost,
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
) -> Import:
    import_ = Import()
    if data.meta:
        import_.meta = data.meta
    db_session.add(import_)
    await db_session.commit()
    await db_session.refresh(import_, ["artifacts"])

    return import_


@router.put("/{uuid}", response_model=schemas.ImportResult)
async def put_import(
    uuid: UUID,
    data: schemas.ImportPut,
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
    task_pool: Annotated[ArqRedis, Depends(get_task_pool)],
) -> Import:
    import_ = (
        await db_session.execute(
            select(Import).filter_by(uuid=uuid).options(selectinload(Import.artifacts))
        )
    ).scalar_one()

    old_complete = import_.complete

    for key, value in data:
        try:
            setattr(import_, key, value)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    new_complete = import_.complete

    await db_session.commit()

    if not old_complete and new_complete:
        await task_pool.enqueue_job("process_import", import_.uuid)

    return import_
