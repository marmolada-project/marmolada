import uuid

from marmolada.api import base, schemas


def test_hyphenize():
    assert schemas.hyphenize("a_b-c_d") == "a-b-c-d"


class Thing:
    def __init__(self, a_thing: int):
        self.uuid = uuid.uuid4()
        self.a_thing = a_thing


class ModelToTest(schemas.BaseModel):
    a_thing: int


class UUIDModelToTest(schemas.UUIDBaseModel):
    endpoint = "endpoint"
    a_thing: int


class Reference(UUIDModelToTest, schemas.ResourceReference):
    pass


class TestBaseModel:
    def test_validate(self):
        x = Thing(a_thing=5)
        o = ModelToTest.model_validate(x)
        assert o.a_thing == x.a_thing

    def test_by_alias(self):
        x = Thing(a_thing=5)
        o = ModelToTest.model_validate(x)
        assert o.model_dump(by_alias=True)["a-thing"] == x.a_thing


class TestUUIDBaseModel:
    def test_uuid(self):
        x = Thing(a_thing=10)
        o = UUIDModelToTest.model_validate(x)
        assert isinstance(o.uuid, uuid.UUID)
        assert o.uuid == x.uuid

    def test_self(self):
        x = Thing(a_thing=10)
        o = UUIDModelToTest.model_validate(x)
        assert o.model_dump()["self"] == f"{base.API_PREFIX}/{o.endpoint}/{o.uuid}"


class TestResourceReference:
    def test_serialize(self):
        x = Thing(a_thing=15)
        o = Reference.model_validate(x)
        assert o.model_dump() == f"{base.API_PREFIX}/{o.endpoint}/{o.uuid}"
