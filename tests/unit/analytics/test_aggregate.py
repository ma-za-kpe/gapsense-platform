"""Tests for the non-identifying in-memory analytics sink."""

from concurrent.futures import ThreadPoolExecutor

from gapsense.analytics.events import AnalyticsEventName
from gapsense.analytics.sinks import AggregateAnalyticsSink


def test_aggregate_sink_counts_only_allowlisted_event_names() -> None:
    """The local adapter retains counters, not event bodies or user records."""
    sink = AggregateAnalyticsSink()

    sink.record(
        (
            AnalyticsEventName.ENTRY_VIEWED,
            AnalyticsEventName.PLANNER_REVIEWED,
            AnalyticsEventName.PLANNER_REVIEWED,
        )
    )

    assert sink.snapshot() == {
        "entry_viewed": 1,
        "planner_reviewed": 2,
    }


def test_aggregate_sink_serializes_concurrent_updates() -> None:
    """Concurrent local requests cannot silently lose aggregate counts."""
    sink = AggregateAnalyticsSink()

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(
            executor.map(
                sink.record,
                [(AnalyticsEventName.COVERAGE_RETRY_SELECTED,)] * 20,
            )
        )

    assert sink.snapshot() == {"coverage_retry_selected": 20}
