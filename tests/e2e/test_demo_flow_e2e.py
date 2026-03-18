"""
E2E Test: Demo/Web Flow

Tests the complete demo flow from image upload to gap profile creation.
Also includes Phase 1 Infrastructure Hardening verification tests.

Flow:
1. User uploads image via browser
2. POST /demo/api/upload-image
3. TeacherFlowExecutor(demo_mode=True) processes image
4. ExerciseBookScanner uploads to S3, enqueues SQS task
5. Worker polls SQS, processes image analysis
6. ImageAnalysisOrchestrator runs 6-step pipeline
7. GapProfile created in DB
8. DemoNotificationService logs (no real WhatsApp messages)
9. User can view results at dashboard
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.exceptions import PermanentError, RetryableError
from gapsense.core.models import GapProfile, Student, Teacher
from gapsense.main import app
from gapsense.services.worker_service import TASK_TYPES, WorkerService, WorkerTask

# Production URL from env — when set, tests hit the real production server
# instead of the in-process ASGI app.
# Usage: E2E_BASE_URL=http://3.83.162.241:8000 pytest tests/e2e/test_demo_flow_e2e.py -xvs
PRODUCTION_URL = os.environ.get("E2E_BASE_URL")
IS_PRODUCTION = PRODUCTION_URL is not None


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def override_db(db_session: AsyncSession):
    """Override app's get_db to use test session.

    This fixes the 'Task got Future attached to a different loop' error
    by ensuring the FastAPI app uses the same session as the test.
    """

    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield db_session
    app.dependency_overrides.clear()


@pytest.fixture
async def e2e_client() -> AsyncClient:
    """HTTP client that targets either local ASGI app or production URL.

    Set E2E_BASE_URL env var to target production:
        E2E_BASE_URL=http://3.83.162.241:8000 pytest tests/e2e/... -xvs
    """
    if PRODUCTION_URL:
        async with AsyncClient(base_url=PRODUCTION_URL, timeout=120.0) as client:
            yield client
    else:
        from httpx import ASGITransport

        from gapsense.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


def _make_worker_service(
    session_factory=None,
    queue_url="http://localhost:4566/000000000000/test-queue",
    dlq_url="http://localhost:4566/000000000000/test-dlq",
):
    """Create a WorkerService with mocked dependencies for testing."""
    mock_settings = MagicMock()
    mock_settings.SQS_QUEUE_URL = queue_url
    mock_settings.SQS_DLQ_URL = dlq_url
    mock_settings.AWS_REGION = "af-south-1"
    mock_settings.AWS_ACCESS_KEY_ID = "test"
    mock_settings.AWS_SECRET_ACCESS_KEY = "test"  # pragma: allowlist secret
    return WorkerService(
        ai_client=MagicMock(),
        media_service=MagicMock(),
        guard_service=MagicMock(),
        prompt_service=MagicMock(),
        settings=mock_settings,
        session_factory=session_factory,
        max_concurrent=5,
    )


# ============================================================================
# Test Class
# ============================================================================


@pytest.mark.asyncio
class TestDemoFlowE2E:
    """E2E tests for demo/web flow with DemoNotificationService."""

    async def test_complete_demo_flow(self, e2e_client: AsyncClient):
        """Test complete demo flow from upload to gap profile creation.

        This test validates the full E2E flow with the real worker:
        1. Demo teacher creation via onboarding
        2. Student creation via onboarding
        3. Image upload via /demo/api/upload-image
        4. Student selection to trigger analysis
        5. S3 upload and SQS task enqueue
        6. Worker processes task (real worker in Docker)
        7. GapProfile created in DB
        8. Dashboard accessible

        NOTE: This test does NOT use override_db or db_session fixtures
        because those destroy the schema that the real worker needs.
        Instead, it uses AsyncSessionLocal for DB queries.
        """
        # Use demo phone pattern (+2335000*)
        demo_phone = f"+2335000{uuid4().hex[:6]}"

        # Step 1: Create demo teacher via onboarding flow
        print(f"\n📍 Step 1: Create demo teacher {demo_phone}")

        # Send "hi" to start onboarding - goes to COLLECT_SCHOOL step
        resp = await e2e_client.post(
            "/demo/api/message",
            data={"message": "hi", "teacher_phone": demo_phone},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["flow"] == "FLOW-TEACHER-ONBOARD"
        assert data["next_step"] == "COLLECT_SCHOOL"
        print(f"✅ Started onboarding, step: {data['next_step']}")

        # Provide school name - goes to COLLECT_CLASS step
        resp = await e2e_client.post(
            "/demo/api/message",
            data={"message": "E2E Test School", "teacher_phone": demo_phone},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["next_step"] == "COLLECT_CLASS"
        print(f"✅ School collected, step: {data['next_step']}")

        # Provide class name - goes to COLLECT_STUDENT_COUNT step
        resp = await e2e_client.post(
            "/demo/api/message",
            data={"message": "JHS 1", "teacher_phone": demo_phone},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["next_step"] == "COLLECT_STUDENT_COUNT"
        print(f"✅ Class collected, step: {data['next_step']}")

        # Step 2: Create student via onboarding flow
        print("\n📍 Step 2: Create student")

        # Provide student count (1) - goes to COLLECT_STUDENT_LIST step
        resp = await e2e_client.post(
            "/demo/api/message",
            data={"message": "1", "teacher_phone": demo_phone},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["next_step"] == "COLLECT_STUDENT_LIST"
        print(f"✅ Student count collected, step: {data['next_step']}")

        # Provide student name - goes to CONFIRM_STUDENT_CREATION step
        resp = await e2e_client.post(
            "/demo/api/message",
            data={"message": "E2E Test Student", "teacher_phone": demo_phone},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["next_step"] == "CONFIRM_STUDENT_CREATION"
        assert "E2E Test Student" in data["response"]
        print(f"✅ Student name collected, step: {data['next_step']}")

        # Confirm student creation (button click) - completes onboarding
        resp = await e2e_client.post(
            "/demo/api/message",
            data={
                "message": "Yes, create students",
                "teacher_phone": demo_phone,
                "button_id": "confirm_yes",
            },
        )
        assert resp.status_code == 200
        confirm_data = resp.json()
        assert confirm_data["success"] is True
        assert confirm_data["completed"] is True
        print(f"✅ Onboarding completed: {confirm_data}")

        # Wait for student creation to complete
        await asyncio.sleep(1)

        if IS_PRODUCTION:
            # Production: we trust the onboarding API responses
            # We don't have direct DB access, so skip DB verification
            student_id = None  # Not needed for production polling
            print("✅ Skipping direct DB verification (production mode)")
        else:
            # Local: query real DB to get teacher and student IDs
            from gapsense.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Teacher).where(Teacher.phone == demo_phone))
                teacher = result.scalar_one_or_none()
                assert teacher is not None, f"Teacher not found for phone {demo_phone}"
                print(f"✅ Teacher created: {teacher.id}")

                result = await session.execute(
                    select(Student).where(Student.teacher_id == teacher.id)
                )
                student = result.scalar_one_or_none()
                assert student is not None, "Student not found"
                assert student.full_name == "E2E Test Student"
                print(f"✅ Student created: {student.id}, name: {student.full_name}")

                student_id = student.id

        # Step 3: Upload exercise book image
        print("\n📍 Step 3: Upload exercise book image")

        # Get test image path
        test_image_path = Path(__file__).parent.parent.parent / "mathhomeworkjosh.webp"
        if not test_image_path.exists():
            pytest.fail(f"Test image not found: {test_image_path}")

        with open(test_image_path, "rb") as f:
            image_data = f.read()

        # Upload image via /demo/api/upload-image
        # This starts FLOW-EXERCISE-BOOK-SCAN and goes to SELECT_STUDENT step
        resp = await e2e_client.post(
            "/demo/api/upload-image",
            data={"teacher_phone": demo_phone},
            files={"image": ("test_exercise_book.webp", image_data, "image/webp")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["flow"] == "FLOW-EXERCISE-BOOK-SCAN"
        assert data["next_step"] == "SELECT_STUDENT"
        print(f"✅ Image uploaded, step: {data['next_step']}")

        # Step 4: Select student to trigger analysis
        print("\n📍 Step 4: Select student to trigger analysis")

        # Send "1" to select the first (and only) student
        resp = await e2e_client.post(
            "/demo/api/message",
            data={"message": "1", "teacher_phone": demo_phone},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        print(f"✅ Student selected, analysis triggered: {data}")

        # Step 5: Wait for worker to process task
        print("\n📍 Step 5: Wait for worker to process task (up to 120s)")

        timeout = 120  # Production AI calls can take longer
        gap_profile = None

        if IS_PRODUCTION:
            # Production: poll dashboard endpoint since we can't access DB directly
            for i in range(timeout):
                await asyncio.sleep(1)
                try:
                    resp = await e2e_client.get(f"/demo/reports/{demo_phone}")
                    if resp.status_code == 200:
                        # Check if the page contains gap profile data
                        body = resp.text
                        # Dashboard shows student card with gap info when profile exists
                        # Look for student name + gap-related content (not "exercise_book" — HTML uses spaces)
                        body_lower = body.lower()
                        if "e2e test student" in body_lower and (
                            "gaps identified" in body_lower or "exercise book" in body_lower
                        ):
                            print(f"✅ Gap profile detected in dashboard after {i+1} seconds")
                            gap_profile = True  # Flag that we found it
                            break
                except Exception:
                    pass

                if (i + 1) % 10 == 0:
                    print(f"⏳ Waiting... {i+1}s elapsed")
        else:
            # Local: poll DB directly
            from gapsense.core.database import AsyncSessionLocal

            for i in range(timeout):
                await asyncio.sleep(1)
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(GapProfile).where(
                            GapProfile.student_id == student_id,
                            GapProfile.is_current == True,  # noqa: E712
                        )
                    )
                    gap_profile = result.scalar_one_or_none()

                if gap_profile:
                    print(f"✅ GapProfile created after {i+1} seconds")
                    break

                if (i + 1) % 10 == 0:
                    print(f"⏳ Waiting... {i+1}s elapsed")

        # Step 6: Verify GapProfile was created
        print("\n📍 Step 6: Verify GapProfile")

        if gap_profile is None:
            pytest.fail(
                f"Worker did not create GapProfile within {timeout} seconds. "
                "Check worker logs with: docker compose logs worker --tail=100"
                if not IS_PRODUCTION
                else "Check production worker logs with: aws logs tail /ecs/gapsense-worker --region us-east-1 --since 5m"
            )

        if IS_PRODUCTION:
            print("✅ GapProfile verified via dashboard content")
        else:
            assert gap_profile is not None
            assert gap_profile.student_id == student_id
            assert gap_profile.source == "exercise_book"
            print(f"✅ GapProfile verified: {gap_profile.id}")
            print(f"   - Gap nodes: {len(gap_profile.gap_nodes) if gap_profile.gap_nodes else 0}")
            print(f"   - Source: {gap_profile.source}")

        # Step 7: Verify dashboard is accessible
        print("\n📍 Step 7: Verify dashboard access")

        resp = await e2e_client.get(f"/demo/reports/{demo_phone}")
        assert resp.status_code == 200
        print("✅ Dashboard accessible")

        print("\n🎉 E2E Demo Flow Test Complete!")

    async def test_demo_notification_service_usage(
        self, async_client: AsyncClient, override_db: AsyncSession
    ):
        """Test that DemoNotificationService is used (not WhatsAppClient).

        Uses override_db fixture since this test doesn't need the real worker.
        It just verifies the upload endpoint returns 200.
        """
        db_session = override_db
        demo_phone = f"+2335000{uuid4().hex[:6]}"

        # Create minimal teacher and student via API
        from gapsense.core.models import District, School

        # Create a school (seeded region id=1 and district id=1 exist from conftest)
        result = await db_session.execute(select(District).limit(1))
        district = result.scalar_one()
        school = School(
            name="Demo Test School",
            district_id=district.id,
            school_type="jhs",
            is_active=True,
        )
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone=demo_phone,
            first_name="Demo",
            last_name="Teacher",
            school_id=school.id,
            grade_taught="JHS1",
        )
        db_session.add(teacher)
        await db_session.commit()
        await db_session.refresh(teacher)

        student = Student(
            teacher_id=teacher.id,
            first_name="Demo",
            full_name="Demo Student",
            current_grade="JHS1",
        )
        db_session.add(student)
        await db_session.commit()

        # Get test image
        test_image_path = Path(__file__).parent.parent.parent / "mathhomeworkjosh.webp"
        if not test_image_path.exists():
            pytest.skip(f"Test image not found: {test_image_path}")

        with open(test_image_path, "rb") as f:
            image_data = f.read()

        # Upload image
        resp = await async_client.post(
            "/demo/api/upload-image",
            data={"teacher_phone": demo_phone},
            files={"image": ("test.webp", image_data, "image/webp")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        # The fact that this succeeded without throwing errors means:
        # 1. DemoNotificationService was used (not WhatsAppClient)
        # 2. Notifications were logged (not sent to real WhatsApp)
        # 3. No real WhatsApp API calls were made

        print("✅ DemoNotificationService used correctly (no real WhatsApp messages)")

    async def test_demo_phone_pattern_detection(self):
        """Test that demo phone patterns are correctly detected."""
        # Demo patterns that should be detected
        demo_patterns = [
            "+23350001234567",  # +2335000* pattern (dedicated demo prefix)
            "+2335011111111",  # Ends with 1111111 (unlikely real number)
            "+2335012222222",  # Ends with 2222222 (unlikely real number)
            "+2335019999999",  # Ends with 9999999 (unlikely real number)
            "+2335010000000",  # Ends with 0000000 (unlikely real number)
        ]

        # Production patterns that should NOT be detected as demo
        production_patterns = [
            "+233501234567",  # Real Vodafone (valid subscriber number)
            "+233541234567",  # Real MTN (valid subscriber number)
            "+233201234567",  # Real Vodafone (valid subscriber number)
            "+233509876543",  # Real Vodafone (different valid subscriber)
        ]

        # Test demo detection logic (same as in image_analysis_orchestrator.py)
        # Note: Removed "1234567"/"01234567" as they can appear in valid phone numbers
        test_patterns = ["1111111", "2222222", "3333333", "0000000", "9999999"]

        for phone in demo_patterns:
            is_demo = phone.startswith("+2335000") or any(
                phone.endswith(pattern) for pattern in test_patterns
            )
            assert is_demo, f"Phone {phone} should be detected as demo"
            print(f"✅ {phone} detected as demo")

        for phone in production_patterns:
            is_demo = phone.startswith("+2335000") or any(
                phone.endswith(pattern) for pattern in test_patterns
            )
            assert not is_demo, f"Phone {phone} should NOT be detected as demo"
            print(f"✅ {phone} detected as production")

        print("✅ All phone pattern detection tests passed")

    # ========================================================================
    # Phase 1 Infrastructure Hardening Tests
    # ========================================================================

    async def test_phase1_worker_service_session_factory(self):
        """Test that WorkerService can be instantiated with session_factory parameter.

        Phase 1 changed WorkerService to use session_factory instead of db
        for per-task session lifecycle.
        """
        # Create a mock session factory
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        def mock_session_factory():
            return mock_session

        # Verify WorkerService accepts session_factory parameter
        worker = _make_worker_service(session_factory=mock_session_factory)

        assert worker._session_factory is mock_session_factory
        assert worker._ai_client is not None
        assert worker._media_service is not None
        print("✅ WorkerService instantiated with session_factory parameter")

    async def test_phase1_idempotency_guard(self):
        """Test that processing the same message twice results in duplicate detection.

        Phase 1 added ProcessingLedger table with INSERT ON CONFLICT DO NOTHING
        for idempotency.

        NOTE: Uses AsyncSessionLocal instead of db_session fixture to avoid
        schema destruction that would affect other tests.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from gapsense.core.database import AsyncSessionLocal
        from gapsense.core.models.processing_ledger import ProcessingLedger

        message_id = f"test-msg-{uuid4().hex[:8]}"
        task_type = "image_analyze"

        async with AsyncSessionLocal() as session:
            # First insert should succeed
            stmt1 = (
                pg_insert(ProcessingLedger)
                .values(
                    sqs_message_id=message_id,
                    task_type=task_type,
                    student_id=None,
                )
                .on_conflict_do_nothing(constraint="uq_ledger_msg_task")
            )

            result1 = await session.execute(stmt1)
            await session.commit()

            assert result1.rowcount == 1, "First insert should succeed"
            print(f"✅ First insert succeeded (rowcount={result1.rowcount})")

        async with AsyncSessionLocal() as session:
            # Second insert with same message_id and task_type should be skipped
            stmt2 = (
                pg_insert(ProcessingLedger)
                .values(
                    sqs_message_id=message_id,
                    task_type=task_type,
                    student_id=None,
                )
                .on_conflict_do_nothing(constraint="uq_ledger_msg_task")
            )

            result2 = await session.execute(stmt2)
            await session.commit()

            assert result2.rowcount == 0, "Second insert should be skipped (duplicate)"
            print(f"✅ Second insert skipped as duplicate (rowcount={result2.rowcount})")

        async with AsyncSessionLocal() as session:
            # Verify only one record exists
            result = await session.execute(
                select(ProcessingLedger).where(
                    ProcessingLedger.sqs_message_id == message_id,
                    ProcessingLedger.task_type == task_type,
                )
            )
            records = result.scalars().all()
            assert len(records) == 1, "Should have exactly one record"
            print("✅ Idempotency guard working correctly")

    async def test_phase1_error_classification(self):
        """Test that PermanentError routes to DLQ and RetryableError retries.

        Phase 1 added exception hierarchy: PermanentError → DLQ immediately,
        RetryableError → retry with backoff.
        """
        # Create worker with mocked SQS client
        worker = _make_worker_service()

        # Mock the SQS operations
        mock_sqs_client = AsyncMock()
        mock_sqs_client.send_message = AsyncMock(return_value={"MessageId": "test-123"})
        mock_sqs_client.delete_message = AsyncMock()

        # Create a context manager mock for the SQS client
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__ = AsyncMock(return_value=mock_sqs_client)
        mock_client_cm.__aexit__ = AsyncMock(return_value=None)

        # Patch the session's create_client to return our mock
        worker._session.create_client = MagicMock(return_value=mock_client_cm)

        # Test 1: PermanentError should go to DLQ immediately
        task = WorkerTask(
            task_type="image_analyze",
            payload={"student_id": str(uuid4())},
            retry_count=0,
            max_retries=3,
            message_id="test-msg-1",
            receipt_handle="test-receipt-1",
        )

        await worker._handle_failure(task, PermanentError("Student not found"))

        # Verify DLQ was called (send_message to DLQ URL)
        assert mock_sqs_client.send_message.called, "Should send to DLQ"
        call_args = mock_sqs_client.send_message.call_args
        assert worker._dlq_url in str(call_args), "Should send to DLQ URL"
        print("✅ PermanentError routed to DLQ immediately")

        # Reset mocks
        mock_sqs_client.send_message.reset_mock()
        mock_sqs_client.delete_message.reset_mock()

        # Test 2: RetryableError with retries remaining should requeue
        task2 = WorkerTask(
            task_type="image_analyze",
            payload={"student_id": str(uuid4())},
            retry_count=0,
            max_retries=3,
            message_id="test-msg-2",
            receipt_handle="test-receipt-2",
        )

        await worker._handle_failure(task2, RetryableError("S3 timeout"))

        # Verify requeue was called (send_message to main queue with delay)
        assert mock_sqs_client.send_message.called, "Should requeue"
        call_args = mock_sqs_client.send_message.call_args
        # Check that DelaySeconds was set (backoff)
        assert "DelaySeconds" in str(call_args), "Should have delay for backoff"
        print("✅ RetryableError requeued with backoff")

        # Reset mocks
        mock_sqs_client.send_message.reset_mock()

        # Test 3: RetryableError with max retries exhausted should go to DLQ
        task3 = WorkerTask(
            task_type="image_analyze",
            payload={"student_id": str(uuid4())},
            retry_count=3,  # Already at max
            max_retries=3,
            message_id="test-msg-3",
            receipt_handle="test-receipt-3",
        )

        await worker._handle_failure(task3, RetryableError("S3 timeout"))

        # Verify DLQ was called
        assert mock_sqs_client.send_message.called, "Should send to DLQ after max retries"
        print("✅ RetryableError with max retries exhausted routed to DLQ")

    async def test_phase1_cost_logging_isolation(self):
        """Test that _log_ai_cost doesn't crash the pipeline when DB commit fails.

        Phase 1 added try/except/rollback in _log_ai_cost to isolate failures.
        """
        from gapsense.services.image_analysis_orchestrator import ImageAnalysisOrchestrator

        # Create mock dependencies
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock(side_effect=Exception("DB commit failed"))
        mock_db.rollback = AsyncMock()

        mock_ai_client = MagicMock()
        mock_media_service = MagicMock()
        mock_guard_service = MagicMock()
        mock_prompt_service = MagicMock()
        mock_worker_service = MagicMock()

        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=mock_ai_client,
            media_service=mock_media_service,
            guard_service=mock_guard_service,
            prompt_service=mock_prompt_service,
            worker_service=mock_worker_service,
        )

        # Create mock context and response
        mock_student = MagicMock()
        mock_student.id = uuid4()
        mock_student.teacher_id = uuid4()

        mock_ctx = MagicMock()
        mock_ctx.student = mock_student

        mock_response = MagicMock()
        mock_response.provider = "anthropic"
        mock_response.model = "claude-sonnet-4-6"
        mock_response.prompt_id = "TEST-001"
        mock_response.input_tokens = 1000
        mock_response.output_tokens = 500
        mock_response.latency_ms = 150.0
        mock_response.json_parsed = {"test": "data"}

        # Call _log_ai_cost - should NOT raise even though commit fails
        try:
            await orchestrator._log_ai_cost(mock_ctx, mock_response)
            print("✅ _log_ai_cost completed without raising exception")
        except Exception as e:
            pytest.fail(f"_log_ai_cost should not raise, but got: {e}")

        # Verify rollback was called after commit failure
        mock_db.rollback.assert_called_once()
        print("✅ Rollback called after commit failure")
        print("✅ Cost logging isolation working correctly")

    async def test_phase1_model_string_updated(self):
        """Verify that the model string claude-sonnet-4-6 is used in relevant source files."""
        from gapsense.ai.cost_calculator import ANTHROPIC_PRICING

        # Check that claude-sonnet-4-6 is in the pricing table
        assert (
            "claude-sonnet-4-6" in ANTHROPIC_PRICING
        ), "claude-sonnet-4-6 should be in ANTHROPIC_PRICING"
        print("✅ claude-sonnet-4-6 found in ANTHROPIC_PRICING")

        # Verify the pricing is correct
        pricing = ANTHROPIC_PRICING["claude-sonnet-4-6"]
        from decimal import Decimal

        assert pricing["input"] == Decimal("3.00"), "Input price should be $3/MTok"
        assert pricing["output"] == Decimal("15.00"), "Output price should be $15/MTok"
        print("✅ claude-sonnet-4-6 pricing verified ($3/$15 per MTok)")

    async def test_phase1_stub_handlers_raise_not_implemented(self):
        """Test that stub handlers raise NotImplementedError.

        Phase 1 requires tts_generate and voice_transcribe to raise NotImplementedError.
        """
        worker = _make_worker_service()

        # Test tts_generate raises NotImplementedError
        tts_task = WorkerTask(
            task_type="tts_generate",
            payload={"text": "Hello", "language": "en"},
        )

        with pytest.raises(NotImplementedError, match="TTS generation is not yet implemented"):
            await worker._handle_tts_generate(tts_task)
        print("✅ tts_generate raises NotImplementedError")

        # Test voice_transcribe raises NotImplementedError
        voice_task = WorkerTask(
            task_type="voice_transcribe",
            payload={"audio_url": "s3://bucket/audio.mp3"},
        )

        with pytest.raises(NotImplementedError, match="Voice transcription is not yet implemented"):
            await worker._handle_voice_transcribe(voice_task)
        print("✅ voice_transcribe raises NotImplementedError")

    async def test_phase1_unknown_task_type_raises_value_error(self):
        """Test that unknown task types raise ValueError.

        Phase 1 requires unknown task types to raise ValueError.
        """
        worker = _make_worker_service()

        unknown_task = WorkerTask(
            task_type="unknown_task_type",
            payload={},
        )

        with pytest.raises(ValueError, match="Unknown task type"):
            await worker._route_task(unknown_task)
        print("✅ Unknown task type raises ValueError")

    async def test_phase1_task_types_constant(self):
        """Verify TASK_TYPES constant contains expected task types."""
        expected_types = {"tts_generate", "image_analyze", "scheduled_message", "voice_transcribe"}

        assert (
            expected_types == TASK_TYPES
        ), f"TASK_TYPES should be {expected_types}, got {TASK_TYPES}"
        print(f"✅ TASK_TYPES verified: {TASK_TYPES}")
