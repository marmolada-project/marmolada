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
RedisDsn = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["redis"], host_required=True)]


# Pydantic models


class TaskiqWorkerSettings(BaseModel):
    workers: int | None = None
    max_threadpool_threads: int | None = None
    shutdown_timeout: float | None = None
    max_async_tasks: int | None = None
    max_prefetch: int | None = None
    max_fails: int | None = None
    max_tasks_per_child: int | None = None
    wait_tasks_timeout: float | None = None
    hardkill_count: int | None = None
    use_process_pool: bool | None = None
    max_process_pool_processes: int | None = None


class TaskiqModel(BaseModel):
    broker_url: RedisDsn
    worker_settings: TaskiqWorkerSettings | None = TaskiqWorkerSettings()


class TasksModel(BaseModel):
    taskiq: TaskiqModel


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

    model_config = SettingsConfigDict(
        env_prefix="marmolada_",
        env_nested_delimiter="__",
    )

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
