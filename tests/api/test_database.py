from unittest import mock

import pytest

from marmolada.api import database


@pytest.mark.parametrize("with_exception", (False, True))
@mock.patch("marmolada.api.database.session_maker")
async def test_req_db_session(session_maker, with_exception):
    session_maker.return_value = db_session = mock.AsyncMock()

    sess_generator = database.req_db_session()

    session = await anext(sess_generator)

    assert session == db_session
    session_maker.assert_called_once_with()

    if not with_exception:
        with pytest.raises(StopAsyncIteration):
            await sess_generator.asend(None)
    else:
        exc = Exception("BOOP")
        with pytest.raises(Exception) as excinfo:
            await sess_generator.athrow(exc)

        assert excinfo.value == exc

    db_session.close.assert_awaited_once_with()
