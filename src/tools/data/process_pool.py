"""Singleton subprocess pool for isolating crash-prone yfinance calls.

A SIGSEGV inside curl_cffi (yfinance's HTTP backend) kills whatever process
it happens in. The gateway runs its API server and cron scheduler as threads
in one process, so a crash there takes everything down. Running yfinance
calls in a `spawn`-started worker process means the crash only kills that
worker; the pool is recreated lazily on the next call.
"""

import multiprocessing
import threading
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from concurrent.futures.process import BrokenProcessPool

DEFAULT_TIMEOUT = 30

_lock = threading.Lock()
_executor: ProcessPoolExecutor | None = None
_spawn_context = multiprocessing.get_context("spawn")


def _get_executor() -> ProcessPoolExecutor:
    global _executor
    with _lock:
        if _executor is None:
            _executor = ProcessPoolExecutor(max_workers=1, mp_context=_spawn_context)
        return _executor


def run_isolated(fn, *args, timeout: float = DEFAULT_TIMEOUT):
    """Run fn(*args) in the isolated worker process and return its result.

    Raises BrokenProcessPool if the worker crashed (e.g. SIGSEGV) and
    concurrent.futures.TimeoutError if it didn't return in time. Either way
    the broken/stuck pool is torn down so the next call gets a fresh worker.
    """
    global _executor
    executor = _get_executor()
    future = executor.submit(fn, *args)
    try:
        return future.result(timeout=timeout)
    except (BrokenProcessPool, FutureTimeoutError):
        with _lock:
            if _executor is executor:
                executor.shutdown(wait=False)
                _executor = None
        raise
