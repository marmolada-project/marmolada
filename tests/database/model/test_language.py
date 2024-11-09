import pytest
from sqlalchemy.exc import DBAPIError

from marmolada.database.model import Language

from .common import ModelTestBase


class TestLanguage(ModelTestBase):
    cls = Language

    attrs = {"iso_code": "en_US"}

    async def test_by_iso_code(self, db_session):
        new_lang = await Language.by_iso_code(db_session, "de_DE")
        await db_session.flush()

        assert new_lang.lang == "de"
        assert new_lang.territory == "DE"

        existing_lang = await Language.by_iso_code(db_session, "de_DE")

        assert existing_lang is new_lang

        another_lang = await Language.by_iso_code(db_session, "de")
        await db_session.flush()

        another_existing_lang = await Language.by_iso_code(db_session, "de")

        assert another_existing_lang is another_lang

    @pytest.mark.parametrize(
        "with_territory", (True, False), ids=("with-territory", "without-territory")
    )
    async def test_getters_setters(self, with_territory, db_session):
        if with_territory:
            iso_code = "it_CH"
        else:
            iso_code = "it"

        lang = Language(iso_code=iso_code)

        assert lang.lang == "it"
        assert lang.territory == ("CH" if with_territory else None)
        assert lang.iso_code == iso_code

        with pytest.raises(AttributeError):
            lang.iso_code = iso_code

    @pytest.mark.parametrize("iso_code", ("abc", "", "xz-15"))
    async def test_setter_illegal_isocodes(self, iso_code, db_session):
        with pytest.raises(ValueError, match="must match 'xx_XX'"):
            await Language.by_iso_code(db_session, iso_code)

    @pytest.mark.parametrize("lang, territory", (("de", "de"), ("deu", None), (None, "DE")))
    async def test_db_constraint_illegal_isocodes(self, lang, territory, db_session):
        # Bypass normalization through iso_code property
        lang = Language(_lang=lang, _territory=territory)
        db_session.add(lang)

        with pytest.raises(DBAPIError):
            await db_session.flush()
