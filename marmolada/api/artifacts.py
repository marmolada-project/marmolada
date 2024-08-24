from socket import getfqdn
from typing import Annotated
from uuid import UUID

from anyio import Path as AsyncPath
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi_pagination.cursor import CursorPage
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import AnyUrl
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.model import Artifact, Import
from ..tasks.base import ArqRedis, get_task_pool
from . import schemas
from .database import req_db_session
from .imports import router as imports_router

router = APIRouter(prefix="/artifacts")


def _get_artifacts_query(import_uuid: UUID | None = None) -> Select:
    query = select(Artifact).order_by(Artifact.created_at).options(selectinload(Artifact.import_))
    if import_uuid:
        query = query.join(Artifact.import_.and_(Import.uuid == import_uuid))
    return query


@router.get("", response_model=CursorPage[schemas.ArtifactResult])
async def get_artifacts(
    db_session: Annotated[AsyncSession, Depends(req_db_session)]
) -> CursorPage[Artifact]:
    return await paginate(db_session, _get_artifacts_query())


@imports_router.get("/{uuid}/artifacts", response_model=CursorPage[schemas.ArtifactResult])
async def get_artifacts_for_import(
    uuid: UUID, db_session: Annotated[AsyncSession, Depends(req_db_session)]
) -> CursorPage[Artifact]:
    return await paginate(db_session, _get_artifacts_query(uuid))


@router.get("/{uuid}", response_model=schemas.ArtifactResult)
async def get_artifact(
    uuid: UUID,
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
) -> Artifact:
    artifact = (
        await db_session.execute(
            select(Artifact).filter_by(uuid=uuid).options(selectinload(Artifact.import_))
        )
    ).scalar_one()
    return artifact


@imports_router.post(
    "/{uuid}/artifacts", response_model=schemas.ArtifactResult, status_code=status.HTTP_201_CREATED
)
async def post_artifact_for_import(
    uuid: UUID,
    file: UploadFile,
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
    task_pool: Annotated[ArqRedis, Depends(get_task_pool)],
    source_uri: Annotated[AnyUrl | None, Query(alias="source-uri")] = None,
) -> Artifact:
    import_ = (await db_session.execute(select(Import).filter_by(uuid=uuid))).scalar_one_or_none()

    if not import_:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="import not found")

    artifact = Artifact(
        import_=import_,
        source_uri=str(source_uri) if source_uri else None,
        file_name=file.filename,
    )

    db_session.add(artifact)
    await db_session.flush()

    artifact.data = await file.read()

    await db_session.commit()

    await task_pool.enqueue_job("process_artifact", artifact.uuid)

    return artifact


@imports_router.post(
    "/{uuid}/artifacts/from-local-file",
    response_model=schemas.ArtifactResult,
    status_code=status.HTTP_201_CREATED,
)
async def post_artifact_for_import_from_local_file(
    uuid: UUID,
    data: schemas.ArtifactPostLocal,
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
    task_pool: Annotated[ArqRedis, Depends(get_task_pool)],
) -> Artifact:
    if (
        data.source_uri.scheme != "file"
        or data.source_uri.host != getfqdn()
        or not await (local_path := AsyncPath(data.source_uri.path)).exists()
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source-uri must point to a local file on the server",
        )

    import_ = (await db_session.execute(select(Import).filter_by(uuid=uuid))).scalar_one_or_none()

    if not import_:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="import not found")

    artifact = Artifact(
        content_type=data.content_type,
        import_=import_,
        source_uri=str(data.source_uri),
        file_name=data.source_uri.path.rsplit("/", 1)[-1],
    )

    db_session.add(artifact)
    await db_session.flush()
    await db_session.refresh(artifact, ["_path"])

    await artifact.async_full_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        await artifact.async_full_path.hardlink_to(local_path)
    except OSError:
        async with await local_path.open("rb") as source, await artifact.async_full_path.open(
            "wb"
        ) as destination:
            await destination.write(await source.read())

    await db_session.commit()

    await task_pool.enqueue_job("process_artifact", artifact.uuid)

    return artifact
