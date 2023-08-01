from unittest import mock

import pytest

from marmolada.database.types import enum as db_enum


class FooEnum(db_enum.DeclEnum):
    val1 = "val1"
    val2 = "val2"


class TestDeclEnum:
    def test_db_type(self):
        db_type = FooEnum.db_type()

        # test caching
        assert db_type is FooEnum.db_type()

        # smoke test returned DeclEnumType
        assert isinstance(db_type, db_enum.DeclEnumType)
        assert db_type.enum is FooEnum
        assert db_type.impl.name == "foo_enum_enum"  # FooEnum -> lower/underscores + "_enum"
        assert set(db_type.impl.enums) == set(FooEnum.values())

    @pytest.mark.parametrize("strval", ("val1", "val2", "unknownval"))
    def test_from_string(self, strval):
        enumval = getattr(FooEnum, strval, None)

        if enumval:
            assert FooEnum.from_string(strval) is enumval
        else:
            with pytest.raises(ValueError):
                FooEnum.from_string(strval)

    def test_values(self):
        assert set(FooEnum.values()) == {"val1", "val2"}


class TestDeclEnumType:
    def test__set_table(self):
        db_type = FooEnum.db_type()
        table = object()
        column = object()

        with mock.patch.object(db_type, "impl") as impl:
            db_type._set_table(table, column)

        impl._set_table.assert_called_with(table, column)

    def test_copy(self):
        db_type = FooEnum.db_type()
        copied_type = db_type.copy()
        assert db_type is not copied_type
        assert db_type.enum is copied_type.enum

    @pytest.mark.parametrize("input_val", (None, "val1", FooEnum.db_type().enum.val1))
    def test_process_bind_param(self, input_val):
        db_type = FooEnum.db_type()
        output_val = db_type.process_bind_param(input_val, None)
        if input_val is None:
            assert output_val is None
        else:
            assert output_val == "val1"

    @pytest.mark.parametrize("input_val", (None, "val1"))
    def test_process_result_value(self, input_val):
        db_type = FooEnum.db_type()
        output_val = db_type.process_result_value(input_val, None)
        if input_val is None:
            assert output_val is None
        else:
            assert output_val == FooEnum.val1
