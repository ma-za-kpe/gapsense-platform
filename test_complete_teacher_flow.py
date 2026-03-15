"""
Complete Teacher Flow Test - Including Exercise Book Upload

Tests the entire teacher journey:
1. START and onboarding
2. Upload exercise book
3. Check status/gaps/student reports
"""

import asyncio
import io

import httpx


async def test_complete_flow():
    """Test complete teacher flow with exercise book upload."""

    base_url = "http://localhost:8000"
    teacher_phone = "+233500999999"

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n" + "=" * 60)
        print("🎓 COMPLETE TEACHER FLOW TEST")
        print("=" * 60)

        # Step 0: RESTART to clear any previous state
        print("\n0️⃣  Sending RESTART to clear previous state...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "RESTART", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print("   ✅ State cleared")

        # Step 1: START onboarding
        print("\n1️⃣  Sending START...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "START", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print(f"   ✅ Response: {data['response'][:100]}...")
        print(f"   Flow: {data.get('flow')}, Next Step: {data.get('next_step')}")

        # Step 2: School name
        print("\n2️⃣  Entering school name...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "St. Mary's JHS, Accra", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print(f"   ✅ Response: {data['response'][:100]}...")
        print(f"   Next Step: {data.get('next_step')}")

        # Step 3: Class name
        print("\n3️⃣  Entering class name...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "JHS 1A", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print(f"   ✅ Response: {data['response'][:100]}...")
        print(f"   Next Step: {data.get('next_step')}")

        # Step 4: Student count
        print("\n4️⃣  Entering student count...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "3", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print(f"   ✅ Response: {data['response'][:100]}...")
        print(f"   Next Step: {data.get('next_step')}")

        # Step 5: Student names
        print("\n5️⃣  Entering student names...")
        student_names = "Kwame Mensah\nAkosua Boateng\nKofi Asante"
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": student_names, "teacher_phone": teacher_phone},
        )
        data = response.json()
        print(f"   ✅ Response: {data['response'][:200]}...")
        print(f"   Completed: {data.get('completed')}")
        print(f"   Flow: {data.get('flow')}, Next Step: {data.get('next_step')}")

        # Step 5b: Confirm student creation (send as button click)
        if data.get("next_step") == "CONFIRM_STUDENT_CREATION":
            print("\n5️⃣b Confirming student creation (clicking 'Yes' button)...")
            response = await client.post(
                f"{base_url}/demo/api/message",
                data={
                    "message": "Yes, create profiles",
                    "button_id": "confirm_yes",
                    "teacher_phone": teacher_phone,
                },
            )
            data = response.json()
            print(f"   ✅ Response: {data['response'][:200]}...")
            print(f"   Completed: {data.get('completed')}")
            print(f"   Flow: {data.get('flow')}, Next Step: {data.get('next_step')}")

        # Step 6: Get teacher info to verify setup
        print("\n6️⃣  Getting teacher info...")
        response = await client.get(
            f"{base_url}/demo/api/teacher-info",
            params={"teacher_phone": teacher_phone},
        )
        data = response.json()
        if data.get("success"):
            print(f"   ✅ School: {data['teacher'].get('school_name')}")
            print(f"   ✅ Class: {data['teacher'].get('class_name')}")
            print(f"   ✅ Students: {len(data['students'])} students")
            for student in data["students"]:
                print(f"      • {student['name']}")
        else:
            print(f"   ❌ Error getting teacher info: {data.get('error')}")
            print(f"   Response: {data}")

        # Step 7: Create and upload exercise book image
        print("\n7️⃣  Creating exercise book image...")
        # Create a minimal valid JPEG (1x1 pixel)
        # JPEG header + minimal data
        jpeg_data = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
            b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
            b"\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01"
            b"\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00"
            b"?\x00\x7f\x00\xff\xd9"
        )
        img_bytes = io.BytesIO(jpeg_data)

        print("\n8️⃣  Uploading exercise book...")
        files = {"image": ("exercise_book.jpg", img_bytes, "image/jpeg")}
        form_data = {"teacher_phone": teacher_phone}

        response = await client.post(
            f"{base_url}/demo/api/upload-image",
            files=files,
            data=form_data,
        )
        data = response.json()

        if data.get("success"):
            print("   ✅ Upload successful!")
            print(f"   Response: {data['response'][:200]}...")
            print(f"   Flow: {data.get('flow')}, Next Step: {data.get('next_step')}")
        else:
            print(f"   ❌ Upload failed: {data.get('error')}")
            print(f"   Full response: {data}")

        # Step 9: Try to select a student (if prompted)
        if data.get("success") and data.get("next_step") == "AWAITING_STUDENT_SELECTION":
            print("\n9️⃣  Selecting student (Kwame - option 1)...")
            response = await client.post(
                f"{base_url}/demo/api/message",
                data={"message": "1", "teacher_phone": teacher_phone},
            )
            data = response.json()
            print(f"   ✅ Response: {data['response'][:200]}...")
            print(f"   Flow: {data.get('flow')}, Next Step: {data.get('next_step')}")

        # Step 10: Check STATUS
        print("\n🔟 Checking /STATUS...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "/STATUS", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print(f"   ✅ Response: {data['response'][:300]}...")

        # Step 11: Check /GAPS
        print("\n1️⃣1️⃣  Checking /GAPS...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "/GAPS", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print(f"   ✅ Response: {data['response'][:300]}...")

        # Step 12: Check individual student
        print("\n1️⃣2️⃣  Checking /STUDENT Kwame...")
        response = await client.post(
            f"{base_url}/demo/api/message",
            data={"message": "/STUDENT Kwame", "teacher_phone": teacher_phone},
        )
        data = response.json()
        print(f"   ✅ Response: {data['response'][:300]}...")

        print("\n" + "=" * 60)
        print("✅ COMPLETE TEACHER FLOW TEST FINISHED")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_complete_flow())
