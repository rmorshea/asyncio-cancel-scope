from __future__ import annotations

from functools import wraps
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from asyncio import Task
    from asyncio import TaskGroup
    from collections.abc import Callable
    from contextlib import AbstractAsyncContextManager

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # nocov
    __version__ = "0.0.0"


def cancel_scope(
    task_group: TaskGroup, /
) -> AbstractAsyncContextManager[tuple[TaskGroup, Callable[[], None]]]:
    """Yield the task group and a callback to cancel the task group."""
    return _CancelScope(task_group)


class _CancelScope:
    def __init__(self, task_group: TaskGroup) -> None:
        self.task_group = task_group
        self._tasks: set[Task] = set()

    def _cancel(self) -> None:
        """Cancel all tasks in the task group."""
        for task in self._tasks:
            if not task.done():
                task.cancel()

    async def __aenter__(self) -> tuple[TaskGroup, Callable[[], None]]:
        old_create_task = self.task_group.create_task

        @wraps(self.task_group.create_task)
        def new_create_task(*args: Any, **kwargs: Any) -> Task:
            task = old_create_task(*args, **kwargs)
            self._tasks.add(task)
            return task

        self.task_group.create_task = new_create_task
        await self.task_group.__aenter__()
        return self.task_group, self._cancel

    async def __aexit__(self, *args: Any) -> None:
        return await self.task_group.__aexit__(*args)
