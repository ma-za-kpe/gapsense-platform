"""Versioned, non-identifying product analytics event names."""

from enum import StrEnum


class AnalyticsEventName(StrEnum):
    """The complete allowlist for the current anonymous web funnel."""

    ENTRY_VIEWED = "entry_viewed"
    NAVIGATION_COUNTRIES_SELECTED = "navigation_countries_selected"
    NAVIGATION_PRINCIPLES_SELECTED = "navigation_principles_selected"
    NAVIGATION_PLANNER_SELECTED = "navigation_planner_selected"
    PLANNER_ROLE_SELECTED = "planner_role_selected"
    PLANNER_COUNTRY_SELECTED = "planner_country_selected"
    PLANNER_GOAL_SELECTED = "planner_goal_selected"
    PLANNER_REVIEWED = "planner_reviewed"
    PLANNER_RESET = "planner_reset"
    READINESS_RETRY_SELECTED = "readiness_retry_selected"
    COVERAGE_RETRY_SELECTED = "coverage_retry_selected"
