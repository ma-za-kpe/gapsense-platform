"""
Twilio WhatsApp Integration Test

Tests both regular messages and Content API templates.
Run with: docker compose exec web python test_twilio_integration.py
"""

import asyncio

from gapsense.engagement.whatsapp import get_whatsapp_client


async def test_twilio_integration():
    """Test Twilio WhatsApp integration."""
    client = get_whatsapp_client()

    print("=" * 60)
    print("Twilio WhatsApp Integration Test")
    print("=" * 60)
    print(f"Provider: {type(client).__name__}")
    print(f"Account SID: {client.account_sid[:15]}...")
    print(f"From: {client.from_number}")
    print()

    # Test phone number (Uganda number from your curl example)
    test_number = "+256779401600"

    print(f"Test recipient: {test_number}")
    print()
    print("⚠️  Make sure this number has joined the sandbox:")
    print("   Send 'join title-effort' to +1 415 523 8886")
    print()

    # Test 1: Simple text message
    print("=" * 60)
    print("Test 1: Simple Text Message")
    print("=" * 60)
    try:
        message_id = await client.send_text_message(
            to=test_number,
            text="Hello from GapSense! This is a test message from Twilio sandbox.",
        )
        print(f"✅ Text message sent! Message SID: {message_id}")
    except Exception as e:
        print(f"❌ Text message failed: {e}")

    print()

    # Test 2: Button message (falls back to numbered list)
    print("=" * 60)
    print("Test 2: Button Message (Numbered List)")
    print("=" * 60)
    try:
        message_id = await client.send_button_message(
            to=test_number,
            body="What would you like to do?",
            header="📚 GapSense Menu",
            footer="Reply with a number",
            buttons=[
                {"id": "1", "title": "📖 Start Learning"},
                {"id": "2", "title": "📊 View Progress"},
                {"id": "3", "title": "💬 Get Help"},
            ],
        )
        print(f"✅ Button message sent! Message SID: {message_id}")
    except Exception as e:
        print(f"❌ Button message failed: {e}")

    print()

    # Test 3: Content API Template (if you have one created)
    print("=" * 60)
    print("Test 3: Content API Template")
    print("=" * 60)
    print("📝 To test templates:")
    print("   1. Create a template in Twilio Console → Content")
    print("   2. Copy the Content SID (starts with HX)")
    print("   3. Uncomment and update the code below")
    print()

    # Example template from your curl:
    # content_sid = "HXb5b62575e6e4ff6129ad7c8efe1f983e"
    # try:
    #     message_id = await client.send_template(
    #         to=test_number,
    #         template_name=content_sid,  # Use Content SID as template_name
    #         language_code="en",
    #         parameters=[
    #             {"text": "12/1"},  # Variable 1
    #             {"text": "3pm"},   # Variable 2
    #         ],
    #     )
    #     print(f"✅ Template sent! Message SID: {message_id}")
    # except Exception as e:
    #     print(f"❌ Template failed: {e}")

    print()
    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Check your WhatsApp (+256779401600) for the messages")
    print("2. Create Content templates in Twilio Console")
    print("3. Configure webhook URL for incoming messages")


if __name__ == "__main__":
    asyncio.run(test_twilio_integration())
