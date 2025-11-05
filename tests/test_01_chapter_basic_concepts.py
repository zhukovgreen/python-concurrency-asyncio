# language=markdown
"""
# Chapter 1: Basic concepts.

This module introduces the fundamental concepts of Python's asyncio framework.

Main definitions:
- event loop: The core execution mechanism that manages and runs async tasks
- coroutine: An async function defined with 'async def', executed with 'await'
- task: A wrapper around a coroutine that schedules it to run on the event loop
- await: Keyword that suspends coroutine execution until the awaited operation
  completes
"""

import asyncio
import re
import threading
import time

import pytest


# language=markdown
"""
## Key concepts: event loop

It is a single threaded scheduler which is running in infinite cycle.
If normal sequential program runs the code as it is written - line by line,
then in concurrent programming the event loop decides on the order of
code execution.

------------------------------------------------------------
??? 

- Can we have more event loops in a single program?
------------------------------------------------------------

It does three things in cycle:

- Monitor OS I/O events (sockets, pipes, file descriptors) using an OS-level
  selector

  Kind of OS level "event loop" (called IO multiplexer) which allows easy
  querying batches of fds (sockets for IOs for example) and get the state if
  the fd is ready. While the fd is not ready the event loop can do a different
  job. If ready - the loop will resume a suspended task.

- Run ready callbacks scheduled via call_soon(), call_later(), or event
  handlers

  The event loop maintains multiple callback queues with different priorities:

  - call_soon() callbacks: Execute on the next iteration with the highest 
    priority
  - call_later(delay, callback) callbacks: Execute after a specified delay (via
    an internal timer)
  - call_at() is another callback scheduling method that works similarly to 
    call_later(), but with a crucial difference: it uses absolute time instea
    of relative delay
  - I/O callbacks: Execute when their associated I/O events complete
  - Signal handlers: Execute when OS signals arrive

- Resume coroutines whose awaited operations have completed

Basically schedules the task execution to continue once IO operation was
completed.

------------------------------------------------------------
???

- Why the loop.call_* callbacks are synchronous?
------------------------------------------------------------

Loop execution steps:

- The loop takes one job from its internal queues and invokes it (gives it control)
- The job runs until it hits an await point (!!! only for task, if this is a coro,
  then the task just continue)
- That coroutine yields control back to the event loop (if the task was awaited)
- The loop moves to the next job in the queue
- Once a pending I/O operation completes (OS selector), the loop schedules the
  associated callback/coroutine to resume
- This process repeats

Awesome resources:
[1] https://docs.python.org/3/howto/a-conceptual-overview-of-asyncio.html

"""


async def test_event_loop_creation_recommended_way():
    def _() -> None:
        # just a check that there is no event loop in this thread now
        with pytest.raises(
            RuntimeError,
            match=re.compile("no running event loop"),
        ):
            asyncio.get_running_loop()

        # this is the program entrypoint coro
        async def main():
            print("Creating and running my asyncio tasks")
            await asyncio.sleep(1)
            print("Program completed")
            loop = asyncio.get_running_loop()
            assert loop

        # if __name__ == "__main__":
        asyncio.run(main())

    background_thread = threading.Thread(target=_)
    background_thread.start()
    background_thread.join(timeout=5.0)


async def test_normal_function_vs_async():
    loop = asyncio.get_running_loop()
    print(loop)

    def foo(): ...
    async def bar(): ...

    print(foo())
    # look how similar it is with the generator function
    print(bar())
    print(bar)
    # for generators, you need to use next(bar), for coros - await
    print(await bar())


async def test_loop_call_scheduling():
    loop = asyncio.get_running_loop()

    def callback_soon():
        print("call_soon at", loop.time())

    def callback_later():
        print("call_later at", loop.time())

    def callback_at():
        print("call_at at", loop.time())

    now = loop.time()
    print(now)

    loop.call_soon(callback_soon)
    loop.call_later(0.5, callback_later)
    loop.call_at(now + 0.2, callback_at)

    await asyncio.sleep(1)


# language=markdown
"""
## Asyncio tasks

Tasks are coroutines (not coroutine functions) tied to an
event loop. A task also maintains a list of callback functions whose importance
will become clear in a moment when we will be running await snippet. 

The recommended way to create tasks is via asyncio.create_task().

Creating a task automatically schedules it for execution (by adding a callback
to run it in the event loop’s to-do list, that is, collection of jobs).

Since there’s only one event loop (in each thread), asyncio takes care of
associating the task with the event loop for you. As such, there’s no need to
specify the event loop
"""

# language=markdown
"""
## Demonstrate the difference between tasks and coroutines

Key concepts:
- asyncio.create_task() schedules a coroutine to run by the event loop
- direct 'await' on a coroutine runs it sequentially

The awaited coroutine runs within the current task until it hits a
suspension point (like I/O operations, asyncio.sleep(), or other
awaitables that truly yield control(i.e. tasks))
"""


# ??? What is going to be printed?
async def test_tasks_vs_coroutine():
    async def coro_a():
        print("I am coro_a(). Hi!")

    async def coro_b():
        print("I am coro_b(). I sure hope no one hogs the event loop...")

    async def main():
        task_b = asyncio.create_task(coro_b())
        num_repeats = 3
        for _ in range(num_repeats):
            await coro_a()
        await task_b

    await main()


# ??? What is going to be printed?
async def test_tasks_loop_execution():
    async def coro_a():
        print("I am coro_a(). Hi!")
        await asyncio.sleep(5)
        print("I am coro_a(). Hi again!")

    async def coro_b():
        print("I am coro_b(). I sure hope no one hogs the event loop...")
        time.sleep(2)

    async def bad_task():
        raise ValueError("bad task failed!")

    async def main():
        asyncio.create_task(coro_b())
        num_repeats = 3
        for _ in range(num_repeats):
            asyncio.create_task(coro_a())

    await main()
    await asyncio.sleep(1)
    # await asyncio.sleep(10)
    # t = asyncio.create_task(bad_task())
