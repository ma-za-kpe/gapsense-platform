"""
Test Demo Mode Bypass in Exercise Book Scanner

Verifies that demo phone numbers bypass WhatsApp/Twilio calls.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path
sys.path.insert(0, "/Users/mac/Documents/projects/gapsense platform/gapsense/src")


async def test_demo_mode_detection():
    """Test that demo phone patterns are correctly detected."""
    from gapsense.engagement.exercise_book_scanner import ExerciseBookScanner

    # Test patterns that SHOULD be demo mode
    demo_phones = [
        "+233500012345",  # Double-zero pattern
        "+233501234567",  # Test pattern 1234567
        "+233501111111",  # Test pattern 1111111
        "+233502222222",  # Test pattern 2222222
        "+233509999999",  # Test pattern 9999999
    ]

    # Test patterns that should NOT be demo mode (real Vodafone)
    real_phones = [
        "+233501234568",  # Doesn't match test patterns
        "+233508888888",  # Different pattern
        "+233509876543",  # Different pattern
    ]

    print("🧪 Testing Demo Mode Detection\n")

    print("✅ Should be DEMO MODE:")
    for phone in demo_phones:
        is_demo = ExerciseBookScanner._is_demo_mode(phone)
        print(f"  {phone}: {is_demo}")
        assert is_demo, f"{phone} should be demo mode"

    print("\n❌ Should be REAL MODE:")
    for phone in real_phones:
        is_demo = ExerciseBookScanner._is_demo_mode(phone)
        print(f"  {phone}: {is_demo}")
        assert not is_demo, f"{phone} should NOT be demo mode"

    print("\n✅ Demo mode detection working correctly!\n")


async def test_demo_mode_bypass_in_process_analysis_result():
    """Test that process_analysis_result skips WhatsApp for demo phones."""
    from gapsense.engagement.exercise_book_scanner import ExerciseBookScanner

    # Mock database session
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    # Mock services
    mock_media = MagicMock()
    mock_worker = MagicMock()
    mock_guard = MagicMock()
    mock_ai = MagicMock()
    mock_prompt = MagicMock()

    scanner = ExerciseBookScanner(
        db=mock_db,
        media_service=mock_media,
        worker_service=mock_worker,
        guard_service=mock_guard,
        ai_client=mock_ai,
        prompt_service=mock_prompt,
    )

    # Mock database queries
    from uuid import uuid4

    student_id = str(uuid4())
    mock_student = MagicMock()
    mock_student.id = student_id
    mock_student.first_name = "Test Student"

    # Mock select().where() chain for student lookup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_student
    mock_db.execute.return_value = mock_result

    # Test analysis data
    analysis = {
        "gap_node_ids": ["GH.JHS1.MATH.001"],
        "errors": [{"description": "Test error"}],
        "patterns": ["Pattern 1"],
        "focus_areas": ["Focus area 1"],
        "image_quality": "good",
        "confidence": 0.85,
    }

    print("🧪 Testing WhatsApp Bypass in process_analysis_result\n")

    # Test with DEMO phone
    print("Testing with DEMO phone: +233501234567")
    with patch("gapsense.engagement.exercise_book_scanner.WhatsAppClient") as mock_whatsapp_class:
        mock_client = AsyncMock()
        mock_whatsapp_class.from_settings.return_value = mock_client

        await scanner.process_analysis_result(
            student_id=student_id,
            teacher_phone="+233501234567",  # DEMO phone
            analysis=analysis,
            country="GH",
            language="en",
        )

        # WhatsApp client should NOT be created or called for demo phone
        if mock_whatsapp_class.from_settings.called:
            print("  ❌ WhatsApp client WAS created (should be skipped for demo)")
            print(f"     Called {mock_whatsapp_class.from_settings.call_count} times")
            return False
        else:
            print("  ✅ WhatsApp client NOT created (correctly skipped for demo)")

    # Test with REAL phone
    print("\nTesting with REAL phone: +233508888888")
    with patch("gapsense.engagement.exercise_book_scanner.WhatsAppClient") as mock_whatsapp_class:
        mock_client = AsyncMock()
        mock_whatsapp_class.from_settings.return_value = mock_client

        # Reset mock_db
        mock_result.scalar_one_or_none.return_value = mock_student

        await scanner.process_analysis_result(
            student_id=student_id,
            teacher_phone="+233508888888",  # REAL phone
            analysis=analysis,
            country="GH",
            language="en",
        )

        # WhatsApp client SHOULD be created and called for real phone
        if mock_whatsapp_class.from_settings.called:
            print("  ✅ WhatsApp client WAS created (correct for real phone)")
            print(f"     send_text_message called: {mock_client.send_text_message.called}")
            if not mock_client.send_text_message.called:
                print("  ⚠️  send_text_message was NOT called (unexpected)")
        else:
            print("  ❌ WhatsApp client NOT created (should be called for real phone)")
            return False

    print("\n✅ WhatsApp bypass working correctly!\n")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("DEMO MODE BYPASS TEST SUITE")
    print("=" * 60 + "\n")

    try:
        # Test 1: Demo mode detection
        await test_demo_mode_detection()

        # Test 2: WhatsApp bypass in process_analysis_result
        success = await test_demo_mode_bypass_in_process_analysis_result()

        if success:
            print("=" * 60)
            print("✅ ALL TESTS PASSED")
            print("=" * 60)
            return 0
        else:
            print("=" * 60)
            print("❌ TESTS FAILED")
            print("=" * 60)
            return 1

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
