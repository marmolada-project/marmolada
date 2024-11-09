import re
from collections.abc import Sequence

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Selectable,
    Table,
    UnicodeText,
    func,
    literal_column,
    select,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .. import Base
from ..mixins import BigIntPrimaryKey, Creatable, Updatable, UuidAltKey
from .language import Language


class TagCyclicGraphError(Exception):
    """Operation would cause a cyclic reference between Tags."""


tags_relations = Table(
    "tags_relations",
    Base.metadata,
    Column(
        "parent_id",
        BigInteger,
        ForeignKey("tags.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "child_id",
        BigInteger,
        ForeignKey("tags.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(Base, BigIntPrimaryKey, UuidAltKey, Creatable, Updatable):
    """Represent a hierarchical tag to label things with.

    This object represents the tag semantically in a directed, acyclic
    graph, i.e. it can specify one or more "parent" tags more precisely.
    For example, a "Dolphin" can be both an "Aquatic animal" and a
    "Mammal".

    It can have more than one label (all of which should be synonymous),
    e.g. the "Giant Sequoia" is also known as "Giant Redwood"."""

    __tablename__ = "tags"

    parents: Mapped[set["Tag"]] = relationship(
        "Tag",
        secondary="tags_relations",
        primaryjoin="Tag.id==tags_relations.c.child_id",
        secondaryjoin="Tag.id==tags_relations.c.parent_id",
        collection_class=set,
        back_populates="children",
    )
    children: Mapped[set["Tag"]] = relationship(
        "Tag",
        secondary="tags_relations",
        primaryjoin="Tag.id==tags_relations.c.parent_id",
        secondaryjoin="Tag.id==tags_relations.c.child_id",
        collection_class=set,
        back_populates="parents",
    )

    label_objs: Mapped[set["TagLabel"]] = relationship(
        "TagLabel", back_populates="tag", lazy="joined"
    )
    labels = association_proxy("label_objs", "label")

    def __repr__(self) -> str:
        attrs = {}
        for attr_name in ("id", "uuid", "labels"):
            try:
                attrs[attr_name] = getattr(self, attr_name)
            except Exception:  # noqa: S110
                pass

        attr_string = ", ".join(f"{k}={v!r}" for k, v in attrs.items())

        return f"{type(self).__name__}({attr_string})"

    @classmethod
    async def by_label_path(
        cls, session: AsyncSession, label_path: Sequence[str], create=False
    ) -> "Tag":
        tag = None
        creating_tags = False

        for label in label_path:
            if not creating_tags:
                with session.no_autoflush:
                    query = select(Tag).filter(
                        Tag.label_objs.any(func.lower(TagLabel.label) == label.lower().strip()),
                    )

                    if tag:
                        query = query.filter(Tag.parents.any(Tag.id == tag.id))
                    else:
                        query = query.filter(~Tag.parents.any())

                    try:
                        tag = (await session.execute(query)).unique().scalar_one()
                    except NoResultFound:
                        if not create:
                            raise
                        creating_tags = True

            if creating_tags:
                new_tag = Tag()
                session.add(new_tag)
                if tag:
                    await session.flush()
                    await new_tag.add_parents(session, tag)
                (await new_tag.awaitable_attrs.label_objs).add(TagLabel(label=label))
                tag = new_tag

        if creating_tags:
            await session.flush()

        return tag

    @property
    def ancestors_id_query(self) -> Selectable:
        parents = (
            select(tags_relations.c.parent_id)
            .where(tags_relations.c.child_id == self.id)
            .cte(name="parents", recursive=True)
        )

        parents_alias = parents.alias()
        tags_relations_alias = tags_relations.alias()

        ancestors = parents.union(
            select(tags_relations_alias.c.parent_id).where(
                tags_relations_alias.c.child_id == parents_alias.c.parent_id
            )
        )

        return ancestors

    @property
    def ancestors_query(self) -> Selectable:
        return select(Tag).filter(Tag.id.in_(select(self.ancestors_id_query)))

    @property
    def descendants_id_query(self) -> Selectable:
        children = (
            select(tags_relations.c.child_id)
            .where(tags_relations.c.parent_id == self.id)
            .cte(name="children", recursive=True)
        )

        children_alias = children.alias()
        tags_relations_alias = tags_relations.alias()

        descendants = children.union(
            select(tags_relations_alias.c.child_id).where(
                tags_relations_alias.c.parent_id == children_alias.c.child_id
            )
        )

        return descendants

    @property
    def descendants_query(self) -> Selectable:
        return select(Tag).filter(Tag.id.in_(select(self.descendants_id_query)))

    async def add_parents(self, session: AsyncSession, *new_parents: tuple["Tag"]) -> None:
        cyclic_candidates = []

        for candidate in new_parents:
            if (
                candidate is self
                or (
                    await session.execute(
                        select(func.count()).select_from(
                            candidate.ancestors_query.filter(Tag.id == self.id).subquery()
                        )
                    )
                ).scalar_one()
                > 0
            ):
                cyclic_candidates.append(candidate)

        if cyclic_candidates:
            raise TagCyclicGraphError(
                f"{self} is an ancestor of {', '.join(str(c) for c in cyclic_candidates)}"
            )

        (await self.awaitable_attrs.parents).update(new_parents)
        for new_parent in new_parents:
            (await new_parent.awaitable_attrs.children).add(self)

    async def add_children(self, session: AsyncSession, *new_children: tuple["Tag"]) -> None:
        cyclic_candidates = []

        for candidate in new_children:
            if (
                candidate is self
                or (
                    await session.execute(
                        select(func.count()).select_from(
                            candidate.descendants_query.filter(Tag.id == self.id).subquery()
                        )
                    )
                ).scalar_one()
                > 0
            ):
                cyclic_candidates.append(candidate)

        if cyclic_candidates:
            raise TagCyclicGraphError(
                f"{self} is a descendant of {', '.join(str(c) for c in cyclic_candidates)}"
            )

        (await self.awaitable_attrs.children).update(new_children)
        for new_child in new_children:
            (await new_child.awaitable_attrs.parents).add(self)


tag_language_table = Table(
    "tag_labels_languages",
    Base.metadata,
    Column(
        "tag_label_id",
        BigInteger,
        ForeignKey("tag_labels.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    ),
    Column(
        "language_id",
        BigInteger,
        ForeignKey("languages.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    ),
)


REPEATED_WS_RE = re.compile(r"\s\s+")


class TagLabel(Base, BigIntPrimaryKey, UuidAltKey, Creatable, Updatable):
    """Represent one label of a Tag.

    A tag can only have one associated TagLabel for the same label,
    ignoring case. Each TagLabel can be associated with zero or more
    languages. Whitespace at the beginning or end of labels will be
    stripped.
    """

    __tablename__ = "tag_labels"
    __table_args__ = (
        Index("ix_tag_label_unique", "tag_id", func.lower(literal_column("label")), unique=True),
        CheckConstraint(r"label ~ '^\S+(?:\s\S+)*$'", "label_well_formatted"),
    )

    tag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(Tag.id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[Tag] = relationship(Tag, back_populates="label_objs")

    language_objs: Mapped[set[Language]] = relationship(
        Language, secondary=tag_language_table, collection_class=set, lazy="joined"
    )
    languages = association_proxy("language_objs", "iso_code")

    _label: Mapped[str] = mapped_column("label", UnicodeText, nullable=False, index=True)

    @hybrid_property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, label: str) -> None:
        label = label.strip()
        label = REPEATED_WS_RE.sub(" ", label)
        self._label = label

    @label.expression
    def label(cls):
        return cls._label
