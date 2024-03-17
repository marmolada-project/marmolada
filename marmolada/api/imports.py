from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination.cursor import CursorPage
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.model import Import
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
    data: schemas.ImportPatch,
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
) -> Import:
    import_ = (
        await db_session.execute(
            select(Import).filter_by(uuid=uuid).options(selectinload(Import.artifacts))
        )
    ).scalar_one()

    for key, value in data:
        try:
            setattr(import_, key, value)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    await db_session.commit()

    return import_
