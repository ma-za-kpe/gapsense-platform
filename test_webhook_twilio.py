"""
Test Twilio Webhook Handler

Simulates Twilio sending a WhatsApp message webhook to our endpoint.
Run with: docker compose exec web python test_webhook_twilio.py
"""

import asyncio

import httpx


async def test_twilio_webhook():
    """Test Twilio WhatsApp webhook handling."""
    print("=" * 60)
    print("Twilio Webhook Integration Test")
    print("=" * 60)
    print()

    # Simulate Twilio webhook payload (form-encoded format)
    # This is what Twilio sends when a user messages us
    twilio_webhook_data = {
        "SmsMessageSid": "SM1234567890abcdef",
        "NumMedia": "0",
        "ProfileName": "Test User",
        "MessageType": "text",
        "SmsSid": "SM1234567890abcdef",
        "WaId": "256779401600",
        "SmsStatus": "received",
        "Body": "Hello GapSense!",
        "To": "whatsapp:+14155238886",
        "NumSegments": "1",
        "ReferralNumMedia": "0",
        "MessageSid": "SM1234567890abcdef",
        "AccountSid": "ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
        "From": "whatsapp:+256779401600",
        "ApiVersion": "2010-04-01",
    }

    print("Sending Twilio webhook to http://localhost:8000/v1/webhooks/whatsapp")
    print(f"From: {twilio_webhook_data['From']}")
    print(f"Body: {twilio_webhook_data['Body']}")
    print()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/v1/webhooks/whatsapp",
                data=twilio_webhook_data,  # Form-encoded
                timeout=10.0,
            )

            print(f"✅ Response Status: {response.status_code}")
            print(f"✅ Response Body: {response.text}")
            print()

            if response.status_code == 200:
                print("✅ SUCCESS! Webhook handler accepted Twilio format")
                print()
                print("What happened:")
                print("1. Twilio webhook → normalized to Meta format")
                print("2. Message routed to appropriate flow (teacher/parent)")
                print("3. Response sent via Twilio API (async)")
                print()
                print("Check logs: docker compose logs web --tail=50")
            else:
                print(f"❌ FAILED with status {response.status_code}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_twilio_webhook())
