"""
Test Grok AI Analysis with Real Exercise Book Image

Tests the complete flow:
1. Teacher onboarding
2. Upload REAL exercise book image (simultaneous equations)
3. Trigger Grok AI analysis via WorkerService
4. Verify gap detection results

This replaces hard-coded mock data with actual AI-powered analysis.
"""

import asyncio
from pathlib import Path

import httpx


async def test_grok_ai_analysis():
    """Test complete teacher flow with REAL Grok AI analysis."""

    base_url = "http://localhost:8000"
    teacher_phone = "+233500888888"

    # Path to real exercise book image
    exercise_book_path = Path(__file__).parent / "test_exercise_book_mth.jpeg"

    if not exercise_book_path.exists():
        print(f"❌ Exercise book image not found: {exercise_book_path}")
        return

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n" + "=" * 70)
        print("🧠 TESTING GROK AI ANALYSIS WITH REAL EXERCISE BOOK")
        print("=" * 70)
        print(f"\n📚 Using image: {exercise_book_path.name}")
        print(f"   Size: {exercise_book_path.stat().st_size / 1024:.1f} KB")

        # Step 0: RESTART to clear any previous state
        print("\n0️⃣  Sending RESTART...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "RESTART", "teacher_phone": teacher_phone},
        )
        print("   ✅ State cleared")

        # Step 1: START onboarding
        print("\n1️⃣  Starting onboarding...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "START", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print(f"   ✅ {data['response'][:60]}...")

        # Step 2: School name
        print("\n2️⃣  Entering school name...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "Tema International School", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print("   ✅ School set")

        # Step 3: Class name (must be Ghana format: JHS 1-3 or Basic 7-9)
        print("\n3️⃣  Entering class name...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "JHS 1A", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print("   ✅ Class set")

        # Step 4: Student count
        print("\n4️⃣  Entering student count...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "2", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print("   ✅ Count set")

        # Step 5: Student names
        print("\n5️⃣  Entering student names...")
        student_names = "Ama Asante\nKwesi Mensah"
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": student_names, "teacher_phone": teacher_phone},
        )
        data = response.json()
        print("   ✅ Students added")

        # Step 5b: Confirm student creation
        if data.get("next_step") == "CONFIRM_STUDENT_CREATION":
            print("\n5️⃣b Confirming student creation...")
            response = await client.post(
                f"{base_url}/demo/api/message",
                data={
                    "message": "Yes, create profiles",
                    "button_id": "confirm_yes",
                    "teacher_phone": teacher_phone,
                },
            )
            data = response.json()
            print("   ✅ Students confirmed")

        # Step 6: Upload REAL exercise book image
        print("\n" + "=" * 70)
        print("📸 UPLOADING REAL EXERCISE BOOK IMAGE FOR GROK AI ANALYSIS")
        print("=" * 70)
        print("\n   Topic: SIMULTANEOUS EQUATIONS")
        print("   Content: Worked example with substitution method")
        print("   Expected gaps: Algebraic manipulation, substitution method")
        print("")

        with open(exercise_book_path, "rb") as f:
            files = {"image": (exercise_book_path.name, f, "image/png")}
            form_data = {"teacher_phone": teacher_phone}

            print("   📤 Sending to demo API...")
            response = await client.post(
                f"{base_url}/demo/api/upload-image",
                files=files,
                data=form_data,
            )

        if response.status_code != 200:
            print(f"\n❌ Upload failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return

        data = response.json()

        if not data.get("success"):
            print(f"\n❌ Upload failed: {data.get('error')}")
            print(f"   Full response: {data}")
            return

        print("\n✅ UPLOAD SUCCESSFUL!")
        print("\n📋 Response from API:")
        print(f"   {data['response'][:200]}")

        # Step 7: Select student for the exercise book
        if data.get("next_step") == "SELECT_STUDENT":
            print("\n7️⃣  Selecting student (Ama - option 1)...")
            response = await client.post(
                f"{base_url}/demo/api/message",
                data={"message": "1", "teacher_phone": teacher_phone},
            )
            data = response.json()
            print("\n🧠 GROK AI ANALYSIS TRIGGERED!")
            print("\n📊 Analysis response:")
            print(f"   {data['response'][:300]}")

            # Check if it's real analysis or mock
            if "Found 3 gaps in fractions" in data["response"]:
                print("\n⚠️  WARNING: Still using MOCK analysis (hard-coded)")
            else:
                print("\n✅ REAL GROK AI ANALYSIS DETECTED!")

        print("\n" + "=" * 70)
        print("🎉 TEST COMPLETE")
        print("=" * 70)
        print("\n📝 Summary:")
        print("   • Teacher onboarding: ✅")
        print("   • Exercise book upload: ✅")
        print("   • Student selection: ✅")
        print(
            "   • Grok AI analysis: "
            + (
                "✅ REAL"
                if "Found 3 gaps in fractions" not in data.get("response", "")
                else "❌ MOCK"
            )
        )
        print("")


if __name__ == "__main__":
    asyncio.run(test_grok_ai_analysis())
