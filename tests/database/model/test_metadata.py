import pytest

from marmolada.database.model import Artifact, ArtifactMetadata, Import

from .common import ModelTestBase


class UnknownType:
    pass


class TestArtifactMetadata(ModelTestBase):
    cls = ArtifactMetadata
    attrs = {"name": "name", "value": "value"}

    def _db_obj_get_dependencies(self):
        return {"artifact": Artifact(file_name="filename.ext", import_=Import())}

    @pytest.mark.parametrize(
        "value",
        (
            {"key": "value"},
            5,
            3.7,
            "a string",
        ),
    )
    def test_value(self, value):
        md = ArtifactMetadata(value=value)
        assert md.value == value
        match value:
            case dict():
                md_attr = md.json_value
            case int():
                md_attr = md.int_value
            case float():
                md_attr = md.float_value
            case str():
                md_attr = md.str_value

        assert md_attr == value

    def test_value_set_unknown_type(self):
        with pytest.raises(TypeError):
            _ = ArtifactMetadata(value=UnknownType())

    def test_value_get_unknown_type(self):
        md = ArtifactMetadata()
        with pytest.raises(TypeError):
            _ = md.value

    def test_value_set_again(self):
        md = ArtifactMetadata()
        md.value = "a value"
        with pytest.raises(ValueError):
            md.value = "another value"

    @pytest.mark.parametrize("value", (5, 3.7))
    def test_numeric_value(self, value):
        md = ArtifactMetadata(numeric_value=value)
        assert md.numeric_value == value
        match value:
            case int():
                md_attr = md.int_value
            case float():
                md_attr = md.float_value

        assert md_attr == value

    def test_numeric_value_set_illegal_type(self):
        with pytest.raises(TypeError):
            _ = ArtifactMetadata(numeric_value="Hello")

    def test_numeric_value_get_unknown_type(self):
        md = ArtifactMetadata()
        with pytest.raises(TypeError):
            _ = md.numeric_value

    def test_numeric_value_get_illegal_type(self):
        md = ArtifactMetadata(value="a string")
        with pytest.raises(TypeError):
            _ = md.numeric_value

    def test_numeric_value_set_again(self):
        md = ArtifactMetadata()
        md.numeric_value = 5
        with pytest.raises(ValueError):
            md.numeric_value = 6
