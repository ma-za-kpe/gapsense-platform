"""
GES School Database Scraper

Scrapes all schools from https://ges.gov.gh/schools.php
Extracts: ges_id, name, region, district, school_type

Usage:
    python -m scripts.import_ges_schools [--dry-run] [--output schools.csv]
"""

import argparse
import asyncio
import csv
import logging
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_school_id_from_url(url: str) -> int | None:
    """Extract GES school ID from URL.

    Args:
        url: URL like 'school.php?id=343' or 'https://ges.gov.gh/school.php?id=558'

    Returns:
        School ID as integer, or None if not found
    """
    try:
        # Parse query parameters
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # Extract 'id' parameter
        if "id" in params:
            return int(params["id"][0])

        return None
    except (ValueError, IndexError, KeyError):
        return None


def extract_school_data_from_row(html_row: str) -> dict[str, Any] | None:
    """Extract school data from HTML table row.

    Args:
        html_row: HTML string containing <tr>...</tr>

    Returns:
        Dictionary with school data, or None if invalid
    """
    try:
        soup = BeautifulSoup(html_row, "html.parser")
        cells = soup.find_all("td")

        if len(cells) < 7:
            return None

        # Extract text from cells (7 columns total)
        # 0: School Name, 1: Type, 2: Courses Offered, 3: Region, 4: District, 5: Contact, 6: Actions
        name = cells[0].get_text(strip=True)
        school_type = cells[1].get_text(strip=True)
        courses_offered = cells[2].get_text(strip=True)
        region = cells[3].get_text(strip=True)
        district = cells[4].get_text(strip=True)
        contact = cells[5].get_text(strip=True)

        # Extract school ID from "View Details" link in Actions column
        link = cells[6].find("a")
        if not link:
            return None

        href = link.get("href", "")
        ges_id = parse_school_id_from_url(href)

        if not ges_id:
            return None

        return {
            "ges_id": ges_id,
            "name": name,
            "school_type": school_type,
            "region": region,
            "district": district,
            "courses_offered": courses_offered if courses_offered != "N/A" else None,
            "contact": contact if contact != "N/A" else None,
        }

    except (AttributeError, IndexError) as e:
        logger.warning(f"Failed to parse row: {e}")
        return None


async def fetch_ges_page(page: int = 1) -> list[dict[str, Any]]:
    """Fetch one page of schools from GES website.

    Args:
        page: Page number to fetch (1-31)

    Returns:
        List of school dictionaries
    """
    url = f"https://ges.gov.gh/schools.php?page={page}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)

            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} for page {page}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            # Find the schools table
            table = soup.find("table")
            if not table:
                logger.warning(f"No table found on page {page}")
                return []

            # Extract rows (skip header row)
            rows = table.find_all("tr")[1:]  # Skip header

            schools = []
            for row in rows:
                school_data = extract_school_data_from_row(str(row))
                if school_data:
                    schools.append(school_data)

            logger.info(f"Page {page}: Found {len(schools)} schools")
            return schools

    except httpx.RequestError as e:
        logger.error(f"Request failed for page {page}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error on page {page}: {e}")
        return []


async def scrape_all_ges_schools(max_pages: int = 31) -> list[dict[str, Any]]:
    """Scrape all schools from GES website.

    Args:
        max_pages: Maximum number of pages to scrape

    Returns:
        List of unique school dictionaries
    """
    all_schools = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        schools = await fetch_ges_page(page)

        # Stop if page is empty
        if not schools:
            logger.info(f"Empty page at {page}, stopping scrape")
            break

        # Deduplicate by ges_id
        for school in schools:
            ges_id = school["ges_id"]
            if ges_id not in seen_ids:
                all_schools.append(school)
                seen_ids.add(ges_id)

        # Be nice to the server
        await asyncio.sleep(1)

    logger.info(f"Total schools scraped: {len(all_schools)}")
    return all_schools


def save_to_csv(schools: list[dict[str, Any]], filename: str = "ges_schools.csv") -> None:
    """Save schools to CSV file.

    Args:
        schools: List of school dictionaries
        filename: Output CSV filename
    """
    if not schools:
        logger.warning("No schools to save")
        return

    fieldnames = [
        "ges_id",
        "name",
        "school_type",
        "region",
        "district",
        "courses_offered",
        "contact",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(schools)

    logger.info(f"Saved {len(schools)} schools to {filename}")


async def main():
    """Main entry point for scraper."""
    parser = argparse.ArgumentParser(description="Scrape GES school database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape but don't save to database (only CSV)",
    )
    parser.add_argument(
        "--output",
        default="ges_schools.csv",
        help="Output CSV filename (default: ges_schools.csv)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=31,
        help="Maximum pages to scrape (default: 31)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting GES school scraper...")
    schools = await scrape_all_ges_schools(max_pages=args.max_pages)

    if schools:
        # Save to CSV
        save_to_csv(schools, filename=args.output)

        # Print summary
        print(f"\n{'='*60}")
        print("Scrape Complete!")
        print(f"{'='*60}")
        print(f"Total schools: {len(schools)}")
        print(f"Output file: {args.output}")
        print("\nSchool Types:")
        type_counts = {}
        for school in schools:
            school_type = school["school_type"]
            type_counts[school_type] = type_counts.get(school_type, 0) + 1

        for school_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {school_type}: {count}")

        print("\nRegions:")
        region_counts = {}
        for school in schools:
            region = school["region"]
            region_counts[region] = region_counts.get(region, 0) + 1

        for region, count in sorted(region_counts.items(), key=lambda x: -x[1]):
            print(f"  {region}: {count}")

        print(f"{'='*60}\n")

    else:
        logger.error("No schools were scraped!")


if __name__ == "__main__":
    asyncio.run(main())
