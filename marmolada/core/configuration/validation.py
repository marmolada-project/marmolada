from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, UrlConstraints
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

# types


class LogLevel(str, Enum):
    trace = "trace"
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


PostgreSQLDsn = Annotated[
    AnyUrl, UrlConstraints(allowed_schemes=["postgresql"], host_required=False)
]


# Pydantic models


class ArqRedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379


class ArqWorkerSettings(BaseModel):
    queue_name: str = "marmolada.tasks"
    max_jobs: int | None = None
    job_timeout: int | float = 300
    poll_delay: int | float = 0.5
    queue_read_limit: int | None = None
    max_tries: int = 5
    health_check_interval: int = 3600
    health_check_key: str | None = None


class ArqModel(BaseModel):
    redis_settings: ArqRedisSettings | None = ArqRedisSettings()
    worker_settings: ArqWorkerSettings | None = ArqWorkerSettings()


class TasksModel(BaseModel):
    arq: ArqModel


class SQLAlchemyModel(BaseModel):
    url: PostgreSQLDsn


class DatabaseModel(BaseModel):
    sqlalchemy: SQLAlchemyModel


class ArtifactsModel(BaseModel):
    root: Path


class LoggingModel(BaseModel):
    version: Literal[1]

    model_config = ConfigDict(extra="allow")


class APIModel(BaseModel):
    loglevel: LogLevel | None = None
    host: str | None = None
    port: Annotated[int, Field(gt=0, lt=65536)] | None = None
    logging: LoggingModel | None = None


class ConfigModel(BaseSettings):
    api: APIModel | None = None
    artifacts: ArtifactsModel | None = None
    database: DatabaseModel | None = None
    tasks: TasksModel | None = None

    model_config = SettingsConfigDict(env_prefix="marmolada_", env_nested_delimiter="__")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return env_settings, dotenv_settings, init_settings, file_secret_settings
