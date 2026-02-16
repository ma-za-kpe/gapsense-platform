"""
Tests for GES school database scraper.

TDD approach: Tests written first to define expected behavior.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from scripts.import_ges_schools import (
    extract_school_data_from_row,
    fetch_ges_page,
    parse_school_id_from_url,
    scrape_all_ges_schools,
)


class TestParseSchoolIdFromUrl:
    """Tests for extracting GES school ID from URL."""

    def test_extract_school_id_from_detail_link(self):
        """Extract ID from 'school.php?id=343' URL."""
        url = "school.php?id=343"
        school_id = parse_school_id_from_url(url)
        assert school_id == 343

    def test_extract_school_id_with_full_url(self):
        """Extract ID from full URL."""
        url = "https://ges.gov.gh/school.php?id=558"
        school_id = parse_school_id_from_url(url)
        assert school_id == 558

    def test_extract_school_id_with_additional_params(self):
        """Extract ID when URL has multiple params."""
        url = "school.php?id=176&region=central"
        school_id = parse_school_id_from_url(url)
        assert school_id == 176

    def test_invalid_url_returns_none(self):
        """Return None for invalid URL."""
        url = "invalid-url"
        school_id = parse_school_id_from_url(url)
        assert school_id is None


class TestExtractSchoolDataFromRow:
    """Tests for extracting school data from HTML table row."""

    def test_extract_complete_school_data(self):
        """Extract all fields from a complete school row."""
        # Mock HTML row structure (7 columns: Name, Type, Courses, Region, District, Contact, Actions)
        html_row = """
        <tr>
            <td>Abakrampa Senior High/Tech</td>
            <td>Senior High Technical</td>
            <td>General Arts, Business</td>
            <td>Central</td>
            <td>Abura/Asebu/Kwamankese</td>
            <td>N/A</td>
            <td><a href="school.php?id=343">View Details</a></td>
        </tr>
        """

        school_data = extract_school_data_from_row(html_row)

        assert school_data["ges_id"] == 343
        assert school_data["name"] == "Abakrampa Senior High/Tech"
        assert school_data["school_type"] == "Senior High Technical"
        assert school_data["region"] == "Central"
        assert school_data["district"] == "Abura/Asebu/Kwamankese"
        assert school_data["courses_offered"] == "General Arts, Business"
        assert school_data["contact"] is None  # N/A should be converted to None

    def test_extract_primary_school(self):
        """Extract primary school data."""
        html_row = """
        <tr>
            <td>St. Mary's Primary School</td>
            <td>Primary</td>
            <td>N/A</td>
            <td>Greater Accra</td>
            <td>Accra Metro</td>
            <td>Mr. John Doe</td>
            <td><a href="school.php?id=176">View Details</a></td>
        </tr>
        """

        school_data = extract_school_data_from_row(html_row)

        assert school_data["ges_id"] == 176
        assert school_data["name"] == "St. Mary's Primary School"
        assert school_data["school_type"] == "Primary"
        assert school_data["region"] == "Greater Accra"
        assert school_data["contact"] == "Mr. John Doe"

    def test_extract_jhs_school(self):
        """Extract JHS school data."""
        html_row = """
        <tr>
            <td>Wesley Girls JHS</td>
            <td>Junior High School</td>
            <td>N/A</td>
            <td>Central</td>
            <td>Cape Coast Metro</td>
            <td>N/A</td>
            <td><a href="school.php?id=558">View Details</a></td>
        </tr>
        """

        school_data = extract_school_data_from_row(html_row)

        assert school_data["school_type"] == "Junior High School"
        assert school_data["name"] == "Wesley Girls JHS"

    def test_missing_school_id_returns_none(self):
        """Return None if school ID cannot be extracted."""
        html_row = """
        <tr>
            <td>Invalid School</td>
            <td>Primary</td>
            <td>N/A</td>
            <td>Greater Accra</td>
            <td>Accra</td>
            <td>N/A</td>
            <td><a href="invalid.php">No ID</a></td>
        </tr>
        """

        school_data = extract_school_data_from_row(html_row)
        assert school_data is None


class TestFetchGesPage:
    """Tests for fetching a single page from GES website."""

    @pytest.mark.asyncio
    async def test_fetch_page_returns_list_of_schools(self):
        """Fetch page 1 returns list of school dictionaries."""
        with patch("scripts.import_ges_schools.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = """
            <table>
                <tr>
                    <th>School Name</th>
                    <th>Type</th>
                    <th>Courses</th>
                    <th>Region</th>
                    <th>District</th>
                    <th>Contact</th>
                    <th>Action</th>
                </tr>
                <tr>
                    <td>School A</td>
                    <td>Primary</td>
                    <td>N/A</td>
                    <td>Greater Accra</td>
                    <td>Accra Metro</td>
                    <td>N/A</td>
                    <td><a href="school.php?id=1">View Details</a></td>
                </tr>
                <tr>
                    <td>School B</td>
                    <td>JHS</td>
                    <td>N/A</td>
                    <td>Ashanti</td>
                    <td>Kumasi Metro</td>
                    <td>N/A</td>
                    <td><a href="school.php?id=2">View Details</a></td>
                </tr>
            </table>
            """

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            schools = await fetch_ges_page(page=1)

            assert len(schools) == 2
            assert schools[0]["ges_id"] == 1
            assert schools[0]["name"] == "School A"
            assert schools[1]["ges_id"] == 2
            assert schools[1]["name"] == "School B"

    @pytest.mark.asyncio
    async def test_fetch_page_with_page_number(self):
        """Fetch specific page number."""
        with patch("scripts.import_ges_schools.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<table></table>"

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            await fetch_ges_page(page=5)

            # Verify correct URL was called
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "page=5" in str(call_args) or call_args[0][0].endswith("?page=5")

    @pytest.mark.asyncio
    async def test_fetch_page_handles_http_error(self):
        """Handle HTTP errors gracefully."""
        with patch("scripts.import_ges_schools.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            schools = await fetch_ges_page(page=999)

            # Should return empty list on error
            assert schools == []

    @pytest.mark.asyncio
    async def test_fetch_page_filters_invalid_rows(self):
        """Filter out rows without valid school IDs."""
        with patch("scripts.import_ges_schools.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = """
            <table>
                <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Courses</th>
                    <th>Region</th>
                    <th>District</th>
                    <th>Contact</th>
                    <th>Action</th>
                </tr>
                <tr>
                    <td>Valid School</td>
                    <td>Primary</td>
                    <td>N/A</td>
                    <td>Region</td>
                    <td>District</td>
                    <td>N/A</td>
                    <td><a href="school.php?id=1">View</a></td>
                </tr>
                <tr>
                    <td>Invalid School</td>
                    <td>Primary</td>
                    <td>N/A</td>
                    <td>Region</td>
                    <td>District</td>
                    <td>N/A</td>
                    <td><a href="invalid.php">View</a></td>
                </tr>
            </table>
            """

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            schools = await fetch_ges_page(page=1)

            # Should only return valid school (with ID)
            assert len(schools) == 1
            assert schools[0]["ges_id"] == 1


class TestScrapeAllGesSchools:
    """Tests for scraping all pages from GES website."""

    @pytest.mark.asyncio
    async def test_scrape_all_pages(self):
        """Scrape all 31 pages and aggregate results."""
        with patch("scripts.import_ges_schools.fetch_ges_page") as mock_fetch:
            # Mock fetch to return 2 schools per page for first 3 pages, then empty
            async def mock_fetch_page(page):
                if page <= 3:
                    return [
                        {
                            "ges_id": page * 10 + 1,
                            "name": f"School {page}A",
                            "region": "Greater Accra",
                            "district": "Accra",
                            "school_type": "Primary",
                        },
                        {
                            "ges_id": page * 10 + 2,
                            "name": f"School {page}B",
                            "region": "Ashanti",
                            "district": "Kumasi",
                            "school_type": "JHS",
                        },
                    ]
                return []

            mock_fetch.side_effect = mock_fetch_page

            schools = await scrape_all_ges_schools(max_pages=31)

            # Should have called fetch for all pages until empty results
            assert len(schools) == 6  # 3 pages × 2 schools

    @pytest.mark.asyncio
    async def test_scrape_removes_duplicates(self):
        """Remove duplicate schools by GES ID."""
        with patch("scripts.import_ges_schools.fetch_ges_page") as mock_fetch:
            # Mock returning duplicate GES IDs
            async def mock_fetch_page(page):
                if page == 1:
                    return [
                        {
                            "ges_id": 1,
                            "name": "School A",
                            "region": "R",
                            "district": "D",
                            "school_type": "P",
                        },
                        {
                            "ges_id": 2,
                            "name": "School B",
                            "region": "R",
                            "district": "D",
                            "school_type": "P",
                        },
                    ]
                elif page == 2:
                    return [
                        {
                            "ges_id": 1,
                            "name": "School A",
                            "region": "R",
                            "district": "D",
                            "school_type": "P",
                        },  # Duplicate
                        {
                            "ges_id": 3,
                            "name": "School C",
                            "region": "R",
                            "district": "D",
                            "school_type": "P",
                        },
                    ]
                return []

            mock_fetch.side_effect = mock_fetch_page

            schools = await scrape_all_ges_schools(max_pages=31)

            # Should deduplicate by ges_id
            assert len(schools) == 3  # IDs: 1, 2, 3
            ges_ids = [s["ges_id"] for s in schools]
            assert sorted(ges_ids) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_scrape_stops_on_empty_page(self):
        """Stop scraping when encountering empty page."""
        with patch("scripts.import_ges_schools.fetch_ges_page") as mock_fetch:
            call_count = 0

            async def mock_fetch_page(page):
                nonlocal call_count
                call_count += 1
                if page <= 2:
                    return [
                        {
                            "ges_id": page,
                            "name": f"School {page}",
                            "region": "R",
                            "district": "D",
                            "school_type": "P",
                        }
                    ]
                return []  # Empty from page 3 onwards

            mock_fetch.side_effect = mock_fetch_page

            schools = await scrape_all_ges_schools(max_pages=31)

            # Should stop after hitting first empty page
            assert len(schools) == 2
            # Should have tried up to 3 pages (1, 2 had data, 3 was empty)
            assert call_count == 3
