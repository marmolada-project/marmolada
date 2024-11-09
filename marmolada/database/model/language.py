import re

from sqlalchemy import CheckConstraint, String, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import SQLColumnExpression, case

from .. import Base
from ..mixins import BigIntPrimaryKey, Creatable, Updatable, UuidAltKey

LANG_RE = re.compile(r"^[a-z]{2}$")
TERRITORY_RE = re.compile(r"^[A-Z]{2}$")


class Language(Base, BigIntPrimaryKey, UuidAltKey, Creatable, Updatable):
    __tablename__ = "languages"
    __table_args__ = (
        UniqueConstraint("lang", "territory"),
        CheckConstraint(r"lang ~ '^[a-z][a-z]$'", "lang_compliant"),
        CheckConstraint(r"territory is null or territory ~ '^[A-Z][A-Z]$'", "territory_compliant"),
    )

    _lang: Mapped[str] = mapped_column("lang", String(2), nullable=False)
    _territory: Mapped[str | None] = mapped_column("territory", String(2))

    @classmethod
    async def by_iso_code(cls, session: AsyncSession, iso_code: str) -> "Language":
        try:
            with session.no_autoflush:
                obj = (await session.execute(select(cls).filter_by(iso_code=iso_code))).scalar_one()
        except NoResultFound:
            obj = cls(iso_code=iso_code)
            session.add(obj)
        return obj

    @hybrid_property
    def lang(self) -> str:
        return self._lang

    @hybrid_property
    def territory(self) -> str:
        return self._territory

    @hybrid_property
    def iso_code(self) -> str:
        if self.territory:
            return f"{self.lang}_{self.territory}"
        else:
            return self.lang

    @iso_code.setter
    def iso_code(self, iso_code: str) -> None:
        if self._lang or self._territory:
            raise AttributeError("iso_code can’t be changed")

        try:
            lang, territory = iso_code.split("_", 1)
        except ValueError:
            lang = iso_code
            territory = None

        if not LANG_RE.match(lang) or (territory is not None and not TERRITORY_RE.match(territory)):
            raise ValueError(f"iso_code {iso_code!r} must match 'xx_XX'")

        self._lang, self._territory = lang, territory

    @iso_code.expression
    def iso_code(cls) -> SQLColumnExpression:
        return case(
            (cls.territory != None, cls.lang + "_" + cls.territory),  # noqa: E711
            else_=cls.lang,
        )
