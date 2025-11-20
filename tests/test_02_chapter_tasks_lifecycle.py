# language=markdown
"""
# Chapter 2: Tasks lifecycle

It is very important to properly handle asyncio tasks lifecycle, because
the controlflow in the concurrent programming is not sequential and it is
easy to get into the situation where you're skipping important exceptions,
having zombie tasks (memory leakage) or never awaiting them.

These problems lead to creation of the dedicated design paradigm - structured
concurrency.

Key Concepts in structured concurrency:
Structured concurrency requires that concurrent tasks are organized in such a
way that their lifetimes are bound to well-scoped blocks of code

When a task spawns subtasks, these subtasks are treated as a group —
the parent waits for all subtasks to complete before proceeding, improving
reliability and error management.

Error handling and cancellation are streamlined: if a child task fails,
errors are automatically surfaced and the parent scope can react appropriately.

This model is influenced by structured programming, as it brings discipline to
concurrency in the same way that control constructs like if or for structure
sequential programs.
"""
import asyncio

from contextlib import suppress


# language=markdown
"""
## Tasks parenting, cancellations

Tasks can be cancelled due to:
- Manual task cancellation (task.cancel())
- Timeout (asyncio.wait_for, timeout, timeout_at)
- Event loop termination

Showing different potential problems when task is cancelled:
- parent task is cancelled, but child tasks exception is not handled
Very hard to debug
- parent task is cancelled, but children are still running
Memory leaks 
- Ways to solve this problem:
    - Manual task management
    - asyncio.gather
    - asyncio.TaskGroup
"""


async def test_parent_task_cancellation_exception_not_raised():
    """
    - One child failing doesn't automatically cancel siblings—you must handle this yourself
    - much boilerplate code - easy to forget
    - asyncio.create_task is very dangerous and can be garbage collected what
    leads to heisenbug
    https://textual.textualize.io/blog/2023/02/11/the-heisenbug-lurking-in-your-async-code/
    """

    async def child():
        raise ValueError("Child")

    async def parent():
        _ = asyncio.create_task(
            child(),
            name="child",
        )

    parent_task = asyncio.create_task(
        parent(),
        name="parent",
    )
    await asyncio.sleep(1)
    await parent_task


async def test_parent_task_cancelled_childs_are_running():
    async def child():
        await asyncio.sleep(5)

    async def parent():
        childs = [
            asyncio.create_task(
                child(),
                name=f"child_{_}",
            )
            for _ in range(10)
        ]
        await asyncio.sleep(5)

    parent_task = asyncio.create_task(
        parent(),
        name="parent",
    )
    await asyncio.sleep(1)
    parent_task.cancel()
    with suppress(asyncio.CancelledError):
        await parent_task
    all_tasks = asyncio.all_tasks()
    assert len(all_tasks) == 11
    for t in filter(lambda t: t.get_name().startswith("child_"), all_tasks):
        assert t.done() is False


async def test_gather_one_failure_does_not_cancel_siblings() -> None:
    async def success_task() -> None:
        await asyncio.sleep(5)

    async def fail_task() -> None:
        raise ValueError("Oops")

    task_1 = asyncio.create_task(success_task())
    task_2 = asyncio.create_task(fail_task())

    with suppress(ValueError):
        await asyncio.gather(task_1, task_2)

    assert task_2.done()
    assert not task_1.done()


# SOLUTION 1: Manual handling asyncio.CancelledError in each child tasks


async def test_how_to_handle_tasks_cancellation_solution_1():
    async def child():
        # raise ValueError()
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("Child was gracefully shut down")
            raise

    async def parent():
        children = [
            asyncio.create_task(
                child(),
                name=f"child_{_}",
            )
            for _ in range(10)
        ]
        try:
            await asyncio.sleep(5)
        finally:
            for child_ in children:
                child_.cancel()
                with suppress(asyncio.CancelledError):
                    await child_

    parent_task = asyncio.create_task(
        parent(),
        name="parent",
    )
    await asyncio.sleep(1)
    parent_task.cancel()
    with suppress(asyncio.CancelledError):
        await parent_task
    all_tasks = asyncio.all_tasks()
    assert len(all_tasks) == 1
    for t in filter(lambda t: t.get_name().startswith("child_"), all_tasks):
        assert t.done() is True
        assert t.cancelled() is True


# SOLUTION 2: Using asyncio.gather (automatically identifies cancellation and
#   cancels children


async def test_how_to_handle_tasks_cancellation_solution_2():
    """
    - If parent is not cancelled, and child error out, other tasks are not
    cancelled
    """

    async def child():
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("Child was gracefully shut down")
            raise

    async def parent():
        children = [
            asyncio.create_task(
                child(),
                name=f"child_{_}",
            )
            for _ in range(10)
        ]
        await asyncio.sleep(0)
        await asyncio.gather(*children)

    parent_task = asyncio.create_task(
        parent(),
        name="parent",
    )
    await asyncio.sleep(1)
    parent_task.cancel()
    with suppress(asyncio.CancelledError):
        await parent_task
    all_tasks = asyncio.all_tasks()
    assert len(all_tasks) == 1
    for t in filter(lambda t: t.get_name().startswith("child_"), all_tasks):
        assert t.done() is True
        assert t.cancelled() is True


# SOLUTION 3: Using structured concurrency - task groups


async def test_how_to_handle_tasks_cancellation_solution_3():
    """

    - failure of one child leads to cancellation of all siblings and also
    parent task
    - signal handling
    - Exception group is used for exception reporting
    - Special support of SIGTERM and SystemExit
    """

    async def child():
        # raise ValueError()
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("Child was gracefully shut down")
            raise

    async def parent():
        async with asyncio.TaskGroup() as tg:
            [
                tg.create_task(
                    child(),
                )
                for _ in range(10)
            ]

    parent_task = asyncio.create_task(
        parent(),
        name="parent",
    )
    await asyncio.sleep(1)
    parent_task.cancel()
    with suppress(asyncio.CancelledError):
        await parent_task
    all_tasks = asyncio.all_tasks()
    assert len(all_tasks) == 1
    for t in filter(lambda t: t.get_name().startswith("child_"), all_tasks):
        assert t.done() is True
        assert t.cancelled() is True
