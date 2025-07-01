from __future__ import annotations

from contextvars import ContextVar
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from asyncio import TaskGroup
    from collections.abc import Sequence
    from contextlib import AbstractAsyncContextManager

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # nocov
    __version__ = "0.0.0"


def cancel_scope(
    target_task_group: TaskGroup,
    /,
    *parent_task_groups: TaskGroup,
) -> AbstractAsyncContextManager[TaskGroup]:
    """Define a scope for cancelling tasks in a TaskGroup.

    Args:
        target_task_group:
            The target task group being entered and which may be cancelled.
        parent_task_groups:
            Any other task groups that should also be cancelled if the target task group is.
            Note that these task groups must also have been established in an outer cancel scope
            before this function is called, otherwise a RuntimeError will be raised.
    """
    if missing := set(parent_task_groups).difference(_SCOPED_TASK_GROUPS.get()):
        msg = f"No cancel scope for {len(missing)} parent task group(s)"
        raise RuntimeError(msg)
    return _CancelScope(target_task_group, parent_task_groups)


def cancel_group(task_group: TaskGroup) -> None:
    """Cancel a task group and all its parent task groups."""
    if task_group not in _SCOPED_TASK_GROUPS.get():
        msg = f"Task group {task_group} does not have a cancel scope established."
        raise RuntimeError(msg)
    task_group.create_task(_raise_stop())


class _CancelScope:
    __slots__ = (
        "_parent_task_groups",
        "_scoped_task_groups_token",
        "_target_task_group",
    )

    def __init__(
        self,
        target_task_group: TaskGroup,
        parent_task_groups: Sequence[TaskGroup],
    ) -> None:
        self._target_task_group = target_task_group
        self._parent_task_groups = parent_task_groups

    async def __aenter__(self) -> TaskGroup:
        tg = self._target_task_group
        self._scoped_task_groups_token = _SCOPED_TASK_GROUPS.set(_SCOPED_TASK_GROUPS.get() | {tg})
        await tg.__aenter__()
        return tg

    async def __aexit__(self, *args: Any) -> None:
        _SCOPED_TASK_GROUPS.reset(self._scoped_task_groups_token)
        try:
            await self._target_task_group.__aexit__(*args)
        except ExceptionGroup as eg:
            match eg.exceptions:
                case [_StopTaskGroupError()]:
                    for parent_tg in self._parent_task_groups:
                        cancel_group(parent_tg)
                case _:
                    raise

    def __repr__(self) -> str:
        return "AsyncioCancelScope()"


async def _raise_stop() -> None:  # noqa: RUF029
    """Raise _Stop to signal the task group to stop.

    If a non-CancelledError is raised, the TaskGroup will cancel all other tasks and exit.
    """
    raise _StopTaskGroupError


class _StopTaskGroupError(Exception):
    """Exception to stop the task group."""


_SCOPED_TASK_GROUPS = ContextVar("SCOPED_TASK_GROUPS", default=frozenset["TaskGroup"]())
