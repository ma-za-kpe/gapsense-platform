#!/usr/bin/env python3
"""
Verify production E2E test results by directly querying the database.

This script runs inside an ECS task with access to the production database.
It checks for the test data created by the E2E test.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from gapsense.core.models import GapProfile, Student, Teacher


async def verify_e2e_results(phone_number: str):
    """Verify E2E test created the expected records."""
    print("=" * 60)
    print("Production E2E Verification")
    print("=" * 60)
    print()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        sys.exit(1)

    # Mask password for display
    display_url = database_url
    if "@" in display_url and ":" in display_url.split("@")[0]:
        parts = display_url.split("@")
        user_pass = parts[0].split("://")[1]
        user = user_pass.split(":")[0]
        display_url = display_url.replace(user_pass, f"{user}:***")

    print(f"📊 Database: {display_url}")
    print(f"📱 Testing phone: {phone_number}")
    print()

    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Find teacher
            result = await conn.execute(select(Teacher).where(Teacher.phone_number == phone_number))
            teacher = result.scalar_one_or_none()

            if not teacher:
                print(f"❌ Teacher not found for phone {phone_number}")
                sys.exit(1)

            print(f"✅ Teacher found: {teacher.name} (ID: {teacher.id})")

            # Find student
            result = await conn.execute(select(Student).where(Student.teacher_id == teacher.id))
            student = result.scalar_one_or_none()

            if not student:
                print(f"❌ Student not found for teacher {teacher.id}")
                sys.exit(1)

            print(f"✅ Student found: {student.name} (ID: {student.id})")
            print(f"   Grade: {student.current_grade}")
            print(f"   Grade Canonical: {student.grade_canonical}")

            # Find gap profile (created in last 5 minutes)
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            result = await conn.execute(
                select(GapProfile)
                .where(GapProfile.student_id == student.id)
                .where(GapProfile.created_at >= cutoff)
            )
            gap_profile = result.scalar_one_or_none()

            if not gap_profile:
                print(f"❌ GapProfile not found for student {student.id} (created in last 5 min)")
                sys.exit(1)

            print(f"✅ GapProfile found: ID {gap_profile.id}")
            print(f"   Created: {gap_profile.created_at}")
            print(f"   Confidence: {gap_profile.confidence_score}")
            print(f"   Gap nodes: {len(gap_profile.gap_node_ids or [])}")
            print(f"   Seed nodes: {len(gap_profile.seed_node_ids or [])}")
            print()
            print("=" * 60)
            print("✅ E2E VERIFICATION PASSED")
            print("=" * 60)
            return 0

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ E2E VERIFICATION FAILED: {e}")
        print("=" * 60)
        import traceback

        traceback.print_exc()
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_production_e2e.py <phone_number>")
        sys.exit(1)

    phone_number = sys.argv[1]
    exit_code = asyncio.run(verify_e2e_results(phone_number))
    sys.exit(exit_code)
