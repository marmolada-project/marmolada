from enum import Enum
from typing import Annotated, Literal

from pydantic import AmqpDsn, AnyUrl, BaseModel, Field, RedisDsn, UrlConstraints

# types


class LogLevel(str, Enum):
    trace = "trace"
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


AmqpRpcDsn = Annotated[AnyUrl, UrlConstraints(host_required=False, allowed_schemes=("rpc",))]

PostgreSQLDsn = Annotated[
    AnyUrl, UrlConstraints(allowed_schemes=["postgresql"], host_required=False)
]


# Pydantic models


class CeleryModel(BaseModel):
    broker_url: AmqpDsn | RedisDsn
    result_backend: AmqpRpcDsn | RedisDsn


class TasksModel(BaseModel):
    celery: CeleryModel


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
