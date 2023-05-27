from enum import Enum
from typing import Literal

from pydantic import AmqpDsn, BaseModel, RedisDsn, conint, stricturl

# types


class LogLevel(str, Enum):
    trace = "trace"
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


AmqpRpcDsn = stricturl(host_required=False, allowed_schemes=("rpc",))


# Pydantic models


class CeleryModel(BaseModel):
    broker_url: AmqpDsn | RedisDsn
    result_backend: AmqpRpcDsn | RedisDsn


class TasksModel(BaseModel):
    celery: CeleryModel


class SQLAlchemyModel(BaseModel):
    url: stricturl(tld_required=False, host_required=False)


class DatabaseModel(BaseModel):
    sqlalchemy: SQLAlchemyModel


class LoggingModel(BaseModel):
    version: Literal[1]

    class Config:
        extra = "allow"


class APIModel(BaseModel):
    loglevel: LogLevel | None
    host: str | None
    port: conint(gt=0, lt=65536) | None
    logging: LoggingModel | None


class ConfigModel(BaseModel):
    api: APIModel | None
    database: DatabaseModel | None
    tasks: TasksModel | None
