import datetime as dt

import pytest

from marmolada.database.types import TZDateTime


class SQLATypeDecoratorTest:
    db_type: type = None

    @staticmethod
    def pytest_generate_tests(metafunc):
        match metafunc.function.__name__:
            case "test_process_bind_param":
                metafunc.parametrize(
                    "input_value, expected_result", metafunc.cls.process_bind_param_testcases
                )
            case "test_process_result_value":
                metafunc.parametrize(
                    "input_value, expected_result", metafunc.cls.process_result_value_testcases
                )

    def test_process_bind_param(self, input_value, expected_result):
        db_type_obj = self.db_type()
        if isinstance(expected_result, type) and issubclass(expected_result, Exception):
            with pytest.raises(expected_result):
                db_type_obj.process_bind_param(input_value, "dialect")
        else:
            assert db_type_obj.process_bind_param(input_value, "dialect") == expected_result

    def test_process_result_value(self, input_value, expected_result):
        db_type_obj = self.db_type()
        if isinstance(expected_result, type) and issubclass(expected_result, Exception):
            with pytest.raises(expected_result):
                db_type_obj.process_result_value(input_value, "dialect")
        else:
            assert db_type_obj.process_result_value(input_value, "dialect") == expected_result


class TestTZDateTime(SQLATypeDecoratorTest):
    db_type = TZDateTime

    process_bind_param_testcases = (
        (None, None),
        (dt.datetime(2023, 1, 1), TypeError),
        (dt.datetime(2023, 1, 1).replace(tzinfo=dt.UTC), dt.datetime(2023, 1, 1)),
    )

    process_result_value_testcases = (
        (None, None),
        (dt.datetime(2023, 1, 1), dt.datetime(2023, 1, 1).replace(tzinfo=dt.UTC)),
    )
