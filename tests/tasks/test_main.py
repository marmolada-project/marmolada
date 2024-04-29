from uuid import uuid1

from marmolada.tasks import main

TEST_CTX = {}


async def test_process_artifact():
    uuid = uuid1()

    await main.process_artifact(TEST_CTX, uuid)

    # Right not it’s just an empty skeleton…


async def test_process_import():
    uuid = uuid1()

    await main.process_import(TEST_CTX, uuid)

    # Right not it’s just an empty skeleton…
