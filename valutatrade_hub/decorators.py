"""Decorators for the ValutaTrade Hub application."""

import functools
import time
from typing import Callable, Any
from valutatrade_hub.logging_config import get_logger

logger = get_logger("decorators")


def log_action(action_name: str = None):
    """
    Decorator to log function execution with timing.

    Args:
        action_name: Name of the action being logged (optional)

    Usage:
        @log_action("User Registration")
        def register_user(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            name = action_name or func.__name__
            start_time = time.time()

            logger.info(f"Starting action: {name}")

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Completed action: {name} (took {elapsed:.3f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"Failed action: {name} after {elapsed:.3f}s - {type(e).__name__}: {e}"
                )
                raise

        return wrapper

    return decorator
