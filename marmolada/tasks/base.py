import json
import logging
import os

from taskiq import AsyncBroker
from taskiq.brokers.shared_broker import async_shared_broker
from taskiq_redis import RedisStreamBroker

from .. import database
from ..core.configuration import config
from . import main
from .plugins import TaskPluginManager

log = logging.getLogger(__name__)


def configure_broker() -> AsyncBroker:
    log.info("Configuring broker …")

    broker_url = config["tasks"]["taskiq"]["broker_url"]
    configured_broker = RedisStreamBroker(broker_url)
    async_shared_broker.default_broker(configured_broker)

    log.info("Done configuring broker.")

    return configured_broker


def setup_broker_listen() -> AsyncBroker:
    log.info("Setting up broker to listen …")

    config.clear()
    config.update(json.loads(os.environ["MARMOLADA_CONFIG_JSON"]))

    configured_broker = configure_broker()

    database.init_model()
    main.plugin_mgr = TaskPluginManager()
    main.plugin_mgr.discover_plugins()

    log.info("Done setting up broker to listen.")

    return configured_broker
