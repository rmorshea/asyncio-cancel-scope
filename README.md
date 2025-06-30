# Asyncio Cancel Scope

[![PyPI - Version](https://img.shields.io/pypi/v/asyncio_cancel_scope.svg)](https://pypi.org/project/asyncio_cancel_scope)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/asyncio_cancel_scope.svg)](https://pypi.org/project/asyncio_cancel_scope)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A utility for cancelling asyncio task groups in the
[absence](https://github.com/python/cpython/issues/108951) of one from the standard
library.

## Installation

```bash
pip install asyncio_cancel_scope
```

## Usage

The `cancel_scope` function allows you to cleanly cancel all the tasks within a task
group:

```python
import asyncio
from asyncio_cancel_scope import cancel_scope

async def main():
    async with cancel_scope(asyncio.TaskGroup()) as (tg, cancel):
        tg.create_task(asyncio.sleep(1))
        tg.create_task(asyncio.sleep(2))
        tg.create_task(asyncio.sleep(3))
        tg.create_task(asyncio.sleep(4))
        cancel()  # cancels all tasks in the group and exits without an exception

asyncio.run(main())
```

## Alternatives

Without this you'd need to manually cancel each task in the group, which can be
cumbersome and error-prone:

```python
import asyncio


async def main():
    tasks = []
    async with asyncio.TaskGroup() as tg:
        tasks.append(tg.create_task(asyncio.sleep(1)))
        tasks.append(tg.create_task(asyncio.sleep(2)))
        tasks.append(tg.create_task(asyncio.sleep(3)))
        tasks.append(tg.create_task(asyncio.sleep(4)))
        for task in tasks:
            task.cancel()  # manually cancel each task
            try:
                await task  # wait until the task is cancelled
            except asyncio.CancelledError:
                pass  # supress the cancellation exception
```

## Under the Hood

Behind the scenes, `cancel_scope` creates a background task to run the task group. This
makes it easy to cancel all the group's underlying tasks without needing to manually
track them. The implementation looks roughly like this:

```python
import asyncio
import contextlib


@contextlib.asynccontextmanager
async def cancel_scope(tg):
    did_enter = asyncio.Event()
    will_exit = asyncio.Event()
    did_exit = asyncio.Event()

    async def wrapper():
        try:
            async with tg:
                did_enter.set()
                await will_exit.wait()
        finally:
            did_exit.set()

    task = asyncio.create_task(wrapper())
    await did_enter.wait()  # ensure the task has entered the context manager

    try:
        yield tg, task.cancel
        will_exit.set()
        await did_exit.wait()
    except BaseException:
        if task.cancel():
            with contextlib.suppress(asyncio.CancelledError):
                await task
        raise
```
