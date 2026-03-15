# Twilio WhatsApp Integration - Summary

## ✅ What's Completed

### 1. Multi-Provider WhatsApp Abstraction
- **Provider Pattern** - Clean abstraction for Meta and Twilio providers
- **Automatic Provider Selection** - Based on `WHATSAPP_PROVIDER` env var
- **Webhook Normalization** - Twilio webhooks auto-converted to Meta format
- **Media Download** - Both providers support image/voice download:
  - **Meta**: 2-step process (get URL, then download)
  - **Twilio**: Direct URL download with HTTP Basic Auth

### 2. Twilio Content API Support
- **Template Support** - Pass Content SID (e.g., `HXb5b62575e6e4ff6129ad7c8efe1f983e`) as template_name
- **Auto Parameter Conversion** - Meta format `[{"text": "val"}]` → Twilio format `{"1": "val"}`
- **Fallback** - Non-SID templates fall back to plain text

### 3. Feature Implementations
- ✅ **ExerciseBookScanner** - Downloads teacher images, uploads to S3, enqueues analysis
- ✅ **VoiceMicroCoaching** - Downloads parent voice, uploads to S3, enqueues transcription
- ✅ **Interactive Messages** - Buttons/lists fall back to numbered text for Twilio
- ✅ **Error Handling** - Comprehensive logging and user-friendly error messages

### 4. Configuration
- ✅ Docker Compose updated with all Twilio env vars
- ✅ Sandbox credentials configured (ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
- ✅ Production placeholders ready (ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy)
- ✅ Pydantic validation for WHATSAPP_PROVIDER setting

### 5. Testing & Documentation
- ✅ Integration test script (`test_twilio_integration.py`)
- ✅ Comprehensive setup guide (`TWILIO_SETUP.md`)
- ✅ Troubleshooting section with common errors
- ✅ Content API usage examples

---

## 🚧 What You Need to Do

### Critical Steps (Required for Testing)

#### 1. Activate Twilio Sandbox
**Why:** Error 63007 occurs because sandbox isn't activated

**Steps:**
1. Go to: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
2. Click "Activate Sandbox" or accept terms
3. Note your sandbox code (currently: `title-effort`)

#### 2. Join Sandbox from WhatsApp
**Why:** Recipients must join before receiving messages

**Steps:**
1. Open WhatsApp on your phone
2. Send to `+1 415 523 8886`:
   ```
   join title-effort
   ```
3. Wait for confirmation message
4. **Note:** Session expires after 3 days - you'll need to rejoin

#### 3. Get Live Auth Token
**Why:** You may need the production auth token (not test token)

**Steps:**
1. Go to: https://console.twilio.com/us1/account/keys-credentials/api-keys
2. Click "Show" next to "Live credentials" → Auth Token
3. Copy the token
4. Update `.env`:
   ```bash
   TWILIO_AUTH_TOKEN=your_live_auth_token_here
   ```
5. Restart: `docker compose restart web`

---

## 🧪 Testing After Setup

### Quick Test
```bash
# Verify configuration loaded
docker compose exec web python -c "
from gapsense.engagement.whatsapp import get_whatsapp_client
client = get_whatsapp_client()
print(f'Provider: {type(client).__name__}')
print(f'From: {client.from_number}')
"

# Run integration test
docker compose exec web python test_twilio_integration.py
```

### Expected Results
- ✅ Text message delivered to WhatsApp
- ✅ Button message shows as numbered list
- ✅ No error 63007

### If Still Error 63007
1. **Check Sandbox Status** - Console shows "Active"?
2. **Verify Join** - Did you get confirmation message?
3. **Check Account SID** - Does it match sandbox account (ACffb5a30362f6b...)?
4. **Check Auth Token** - Using LIVE token, not test token?

---

## 📝 Optional: Content API Templates

### Create a Template
1. Go to: https://console.twilio.com/us1/develop/sms/content-editor
2. Create new WhatsApp template
3. Copy Content SID (starts with "HX")
4. Use in code:
   ```python
   await client.send_template(
       to="+256779401600",
       template_name="HXb5b62575e6e4ff6129ad7c8efe1f983e",
       language_code="en",
       parameters=[{"text": "12/1"}, {"text": "3pm"}]
   )
   ```

---

## 🌐 Webhook Setup (For Incoming Messages)

### Local Development with ngrok
```bash
# Install ngrok
brew install ngrok  # or: npm install -g ngrok

# Start tunnel
ngrok http 8000

# Copy HTTPS URL (e.g., https://abc123.ngrok.io)
# In Twilio Console → Sandbox Settings:
# "When a message comes in": https://abc123.ngrok.io/webhooks/whatsapp
```

### Test Incoming Message
1. Send message from WhatsApp to +1 415 523 8886
2. Check logs: `docker compose logs web --tail=50 --follow`
3. Should see: "Webhook received" and "Received text message"

---

## 📊 Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Provider Abstraction** | ✅ Complete | Meta + Twilio support |
| **Media Download** | ✅ Complete | Images + Voice |
| **ExerciseBookScanner** | ✅ Wired | Downloads & processes images |
| **VoiceMicroCoaching** | ✅ Wired | Downloads & processes voice |
| **Content API** | ✅ Complete | Template support with SID |
| **Configuration** | ⚠️ Partial | Sandbox credentials set, needs activation |
| **Testing** | ⚠️ Blocked | Waiting for sandbox activation |
| **Webhooks** | 🚧 Pending | Needs ngrok + URL configuration |

---

## 🔄 Switching to Production

When ready to use production Twilio account:

1. **Update .env:**
   ```bash
   # Comment out sandbox
   # TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   # TWILIO_AUTH_TOKEN=fake_auth_token_32chars_here_xxx

   # Uncomment production
   TWILIO_ACCOUNT_SID=ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
   TWILIO_AUTH_TOKEN=your_production_auth_token
   TWILIO_WHATSAPP_NUMBER=whatsapp:+your_production_number
   ```

2. **Restart:**
   ```bash
   docker compose restart web
   ```

3. **No join required** - Production numbers work directly

---

## 📚 Resources

- **Twilio Console:** https://console.twilio.com
- **WhatsApp Sandbox:** https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
- **Content Templates:** https://console.twilio.com/us1/develop/sms/content-editor
- **API Docs:** https://www.twilio.com/docs/whatsapp
- **Error 63007:** https://www.twilio.com/docs/api/errors/63007

---

## 🆘 Getting Help

If you encounter issues:

1. **Check sandbox activation** - Most common cause of error 63007
2. **Verify you've joined** - Send "join title-effort" if not done
3. **Check logs** - `docker compose logs web --tail=50`
4. **Review TWILIO_SETUP.md** - Detailed troubleshooting guide
5. **Test with curl** - Bypass our code to isolate Twilio issues:
   ```bash
   curl 'https://api.twilio.com/2010-04-01/Accounts/ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/Messages.json' \
     -X POST \
     --data-urlencode 'To=whatsapp:+256779401600' \
     --data-urlencode 'From=whatsapp:+14155238886' \
     --data-urlencode 'Body=Test from curl' \
     -u ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx:fake_auth_token_32chars_here_xxx
   ```

---

**Last Updated:** 2026-03-15
**Platform Version:** Local Development
**Twilio Provider:** Sandbox (ACffb5a30362f6b...)
