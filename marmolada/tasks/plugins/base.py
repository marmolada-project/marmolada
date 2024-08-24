import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from importlib.metadata import entry_points
from types import ModuleType
from typing import Literal, assert_never, get_args
from uuid import UUID

from sqlalchemy import select

from ...database import session_maker
from ...database.model import Artifact, ArtifactTask, Import, ImportTask

ScopeType = Literal["artifact", "import"]
SCOPE_NAMES: tuple[ScopeType, ...] = get_args(ScopeType)

log = logging.getLogger(__name__)


class TaskPluginManager:
    scoped_plugins: dict[str, list[ModuleType]] | None

    def __init__(self) -> None:
        self.scoped_plugins = None

    def discover_plugins(self) -> None:
        ordered_scope_plugins: dict[str, dict[str, ModuleType]] = {}

        unsorted_plugins: defaultdict[str, dict[str, ModuleType]] = defaultdict(dict)

        for entry_point in entry_points(group="marmolada.tasks"):
            module = entry_point.load()

            errors = []

            if not isinstance(module, ModuleType):
                errors.append("must be a module")

            for item_name in ("scope", "name", "dependencies", "process"):
                item_value = getattr(module, item_name, None)

                match item_name:
                    case "dependencies":
                        item_types = str | Sequence
                    case "process":
                        item_types = Callable
                    case _:
                        item_types = str

                if item_value is None:
                    if item_name != "dependencies":
                        errors.append(f"`{item_name}` must be set")
                else:
                    if not isinstance(item_value, item_types):
                        match item_name:
                            case "process":
                                errors.append(f"`{item_name}` must be a callable")
                            case "dependencies":
                                errors.append(f"`{item_name}` must be string or sequence")
                            case _:
                                item_types = getattr(item_types, "__name__", item_types)
                                errors.append(f"`{item_name}` must be of type {item_types}")
                    else:
                        match item_name:
                            case "scope":
                                if item_value not in SCOPE_NAMES:
                                    errors.append(f"unknown scope: {item_value}")
                            case "name":
                                if (
                                    hasattr(module, "scope")
                                    and item_value in unsorted_plugins[module.scope]
                                ):
                                    errors.append(
                                        f"duplicate scope/name: {module.scope}/{item_value}"
                                    )
                            case "dependencies":
                                if isinstance(item_value, Sequence) and any(
                                    not isinstance(x, str) for x in item_value
                                ):
                                    errors.append("`dependencies` must all be strings")

            if errors:
                log.error(
                    "Skipping broken task plugin %s: %s", entry_point.value, ", ".join(errors)
                )
                continue

            if not hasattr(module, "dependencies"):
                module.dependencies = ()
            elif isinstance(module.dependencies, str):
                module.dependencies = (module.dependencies,)
            unsorted_plugins[module.scope][module.name] = module

        for scope, plugins in unsorted_plugins.items():
            if not plugins:
                continue
            ordered_scope_plugins[scope] = scope_plugins = {}

            while plugins:
                fulfilled_plugins = []

                for name, plugin in plugins.items():
                    if plugin.dependencies and any(
                        dep not in scope_plugins for dep in plugin.dependencies
                    ):
                        continue
                    scope_plugins[name] = plugin
                    fulfilled_plugins.append(name)

                if not fulfilled_plugins:
                    leftovers = ", ".join(plugins)
                    log.error("Unresolvable dependencies between %s plugins: %s", scope, leftovers)
                    plugins = None
                else:
                    for name in fulfilled_plugins:
                        del plugins[name]

        self.scoped_plugins = ordered_scope_plugins

    async def process_scope(self, scope: ScopeType, uuid: UUID) -> None:
        if self.scoped_plugins is None:
            raise RuntimeError(f"{self}.discover_plugins() must be called before .process_scope()")

        plugins_raised_exception = set()
        for plugin in self.scoped_plugins[scope].values():
            unfulfilled_deps = [
                dep for dep in plugin.dependencies if dep in plugins_raised_exception
            ]
            if unfulfilled_deps:
                log.warning(
                    "Skipping plugin %s/%s[%s] due to unfulfilled deps: %s",
                    plugin.scope,
                    plugin.name,
                    uuid,
                    ", ".join(unfulfilled_deps),
                )
                continue

            try:
                maybe_awaitable = plugin.process(uuid)
                if isinstance(maybe_awaitable, Awaitable):
                    await maybe_awaitable
            except Exception:
                log.exception(
                    "Task plugin %s/%s[%s] raised exception", plugin.scope, plugin.name, uuid
                )
                plugins_raised_exception.add(plugin.name)
            else:
                async with session_maker() as db_session:
                    match scope:
                        case "artifact":
                            artifact = (
                                await db_session.execute(select(Artifact).filter_by(uuid=uuid))
                            ).one()
                            task = ArtifactTask(name=plugin.name, artifact=artifact)
                        case "import":
                            import_ = (
                                await db_session.execute(select(Import).filter_by(uuid=uuid))
                            ).one()
                            task = ImportTask(name=plugin.name, import_=import_)
                        case _ as unreachable:
                            assert_never(unreachable)
                    db_session.add(task)
