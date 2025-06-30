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

Behind the scenes, `cancel_scope` patches the `TaskGroup` to capture the tasks created
within it. When the `cancel` callback is called, it cancels all those tasks.
