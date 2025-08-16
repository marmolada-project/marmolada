from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Text, cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import SQLColumnExpression, case

from .. import Base

type JSONDict = dict[str, "JSONValue"]
type JSONType = list["JSONValue"] | JSONDict
type JSONValue = int | float | str | None | JSONType


class MetadataType(Enum):
    JSON = "json"
    INT = "int"
    FLOAT = "float"
    STR = "str"


class Metadata:
    name: Mapped[str] = mapped_column(primary_key=True)

    _type: Mapped[MetadataType] = mapped_column("type")

    json_value: Mapped[dict[str, Any] | None]
    int_value: Mapped[int | None]
    float_value: Mapped[float | None]
    str_value: Mapped[str | None]

    @hybrid_property
    def value(self) -> JSONValue:
        match self._type:
            case MetadataType.JSON:
                return self.json_value
            case MetadataType.INT:
                return self.int_value
            case MetadataType.FLOAT:
                return self.float_value
            case MetadataType.STR:
                return self.str_value
            case _:
                raise TypeError("_type unset")

    @value.setter
    def value(self, value: JSONValue) -> None:
        if self._type:
            raise ValueError("Value already set")
        match value:
            case dict():
                self._type = MetadataType.JSON
                self.json_value = value
            case int():
                self._type = MetadataType.INT
                self.int_value = value
            case float():
                self._type = MetadataType.FLOAT
                self.float_value = value
            case str():
                self._type = MetadataType.STR
                self.str_value = value
            case _:
                raise TypeError(f"Can’t store {value!r}, unknown type {type(value)}")

    @value.expression
    def value(cls) -> SQLColumnExpression:
        return case(
            (cls._type == MetadataType.JSON, cast(cls.json_value, Text)),
            (cls._type == MetadataType.INT, cast(cls.int_value, Text)),
            (cls._type == MetadataType.FLOAT, cast(cls.float_value, Text)),
            (cls._type == MetadataType.STR, cls.str_value),
        )

    @hybrid_property
    def numeric_value(self) -> int | float:
        match self._type:
            case MetadataType.INT:
                return self.int_value
            case MetadataType.FLOAT:
                return self.float_value
            case _:
                if self._type:
                    raise TypeError(f"Value isn’t numeric: {self.value}")
                else:
                    raise TypeError("_type unset")

    @numeric_value.setter
    def numeric_value(self, value: int | float) -> None:
        if self._type:
            raise ValueError("Value already set")
        match value:
            case int():
                self._type = MetadataType.INT
                self.int_value = value
            case float():
                self._type = MetadataType.FLOAT
                self.float_value = value
            case _:
                raise TypeError(f"Can’t store {value!r}, not of numerical type {type(value)}")

    @numeric_value.expression
    def numeric_value(cls) -> SQLColumnExpression:
        return case(
            (cls._type == MetadataType.INT, cls.int_value),
            (cls._type == MetadataType.FLOAT, cls.float_value),
        )


class ArtifactMetadata(Base, Metadata):
    __tablename__ = "artifact_metadata"

    artifact_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artifacts.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    artifact = relationship("Artifact", back_populates="metadata_objs")
