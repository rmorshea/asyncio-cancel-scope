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

The `cancel_scope` function allows you to establish a task group that can be cancelled
with the `cancel_group` function. This is useful for managing multiple tasks that should
be stopped together.

```python
import asyncio
from asyncio_cancel_scope import cancel_scope, cancel_group

async def main():
    async with cancel_scope(asyncio.TaskGroup()) as tg:
        tg.create_task(asyncio.sleep(1))
        tg.create_task(asyncio.sleep(2))
        tg.create_task(asyncio.sleep(3))
        tg.create_task(asyncio.sleep(4))
        cancel_group(tg)  # cancels all tasks in the group and exits without an exception

asyncio.run(main())
```

You can link cancel scopes so that parent task groups are cancelled when inner task
groups are.

```python
import asyncio
from asyncio_cancel_scope import cancel_scope, cancel_group

async def outer():
    forever = asyncio.Event()
    async with cancel_scope(asyncio.TaskGroup()) as outer_tg:
        outer_tg.create_task(forever.wait())
        outer_tg.create_task(inner(outer_tg))

async def inner(parent_tg):
    async with cancel_scope(asyncio.TaskGroup(), parent_tg) as inner_tg:
        cancel_group(inner_tg)

asyncio.run(outer())
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
```

## Under the Hood

The `cancel_group` function adds a task to the task group that immediately raises a
special exception. When this happens the behavior of `asyncio.TaskGroup` is to cancel
all tasks in the group and propagate the exception. The purpose of `cancel_scope` is to
supress that special exception so that it does not propagate to the caller of
`cancel_scope`.
