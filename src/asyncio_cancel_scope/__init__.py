from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict

if TYPE_CHECKING:
    from asyncio import TaskGroup
    from collections.abc import Sequence
    from contextlib import AbstractAsyncContextManager

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # nocov
    __version__ = "0.0.0"


def cancel_scope(
    current_task_group: TaskGroup,
    /,
    *parent_task_groups: TaskGroup,
) -> AbstractAsyncContextManager[TaskGroup]:
    """Define a scope for cancelling tasks in a TaskGroup.

    Args:
        current_task_group:
            The task group being entered and which may be cancelled.
        parent_task_groups:
            Any other task groups that should also be cancelled when the current task group is.
            Note that these task groups must also have been established with the `cancel_scope`
            context manager.
    """
    if _get_cancel_scope_info(current_task_group) is not None:
        msg = f"Task group {current_task_group!r} was already established with cancel_scope()"
        raise RuntimeError(msg)

    for parent_tg in parent_task_groups:
        if _get_cancel_scope_info(parent_tg) is None:
            msg = f"Parent task group {parent_tg!r} was not established with cancel_scope()"
            raise RuntimeError(msg)
    scope = _CancelScope(current_task_group)
    _set_cancel_scope_info(current_task_group, {"parent_task_groups": parent_task_groups})
    return scope


def cancel_group(task_group: TaskGroup) -> None:
    """Cancel a task group and all its parent task groups."""
    info = _get_cancel_scope_info(task_group)
    if info is None:
        msg = f"Task group {task_group!r} was not established with cancel_scope()"
        raise RuntimeError(msg)
    task_group.create_task(_raise_stop())
    for parent_tg in info["parent_task_groups"]:
        parent_tg.create_task(_raise_stop())


class _CancelScope:
    __slots__ = ("_task_group",)

    def __init__(self, task_group: TaskGroup) -> None:
        self._task_group = task_group

    async def __aenter__(self) -> TaskGroup:
        tg = self._task_group
        await tg.__aenter__()
        return tg

    async def __aexit__(self, *args: Any) -> None:
        try:
            await self._task_group.__aexit__(*args)
        except ExceptionGroup as eg:
            match eg.exceptions:
                case [_StopTaskGroupError()]:
                    pass
                case _:
                    raise

    def __repr__(self) -> str:
        return f"<CancelScope task_group={self._task_group!r}>"


async def _raise_stop() -> None:  # noqa: RUF029
    """Raise _Stop to signal the task group to stop.

    If a non-CancelledError is raised, the TaskGroup will cancel all other tasks and exit.
    """
    raise _StopTaskGroupError


class _StopTaskGroupError(Exception):
    """Exception to stop the task group."""


def _set_cancel_scope_info(tg: TaskGroup, info: _ScopeInfo) -> None:
    """Set the cancel scope for a TaskGroup."""
    tg._asyncio_cancel_scope_info_ = info  # type: ignore[reportAttributeAccessIssue]


def _get_cancel_scope_info(tg: TaskGroup) -> _ScopeInfo | None:
    """Get the cancel scope for a TaskGroup."""
    info = getattr(tg, "_asyncio_cancel_scope_info_", None)
    if info is None:
        return None
    return info


class _ScopeInfo(TypedDict):
    """Information about the cancel scope."""

    parent_task_groups: Sequence[TaskGroup]
    """Any parent task groups that should also be cancelled."""
