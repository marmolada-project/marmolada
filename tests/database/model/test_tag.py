import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import NoResultFound

from marmolada.database.model import Tag, TagCyclicGraphError, TagLabel

from .common import ModelTestBase


class TestTag(ModelTestBase):
    cls = Tag

    async def test_by_label_path(self, db_session):
        await db_session.execute(delete(Tag))

        created_bar_tag = await Tag.by_label_path(db_session, ["foo", "bar"], create=True)
        assert created_bar_tag.labels == {"bar"}

        created_bar_parent = next(iter(created_bar_tag.parents))

        queried_foo_tag = await Tag.by_label_path(db_session, ["foo"])
        assert created_bar_parent is queried_foo_tag

        queried_bar_tag = await Tag.by_label_path(db_session, ["foo", "bar"])
        assert queried_bar_tag is created_bar_tag

        with pytest.raises(NoResultFound):
            await Tag.by_label_path(db_session, ["foo", "gna"])

    async def test_get_ancestors(self, db_session):
        foo = await Tag.by_label_path(db_session, ["foo"], create=True)
        bar = await Tag.by_label_path(db_session, ["foo", "bar"], create=True)
        baz = await Tag.by_label_path(db_session, ["baz"], create=True)

        await db_session.flush()
        await baz.add_parents(db_session, bar)

        assert set((await db_session.execute(baz.ancestors_query)).scalars().unique()) == {foo, bar}

    async def test_get_descendants(self, db_session):
        foo = await Tag.by_label_path(db_session, ["foo"], create=True)
        bar = await Tag.by_label_path(db_session, ["foo", "bar"], create=True)
        baz = await Tag.by_label_path(db_session, ["baz"], create=True)

        await db_session.flush()
        await baz.add_parents(db_session, bar)

        assert baz in (await db_session.execute(foo.descendants_query)).scalars().unique()
        assert baz in (await db_session.execute(bar.descendants_query)).scalars().unique()

    async def test_add_parents(self, db_session):
        foo = Tag()
        bar = Tag()
        db_session.add(foo)
        db_session.add(bar)

        await bar.add_parents(db_session, foo)

        assert foo in (await db_session.execute(bar.ancestors_query)).scalars().unique()
        assert foo in bar.parents
        assert (
            foo
            in (await db_session.execute(select(Tag).filter(Tag.children.any(Tag.id == bar.id))))
            .scalars()
            .unique()
        )
        assert bar in (await db_session.execute(foo.descendants_query)).scalars().unique()
        assert bar in foo.children
        assert (
            bar
            in (await db_session.execute(select(Tag).filter(Tag.parents.any(Tag.id == foo.id))))
            .scalars()
            .unique()
        )

        with pytest.raises(TagCyclicGraphError):
            await foo.add_parents(db_session, bar)

    async def test_add_children(self, db_session):
        foo = Tag()
        bar = Tag()
        db_session.add(foo)
        db_session.add(bar)

        await foo.add_children(db_session, bar)

        assert foo in (await db_session.execute(bar.ancestors_query)).scalars().unique()
        assert foo in bar.parents
        assert (
            foo
            in (await db_session.execute(select(Tag).filter(Tag.children.any(Tag.id == bar.id))))
            .scalars()
            .unique()
        )
        assert bar in (await db_session.execute(foo.descendants_query)).scalars().unique()
        assert bar in foo.children
        assert (
            bar
            in (await db_session.execute(select(Tag).filter(Tag.parents.any(Tag.id == foo.id))))
            .scalars()
            .unique()
        )

        with pytest.raises(TagCyclicGraphError):
            await bar.add_children(db_session, foo)

    @pytest.mark.parametrize("label", (" Unstripped whitespace ", "Two  spaces  between  words"))
    async def test_db_constraint_illegal_label(self, label, db_session):
        tag = Tag()
        label = TagLabel()
        # Bypass normalization through property
        label._label = label
        (await tag.awaitable_attrs.label_objs).add(label)
        db_session.add(tag)

        with pytest.raises(DBAPIError):
            await db_session.flush()
