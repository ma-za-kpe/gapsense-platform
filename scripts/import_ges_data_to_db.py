"""
Import GES schools CSV data into database.

Usage:
    python -m scripts.import_ges_data_to_db ges_schools.csv
"""

import argparse
import asyncio
import csv
import sys

from sqlalchemy import select

from gapsense.core.database import get_db
from gapsense.core.models import GESSchool


async def import_ges_schools(csv_file: str) -> int:
    """Import GES schools from CSV file into database.

    Args:
        csv_file: Path to CSV file

    Returns:
        Number of schools imported
    """
    count = 0
    async for db in get_db():
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Check if school already exists
                stmt = select(GESSchool).where(GESSchool.ges_id == int(row["ges_id"]))
                existing = await db.execute(stmt)
                if existing.scalar_one_or_none():
                    print(f"Skipping duplicate: {row['name']} (GES ID: {row['ges_id']})")
                    continue

                school = GESSchool(
                    ges_id=int(row["ges_id"]),
                    name=row["name"],
                    region=row["region"],
                    district=row["district"],
                    school_type=row["school_type"],
                    courses_offered=row.get("courses_offered") or None,
                    contact=row.get("contact") or None,
                )
                db.add(school)
                count += 1

                if count % 50 == 0:
                    print(f"Imported {count} schools...")
                    await db.commit()

            await db.commit()
            print(f"\n✅ Successfully imported {count} schools!")
            return count


async def main():
    parser = argparse.ArgumentParser(description="Import GES schools CSV into database")
    parser.add_argument("csv_file", help="Path to GES schools CSV file")
    args = parser.parse_args()

    try:
        count = await import_ges_schools(args.csv_file)
        sys.exit(0 if count > 0 else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
