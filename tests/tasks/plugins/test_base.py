from asyncio import iscoroutinefunction
from contextlib import AbstractAsyncContextManager
from functools import partial
from importlib import metadata
from inspect import isawaitable
from types import ModuleType
from unittest import mock
from uuid import uuid4

import pytest

from marmolada.database import model
from marmolada.tasks.plugins import base


class IllegalPlugin:
    def __init__(self, name, *args, **kwargs):
        self.name = name


async def process_raises_exception(uuid):
    raise RuntimeError("Ah-ah, ah!")


TEST_PLUGIN_SPECS = [
    # unproblematic
    {"scope": "artifact", "name": "test1"},
    {"scope": "artifact", "name": "test2", "dependencies": ["test1", "test3"]},
    {"scope": "artifact", "name": "test3", "dependencies": ["test1"], "process": "sync"},
    {"scope": "import", "name": "test1"},
    {"scope": "import", "name": "test2", "dependencies": "test1"},
    # raising exception, depending in it
    {"scope": "artifact", "name": "test4", "process": process_raises_exception},
    {"scope": "artifact", "name": "test5", "dependencies": "test4"},
    # illegal plugin type
    {"scope": "artifact", "name": "illegaltype", "type": IllegalPlugin},
    # missing scope
    {"name": "missingscope"},
    # missing name
    {"scope": "artifact"},
    # process is missing
    {"scope": "artifact", "name": "missingprocess", "process": None},
    # process isn’t a function
    {"scope": "import", "name": "illegalprocess", "process": 13},
    # illegal scope
    {"scope": 5, "name": "illegalscopetype"},
    {"scope": "illegal", "name": "illegalscope"},
    # duplicate scope/name
    {"scope": "import", "name": "test1"},
    # unresolvable dependency
    {"scope": "artifact", "name": "unresolvable", "dependencies": "doesntexist"},
    # cyclic dependencies
    {"scope": "import", "name": "cyclic1", "dependencies": "cyclic3"},
    {"scope": "import", "name": "cyclic2", "dependencies": "cyclic1"},
    {"scope": "import", "name": "cyclic3", "dependencies": "cyclic1"},
    # illegal dependencies type
    {"scope": "artifact", "name": "illegaldependencies1", "dependencies": 5},
    {"scope": "artifact", "name": "illegaldependencies2", "dependencies": [7]},
]


@pytest.fixture
def plugin_objs():
    objs = []

    async def async_process_impl(scope, name, uuid):
        print(f"Async {scope}/{name}.process({uuid})")

    def sync_process_impl(scope, name, uuid):
        print(f"Sync {scope}/{name}.process({uuid})")

    for spec in TEST_PLUGIN_SPECS:
        obj = spec.get("type", ModuleType)(name=spec.get("name", ""))

        for item in ("name", "scope", "dependencies"):
            if item in spec:
                setattr(obj, item, spec[item])

        scope = getattr(obj, "scope", None)
        name = getattr(obj, "name", None)

        process = spec.get("process", partial(async_process_impl, scope, name))
        if process:
            if process == "sync":
                process = partial(sync_process_impl, scope, name)

            if iscoroutinefunction(process) or isawaitable(process):
                obj.process = mock.AsyncMock(wraps=process)
            elif callable(process):
                obj.process = mock.Mock(wraps=process)
            else:
                obj.process = process

        objs.append(obj)

    return objs


@pytest.fixture
def entry_points(plugin_objs):
    with mock.patch.object(base, "entry_points") as entry_points:
        mocked_entry_points = []

        for spec, obj in zip(TEST_PLUGIN_SPECS, plugin_objs, strict=False):
            scope = spec.get("scope", "unset")
            ep = mock.Mock()
            ep.name = spec.get("name", "entrypointname")
            ep.value = f"marmolada.tests.tasks.plugins.{scope}.{ep.name}"
            ep.group = "marmolada.tasks"
            ep.load.return_value = obj
            mocked_entry_points.append(ep)

        entry_points.return_value = epobj = metadata.EntryPoints(mocked_entry_points)

        yield epobj


@pytest.fixture
def mgr(entry_points):
    return base.TaskPluginManager()


class TestTaskPluginManager:
    def test___init__(self, mgr):
        assert mgr.scoped_plugins is None

    async def test_discover_plugins(self, plugin_objs, mgr, caplog):
        with caplog.at_level("DEBUG"):
            mgr.discover_plugins()

        assert sorted(mgr.scoped_plugins) == sorted(base.SCOPE_NAMES)
        assert [p for p in mgr.scoped_plugins["artifact"] if p in ("test1", "test2", "test3")] == [
            "test1",
            "test3",
            "test2",
        ]
        assert [p for p in mgr.scoped_plugins["artifact"] if p in ("test4", "test5")] == [
            "test4",
            "test5",
        ]
        assert list(mgr.scoped_plugins["import"]) == ["test1", "test2"]

        for plugin_issue in (
            ".artifact.illegaltype: must be a module",
            ".unset.missingscope: `scope` must be set",
            ".artifact.entrypointname: `name` must be set",
            ".artifact.missingprocess: `process` must be set",
            ".import.illegalprocess: `process` must be a callable",
            ".5.illegalscopetype: `scope` must be of type str",
            ".illegal.illegalscope: unknown scope: illegal",
            ".import.test1: duplicate scope/name: import/test1",
            ".artifact.illegaldependencies1: `dependencies` must be string or sequence",
            ".artifact.illegaldependencies2: `dependencies` must all be strings",
            "Unresolvable dependencies between artifact plugins: unresolvable",
            "Unresolvable dependencies between import plugins: cyclic1, cyclic2, cyclic3",
        ):
            assert plugin_issue in caplog.text

    @pytest.mark.parametrize("scope", ("artifact", "import"))
    async def test_process_scope(self, scope, plugin_objs, mgr, capsys, caplog):
        mgr.discover_plugins()

        uuid = uuid4()
        match scope:
            case "artifact":
                scoped_obj = model.Artifact(uuid=uuid)
            case "import":
                scoped_obj = model.Import(uuid=uuid)

        caplog.clear()

        with mock.patch("marmolada.tasks.plugins.base.session_maker") as session_maker:
            session_maker.return_value = ctxmgr = mock.MagicMock(AbstractAsyncContextManager)
            db_session = ctxmgr.__aenter__.return_value = mock.AsyncMock()
            db_session.add = mock.Mock()
            db_session.execute.return_value = query_result = mock.Mock()
            query_result.one.return_value = scoped_obj

            await mgr.process_scope(scope, uuid)

        added_db_objs = [call[0][0] for call in db_session.add.call_args_list]

        out, err = capsys.readouterr()

        if scope == "artifact":
            expected_output = [
                f"Async artifact/test1.process({uuid})",
                f"Sync artifact/test3.process({uuid})",
                f"Async artifact/test2.process({uuid})",
            ]
        elif scope == "import":
            expected_output = [
                f"Async import/test1.process({uuid})",
                f"Async import/test2.process({uuid})",
            ]

        assert out.strip().split("\n") == expected_output

        match scope:
            case "artifact":
                assert all(isinstance(obj, model.ArtifactTask) for obj in added_db_objs)
                assert [o.name for o in added_db_objs] == ["test1", "test3", "test2"]

                assert f"Task plugin artifact/test4[{uuid}] raised exception" in caplog.messages
                assert (
                    f"Skipping plugin artifact/test5[{uuid}] due to unfulfilled deps: test4"
                    in caplog.messages
                )
            case "import":
                assert all(isinstance(obj, model.ImportTask) for obj in added_db_objs)
                assert [o.name for o in added_db_objs] == ["test1", "test2"]

    async def test_process_scope_without_discovery(self, mgr):
        with pytest.raises(
            RuntimeError, match=r"\.discover_plugins\(\) must be called before \.process_scope\(\)"
        ):
            await mgr.process_scope("artifact", uuid4())
