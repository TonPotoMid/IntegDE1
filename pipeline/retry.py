"""Mécanisme de retry générique avec backoff exponentiel."""
from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")
log = logging.getLogger(__name__)


def retry(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            wait = delay
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == attempts:
                        log.error("%s: échec définitif après %d tentatives (%s)", func.__name__, attempts, exc)
                        raise
                    log.warning(
                        "%s: tentative %d/%d échouée (%s), retry dans %.1fs",
                        func.__name__, attempt, attempts, exc, wait,
                    )
                    sleep(wait)
                    wait *= backoff
            raise AssertionError("unreachable")

        return wrapper

    return decorator
