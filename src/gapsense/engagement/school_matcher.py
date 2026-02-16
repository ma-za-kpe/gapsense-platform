"""
School fuzzy matching to prevent duplicate school records.

Phase E of TDD implementation plan.

Handles:
- Punctuation differences (St. vs St)
- Capitalization differences
- Extra whitespace
- Minor typos (future: Levenshtein distance)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from gapsense.core.models import School


def normalize_school_name(name: str) -> str:
    """Normalize school name for fuzzy matching.

    Args:
        name: Raw school name

    Returns:
        Normalized name (lowercase, no punctuation, single spaces)
    """
    if not name:
        return ""

    # Convert to lowercase
    normalized = name.lower()

    # Remove punctuation (keep only alphanumeric and spaces)
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)

    # Normalize whitespace (multiple spaces to single space)
    normalized = re.sub(r"\s+", " ", normalized)

    # Strip leading/trailing whitespace
    normalized = normalized.strip()

    return normalized


async def find_matching_schools(
    db: AsyncSession,
    query: str,
    max_results: int = 10,
) -> list[School]:
    """Find schools with names matching the query (fuzzy matching).

    Handles common variations:
    - Punctuation: "St. Mary's" matches "St Marys"
    - Capitalization: "st. mary's" matches "St. Mary's"
    - Whitespace: "St.  Mary's" matches "St. Mary's"

    Args:
        db: Database session
        query: School name query
        max_results: Maximum number of matches to return

    Returns:
        List of matching School objects (active only)
    """
    # Normalize query
    normalized_query = normalize_school_name(query)

    if not normalized_query:
        return []

    # Get all active schools
    stmt = select(School).where(School.is_active.is_(True))
    result = await db.execute(stmt)
    all_schools = result.scalars().all()

    # Common words to filter out (stopwords for school names)
    stopwords = {
        "jhs",
        "shs",
        "primary",
        "school",
        "basic",
        "junior",
        "senior",
        "high",
        "accra",
        "kumasi",
        "tamale",
        "takoradi",
        "cape",
        "coast",
        "ghana",
    }

    # Find matches by comparing normalized names
    matches = []
    query_words = set(normalized_query.split())
    # Filter out stopwords from query to focus on unique identifying words
    query_unique_words = query_words - stopwords

    for school in all_schools:
        normalized_school_name = normalize_school_name(school.name)
        school_words = set(normalized_school_name.split())
        school_unique_words = school_words - stopwords

        # Match if:
        # 1. Exact substring match (handles full name matches)
        is_substring_match = (
            normalized_query in normalized_school_name or normalized_school_name in normalized_query
        )

        # 2. Most UNIQUE (non-stopword) query words are in school name
        # This prevents "St. Mary's" matching "St. Paul's" just because they both have "St JHS Accra"
        if len(query_unique_words) > 0:
            unique_overlap = len(query_unique_words & school_unique_words)
            is_word_match = unique_overlap >= len(query_unique_words) * 0.75
        else:
            # If query is all stopwords, fall back to full word matching
            overlap = len(query_words & school_words)
            is_word_match = len(query_words) > 0 and overlap >= len(query_words) * 0.75

        if is_substring_match or is_word_match:
            matches.append(school)

    # Limit results
    return matches[:max_results]
