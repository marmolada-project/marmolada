import datetime as dt
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

from marmolada.database import mixins
from marmolada.database.main import Base


class Thing(Base, mixins.BigIntPrimaryKey, mixins.UuidAltKey, mixins.Creatable, mixins.Updatable):
    __tablename__ = "things"

    something: Mapped[int] = mapped_column(nullable=True)


async def test_creating(db_session):
    now = dt.datetime.now(dt.UTC)

    thing = Thing()
    db_session.add(thing)
    await db_session.flush()

    then = dt.datetime.now(dt.UTC)

    assert now <= thing.created_at <= then


async def test_updating(db_session):
    async with db_session.begin():
        thing = Thing()
        db_session.add(thing)

    then = dt.datetime.now(dt.UTC)

    async with db_session.begin():
        thing = await db_session.get(Thing, thing.id, with_for_update=True)
        thing.something = 5

    then_again = dt.datetime.now(dt.UTC)

    async with db_session.begin():
        thing = await db_session.get(Thing, thing.id, populate_existing=True, with_for_update=True)
        assert then <= thing.updated_at <= then_again
        thing.something = 6

    then_again_and_later = dt.datetime.now(dt.UTC)

    async with db_session.begin():
        thing = await db_session.get(Thing, thing.id, populate_existing=True)
        assert then_again <= thing.updated_at <= then_again_and_later


class TestUuidAltKey:
    async def test_instance_attribute(self, db_session):
        async with db_session.begin():
            thing = Thing()
            db_session.add(thing)

        assert isinstance(thing.uuid, uuid.UUID)
        assert thing.uuid.version == 1

        with pytest.raises(AttributeError, match="Can’t modify Thing.uuid"):
            thing.uuid = 5

    async def test_class_attribute(self, db_session):
        async with db_session.begin():
            written_thing = Thing()
            db_session.add(written_thing)
            await db_session.flush()

            queried_thing = (
                await db_session.execute(select(Thing).filter(Thing.uuid == written_thing.uuid))
            ).scalar_one()

            assert queried_thing is written_thing
