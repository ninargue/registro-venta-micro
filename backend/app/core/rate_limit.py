import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Limitador de tasa en memoria basado en ventana deslizante."""

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check_and_record(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Registra un intento para `key`; devuelve True si está permitido, False si excede."""
        if max_requests <= 0:
            return False
        now = time.monotonic()
        cutoff = now - window_seconds
        bucket = self._buckets[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        return True

    def reset(self) -> None:
        """Limpia todos los contadores (útil en tests)."""
        self._buckets.clear()


login_rate_limiter = SlidingWindowRateLimiter()
