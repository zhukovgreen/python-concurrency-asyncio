# language=markdown
"""
# Chapter 3: Architecture principles

To cover:
- synchronization primitives
- resource management (lifecycle)
- context variables https://docs.python.org/3/library/contextvars.html#module-contextvars
- delegating CPU intensive code to the process pool executor
- delegating I/O intensive synchronous code to the thread pool executor (
show on example with a time sleep or file read)
- asyncio.Queues
# - Creating subprocesses
- Debugging

Call graph introspection
"""
import asyncio
import concurrent

from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar


# language=markdown
"""
## Synchronization primitives

https://docs.python.org/3/library/asyncio-sync.html

What is important:
- primitives are not thread safe

"""


async def test_conditon_sync_primitive():

    cond = asyncio.Condition()
    queue: list[int] = []

    async def consumer() -> None:
        async with cond:
            await cond.wait_for(lambda: len(queue) > 0)
            item = queue.pop()
            print(f"Consumed {item}")

    async def producer() -> None:
        async with cond:
            queue.append(1)
            cond.notify()

    async def main() -> None:
        await asyncio.gather(consumer(), producer())

    await main()


async def test_barrier_primitive():
    barrier = asyncio.Barrier(3)

    async def worker(i: int) -> None:
        print(f"Worker {i} waiting at barrier")
        await barrier.wait()
        print(f"Worker {i} passed barrier")

    async def main() -> None:
        tasks = [worker(i) for i in range(3)]
        await asyncio.gather(*tasks)

    await main()


# language=markdown
"""
## Resource management

"""


async def test_database_connection_lifecycle() -> None:
    class DatabaseConnection:
        def __init__(self, db_url: str) -> None:
            self.db_url = db_url
            self.is_connected = False

        async def __aenter__(self) -> "DatabaseConnection":
            await asyncio.sleep(0.01)
            self.is_connected = True
            return self

        async def __aexit__(
            self,
            exc_type,
            exc,
            tb,
        ) -> None:
            await asyncio.sleep(0.01)
            self.is_connected = False

    connection = DatabaseConnection("postgres://localhost")

    assert not connection.is_connected

    async with connection as conn:
        assert conn.is_connected
        assert conn.db_url == "postgres://localhost"

    assert not connection.is_connected


async def test_dynamic_stack_management() -> None:
    class DatabaseConnection:
        def __init__(self, db_url: str) -> None:
            self.db_url = db_url
            self.is_connected = False

        async def __aenter__(self) -> "DatabaseConnection":
            await asyncio.sleep(0.01)
            self.is_connected = True
            return self

        async def __aexit__(
            self,
            exc_type,
            exc,
            tb,
        ) -> None:
            await asyncio.sleep(0.01)
            self.is_connected = False

    urls = ["db1", "db2", "db3"]
    connections = []

    async with AsyncExitStack() as stack:
        for url in urls:
            conn = await stack.enter_async_context(DatabaseConnection(url))
            connections.append(conn)

        assert len(connections) == 3
        assert all(c.is_connected for c in connections)

    assert all(not c.is_connected for c in connections)


async def test_asynccontextmanager_decorator():
    status = None

    @asynccontextmanager
    async def managed_resource(name: str):
        nonlocal status
        status = "active"
        await asyncio.sleep(0.01)

        try:
            yield status
        finally:
            status = "closed"
            await asyncio.sleep(0.01)

    async with managed_resource("test_res") as state:
        assert status == "active"
    assert status == "closed"


# language=markdown
"""
## Context variables

"""


async def test_context_isolation() -> None:
    ctx_id: ContextVar[str] = ContextVar("ctx_id", default="empty")

    async def worker(tag: str) -> None:
        ctx_id.set(tag)

        await asyncio.sleep(0.01)

        current = ctx_id.get()
        assert current == tag, f"Expected {tag}, got {current}"

    ctx_id.set("parent")

    async with asyncio.TaskGroup() as tg:
        tg.create_task(worker("A"))
        tg.create_task(worker("B"))

    assert ctx_id.get() == "parent"


# language=markdown
"""
## Process/Thread Pools


https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor

"""


async def test_run_in_executor():
    def blocking_io():
        # File operations (such as logging) can block the
        # event loop: run them in a thread pool.
        with open("/dev/urandom", "rb") as f:
            return f.read(100)

    def cpu_bound():
        # CPU-bound operations will block the event loop:
        # in general it is preferable to run them in a
        # process pool.
        return sum(i * i for i in range(10**7))

    async def main():
        loop = asyncio.get_running_loop()

        ## Options:

        # 1. Run in the default loop's executor:
        result = await loop.run_in_executor(None, blocking_io)
        print("default thread pool", result)

        # 2. Run in a custom thread pool:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, blocking_io)
            print("custom thread pool", result)

        # 3. Run in a custom process pool:
        with concurrent.futures.ProcessPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, cpu_bound)
            print("custom process pool", result)

        # 4. Run in a custom interpreter pool:
        with concurrent.futures.InterpreterPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, cpu_bound)
            print("custom interpreter pool", result)

    await main()

# language=markdown
"""
## asyncio.queue

https://docs.python.org/3/library/asyncio-queue.html#examples

"""
# language=markdown
"""
## Debug Mode Enablement

Debug mode is the **foundational tool** for debugging asyncio applications. Three methods can enable it:[1]

1. Setting the `PYTHONASYNCIODEBUG` environment variable to `1`[1]
2. Passing `debug=True` to `asyncio.run()`[1]
3. Calling `loop.set_debug(True)` on the event loop[1]

```python
import asyncio

loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
loop.set_debug(True)
asyncio.set_event_loop(loop)
```

Alternatively, use `asyncio.run()` with the debug flag:[1]

```python
asyncio.run(main_coro, debug=True)
```

## Enhanced Logging Configuration

When debug mode is active, configure logging to capture asyncio diagnostics:[1]

```python
import logging

logging.basicConfig(level=logging.DEBUG)
asyncio.run(main_coro, debug=True)
```

The asyncio module logs via the `"asyncio"` logger, configurable independently:[1]

```python
asyncio_logger: logging.Logger = logging.getLogger("asyncio")
asyncio_logger.setLevel(logging.DEBUG)
```

## Performance Monitoring

Debug mode includes automatic detection of **slow callbacks** that block the event loop. The default threshold is 100 milliseconds:[1]

```python
loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
loop.set_debug(True)
loop.slow_callback_duration: float = 0.001  # Set to 1ms for stricter detection
```

When enabled, callbacks exceeding this threshold are logged, and I/O selector operations taking excessive time are reported.[1]

## Exception Tracking

Debug mode provides traceback information for unhandled exceptions in tasks. Without debug mode, exceptions in unawaited tasks may be silently lost:[1]

Standard mode shows only the immediate error:

```python
import asyncio

async def failing_task() -> None:
    raise ValueError("Task failed")

async def main() -> None:
    asyncio.create_task(failing_task())

asyncio.run(main())  # Silent or minimal output
```

Debug mode reveals the task creation source:[1]

```python
asyncio.run(main(), debug=True)  # Prints full traceback and creation location
```

## Never-Awaited Coroutine Detection

Debug mode detects coroutines that are never awaited, preventing logic errors where coroutines are called but not scheduled:[1]

```python
import asyncio

async def fetch_data() -> str:
    return "data"

async def main() -> None:
    fetch_data()  # Called but not awaited - warning in debug mode

asyncio.run(main(), debug=True)
```

## Thread-Safety Enforcement

Debug mode raises exceptions when non-threadsafe asyncio APIs are called from wrong threads, preventing subtle race conditions:[1]

```python
loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
loop.set_debug(True)

callback: callable = lambda: None
loop.call_soon_threadsafe(callback)  # Correct cross-thread usage
```

## Resource Warning Configuration

Enable resource warnings to detect unclosed resources:[1]

```python
import asyncio
import warnings

warnings.simplefilter("always", ResourceWarning)
loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
loop.set_debug(True)
```
"""
