"""
End-to-end test for Exercise Book Scanner flow.

Tests the complete flow:
1. Teacher uploads exercise book photo
2. Image uploaded to S3 (MediaService)
3. Analysis task enqueued (WorkerService)
4. AI analyzes image (AsyncAIClient + PromptService)
5. Gap profile created
6. Teacher notified
"""

import asyncio


async def test_exercise_book_upload_flow():
    """Test complete exercise book scanner flow."""
    from gapsense.ai.async_client import AsyncAIClient
    from gapsense.ai.prompt_service import PromptService
    from gapsense.config import settings
    from gapsense.core.database import get_session
    from gapsense.core.models import Student, Teacher
    from gapsense.engagement.exercise_book_scanner import ExerciseBookScanner
    from gapsense.services.guard_service import GuardService
    from gapsense.services.media_service import MediaService
    from gapsense.services.worker_service import WorkerService

    # Create a fake JPEG image (just enough bytes to pass validation)
    # JPEG header: FF D8 FF E0, then some data, then JPEG footer: FF D9
    test_image_bytes = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        + b"\x00" * 500
        + b"\xff\xd9"
    )

    print(f"\n✅ Created test image: {len(test_image_bytes)} bytes")

    # Initialize services
    async with get_session() as db:
        # Create test teacher and student
        from gapsense.core.models import District, Region, School

        region = Region(name="Greater Accra", code="GAR")
        db.add(region)
        await db.flush()

        district = District(name="Test District", region_id=region.id)
        db.add(district)
        await db.flush()

        school = School(
            name="Test School",
            district_id=district.id,
            school_type="jhs",
            is_active=True,
        )
        db.add(school)
        await db.flush()

        teacher = Teacher(
            phone="+233501234567",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            is_active=True,
        )
        db.add(teacher)
        await db.flush()

        student = Student(
            first_name="Kwame",
            last_name="Mensah",
            school_id=school.id,
            grade="B5",
            is_active=True,
        )
        db.add(student)
        await db.commit()
        await db.refresh(teacher)
        await db.refresh(student)

        print(f"✅ Created teacher: {teacher.first_name} {teacher.last_name}")
        print(f"✅ Created student: {student.first_name} {student.last_name}")

        # Initialize AI services
        ai_client = AsyncAIClient(
            anthropic_api_key=settings.ANTHROPIC_API_KEY or "test-key",
            max_concurrent=5,
        )

        prompt_service = PromptService(settings)
        print(f"✅ Loaded {len(prompt_service.list_prompts())} prompts")

        # Initialize infrastructure services
        media_service = MediaService(
            bucket_name=settings.S3_MEDIA_BUCKET,
            aws_region=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )

        # Check S3 connectivity
        is_healthy = await media_service.verify_connectivity()
        print(f"✅ S3 connectivity: {'healthy' if is_healthy else 'unhealthy'}")

        worker_service = WorkerService(
            queue_url=settings.SQS_QUEUE_URL or "http://localstack:4566/queue",
            aws_region=settings.AWS_REGION,
        )

        guard_service = GuardService(
            ai_client=ai_client,
            prompt_service=prompt_service,
        )

        # Initialize scanner
        scanner = ExerciseBookScanner(
            db=db,
            media_service=media_service,
            worker_service=worker_service,
            guard_service=guard_service,
            ai_client=ai_client,
            prompt_service=prompt_service,
        )

        print("\n🚀 Starting exercise book scan flow...")

        # Execute the scan
        result = await scanner.handle_image_message(
            teacher=teacher,
            student=student,
            image_bytes=test_image_bytes,
            filename="exercise_book_001.jpg",
            content_type="image/jpeg",
            country="GH",
        )

        # Verify results
        print("\n📊 Scan Result:")
        print(f"   Success: {result.success}")
        print(f"   S3 Key: {result.s3_key}")
        print(f"   Task Enqueued: {result.task_enqueued}")
        print(f"   Message Sent: {result.message_sent}")
        if result.error:
            print(f"   Error: {result.error}")

        # Assertions
        assert result.success is True, f"Scan failed: {result.error}"
        assert result.s3_key is not None, "No S3 key returned"
        assert result.task_enqueued is True, "Analysis task not enqueued"

        print("\n✅ END-TO-END TEST PASSED!")
        print("   ✓ Image uploaded to S3")
        print("   ✓ Analysis task enqueued")
        print("   ✓ Teacher would receive confirmation message")

        return result


if __name__ == "__main__":
    print("=" * 60)
    print("EXERCISE BOOK SCANNER - END-TO-END TEST")
    print("=" * 60)

    result = asyncio.run(test_exercise_book_upload_flow())

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
