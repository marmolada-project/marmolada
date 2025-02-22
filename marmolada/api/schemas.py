from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal
from uuid import UUID

from pydantic import AnyUrl, ConfigDict, Field, field_serializer, model_serializer
from pydantic import BaseModel as PydanticBaseModel

from .base import API_PREFIX

# Base


def hyphenize(fname: str) -> str:
    return fname.replace("_", "-")


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=hyphenize, populate_by_name=True
    )


class UUIDBaseModel(BaseModel):
    endpoint: ClassVar[str]

    self: str = ""
    uuid: UUID

    @field_serializer("self", check_fields=False)
    def fill_self(self, self_: Any) -> str:
        return f"{API_PREFIX}/{self.endpoint}/{self.uuid}"


class ResourceReference(UUIDBaseModel):
    """Reference another resource in the API.

    This serializes the uuid field to a REST URL.

    See:
    https://docs.pydantic.dev/2.6/concepts/serialization/#overriding-the-return-type-when-dumping-a-model
    """

    endpoint: ClassVar[str]

    @model_serializer
    def serialize_reference(self) -> str:
        return f"{API_PREFIX}/{self.endpoint}/{self.uuid}"

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(
            self,
            *,
            mode: Literal["json", "python"] | str = "python",
            include: Any = None,
            exclude: Any = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool = True,
        ) -> str: ...


# References


class ArtifactReference(ResourceReference):
    endpoint = "artifacts"


class ImportReference(ResourceReference):
    endpoint = "imports"


class TagReference(ResourceReference):
    endpoint = "tags"


# Imports


class ImportPost(BaseModel):
    meta: dict[str, Any] | None = None


class ImportPut(BaseModel):
    complete: bool


class ImportResult(UUIDBaseModel):
    endpoint = "imports"
    meta: dict[str, Any]
    complete: bool
    artifacts: list[ArtifactReference]


# Artifacts


class ArtifactPost(BaseModel):
    content_type: str | None = None
    source_uri: Annotated[AnyUrl | None, Field(alias="source-uri")] = None


class ArtifactPostLocal(ArtifactPost):
    source_uri: Annotated[AnyUrl, Field(alias="source-uri")]


class ArtifactResult(ArtifactPost, UUIDBaseModel):
    endpoint = "artifacts"
    import_: ImportReference = Field(alias="import")
    file_name: str


# Tags


class QualifiedTagLabel(BaseModel):
    label: Annotated[str, Field(pattern=r"^\S+(?:\s\S+)*$", examples=["Cab", "Taxi"])]
    languages: list[
        Annotated[
            str,
            Field(
                validation_alias="languages_by_iso_code",
                pattern=r"^\S\S(?:_\S\S)?$",
                examples=["en_US", "en_GB"],
            ),
        ]
    ]


class TagPost(BaseModel):
    labels: list[str | QualifiedTagLabel]
    parents: list[UUID] | None = None


class TagPut(BaseModel):
    labels: list[Annotated[str, Field(examples=["Dog", "Cat"])] | QualifiedTagLabel] | None = None
    parents: list[UUID] | None = None
    children: list[UUID] | None = None


class TagResult(UUIDBaseModel):
    endpoint = "tags"
    label_objs: Annotated[list[QualifiedTagLabel], Field(serialization_alias="labels")]
    parents: list[TagReference]
    children: list[TagReference]
