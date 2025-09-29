import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination.cursor import CursorPage
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.model import Language, Tag, TagCyclicGraphError, TagLabel
from . import schemas
from .database import req_db_session

router = APIRouter(prefix="/tags")


@router.get("")
async def get_tags(
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
) -> CursorPage[schemas.TagResult]:
    return await apaginate(
        db_session,
        select(Tag)
        .order_by(Tag.created_at)
        .options(selectinload(Tag.parents, Tag.children, Tag.label_objs)),
    )


@router.get("/{uuid}", response_model=schemas.TagResult)
async def get_tag(uuid: UUID, db_session: Annotated[AsyncSession, Depends(req_db_session)]) -> Tag:
    tag = (await db_session.execute(select(Tag).filter_by(uuid=uuid))).unique().scalar_one()

    # This is because selectinload() above isn’t effective.
    await asyncio.gather(tag.awaitable_attrs.parents, tag.awaitable_attrs.children)

    return tag


@router.post("", response_model=schemas.TagResult, status_code=status.HTTP_201_CREATED)
async def post_tag(
    data: schemas.TagPost,
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
) -> Tag:
    tag = Tag()

    if data.parents:
        parents = (
            (await db_session.execute(select(Tag).filter(Tag.uuid.in_(data.parents))))
            .unique()
            .scalars()
            .all()
        )

        p_uuid_set = {p.uuid for p in parents}
        if p_uuid_set != set(data.parents):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Failure looking up parents:"
                    + f" {', '.join(str(u) for u in set(data.parents) - p_uuid_set)}"
                ),
            )

        # No need to use .add_parents() as tag doesn’t have children yet, i.e. simply setting this
        # can’t introduce a cyclic dependency.
        (await tag.awaitable_attrs.parents).update(parents)

    tag.label_objs = {
        TagLabel(label=spec, language_objs=set())
        if isinstance(spec, str)
        else TagLabel(
            label=spec.label,
            language_objs={await Language.by_iso_code(db_session, lang) for lang in spec.languages},
        )
        for spec in data.labels
    }

    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag, ["parents", "children"])

    return tag


@router.put("/{uuid}", response_model=schemas.TagResult)
async def put_tag(
    uuid: UUID,
    data: schemas.TagPut,
    db_session: Annotated[AsyncSession, Depends(req_db_session)],
) -> Tag:
    try:
        tag = (
            (
                await db_session.execute(
                    select(Tag)
                    .filter_by(uuid=uuid)
                    .options(selectinload(Tag.parents, Tag.children, Tag.label_objs))
                )
            )
            .unique()
            .scalar_one()
        )
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc

    if data.parents is not None:
        new_parents = set(
            (await db_session.execute(select(Tag).filter(Tag.uuid.in_(data.parents))))
            .unique()
            .scalars()
        )

        p_uuid_set = {p.uuid for p in new_parents}
        if p_uuid_set != set(data.parents):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Failure looking up parents:"
                    + f" {', '.join(str(u) for u in set(data.parents) - p_uuid_set)}"
                ),
            )

        parents = await tag.awaitable_attrs.parents
        add_parents = new_parents - parents
        parents.intersection_update(new_parents)
        try:
            await tag.add_parents(db_session, *add_parents)
        except TagCyclicGraphError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.args[0]) from exc

    if data.children is not None:
        new_children = set(
            (await db_session.execute(select(Tag).filter(Tag.uuid.in_(data.children))))
            .unique()
            .scalars()
        )

        c_uuid_set = {c.uuid for c in new_children}
        if c_uuid_set != set(data.children):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Failure looking up children:"
                    + f" {', '.join(str(u) for u in set(data.children) - c_uuid_set)}"
                ),
            )

        children = await tag.awaitable_attrs.children
        add_children = new_children - children
        children.intersection_update(new_children)
        try:
            await tag.add_children(db_session, *add_children)
        except TagCyclicGraphError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.args[0]) from exc

    if data.labels is not None:
        qualified_labels_after = [
            schemas.QualifiedTagLabel(label=label, languages=[])
            if isinstance(label, str)
            else label
            for label in data.labels
        ]

        labels_byname_after = {label.label: label for label in qualified_labels_after}
        label_names_after = set(labels_byname_after)

        labels_byname_before = tag.labels
        label_names_before = set(labels_byname_before)

        label_names_to_delete = label_names_before - label_names_after
        label_names_existing = label_names_before & label_names_after
        label_names_to_create = label_names_after - label_names_before

        for label_obj in tag.label_objs:
            if label_obj.label in label_names_to_delete:
                await db_session.delete(label_obj)
            if label_obj.label in label_names_existing:
                label_obj.language_objs = {
                    await Language.by_iso_code(db_session, iso_code=iso_code)
                    for iso_code in labels_byname_after[label_obj.label].languages
                }
        await tag.awaitable_attrs.label_objs

        for label in label_names_to_create:
            tag_label = TagLabel(tag_id=tag.id, label=label)
            tag_label.language_objs = {
                await Language.by_iso_code(db_session, iso_code)
                for iso_code in labels_byname_after[label].languages
            }
            db_session.add(tag_label)

    await db_session.commit()
    await db_session.refresh(tag, ["label_objs", "parents", "children"])

    return tag


@router.get("/{uuid}/ancestors", response_model=CursorPage[schemas.TagResult])
async def get_tag_ancestors(
    uuid: UUID, db_session: Annotated[AsyncSession, Depends(req_db_session)]
) -> list[Tag]:
    tag = (await db_session.execute(select(Tag).filter_by(uuid=uuid))).unique().scalar_one()

    return await apaginate(db_session, tag.ancestors_query.order_by(Tag.created_at))


@router.get("/{uuid}/descendants", response_model=CursorPage[schemas.TagResult])
async def get_tag_descendants(
    uuid: UUID, db_session: Annotated[AsyncSession, Depends(req_db_session)]
) -> list[Tag]:
    tag = (await db_session.execute(select(Tag).filter_by(uuid=uuid))).unique().scalar_one()

    return await apaginate(db_session, tag.descendants_query.order_by(Tag.created_at))
