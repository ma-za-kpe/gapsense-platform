"""Replaceable analytics ports and the local aggregate-only adapter."""

from collections import Counter
from collections.abc import Sequence
from threading import Lock
from typing import Protocol

from gapsense.analytics.events import AnalyticsEventName


class AnalyticsSink(Protocol):
    """A boundary that can retain approved event counts without user identity."""

    def record(self, events: Sequence[AnalyticsEventName]) -> None:
        """Record one already-validated batch."""


class AggregateAnalyticsSink:
    """Thread-safe, process-local counters with no event-level records."""

    def __init__(self) -> None:
        self._counts: Counter[AnalyticsEventName] = Counter()
        self._lock = Lock()

    def record(self, events: Sequence[AnalyticsEventName]) -> None:
        """Increment allowlisted counters as one critical section."""
        with self._lock:
            self._counts.update(events)

    def snapshot(self) -> dict[str, int]:
        """Return a detached operational snapshot for tests and local operators."""
        with self._lock:
            return {event.value: count for event, count in self._counts.items()}
