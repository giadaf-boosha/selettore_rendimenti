"""
Rate Limiter globale per tutte le fonti.

Thread-safe per uso con ThreadPoolExecutor.
"""
from collections import defaultdict
from time import time, sleep
from threading import Lock
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter globale per tutte le fonti dati.

    Thread-safe per uso concorrente con ThreadPoolExecutor.
    Implementa rate limiting per-source per evitare di
    sovraccaricare le piattaforme.
    """

    def __init__(self):
        self._locks: Dict[str, Lock] = defaultdict(Lock)
        self._last_request: Dict[str, float] = defaultdict(float)

        # Rate limits per fonte (seconds between requests)
        # Increased to 2.0s to avoid triggering anti-bot measures on cloud deployments
        self.limits = {
            "justetf": 2.0,       # 0.5 req/sec (conservative)
            "morningstar": 2.0,   # 0.5 req/sec (was 0.5, too aggressive)
            "investiny": 2.0,     # 0.5 req/sec (conservative)
        }

    def wait(self, source: str) -> None:
        """
        Attende se necessario per rispettare il rate limit.

        Thread-safe grazie all'uso di lock per-source.

        Args:
            source: Nome della fonte (justetf, morningstar, investiny)
        """
        limit = self.limits.get(source, 1.0)

        with self._locks[source]:
            elapsed = time() - self._last_request[source]
            if elapsed < limit:
                wait_time = limit - elapsed
                logger.debug(f"Rate limiting {source}: waiting {wait_time:.2f}s")
                sleep(wait_time)
            self._last_request[source] = time()

    def set_limit(self, source: str, seconds: float) -> None:
        """
        Aggiorna il rate limit per una fonte.

        Args:
            source: Nome della fonte
            seconds: Secondi minimi tra le richieste
        """
        self.limits[source] = seconds
        logger.info(f"Updated rate limit for {source}: {seconds}s")

    def get_limit(self, source: str) -> float:
        """
        Ottiene il rate limit corrente per una fonte.

        Args:
            source: Nome della fonte

        Returns:
            Secondi tra le richieste
        """
        return self.limits.get(source, 1.0)

    def reset(self, source: str = None) -> None:
        """
        Resetta il timestamp dell'ultima richiesta.

        Args:
            source: Se specificato, resetta solo quella fonte.
                   Altrimenti resetta tutte.
        """
        if source:
            self._last_request[source] = 0.0
        else:
            self._last_request.clear()


# Singleton instance
_rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    """
    Restituisce l'istanza singleton del rate limiter.

    Returns:
        RateLimiter singleton
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
