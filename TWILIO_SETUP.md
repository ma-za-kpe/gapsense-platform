# Twilio WhatsApp Setup Guide

## What You Need from Twilio Console

**Your Account SID:** `ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy`

### 1. Get Auth Token
**Location:** [Twilio Console → Account → API Keys & Tokens](https://console.twilio.com/us1/account/keys-credentials/api-keys)

**⚠️ IMPORTANT:** You need the **Live Auth Token**, not a test token

```bash
# In Twilio Console:
# 1. Go to Account → API Keys & Tokens
# 2. Click "Show" next to Auth Token (under "Live credentials")
# 3. Copy the token (starts with a random string)
```

**Add to `.env`:**
```bash
TWILIO_AUTH_TOKEN=your_auth_token_here
```

### 2. Activate WhatsApp Sandbox & Get Sender Number

**Option A: Twilio Sandbox (Immediate - for testing)**

**Step 1: Activate Sandbox in Console**
1. Go to [Twilio Console → Messaging → Try it out → Send a WhatsApp message](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
2. Accept terms and conditions to activate your sandbox
3. You'll see your sandbox number: `+14155238886`
4. Note your sandbox code (e.g., `title-effort`)

**Step 2: Join Sandbox from Your WhatsApp**
1. Open WhatsApp on your phone
2. Send this message to `+1 415 523 8886`:
   ```
   join title-effort
   ```
3. You'll receive a confirmation message
4. **Important:** Sandbox sessions expire after 3 days - you'll need to rejoin

**Step 3: Add to .env**
```bash
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

**⚠️ Common Issue:** Error 63007 means:
- Sandbox not activated in Console (Step 1)
- OR recipient hasn't joined sandbox (Step 2)
- OR using wrong Account SID/Auth Token

**Option B: Production Number (Requires approval - 1-2 weeks)**
```bash
# Location: Twilio Console → Messaging → Senders → WhatsApp senders
# URL: https://console.twilio.com/us1/develop/sms/senders/whatsapp-senders

# Steps:
# 1. Click "Request to enable your Twilio number for WhatsApp"
# 2. Fill out Meta Business verification
# 3. Wait for approval (1-2 weeks)
# 4. Once approved, number format:
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
```

### 3. Configure Webhook URL

**Location:** Twilio Console → Messaging → Settings → WhatsApp sandbox settings

```bash
# When a message comes in:
https://your-domain.com/webhooks/whatsapp

# Method: POST
# Content-Type: application/x-www-form-urlencoded
```

**For local testing with ngrok:**
```bash
# Install ngrok
brew install ngrok  # macOS

# Start ngrok tunnel
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Set webhook to: https://abc123.ngrok.io/webhooks/whatsapp
```

---

## Twilio CLI Setup (Optional but Recommended)

### Install Twilio CLI
```bash
brew tap twilio/brew && brew install twilio

# Or with npm
npm install -g twilio-cli
```

### Login
```bash
twilio login

# You'll be prompted for:
# Account SID: ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
# Auth Token: [from step 1 above]
```

### Useful CLI Commands
```bash
# List your phone numbers
twilio phone-numbers:list

# List WhatsApp senders
twilio api:messaging:v1:services:list

# Send test WhatsApp message
twilio api:core:messages:create \
  --from "whatsapp:+14155238886" \
  --to "whatsapp:+233244123456" \
  --body "Test from GapSense"

# View message logs
twilio api:core:messages:list --limit 10

# Check webhook configuration
twilio phone-numbers:update [YOUR_NUMBER_SID] \
  --sms-url "https://your-domain.com/webhooks/whatsapp"
```

---

## Using Twilio Content API (Templates)

GapSense now supports Twilio Content API for WhatsApp templates.

### How it works:
```python
# If template_name starts with "HX", it's treated as a Content SID
await client.send_template(
    to="+256779401600",
    template_name="HXb5b62575e6e4ff6129ad7c8efe1f983e",  # Content SID
    language_code="en",  # Not used by Twilio
    parameters=[
        {"text": "12/1"},  # Variable 1
        {"text": "3pm"},   # Variable 2
    ]
)
```

### Creating Content Templates:
1. Go to [Twilio Console → Content](https://console.twilio.com/us1/develop/sms/content-editor)
2. Create a new Content template
3. Copy the Content SID (starts with "HX")
4. Use that SID as the template_name

**Example curl:**
```bash
curl 'https://api.twilio.com/2010-04-01/Accounts/ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy/Messages.json' -X POST \
  --data-urlencode 'To=whatsapp:+256779401600' \
  --data-urlencode 'From=whatsapp:+14155238886' \
  --data-urlencode 'ContentSid=HXb5b62575e6e4ff6129ad7c8efe1f983e' \
  --data-urlencode 'ContentVariables={"1":"12/1","2":"3pm"}' \
  -u ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy:[YourAuthToken]
```

---

## Complete .env Configuration

```bash
# Choose provider: "meta" or "twilio"
WHATSAPP_PROVIDER=twilio

# Twilio credentials (from steps above)
TWILIO_ACCOUNT_SID=ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# For webhook verification (can be any string)
WHATSAPP_VERIFY_TOKEN=gapsense_verify_token_2026
```

---

## Testing Your Setup

### 1. Start the server
```bash
docker compose up web
```

### 2. Send test message
From your WhatsApp, send a message to your Twilio number

### 3. Check logs
```bash
docker compose logs web --tail=50 --follow
```

You should see:
```
Webhook received: {...}
Received text message from +233244123456
```

### 4. Test API directly
```bash
# Test sending a message
curl -X POST http://localhost:8000/api/v1/test/send-whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+233244123456",
    "text": "Test from GapSense API"
  }'
```

---

## Troubleshooting

### Webhook not receiving messages
1. Check webhook URL is correct in Twilio Console
2. Ensure ngrok is running (for local dev)
3. Check server logs for errors

### Messages not sending

**Error 63007: "Channel with the specified From address not found"**
- The sandbox WhatsApp channel is not activated
- **Solution:** In [Twilio Console → WhatsApp Sandbox](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn), ensure:
  1. Sandbox is activated
  2. Your test number has joined (send "join title-effort" to +1 415 523 8886)
  3. The From number matches the sandbox number exactly

```bash
# Check Twilio logs
twilio api:core:messages:list --limit 5

# Common errors:
# - Invalid phone number format (must be E.164: +233244123456)
# - Sandbox not joined (send "join [code]" first)
# - Auth token incorrect
# - Sandbox not activated (error 63007)
```

### Meta vs Twilio Differences

| Feature | Meta WhatsApp Cloud API | Twilio WhatsApp |
|---------|------------------------|-----------------|
| **Setup Time** | Instant | Sandbox: Instant, Production: 1-2 weeks |
| **Cost** | Free tier: 1000 conversations/month | Pay per message (~$0.005) |
| **Interactive Buttons** | ✅ Native support | ❌ Falls back to numbered lists |
| **Templates** | ✅ Template name + language | ✅ Content SID (HX...) supported |
| **Template Variables** | `[{"text": "val"}]` | `{"1": "val"}` (auto-converted) |
| **Webhook Format** | JSON | Form-encoded (auto-normalized) |
| **Media Download** | 2-step (get URL, then download) | Direct URL |

---

## Quick Start Checklist

- [ ] **Activate Sandbox** - Go to [Twilio Console](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn) and activate
- [ ] **Join Sandbox** - Send "join title-effort" to +1 415 523 8886 from WhatsApp
- [ ] **Get Auth Token** - From [API Keys page](https://console.twilio.com/us1/account/keys-credentials/api-keys)
- [ ] **Update .env** - Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
- [ ] **Restart server** - `docker compose restart web`
- [ ] **Test integration** - `docker compose exec web python test_twilio_integration.py`
- [ ] **Configure webhook** - Set up ngrok and add webhook URL in Twilio Console

## Next Steps

1. ✅ Activate sandbox in Twilio Console
2. ✅ Join sandbox from your WhatsApp (send "join title-effort")
3. ✅ Get Auth Token from Twilio Console
4. ✅ Update `.env` file with credentials
5. ✅ Restart server: `docker compose restart web`
6. ✅ Run test: `docker compose exec web python test_twilio_integration.py`
7. ✅ Configure webhook URL for incoming messages

## Support Resources

- **Twilio WhatsApp Docs:** https://www.twilio.com/docs/whatsapp
- **Twilio Console:** https://console.twilio.com
- **Twilio CLI Docs:** https://www.twilio.com/docs/twilio-cli/quickstart
- **WhatsApp Sandbox:** https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
