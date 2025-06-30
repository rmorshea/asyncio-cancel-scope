# ruff: noqa: PT012
import asyncio

import pytest

from asyncio_cancel_scope import _cancel_and_wait as cancel_and_wait
from asyncio_cancel_scope import cancel_scope


class FakeError(Exception):
    """Fake exception for testing purposes."""


async def test_cancel_scope():
    never = asyncio.Event()
    async with cancel_scope(asyncio.TaskGroup()) as (tg, cancel):
        tg.create_task(never.wait())
        cancel()


async def test_cancel_scope_with_exception():
    never = asyncio.Event()
    with pytest.raises(FakeError):
        async with cancel_scope(asyncio.TaskGroup()) as (tg, _):
            tg.create_task(never.wait())
            raise FakeError


async def test_outer_cancel_causes_task_group_to_cancel():
    did_cancel = False
    never = asyncio.Event()
    is_waiting = asyncio.Event()

    async def wait_forever():
        try:
            is_waiting.set()
            await never.wait()
        except asyncio.CancelledError:
            nonlocal did_cancel
            did_cancel = True
            raise

    async def wrapper():
        async with cancel_scope(asyncio.TaskGroup()) as (tg, _):
            tg.create_task(wait_forever())

    task = asyncio.create_task(wrapper())
    await is_waiting.wait()  # Ensure the inner task is running
    with pytest.raises(asyncio.CancelledError):
        await cancel_and_wait(task)


async def test_outer_error_causes_inner_cancel():
    did_cancel = False
    never = asyncio.Event()
    is_waiting = asyncio.Event()

    async def wait_forever():
        try:
            is_waiting.set()
            await never.wait()
        except asyncio.CancelledError:
            nonlocal did_cancel
            did_cancel = True
            raise

    with pytest.raises(FakeError):
        async with cancel_scope(asyncio.TaskGroup()) as (tg, _):
            tg.create_task(wait_forever())
            await is_waiting.wait()
            raise FakeError

    assert did_cancel


async def test_failure_on_enter_is_propagated():
    tg = asyncio.TaskGroup()

    async with tg:
        pass

    # Sanity check to ensure the task group raises if used more than once
    with pytest.raises(RuntimeError):
        async with tg:
            pass  # nocov

    # Now ensure the same error is propagated from the internal task to the outer scope
    with pytest.raises(RuntimeError):
        async with cancel_scope(tg) as _:
            pass  # nocov


async def test_internal_error_is_propagated():
    async def will_raise():
        raise FakeError

    with pytest.raises(ExceptionGroup):
        async with cancel_scope(asyncio.TaskGroup()) as (tg, _):
            tg.create_task(will_raise())
