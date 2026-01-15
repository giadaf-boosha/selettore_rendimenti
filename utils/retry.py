"""
Decorator per retry con exponential backoff.
"""
import functools
import time
import logging
import random
from typing import Type, Tuple, Callable, Any

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] = None,
) -> Callable:
    """
    Decorator per retry con exponential backoff e jitter.

    Args:
        max_retries: Numero massimo di tentativi
        base_delay: Delay iniziale in secondi
        max_delay: Delay massimo in secondi
        exponential_base: Base per crescita esponenziale
        exceptions: Tuple di eccezioni da catchare
        on_retry: Callback opzionale chiamato prima di ogni retry

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        # Calcola delay con exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        # Aggiungi jitter (10-20%)
                        jitter = delay * random.uniform(0.1, 0.2)
                        actual_delay = delay + jitter

                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {actual_delay:.2f}s..."
                        )

                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(actual_delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator
