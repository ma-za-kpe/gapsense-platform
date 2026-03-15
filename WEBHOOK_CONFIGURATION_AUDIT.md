# WhatsApp Webhook Configuration Audit

**Issue Reported:** User receives welcome message but reply gets "configure whatsapp sandbox inbound url to change this message"

**Root Cause:** Twilio webhook URL not configured in Twilio Console

---

## Problem Diagnosis

### What's Happening

```
1. User sends "Hi" to +1 415 523 8886 (Twilio WhatsApp sandbox)
   ↓
2. ✅ GapSense sends welcome message
   "Welcome to GapSense! 📚... Are you ready to begin? Reply YES to continue."
   ↓
3. User replies "YES"
   ↓
4. ❌ Twilio receives message but doesn't know where to send webhook
   ↓
5. Twilio responds with default error message:
   "configure whatsapp sandbox inbound url to change this message"
```

### Why This Happens

**Twilio Webhook Flow:**
- **Outbound (GapSense → User):** Works ✅
  - `TwilioWhatsAppProvider.send_text_message()` → Twilio API → WhatsApp → User
- **Inbound (User → GapSense):** BROKEN ❌
  - User → WhatsApp → Twilio → **WEBHOOK NOT CONFIGURED** → Default error message

**The Missing Piece:**
Twilio needs to know WHERE to send incoming messages. This is configured in Twilio Console under **Sandbox Settings → When a message comes in**.

---

## Fix: Configure Webhook URL

### Option 1: Local Development with ngrok (Recommended for Testing)

#### Step 1: Install and Start ngrok
```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Start ngrok tunnel to your local server
ngrok http 8000
```

**Output:**
```
Forwarding  https://abc123-randomstring.ngrok-free.app -> http://localhost:8000
```

**Copy the HTTPS URL** (e.g., `https://abc123-randomstring.ngrok-free.app`)

#### Step 2: Configure Twilio Webhook

1. Go to **[Twilio Console → Messaging → Try it out → Send a WhatsApp message](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)**

2. Scroll down to **Sandbox Configuration**

3. Under **"When a message comes in":**
   - **URL:** `https://abc123-randomstring.ngrok-free.app/v1/webhooks/whatsapp`
   - **HTTP Method:** `POST`
   - **Content Type:** `application/x-www-form-urlencoded`

4. Click **Save**

#### Step 3: Test
```bash
# Send message from WhatsApp to +1 415 523 8886
"Hi"

# Check ngrok dashboard
open http://127.0.0.1:4040

# You should see POST request to /v1/webhooks/whatsapp

# Check GapSense logs
docker compose logs web --tail=50 --follow
```

**Expected Log Output:**
```
Webhook received: {'object': 'whatsapp_business_account', ...}
Received text message from +256779401600 (ID: SM...)
Found existing parent: +256779401600
Routing to ParentFlowExecutor
Flow executed: FLOW-ONBOARD (completed: False)
```

---

### Option 2: Production Deployment (ngrok Alternative)

If deploying to a server with a public domain:

1. **Deploy GapSense to server** (e.g., AWS EC2, Digital Ocean, Render)

2. **Get HTTPS URL** (e.g., `https://gapsense.yourdomain.com`)

3. **Configure webhook:**
   ```
   URL: https://gapsense.yourdomain.com/v1/webhooks/whatsapp
   Method: POST
   ```

4. **Ensure server is accessible:**
   - Port 443 (HTTPS) open
   - SSL certificate configured
   - Server running and healthy

---

## Webhook Endpoint Details

### Endpoint: `POST /v1/webhooks/whatsapp`

**Location:** `src/gapsense/webhooks/whatsapp.py:71-130`

**What It Does:**
1. Receives webhook from Twilio (form-encoded) or Meta (JSON)
2. Normalizes to Meta format via `TwilioWebhookAdapter`
3. Extracts messages and status updates
4. Routes to `_handle_message()` which:
   - Detects user type (parent vs teacher)
   - Routes to `FlowExecutor` or `TeacherFlowExecutor`
   - Sends response via `WhatsAppClient`

**Returns:** `{"status": "received"}` (must respond within 20 seconds)

### Webhook Payload (Twilio → Normalized)

**Twilio sends (form-encoded):**
```
From=whatsapp:+256779401600
Body=YES
MessageSid=SM1234567890abcdef
AccountSid=ACyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
...
```

**GapSense normalizes to:**
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "field": "messages",
      "value": {
        "messages": [{
          "from": "256779401600",
          "type": "text",
          "text": {"body": "YES"},
          "id": "SM1234567890abcdef"
        }]
      }
    }]
  }]
}
```

**Processed by:**
```python
# src/gapsense/webhooks/whatsapp.py:_handle_message
async def _handle_message(message, value, db):
    from_number = message.get("from")  # "256779401600"
    message_type = message.get("type")  # "text"
    content = _extract_message_content(message)  # "YES"

    # Detect user type
    user_type, user = await _detect_user_type(db, from_number)

    if user_type == "parent":
        executor = FlowExecutor(db=db)
        result = await executor.process_message(
            parent=user,
            message_type="text",
            message_content="YES",
            message_id="SM..."
        )
```

---

## Testing Checklist

### ✅ Pre-Webhook Configuration (Current State)

- [x] Server running: `curl http://localhost:8000/health` returns 200
- [x] Twilio credentials in `.env`
- [x] Twilio sandbox activated
- [x] User joined sandbox (sent "join title-effort")
- [x] GapSense can send messages to user (welcome message received)

### ❌ Post-Webhook Configuration (Needed)

- [ ] ngrok tunnel started
- [ ] Webhook URL configured in Twilio Console
- [ ] Test message sent → webhook received
- [ ] User reply processed → correct flow response

---

## Expected Flow After Fix

```
User sends "Hi"
  ↓
Twilio → POST https://abc123.ngrok-free.app/v1/webhooks/whatsapp
  ↓
GapSense webhook handler
  ↓
_detect_user_type() → Creates new Parent
  ↓
FlowExecutor.process_message()
  ↓
_start_onboarding()
  ↓
WhatsAppClient.send_text_message()
  ↓
Twilio API → User receives:
  "Welcome to GapSense! 📚

  I'm here to help you support your child's learning in math...

  Are you ready to begin? Reply YES to continue."

User sends "YES"
  ↓
Twilio → POST https://abc123.ngrok-free.app/v1/webhooks/whatsapp
  ↓
GapSense webhook handler
  ↓
_handle_message() → Parent found
  ↓
FlowExecutor.process_message()
  ↓
_onboard_opt_in() → Button response expected
  ↓
⚠️ ISSUE: User sent "YES" as text, not button click
  ↓
WhatsAppClient.send_text_message()
  ↓
Twilio API → User receives:
  "Please click one of the buttons above to continue."
```

### ⚠️ Secondary Issue Discovered: Text vs Button Response

**Problem:** GapSense sends button message but user replies with text "YES" instead of clicking button.

**Why:** Twilio falls back to numbered lists (doesn't support native buttons), so user sees:
```
Welcome to GapSense! 📚

Are you ready to begin? Reply YES to continue.

1. Yes, start
2. Not now

Reply with a number (1-2)
```

**Expected User Response:** "1" (not "YES")

**Code Location:** `src/gapsense/engagement/whatsapp/twilio_provider.py:64-92`

---

## Onboarding Flow Audit (From Docs)

### Teacher Onboarding (FLOW-TEACHER-ONBOARD)

**Entry:** Teacher is manually added to database first OR uses invitation code

**Method 1: Manual Entry (Current)**
1. Admin creates Teacher record in database with phone number
2. Teacher sends "START" to WhatsApp
3. Flow begins: School → Class → Student Count → Student List → Confirm
4. Students created with `primary_parent_id = NULL` (awaiting parent linkage)

**Method 2: Invitation Code (Preferred)**
1. School admin creates SchoolInvitation via API/admin panel
2. Admin generates invitation code (e.g., "STMARYS-ABC123")
3. Teacher receives code via SMS/email/in-person
4. Teacher sends code to WhatsApp
5. Teacher automatically linked to school
6. Flow continues: Class → Student Count → Student List → Confirm

**Code:** `src/gapsense/engagement/teacher_flows.py`

**Database Flow:**
```sql
-- School created (if doesn't exist)
INSERT INTO schools (name, district_id, is_active) VALUES (?, ?, TRUE);

-- Teacher updated
UPDATE teachers SET
  school_id = ?,
  class_name = ?,
  grade_taught = ?,
  onboarded_at = NOW()
WHERE phone = ?;

-- Students created (N records)
INSERT INTO students (
  full_name, first_name, current_grade,
  school_id, teacher_id, is_active,
  primary_parent_id  -- NULL (awaiting parent)
) VALUES (?, ?, ?, ?, ?, TRUE, NULL);
```

---

### Parent Onboarding (FLOW-ONBOARD)

**Entry:** Parent sends any message to WhatsApp (auto-creates Parent record)

**Steps:**
1. **AWAITING_OPT_IN:** Parent clicks "Yes, start" button
2. **AWAITING_STUDENT_SELECTION:** Parent selects child from numbered list of unlinked students
3. **CONFIRM_STUDENT_SELECTION:** Parent confirms selection
4. **AWAITING_DIAGNOSTIC_CONSENT:** Parent consents to diagnostic quiz
5. **AWAITING_LANGUAGE:** Parent selects language preference

**Code:** `src/gapsense/engagement/flow_executor.py:370-1390`

**Critical Linkage:**
```python
# flow_executor.py:1318 (AWAITING_LANGUAGE step)
student.primary_parent_id = parent.id  # ✅ LINKS PARENT TO STUDENT
student.home_language = language_code
parent.onboarded_at = now
```

**Database Flow:**
```sql
-- Parent created on first message
INSERT INTO parents (phone, opted_in) VALUES (?, FALSE);

-- Parent opts in
UPDATE parents SET
  opted_in = TRUE,
  opted_in_at = NOW()
WHERE phone = ?;

-- Parent selects student
-- (stored in conversation_state.data.selected_student_id)

-- Parent confirms → CRITICAL LINK
UPDATE students SET
  primary_parent_id = ?,  -- Parent ID
  home_language = ?
WHERE id = ? AND primary_parent_id IS NULL;  -- Race condition check

-- Parent completes onboarding
UPDATE parents SET
  diagnostic_consent = TRUE,
  preferred_language = ?,
  onboarded_at = NOW()
WHERE id = ?;

-- Diagnostic session created (if consented)
INSERT INTO diagnostic_sessions (
  student_id, entry_grade, initiated_by,
  channel, status
) VALUES (?, ?, 'parent', 'whatsapp', 'pending');
```

---

### School Onboarding (Not via WhatsApp)

**Current:** Schools are created via:
1. **Manual database seeding** (migrations)
2. **API endpoint** (admin-only)
3. **Teacher onboarding** (auto-creates if doesn't exist)

**Future:** May add school admin onboarding flow

**Code:** `src/gapsense/core/models/schools.py`

---

## Templates Audit

### Current Template Usage

**None currently in use.** All messages are plain text.

**Code sends text messages only:**
```python
# flow_executor.py:395-403
welcome_text = (
    "Welcome to GapSense! 📚\n\n"
    "I'm here to help you support your child's learning in math. "
    "Let's start by getting to know you better.\n\n"
    "Are you ready to begin? Reply YES to continue."
)
message_id = await client.send_text_message(to=parent.phone, text=welcome_text)
```

**Why No Templates?**
- Meta requires pre-approval for templates (1-2 weeks)
- Twilio requires Content API setup
- For MVP: Plain text is faster to iterate

**Template Support Added:**
- `TwilioWhatsAppProvider.send_template()` supports Content SIDs (HX...)
- `MetaWhatsAppProvider.send_template()` supports template names
- Not yet used in production flows

---

## Button Message Fallback (Twilio)

### Problem

Twilio doesn't support native WhatsApp interactive buttons, so GapSense falls back to numbered lists.

### Example

**Meta sends:**
```
Welcome to GapSense! 📚

Are you ready to begin?

[Button: Yes, start] [Button: Not now]
```

**Twilio sends:**
```
Welcome to GapSense! 📚

Are you ready to begin?

1. Yes, start
2. Not now

Reply with a number (1-2)
```

**Code:** `src/gapsense/engagement/whatsapp/twilio_provider.py:64-92`

```python
async def send_button_message(
    self, *, to: str, body: str, buttons: list[dict[str, str]],
    header: str | None = None, footer: str | None = None
) -> str:
    """Send button message as numbered list (Twilio doesn't support native buttons)."""
    parts = []
    if header:
        parts.append(header)
        parts.append("")

    parts.append(body)
    parts.append("")

    for i, btn in enumerate(buttons, 1):
        parts.append(f"{i}. {btn['title']}")

    parts.append("")
    parts.append(f"Reply with a number (1-{len(buttons)})")

    if footer:
        parts.append("")
        parts.append(footer)

    return await self._send_message(to=to, body="\n".join(parts))
```

### Impact on User Experience

**Parent sees:**
```
Welcome to GapSense! 📚

I'm here to help you support your child's learning in math...

Are you ready to begin?

1. Yes, start
2. Not now

Reply with a number (1-2)
```

**But code expects:** Interactive button response with `type: "interactive", interactive: {type: "button_reply", button_reply: {id: "yes_start"}}`

**What actually happens:** User sends "1" as text → `type: "text", text: {body: "1"}`

**Flow executor checks:**
```python
# flow_executor.py:497-512
if message_type != "interactive" or not isinstance(message_content, dict):
    # Invalid input - they need to click a button
    message_id = await client.send_text_message(
        to=parent.phone,
        text="Please click one of the buttons above to continue.",
    )
```

**Result:** User gets error message even though they replied correctly with "1"

---

## Critical Bugs Identified

### BUG-WEBHOOK-001: Webhook URL Not Configured
**Severity:** CRITICAL - Blocks all inbound messages
**Fix:** Configure webhook in Twilio Console (see Option 1 above)

### BUG-WEBHOOK-002: Button Fallback Not Handled
**Severity:** HIGH - Breaks parent onboarding on Twilio
**Location:** `src/gapsense/engagement/flow_executor.py:497-512`
**Issue:** Code expects interactive button response but Twilio sends numbered text
**Fix:** Accept text responses "1", "2" as button clicks when provider is Twilio

**Required Code Change:**
```python
# flow_executor.py:_onboard_opt_in
async def _onboard_opt_in(
    self, parent: Parent, message_type: str, message_content: str | dict[str, Any]
) -> FlowResult:
    # Check for button response OR numbered text (Twilio fallback)
    button_id = None

    if message_type == "interactive" and isinstance(message_content, dict):
        # Native button response (Meta)
        button_id = message_content.get("id")
    elif message_type == "text" and isinstance(message_content, str):
        # Numbered text response (Twilio fallback)
        text = message_content.strip()
        if text == "1":
            button_id = "yes_start"
        elif text == "2":
            button_id = "not_now"

    if button_id == "yes_start":
        # ... proceed with onboarding
```

**This fix needed for ALL button prompts:**
- `_onboard_opt_in` (AWAITING_OPT_IN)
- `_onboard_confirm_student_selection` (CONFIRM_STUDENT_SELECTION)
- `_onboard_collect_consent` (AWAITING_DIAGNOSTIC_CONSENT)
- `_onboard_collect_language` (AWAITING_LANGUAGE)
- `_confirm_student_creation` (teacher flow)

---

## Immediate Action Items

### 1. Configure Webhook (5 minutes)
```bash
# Terminal 1: Start ngrok
ngrok http 8000

# Copy HTTPS URL

# Browser: Go to Twilio Console
https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn

# Scroll to "When a message comes in"
# Paste: https://abc123.ngrok-free.app/v1/webhooks/whatsapp
# Method: POST
# Save
```

### 2. Test Webhook (2 minutes)
```bash
# Terminal 2: Watch logs
docker compose logs web --tail=50 --follow

# WhatsApp: Send message to +1 415 523 8886
"Hi"

# Verify logs show:
# Webhook received: {...}
# Received text message from...
```

### 3. Fix Button Fallback (30 minutes)
- Update all button handlers to accept numbered text responses
- Test with Twilio provider
- Verify Meta provider still works with native buttons

### 4. Add Webhook URL to .env (Optional)
```bash
# Add to .env for documentation
WEBHOOK_URL=https://abc123.ngrok-free.app/v1/webhooks/whatsapp

# Or for production
WEBHOOK_URL=https://gapsense.yourdomain.com/v1/webhooks/whatsapp
```

---

## Summary

**Root Cause:** Twilio webhook URL not configured → incoming messages have nowhere to go → default error message

**Primary Fix:** Configure webhook URL in Twilio Console

**Secondary Issue:** Twilio button fallback sends numbered text but code expects interactive response

**Impact:** Parent onboarding completely broken on Twilio until both issues fixed

**Next Steps:**
1. Configure webhook URL (5 min) ← **DO THIS NOW**
2. Test incoming messages (2 min)
3. Fix button fallback handling (30 min)
4. Update BUGFIX_REQUIREMENTS.md with new issues
