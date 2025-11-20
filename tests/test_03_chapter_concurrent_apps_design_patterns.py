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
- Queues
- Creating subprocesses
- Debugging
Call graph introspection
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

[1](https://docs.python.org/3/library/asyncio-dev.html)
[2](https://realpython.com/async-io-python/)
[3](https://www.youtube.com/watch?v=JCbpcOd29eE)
[4](https://www.linkedin.com/advice/0/how-do-you-debug-asynchronous-python-applications-zaroc)
[5](https://pymotw.com/3/asyncio/debugging.html)
[6](https://www.aiida.net/news/posts/2025-01-31-how-to-debug-async-in-aiida.html)
[7](https://python4data.science/en/latest/performance/asyncio-example.html)
[8](https://www.linkedin.com/advice/0/how-do-you-debug-async-code-python-more-efficiently-kevie)
[9](https://krython.com/tutorial/python/asyncio-debugging-tools-and-techniques/)
[10](https://python.readthedocs.io/fr/latest/library/asyncio-dev.html)
"""
