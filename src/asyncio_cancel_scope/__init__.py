from __future__ import annotations

from asyncio import CancelledError
from asyncio import Event
from asyncio import Task
from asyncio import TaskGroup
from asyncio import create_task
from asyncio import current_task
from asyncio import wait
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from typing import TYPE_CHECKING
from typing import Protocol

if TYPE_CHECKING:
    import types
    from contextlib import AbstractAsyncContextManager

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # nocov
    __version__ = "0.0.0"


def cancel_scope(
    task_group: TaskGroup, /
) -> AbstractAsyncContextManager[tuple[TaskGroup, CancelCallback]]:
    """Yield the task group and a callback to cancel the task group."""
    return _CancelScope(task_group)


class CancelCallback(Protocol):
    """A callback to cancel a task group - same interface as Task.cancel()."""

    def __call__(self, msg: str | None = ..., /) -> bool:
        """Cancel the associated task group - same interface as Task.cancel()."""
        ...


class _CancelScope:
    def __init__(self, task_group: TaskGroup) -> None:
        self.task_group = task_group
        self._cancelled_scope = False

    def cancel(self, msg: str | None = None) -> bool:
        """Cancel the associated task group - same interface as Task.cancel()."""
        self._cancelled_scope = True
        return self._task.cancel(msg)
        

    async def __aenter__(self) -> tuple[TaskGroup, CancelCallback]:
        self._did_enter = Event()
        self._will_exit = Event()
        self._did_exit = Event()

        self._task = create_task(
            _wrapper(self.task_group, self._did_enter, self._will_exit)
        )

        did_enter_task = create_task(self._did_enter.wait())

        done, _ = await wait([did_enter_task, self._task], return_when="FIRST_COMPLETED")

        if self._task in done:
            did_enter_task.cancel()
            await self._task
            raise AssertionError(  # nocov  # noqa: TRY003
                "Task exited before entering the context manager"  # noqa: EM101
            )

        return self.task_group, self.cancel

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: types.TracebackType | None,
    ) -> None:
        self._will_exit.set()

        if exc_type is not None:
            try:  # noqa: SIM105
                await _cancel_and_wait(self._task)
            except CancelledError:
                pass
            return

        try:
            await self._task
        except CancelledError:
            if self._cancelled_scope:
                return
            raise


async def _wrapper(task_group: TaskGroup, did_enter: Event, will_exit: Event):
    async with task_group:
        did_enter.set()
        await will_exit.wait()


async def _cancel_and_wait(task: Task, msg: str | None = None) -> None:
    # copied from: https://github.com/python/cpython/issues/103486#issue-1665155187
    task.cancel(msg)
    try:
        await task
    except CancelledError:
        if (ct := current_task()) and ct.cancelling() == 0:
            raise
        return  # this is the only non-exceptional return
    else:  # nocov
        msg = "Cancelled task did not end with an exception"
        raise RuntimeError(msg)
