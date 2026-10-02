import time
from enum import StrEnum


class ProviderHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class CircuitBreaker:
    """Opens after N consecutive retryable failures; after the cooldown one request is let
    through as a health check, and a success closes the circuit again."""

    def __init__(self, failure_threshold: int, cooldown_seconds: float, clock=time.monotonic):
        self._threshold = max(1, failure_threshold)
        self._cooldown = cooldown_seconds
        self._clock = clock
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> ProviderHealth:
        if self._opened_at is not None:
            return ProviderHealth.UNAVAILABLE
        if self._consecutive_failures:
            return ProviderHealth.DEGRADED
        return ProviderHealth.HEALTHY

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def allow_request(self) -> bool:
        if self._opened_at is None:
            return True
        return self._clock() - self._opened_at >= self._cooldown

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._threshold:
            self._opened_at = self._clock()
