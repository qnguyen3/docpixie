"""
Async/sync compatibility helpers
"""

import asyncio
import threading
from typing import Any, Awaitable, TypeVar
from functools import wraps

T = TypeVar('T')


def sync_wrapper(coro: Awaitable[T]) -> T:
    """
    Run async function in sync context
    Handles both cases: existing event loop and no event loop
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # We're in an async context, need to run in a new thread
        return _run_in_thread(coro)
    except RuntimeError:
        # No running event loop, safe to use asyncio.run
        return asyncio.run(coro)


def _run_in_thread(coro: Awaitable[T]) -> T:
    """Run coroutine in a separate thread with its own event loop"""
    result = {"value": None, "exception": None}
    
    def thread_target():
        try:
            # Create new event loop for this thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            result["value"] = new_loop.run_until_complete(coro)
        except Exception as e:
            result["exception"] = e
        finally:
            new_loop.close()
    
    thread = threading.Thread(target=thread_target)
    thread.start()
    thread.join()
    
    if result["exception"]:
        raise result["exception"]
    
    return result["value"]


def ensure_async(func):
    """
    Decorator to ensure function is async-compatible
    If the function is sync, wrap it to run in thread pool
    """
    if asyncio.iscoroutinefunction(func):
        return func
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    return async_wrapper


def make_sync_version(async_func):
    """
    Create a synchronous version of an async function
    """
    @wraps(async_func)
    def sync_version(*args, **kwargs):
        coro = async_func(*args, **kwargs)
        return sync_wrapper(coro)
    
    return sync_version