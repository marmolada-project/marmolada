from marmolada.database import util


def test_utcnow(db_engine):
    compiled = util.utcnow().compile(dialect=db_engine.dialect)
    assert str(compiled) == "(NOW() AT TIME ZONE 'utc')"
