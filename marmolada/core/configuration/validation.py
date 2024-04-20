from enum import Enum
from typing import Annotated, Literal

from pydantic import AnyUrl, BaseModel, Field, UrlConstraints

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


class LoggingModel(BaseModel):
    version: Literal[1]

    class Config:
        extra = "allow"


class APIModel(BaseModel):
    loglevel: LogLevel | None = None
    host: str | None = None
    port: Annotated[int, Field(gt=0, lt=65536)] | None = None
    logging: LoggingModel | None = None


class ConfigModel(BaseModel):
    api: APIModel | None = None
    database: DatabaseModel | None = None
    tasks: TasksModel | None = None
