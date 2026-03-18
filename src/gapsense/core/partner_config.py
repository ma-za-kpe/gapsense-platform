"""
Partner Configuration (Phase 4)

Multi-tenant configuration layer for GapSense partners.

GapSense is licensed to multiple partners with different requirements:
  - Athlete + Her: Uganda student-athletes, S1-S4 focus, mathematics only
  - Viztaedu: Ghana schools, B4-B9 focus, mathematics + literacy

This module provides partner-specific configuration that can be used to:
  - Filter curriculum queries by partner's grade focus
  - Apply rate limits per partner
  - Configure WhatsApp sender IDs per partner
  - Set partner-specific language preferences

Current implementation uses Python dataclasses with hardcoded configs.
Future enhancement: Load from YAML or database for easier management.
See docs/improvements/phase4_spec.md for YAML migration path.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PartnerConfig:
    """Partner-specific configuration for multi-tenant support.

    Attributes:
        partner_id: Unique partner identifier (e.g., "athlete_her", "viztaedu")
        country: Primary country of operation (e.g., "uganda", "ghana")
        subject_focus: List of subjects this partner focuses on
        grade_focus: List of canonical grade codes this partner targets
        rate_limit_per_day: Maximum number of analyses allowed per day
        whatsapp_sender_id: WhatsApp Business number to send from
        report_language: Primary language for teacher reports
    """

    partner_id: str
    country: str
    subject_focus: list[str]
    grade_focus: list[str]
    rate_limit_per_day: int
    whatsapp_sender_id: str
    report_language: str


# ------------------------------------------------------------------
# Partner Configurations
# ------------------------------------------------------------------

PARTNER_CONFIGS: dict[str, PartnerConfig] = {
    "athlete_her": PartnerConfig(
        partner_id="athlete_her",
        country="uganda",
        subject_focus=["mathematics"],
        grade_focus=["S1", "S2", "S3", "S4"],  # Secondary 1-4 (O-Level)
        rate_limit_per_day=500,
        whatsapp_sender_id="",  # TODO: Configure from environment
        report_language="en",
    ),
    "viztaedu": PartnerConfig(
        partner_id="viztaedu",
        country="ghana",
        subject_focus=["mathematics", "literacy"],
        grade_focus=["B4", "B5", "B6", "B7", "B8", "B9"],  # Basic 4-9 (Upper Primary + JHS)
        rate_limit_per_day=2000,
        whatsapp_sender_id="",  # TODO: Configure from environment
        report_language="en",
    ),
    "gapsense_direct": PartnerConfig(
        partner_id="gapsense_direct",
        country="ghana",  # Default country
        subject_focus=["mathematics", "literacy", "science"],
        grade_focus=["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"],  # All grades
        rate_limit_per_day=5000,
        whatsapp_sender_id="",  # TODO: Configure from environment
        report_language="en",
    ),
}


def get_partner_config(partner_id: str) -> PartnerConfig | None:
    """Get partner configuration by partner ID.

    Args:
        partner_id: The partner identifier (e.g., "athlete_her", "viztaedu")

    Returns:
        PartnerConfig if found, None otherwise

    Example:
        >>> config = get_partner_config("athlete_her")
        >>> if config:
        ...     print(config.country)  # "uganda"
        ...     print(config.grade_focus)  # ["S1", "S2", "S3", "S4"]
    """
    return PARTNER_CONFIGS.get(partner_id)


def get_partner_for_school(school_id: str) -> str | None:
    """Get partner ID for a given school.

    This is a placeholder for future implementation where schools
    are explicitly linked to partners in the database.

    For Phase 4 MVP, this returns None (indicating direct GapSense usage).
    Future: Query `schools.partner_id` column.

    Args:
        school_id: School UUID

    Returns:
        Partner ID if school is linked to a partner, None for direct usage
    """
    # TODO: Implement school -> partner lookup when partner_id is added to schools table
    # For now, assume all schools are direct GapSense usage
    return None


def apply_partner_grade_filter(
    partner_config: PartnerConfig | None,
    student_grade: str | None,
) -> list[str] | None:
    """Apply partner-specific grade filtering.

    If a partner config is provided and the student's grade is within the
    partner's grade focus, return the partner's grade focus list.
    Otherwise, return None (no partner-based filtering).

    This ensures that partner-specific analyses only retrieve curriculum
    content relevant to that partner's target grades.

    Args:
        partner_config: The partner configuration, or None for direct usage
        student_grade: The student's canonical grade (e.g., "S1", "B7")

    Returns:
        List of canonical grade codes to filter by, or None for no filtering

    Example:
        >>> config = get_partner_config("athlete_her")
        >>> apply_partner_grade_filter(config, "S2")
        ["S1", "S2", "S3", "S4"]
        >>> apply_partner_grade_filter(config, "P7")  # Primary 7 not in S1-S4 focus
        None
        >>> apply_partner_grade_filter(None, "B7")  # No partner config
        None
    """
    if not partner_config:
        return None

    if not student_grade:
        return None

    # If student's grade is within partner's focus, use partner's grade list
    if student_grade in partner_config.grade_focus:
        return partner_config.grade_focus

    # Student grade outside partner's focus - no filtering
    return None
