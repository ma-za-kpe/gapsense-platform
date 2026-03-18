"""
Unit tests for grade normalization utilities (Phase 4).

Tests cover:
- normalise_grade() for all 4 countries (Ghana, Uganda, Kenya, Nigeria)
- adjacent_grades() with correct radius handling at boundaries
- Case-insensitive matching
- Unknown grade handling
"""

from gapsense.core.grade_utils import GRADE_MAPS, GRADE_SEQUENCES, adjacent_grades, normalise_grade


class TestNormaliseGrade:
    """Test grade normalization across all countries."""

    # Ghana tests
    def test_ghana_canonical_codes(self):
        """Test that canonical codes (B1-B9) pass through unchanged."""
        assert normalise_grade("B1", "ghana") == "B1"
        assert normalise_grade("B7", "ghana") == "B7"
        assert normalise_grade("B9", "ghana") == "B9"

    def test_ghana_jhs_formats(self):
        """Test JHS/JSS format normalization to B7-B9."""
        assert normalise_grade("JHS1", "ghana") == "B7"
        assert normalise_grade("JHS 1", "ghana") == "B7"
        assert normalise_grade("JSS1", "ghana") == "B7"
        assert normalise_grade("JSS 1", "ghana") == "B7"

        assert normalise_grade("JHS2", "ghana") == "B8"
        assert normalise_grade("JHS 2", "ghana") == "B8"

        assert normalise_grade("JHS3", "ghana") == "B9"
        assert normalise_grade("JHS 3", "ghana") == "B9"

    def test_ghana_primary_formats(self):
        """Test Primary/Grade/Class format normalization."""
        assert normalise_grade("Primary 1", "ghana") == "B1"
        assert normalise_grade("P1", "ghana") == "B1"
        assert normalise_grade("Grade 1", "ghana") == "B1"
        assert normalise_grade("Class 1", "ghana") == "B1"

        assert normalise_grade("Primary 6", "ghana") == "B6"
        assert normalise_grade("P6", "ghana") == "B6"

    def test_ghana_case_insensitive(self):
        """Test case-insensitive matching."""
        assert normalise_grade("jhs1", "ghana") == "B7"
        assert normalise_grade("JHS1", "ghana") == "B7"
        assert normalise_grade("Jhs1", "ghana") == "B7"
        assert normalise_grade("primary 6", "ghana") == "B6"

    def test_ghana_country_code_variations(self):
        """Test that country code variations work (GH, ghana)."""
        assert normalise_grade("JHS1", "GH") == "B7"
        assert normalise_grade("JHS1", "gh") == "B7"
        assert normalise_grade("JHS1", "ghana") == "B7"
        assert normalise_grade("JHS1", "GHANA") == "B7"

    # Uganda tests
    def test_uganda_primary_formats(self):
        """Test Uganda primary grades (P1-P7)."""
        assert normalise_grade("P1", "uganda") == "P1"
        assert normalise_grade("Primary 1", "uganda") == "P1"
        assert normalise_grade("Grade 1", "uganda") == "P1"

        assert normalise_grade("P7", "uganda") == "P7"
        assert normalise_grade("Primary 7", "uganda") == "P7"

    def test_uganda_secondary_formats(self):
        """Test Uganda secondary grades (S1-S4)."""
        assert normalise_grade("S1", "uganda") == "S1"
        assert normalise_grade("Senior 1", "uganda") == "S1"
        assert normalise_grade("Form 1", "uganda") == "S1"

        assert normalise_grade("S4", "uganda") == "S4"
        assert normalise_grade("Senior 4", "uganda") == "S4"

    def test_uganda_country_code_variations(self):
        """Test Uganda country code variations (UG, uganda)."""
        assert normalise_grade("S1", "UG") == "S1"
        assert normalise_grade("S1", "ug") == "S1"
        assert normalise_grade("S1", "uganda") == "S1"

    # Kenya tests
    def test_kenya_grade_formats(self):
        """Test Kenya grade formats (G1-G9)."""
        assert normalise_grade("G1", "kenya") == "G1"
        assert normalise_grade("Grade 1", "kenya") == "G1"
        assert normalise_grade("Standard 1", "kenya") == "G1"

        assert normalise_grade("G9", "kenya") == "G9"
        assert normalise_grade("Grade 9", "kenya") == "G9"
        assert normalise_grade("Form 1", "kenya") == "G9"

    def test_kenya_country_code_variations(self):
        """Test Kenya country code variations (KE, kenya)."""
        assert normalise_grade("G1", "KE") == "G1"
        assert normalise_grade("G1", "ke") == "G1"
        assert normalise_grade("G1", "kenya") == "G1"

    # Nigeria tests
    def test_nigeria_primary_formats(self):
        """Test Nigeria primary grades (P1-P6)."""
        assert normalise_grade("P1", "nigeria") == "P1"
        assert normalise_grade("Primary 1", "nigeria") == "P1"
        assert normalise_grade("Grade 1", "nigeria") == "P1"

        assert normalise_grade("P6", "nigeria") == "P6"
        assert normalise_grade("Primary 6", "nigeria") == "P6"

    def test_nigeria_jss_formats(self):
        """Test Nigeria JSS formats (JSS1-JSS3)."""
        assert normalise_grade("JSS1", "nigeria") == "JSS1"
        assert normalise_grade("JSS 1", "nigeria") == "JSS1"
        assert normalise_grade("Junior Secondary 1", "nigeria") == "JSS1"
        assert normalise_grade("JS1", "nigeria") == "JSS1"

        assert normalise_grade("JSS3", "nigeria") == "JSS3"
        assert normalise_grade("JSS 3", "nigeria") == "JSS3"

    def test_nigeria_country_code_variations(self):
        """Test Nigeria country code variations (NG, nigeria)."""
        assert normalise_grade("JSS1", "NG") == "JSS1"
        assert normalise_grade("JSS1", "ng") == "JSS1"
        assert normalise_grade("JSS1", "nigeria") == "JSS1"

    # Cross-country validation tests
    def test_cross_country_rejection(self):
        """Test that grades from one country don't work in another."""
        # JHS1 is Ghana-specific, should not work in Uganda
        assert normalise_grade("JHS1", "uganda") is None

        # S1 is Uganda-specific, should not work in Ghana
        assert normalise_grade("S1", "ghana") is None

        # G1 is Kenya-specific, should not work in Nigeria
        assert normalise_grade("G1", "nigeria") is None

    # Unknown grade handling
    def test_unknown_grade_formats(self):
        """Test that unknown grade formats return None."""
        assert normalise_grade("Unknown", "ghana") is None
        assert normalise_grade("Year 7", "ghana") is None
        assert normalise_grade("", "ghana") is None
        assert normalise_grade("XYZ", "uganda") is None

    def test_unknown_country(self):
        """Test that unknown countries return None."""
        assert normalise_grade("B7", "unknown_country") is None
        assert normalise_grade("B7", "france") is None
        assert normalise_grade("B7", "") is None

    # Whitespace handling
    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled."""
        assert normalise_grade("  JHS1  ", "ghana") == "B7"
        assert normalise_grade(" Primary 6 ", "ghana") == "B6"
        assert normalise_grade("\tS1\t", "uganda") == "S1"


class TestAdjacentGrades:
    """Test adjacent grades functionality."""

    def test_ghana_adjacent_grades_middle(self):
        """Test adjacent grades in the middle of the sequence."""
        assert adjacent_grades("B7", "ghana", radius=1) == ["B6", "B7", "B8"]
        assert adjacent_grades("B5", "ghana", radius=1) == ["B4", "B5", "B6"]

    def test_ghana_adjacent_grades_boundaries(self):
        """Test adjacent grades at sequence boundaries."""
        # At the beginning - no B0 exists
        assert adjacent_grades("B1", "ghana", radius=1) == ["B1", "B2"]

        # At the end - no B10 exists
        assert adjacent_grades("B9", "ghana", radius=1) == ["B8", "B9"]

    def test_ghana_adjacent_grades_wider_radius(self):
        """Test adjacent grades with larger radius."""
        assert adjacent_grades("B5", "ghana", radius=2) == ["B3", "B4", "B5", "B6", "B7"]
        assert adjacent_grades("B7", "ghana", radius=2) == ["B5", "B6", "B7", "B8", "B9"]

    def test_uganda_adjacent_grades(self):
        """Test Uganda grade sequence including primary-secondary transition."""
        # P6 to P7 boundary
        assert adjacent_grades("P6", "uganda", radius=1) == ["P5", "P6", "P7"]

        # P7 to S1 transition (primary to secondary)
        assert adjacent_grades("P7", "uganda", radius=1) == ["P6", "P7", "S1"]
        assert adjacent_grades("S1", "uganda", radius=1) == ["P7", "S1", "S2"]

    def test_uganda_adjacent_grades_boundaries(self):
        """Test Uganda boundaries."""
        # Start boundary
        assert adjacent_grades("P1", "uganda", radius=1) == ["P1", "P2"]

        # End boundary
        assert adjacent_grades("S4", "uganda", radius=1) == ["S3", "S4"]

    def test_kenya_adjacent_grades(self):
        """Test Kenya grade sequence."""
        assert adjacent_grades("G5", "kenya", radius=1) == ["G4", "G5", "G6"]
        assert adjacent_grades("G1", "kenya", radius=1) == ["G1", "G2"]
        assert adjacent_grades("G9", "kenya", radius=1) == ["G8", "G9"]

    def test_nigeria_adjacent_grades(self):
        """Test Nigeria grade sequence including primary-JSS transition."""
        # P6 to JSS1 transition
        assert adjacent_grades("P6", "nigeria", radius=1) == ["P5", "P6", "JSS1"]
        assert adjacent_grades("JSS1", "nigeria", radius=1) == ["P6", "JSS1", "JSS2"]

        # Boundaries
        assert adjacent_grades("P1", "nigeria", radius=1) == ["P1", "P2"]
        assert adjacent_grades("JSS3", "nigeria", radius=1) == ["JSS2", "JSS3"]

    def test_adjacent_grades_zero_radius(self):
        """Test radius=0 returns only the target grade."""
        assert adjacent_grades("B7", "ghana", radius=0) == ["B7"]
        assert adjacent_grades("S1", "uganda", radius=0) == ["S1"]

    def test_adjacent_grades_country_code_variations(self):
        """Test that country code variations work."""
        assert adjacent_grades("B7", "GH", radius=1) == ["B6", "B7", "B8"]
        assert adjacent_grades("S1", "UG", radius=1) == ["P7", "S1", "S2"]

    def test_adjacent_grades_unknown_grade(self):
        """Test that unknown grades return only themselves."""
        # Grade not in sequence
        assert adjacent_grades("Unknown", "ghana", radius=1) == ["Unknown"]

        # Unknown country
        assert adjacent_grades("B7", "unknown_country", radius=1) == ["B7"]

    def test_adjacent_grades_case_sensitivity(self):
        """Test that adjacent_grades requires canonical codes (case-sensitive)."""
        # This should work (canonical code)
        assert adjacent_grades("B7", "ghana", radius=1) == ["B6", "B7", "B8"]

        # This should NOT work (lowercase) - will return just the grade
        assert adjacent_grades("b7", "ghana", radius=1) == ["b7"]


class TestGradeDataIntegrity:
    """Test that grade maps and sequences are consistent."""

    def test_all_canonical_codes_in_sequences(self):
        """Test that all canonical codes appear in grade sequences."""
        for country, grade_map in GRADE_MAPS.items():
            canonical_codes = set(grade_map.values())
            sequence = GRADE_SEQUENCES.get(country, [])

            # Every canonical code should be in the sequence
            for canonical in canonical_codes:
                assert canonical in sequence, f"{canonical} not in {country} sequence"

    def test_sequences_have_no_duplicates(self):
        """Test that grade sequences have no duplicate entries."""
        for country, sequence in GRADE_SEQUENCES.items():
            assert len(sequence) == len(set(sequence)), f"{country} sequence has duplicates"

    def test_all_countries_have_maps_and_sequences(self):
        """Test that every country in GRADE_MAPS has a sequence."""
        for country in GRADE_MAPS.keys():
            assert country in GRADE_SEQUENCES, f"{country} missing from GRADE_SEQUENCES"

        for country in GRADE_SEQUENCES.keys():
            assert country in GRADE_MAPS, f"{country} missing from GRADE_MAPS"
