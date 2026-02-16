# GapSense MVP User Flows — REALISTIC Status
**Evidence-Based Assessment of Current Implementation**

**Last Updated:** February 16, 2026 (Commit: 8d8858f)
**Purpose:** Track progress toward complete MVP user journey
**Audience:** Development team, UNICEF pitch preparation

---

## 🎯 MVP Goal: Complete User Journey

**Definition of "MVP Complete":**
A parent can onboard, receive a diagnostic, get an activity, complete it, and receive the next activity — all through WhatsApp, with minimal manual intervention.

**Current Status:** **35% Complete**
- ✅ Onboarding: 100% working
- ✅ Opt-out: 100% working
- ⚠️ Diagnostic: 70% (API exists, WhatsApp trigger missing)
- ❌ Activity Delivery: 0% (prompts exist, flow missing)
- ❌ Check-in Cycle: 0%
- ❌ Teacher Dashboard: 0%

---

## 📊 Status Legend

| Symbol | Meaning | Evidence Required |
|--------|---------|-------------------|
| ✅ **WORKING** | Can demo end-to-end today | Test passing, code deployed |
| ⚠️ **PARTIAL** | Code exists but not integrated | API/prompt exists, no WhatsApp trigger |
| 🔨 **IN PROGRESS** | Actively being built | Partial implementation, tests failing |
| ❌ **MISSING** | Not started | No code exists |
| 📝 **SPECIFIED** | Designed but not coded | Prompt/ADR exists, no implementation |

---

## THE THREE USER TYPES

```
┌─────────────────────────────────────────────────┐
│  1. PARENT (Home-Side)                          │
│     Primary user in Phase 1a MVP                │
│     Uses: WhatsApp only                         │
│     Status: Onboarding ✅, Diagnostic ❌        │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  2. STUDENT (The Child)                         │
│     Indirect user — does activities with parent │
│     Uses: Nothing directly (age 5-14)           │
│     Status: Record creation ✅, activities ❌   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  3. TEACHER (School-Side)                       │
│     Secondary user in Phase 1a MVP              │
│     Uses: Web dashboard (not built yet)         │
│     Status: API endpoints ✅, dashboard ❌      │
└─────────────────────────────────────────────────┘
```

---

# 🔄 THE SEVEN FLOWS

## FLOW 1: Parent Onboarding ✅ **100% WORKING**

### User Journey:
```
1. Parent gets WhatsApp number: +[GAPSENSE_NUMBER]
   (From teacher, poster, SMS, community champion)

2. Parent sends: "Hi" (or any message)

3. System responds with TMPL-ONBOARD-001:
   ┌──────────────────────────────────────────┐
   │ Welcome to GapSense! 📚                  │
   │                                          │
   │ Help your child learn with fun 3-minute │
   │ activities at home.                      │
   │                                          │
   │ [Yes, let's start!] [Not now]           │
   └──────────────────────────────────────────┘

4. Parent taps "Yes, let's start!"

5. System asks: "What is your child's first name?"
   Parent: "Kwame"

6. System asks: "How old is Kwame?"
   [5-6 years] [7-8 years] [9-10 years] [11-12 years]
   Parent selects: "7-8 years"

7. System asks: "What class is Kwame in?"
   Shows list: B1, B2, B3, B4, B5, B6, B7, B8, B9
   Parent selects: "B2"

8. System asks: "What language do you prefer?"
   [English] [Twi] [Ewe] [Ga] [Dagbani]
   Parent selects: "Twi"

9. System responds:
   ┌──────────────────────────────────────────┐
   │ All set! 🌟                              │
   │                                          │
   │ Kwame is registered for Class 2.        │
   │ We'll send you fun activities to help   │
   │ them learn.                              │
   │                                          │
   │ Thank you! 🙏                            │
   └──────────────────────────────────────────┘
```

### What Happens Behind the Scenes:
```python
# 1. Parent record created or updated
parent = Parent(
    phone="+233501234567",
    preferred_language="tw",
    opted_in=True,
    opted_in_at=datetime.now(UTC)
)

# 2. Student record created
student = Student(
    first_name="Kwame",
    age=7,
    current_grade="B2",
    primary_parent_id=parent.id,
    home_language="tw",
    school_language="English",
    is_active=True
)

# 3. Parent marked as onboarded
parent.onboarded_at = datetime.now(UTC)
parent.conversation_state = None  # Cleared

# FLOW STOPS HERE ❌
# Should trigger FLOW 2 (Diagnostic) but doesn't
```

### Evidence of Working Status:
- **File:** `src/gapsense/engagement/flow_executor.py` (lines 230-900)
- **Tests:** 25/25 passing (`tests/unit/test_flow_executor.py`, `tests/unit/test_onboard_spec_compliant.py`)
- **Coverage:** 72% on flow_executor.py
- **Commit:** 8d8858f (Feb 16, 2026)
- **WhatsApp:** Connected via webhook `/v1/webhooks/whatsapp`

### What's Missing:
- ❌ **Automatic diagnostic trigger** after onboarding completes
- ❌ **L1 messages** (all messages currently English, even if parent selected Twi)

---

## FLOW 2: Diagnostic Assessment ⚠️ **70% WORKING**

### Designed User Journey:
```
[Immediately after FLOW 1 completes]

1. System sends (2 minutes after onboarding):
   Hi [Parent]! 👋

   Time for a quick learning check for Kwame.
   I'll ask 3 simple questions. You can help Kwame answer.

   Ready? [Ready! ✅] [Later]

2. Parent taps "Ready!"

3. System asks Question 1 (starts at grade-1 level):
   [For B2 student, starts at B1 level]

   Kwame has 5 mangoes. Ama gives him 3 more.
   How many mangoes does Kwame have now?

   Parent/child responds: "8"

4. System analyzes (using DIAG-002):
   - ✅ Correct answer
   - ✅ Mastered B1.1.2.1 (Addition concept)
   - → Ask harder question (B2 level)

5. System asks Question 2:
   What is 23 + 15?

   Parent/child responds: "38"

6. System analyzes:
   - ✅ Correct
   - ✅ Mastered B2.1.2.1 (Multi-digit addition)
   - → Ask B2 prerequisite check

7. System asks Question 3:
   In the number 47, what does the 4 mean?

   Parent/child responds: "four"

8. System analyzes:
   - ❌ Incorrect (expected "40" or "4 tens")
   - ❌ Gap detected: B2.1.1.1 (Place value)
   - → Root cause found, stop diagnostic

9. System sends:
   Great job, Kwame! 🌟

   You're doing really well with addition!

   The next building block we're working on is understanding
   that in "47", the 4 means "40" (or 4 groups of 10).

   I'll send a fun activity to practice this tomorrow!
```

### What Actually Works:

#### ✅ **Diagnostic API (6 endpoints working):**
```bash
# Can be called directly via API (not from WhatsApp)

POST /v1/diagnostics/sessions
{
  "student_id": "uuid",
  "channel": "whatsapp"
}
→ Creates diagnostic session

POST /v1/diagnostics/sessions/{session_id}/answers
{
  "node_id": "B2.1.1.1",
  "response": "four",
  "response_type": "text"
}
→ Submits answer, gets next question

GET /v1/diagnostics/sessions/{session_id}/results
→ Returns gap profile when session complete
```

#### ✅ **AI Prompts Exist:**
- **DIAG-001:** Diagnostic Session Orchestrator (system prompt, 76 lines)
- **DIAG-002:** Next Question Generator (adaptive algorithm)
- **DIAG-003:** Gap Profile Synthesizer (dignity-first summary)

#### ✅ **Diagnostic Engine Code:**
- **File:** `src/gapsense/diagnostic/adaptive.py` (140 lines)
- **File:** `src/gapsense/diagnostic/questions.py` (53 lines)
- **Logic:** Backward-tracing through prerequisite graph ✅
- **Algorithm:** Screen 6 priority nodes → trace to root ✅

#### ⚠️ **What's Partially Working:**
```python
# diagnostic/adaptive.py exists but not called from WhatsApp

class AdaptiveEngine:
    async def select_next_question(self, session_id):
        # ✅ This works when called via API
        # ❌ Never called from flow_executor.py
        pass

    async def analyze_response(self, answer):
        # ✅ Uses DIAG-002 prompt
        # ❌ No WhatsApp trigger
        pass
```

### What's Missing:

#### ❌ **FLOW-DIAGNOSTIC (WhatsApp Integration):**
```python
# flow_executor.py SHOULD have this but doesn't:

async def _start_diagnostic(self, parent: Parent, student: Student):
    """Trigger diagnostic after onboarding."""
    # Create diagnostic session
    session = DiagnosticSession(
        student_id=student.id,
        channel="whatsapp",
        status="in_progress"
    )

    # Send first question via WhatsApp
    question = await self.adaptive_engine.get_first_question(student.current_grade)
    await self.whatsapp_client.send_text(parent.phone, question)

    # Update conversation state
    parent.conversation_state = {
        "flow": "FLOW-DIAGNOSTIC",
        "step": "AWAITING_ANSWER",
        "data": {"session_id": session.id, "question_number": 1}
    }

# THIS CODE DOES NOT EXIST ❌
```

#### ❌ **No Trigger from FLOW-ONBOARD:**
```python
# In flow_executor.py, line ~900, SHOULD have:

# After onboarding completes:
if parent.onboarded_at:
    # Trigger diagnostic
    await self._start_diagnostic(parent, student)  # ❌ Missing

# Currently just sends "All set!" and stops ❌
```

### Evidence:
- **Diagnostic API:** `src/gapsense/api/v1/diagnostics.py` (336 lines) ✅
- **Adaptive Engine:** `src/gapsense/diagnostic/adaptive.py` (140 lines) ✅
- **WhatsApp Trigger:** NOT FOUND in `flow_executor.py` ❌
- **Tests:** API tests passing ✅, WhatsApp integration tests missing ❌

### Time to Complete: **3-5 days**
1. Add FLOW-DIAGNOSTIC to flow_executor.py (1 day)
2. Add trigger from onboarding completion (2 hours)
3. Add conversation state handling for answers (1 day)
4. Test end-to-end WhatsApp diagnostic (1 day)
5. Handle edge cases (timeout, invalid answers) (1 day)

---

## FLOW 3: Gap Profile Generation ⚠️ **80% WORKING**

### Designed User Journey:
```
[After FLOW 2 diagnostic completes]

System generates gap profile using DIAG-003:

Hi [Parent]! 🌟

Here's what we learned about Kwame:

DOING GREAT:
✅ Addition and subtraction (counting, combining, taking away)
✅ Understanding equal sharing

NEXT BUILDING BLOCK:
🔨 Place value — understanding that in "47", the 4 means "40"

This is the foundation for multi-digit math. Once Kwame
masters this, everything else (bigger numbers, multiplication)
will be much easier!

I'll send a fun 3-minute activity tomorrow to help with this.
```

### What Works:

#### ✅ **Gap Profile API:**
```bash
GET /v1/diagnostics/sessions/{session_id}/results
→ Returns GapProfile object with:
  - root_gaps: [B2.1.1.1]
  - cascade_path: "Place Value Collapse"
  - mastered_nodes: [B1.1.1.1, B1.1.2.1, B1.1.2.2]
  - confidence: 0.85
```

#### ✅ **DIAG-003 Prompt Exists:**
```json
{
  "id": "DIAG-003",
  "name": "Gap Profile Synthesizer",
  "system_prompt": "Generate dignity-first gap summary...",
  "wolf_aurino_rules": [
    "NEVER use deficit language",
    "ALWAYS lead with what child CAN do",
    "Frame gaps as 'building blocks'"
  ]
}
```

#### ✅ **Database Schema:**
```python
class GapProfile(Base):
    id: UUID
    student_id: UUID
    diagnostic_session_id: UUID
    root_gaps: JSONB  # ["B2.1.1.1"]
    cascade_paths: JSONB  # ["Place Value Collapse"]
    mastered_nodes: JSONB  # ["B1.1.1.1", "B1.1.2.1"]
    confidence: Float  # 0.85
    ai_reasoning_log: JSONB
    created_at: DateTime
```

### What's Missing:

#### ❌ **WhatsApp Message Delivery:**
```python
# SHOULD exist in flow_executor.py but doesn't:

async def _send_gap_profile_summary(self, parent: Parent, gap_profile: GapProfile):
    """Send dignity-first gap summary to parent."""

    # Generate message using DIAG-003
    summary = await self.ai_client.generate(
        prompt="DIAG-003",
        context={
            "child_name": gap_profile.student.first_name,
            "mastered_nodes": gap_profile.mastered_nodes,
            "root_gaps": gap_profile.root_gaps,
            "cascade_path": gap_profile.cascade_paths[0]
        }
    )

    # Validate with GUARD-001
    validated = await self.ai_client.validate(
        prompt="GUARD-001",
        message=summary
    )

    # Send via WhatsApp
    await self.whatsapp_client.send_text(parent.phone, validated)

    # Trigger activity delivery
    await self._trigger_activity_delivery(parent, gap_profile)

# THIS DOES NOT EXIST ❌
```

### Evidence:
- **API Endpoint:** `GET /v1/diagnostics/sessions/{id}/results` ✅
- **Database Table:** `gap_profiles` ✅
- **DIAG-003 Prompt:** Specified in prompt library ✅
- **WhatsApp Delivery:** NOT IMPLEMENTED ❌

### Time to Complete: **2 days**
1. Add gap profile message generation (4 hours)
2. Add GUARD-001 validation (2 hours)
3. Add WhatsApp delivery (2 hours)
4. Test end-to-end (1 day)

---

## FLOW 4: Activity Generation ⚠️ **60% WORKING**

### Designed User Journey:
```
[After gap profile sent]

1 day later, system sends:

Good morning, [Parent]! ☀️

Here's today's 3-minute activity for Kwame:

🎯 STICK BUNDLING GAME

What you need:
- 30 sticks (or straws, pencils, chopsticks)
- String or rubber bands (2)

How to play:
1. Count out 10 sticks together
2. Tie them in a bundle — this is "1 ten"
3. Make another bundle of 10 sticks
4. Ask: "How many sticks in 2 bundles?" (20!)
5. Add 7 loose sticks
6. Ask: "How many total?" (27 = 2 bundles + 7 loose)

If Kwame gets it easily:
Try 3 bundles + 4 loose (34)

What to watch for:
If Kwame counts all 27 sticks one-by-one instead of saying
"20 and 7 more", they're not seeing the bundles as groups
of 10 yet. That's okay — do this again tomorrow!

I'll check back in 3 days. Have fun! 🌟
```

### What Works:

#### ✅ **ACT-001 Prompt (Activity Generator):**
```json
{
  "id": "ACT-001",
  "name": "Remediation Activity Generator",
  "temperature": 0.5,
  "system_prompt": "Create 3-minute activities using household materials...",
  "constraints": [
    "MAX 3 MINUTES",
    "Only items in ANY Ghanaian home (bottle caps, sticks, stones)",
    "Maximum 5 steps",
    "Game-like, not homework",
    "Progression: 'if easy, try this'"
  ],
  "cultural_sensitivity": [
    "Ghanaian contexts: market shopping, sharing food",
    "Works in urban Accra AND rural Northern Region",
    "Must work in daylight (some homes lack electricity)"
  ]
}
```

#### ✅ **PARENT-001 Prompt (Message Formatter):**
```json
{
  "id": "PARENT-001",
  "name": "Parent Message Formatter",
  "system_prompt": "Format activity for WhatsApp delivery...",
  "output": "Friendly, encouraging, L1-aware message"
}
```

#### ✅ **GUARD-001 Prompt (Wolf/Aurino Validator):**
```json
{
  "id": "GUARD-001",
  "name": "Wolf/Aurino Compliance Validator",
  "temperature": 0.0,
  "system_prompt": "Validate message for deficit language...",
  "rejects": ["behind", "struggling", "failing", "weak", "slow", "catching up"]
}
```

#### ⚠️ **Can Generate Activities via API:**
```python
# Can call directly (not from WhatsApp):

activity = await ai_client.generate(
    prompt="ACT-001",
    context={
        "child_name": "Kwame",
        "node_code": "B2.1.1.1",
        "misconception": "Sees 47 as concatenated digits",
        "materials": "household items only"
    }
)

# Returns valid activity JSON ✅
```

### What's Missing:

#### ❌ **FLOW-ACTIVITY-DELIVERY:**
```python
# flow_executor.py SHOULD have:

async def _trigger_activity_delivery(self, parent: Parent, gap_profile: GapProfile):
    """Schedule activity delivery for 1 day after gap profile."""

    # Get root gap
    root_gap = gap_profile.root_gaps[0]  # e.g., "B2.1.1.1"

    # Generate activity
    activity = await self.ai_client.generate(
        prompt="ACT-001",
        context={
            "child_name": parent.students[0].first_name,
            "node_code": root_gap,
            "misconception": gap_profile.misconceptions[root_gap],
            "previous_activities": parent.completed_activities
        }
    )

    # Format for parent
    message = await self.ai_client.format(
        prompt="PARENT-001",
        activity=activity,
        parent_name=parent.preferred_name,
        language=parent.preferred_language
    )

    # Validate compliance
    validated = await self.ai_client.validate(
        prompt="GUARD-001",
        message=message
    )

    # Schedule for tomorrow (not instant)
    await self.scheduler.schedule_message(
        recipient=parent.phone,
        message=validated,
        send_at=datetime.now(UTC) + timedelta(days=1)
    )

    # Update conversation state
    parent.conversation_state = {
        "flow": "FLOW-ACTIVITY",
        "step": "AWAITING_COMPLETION",
        "data": {
            "activity_id": activity.id,
            "gap_profile_id": gap_profile.id,
            "check_in_date": (datetime.now(UTC) + timedelta(days=4)).isoformat()
        }
    }

# NONE OF THIS EXISTS ❌
```

#### ❌ **Message Scheduler:**
```python
# No scheduler exists for delayed message delivery
# All current messages are instant-reply only

# Would need:
# - Celery/RQ for task queue
# - Redis for job storage
# - Background worker process
```

### Evidence:
- **ACT-001 Prompt:** Specified ✅
- **PARENT-001 Prompt:** Specified ✅
- **GUARD-001 Prompt:** Specified ✅
- **Activity API Endpoint:** NOT IMPLEMENTED ❌
- **WhatsApp Delivery:** NOT IMPLEMENTED ❌
- **Message Scheduler:** NOT IMPLEMENTED ❌

### Time to Complete: **4-6 days**
1. Add activity generation endpoint (1 day)
2. Implement message scheduler (Celery/Redis) (2 days)
3. Add FLOW-ACTIVITY-DELIVERY to flow_executor (1 day)
4. Add scheduled message delivery (1 day)
5. Test end-to-end (1 day)

---

## FLOW 5: Check-In Cycle ❌ **0% WORKING**

### Designed User Journey:
```
[3 days after activity sent]

System sends:

Hi [Parent]! 😊

How did the Stick Bundling Game go with Kwame?

[We did it! ✅] [Not yet] [Need help]

--- IF "We did it!" ---
That's wonderful! 🎉

Kwame is building great skills. I'll send another
fun activity soon!

→ Mark activity complete
→ Increment completion counter
→ If 3 activities complete → Trigger new diagnostic

--- IF "Not yet" ---
No problem at all! Life gets busy.

Would you like me to send it again?

[Yes, send again] [Maybe next week]

--- IF "Need help" ---
Of course! What part do you need help with?

→ Parent sends text/voice
→ AI provides clarification
```

### What's Missing (Everything):

#### ❌ **No Scheduled Check-Ins:**
```python
# Would need in flow_executor.py:

async def _schedule_check_in(self, parent: Parent, activity_id: str):
    """Schedule check-in message 3 days after activity."""

    check_in_date = datetime.now(UTC) + timedelta(days=3)

    await self.scheduler.schedule_message(
        recipient=parent.phone,
        message=f"Hi {parent.preferred_name}! How did the activity go?",
        send_at=check_in_date,
        buttons=[
            {"id": "done", "title": "We did it! ✅"},
            {"id": "not_yet", "title": "Not yet"},
            {"id": "help", "title": "Need help"}
        ]
    )

# DOES NOT EXIST ❌
```

#### ❌ **No Completion Tracking:**
```python
# Database table needed:

class ActivityCompletion(Base):
    id: UUID
    student_id: UUID
    activity_id: UUID
    gap_profile_id: UUID
    completed_at: DateTime
    parent_feedback: String  # "done", "not_yet", "help"
    completion_count: Integer  # For triggering next diagnostic

# TABLE DOES NOT EXIST ❌
```

#### ❌ **No Cycle Logic:**
```python
# Would need:

async def _handle_activity_completion(self, parent: Parent):
    """Handle parent completing activity."""

    # Get completion count
    count = await self.db.count_completions(parent.id)

    # If 3 completions → trigger new diagnostic
    if count % 3 == 0:
        await self._start_diagnostic(parent, parent.students[0])
    else:
        # Send next activity
        await self._trigger_activity_delivery(parent, gap_profile)

# DOES NOT EXIST ❌
```

### Evidence:
- **Check-in Logic:** NOT FOUND ❌
- **Activity Completion Table:** DOES NOT EXIST ❌
- **Scheduler:** NOT IMPLEMENTED ❌
- **Cycle Trigger:** NOT IMPLEMENTED ❌

### Time to Complete: **3-5 days**
1. Create ActivityCompletion table (4 hours)
2. Add completion tracking (1 day)
3. Add check-in scheduling (1 day)
4. Add cycle logic (3 completions → new diagnostic) (1 day)
5. Test full cycle (1 day)

---

## FLOW 6: Opt-Out ✅ **100% WORKING**

### User Journey:
```
[Anytime]

Parent sends: "STOP"
(or "gyae" in Twi, "tɔtɔ" in Ewe, "dakpa" in Ga, etc.)

System responds instantly:

We've stopped all messages. 🙏

Your data will be removed from our system.

If you ever want to restart, just send "Hi".

Thank you, [Parent Name].
```

### What Works:

#### ✅ **11+ Opt-Out Keywords in 5 Languages:**
```python
# flow_executor.py, lines 175-210

OPT_OUT_KEYWORDS = [
    # English
    "stop", "unsubscribe", "cancel", "opt out", "opt-out",
    # Twi
    "gyae", "fa me fi",
    # Ewe
    "tɔtɔ", "ðe nye ŋkɔ ɖa",
    # Ga
    "dakpa", "yigbe",
    # Dagbani
    "dakli", "ti n-yua"
]

if message_text.lower() in OPT_OUT_KEYWORDS:
    await self._handle_opt_out(parent)
```

#### ✅ **Database Updates:**
```python
parent.opted_out = True
parent.opted_out_at = datetime.now(UTC)
parent.opted_in = False
parent.conversation_state = None
await self.db.commit()
```

#### ✅ **Compliance:**
- Response sent within 1 second ✅
- Data deletion process begins (currently just flag, full deletion would be manual) ⚠️
- Re-opt-in possible (send "Hi" again) ✅

### Evidence:
- **File:** `src/gapsense/engagement/flow_executor.py` (lines 175-225)
- **Tests:** 2/2 opt-out tests passing
- **Keywords:** 11 tested ✅
- **Database:** opted_out field working ✅

### What Could Be Improved:
- ⚠️ **Automated data deletion:** Currently just sets flag, doesn't actually delete records
- ⚠️ **More L1 keywords:** Could add more dialect variations

### Time to Improve: **1 day** (automated deletion)

---

## FLOW 7: Teacher Dashboard ❌ **0% WORKING**

### Designed User Journey:
```
Teacher logs into: app.gapsense.com/teachers

Dashboard shows:

┌────────────────────────────────────────────────┐
│  Mrs. Ama Mensah - Class B4 (35 students)     │
│  St. Mary's Primary School, Accra              │
└────────────────────────────────────────────────┘

ONBOARDING STATUS:
✅ 28/35 parents onboarded (80%)
⏳ 7 parents not yet reached

GAP PATTERNS:
🔴 Place Value (B2.1.1.1): 15 students
🟡 Fraction Concept (B2.1.3.1): 8 students
🟢 Addition/Subtraction: 5 students ready for B5

RECENT ACTIVITY:
- 22 students completed activities this week
- 12 parents need re-engagement
- 3 students ready for new diagnostic

┌────────────────────────────────────────────────┐
│  💬 Ask GapSense (TEACHER-003)                 │
│                                                │
│  "I'm teaching fractions next week.            │
│   Which students should I watch?"              │
│                                                │
│  [Ask Question]                                │
└────────────────────────────────────────────────┘

STUDENT LIST:
┌──────────────────────────────────────────────┐
│ Kwame Mensah    B4    ⏸️ Fraction Concept    │
│ Akosua Boateng  B4    ✅ Ready for B5        │
│ Kofi Asante     B4    🔴 Place Value Gap     │
│ ...                                          │
└──────────────────────────────────────────────┘
```

### What's Missing (Everything):

#### ❌ **No Web Application:**
```
No frontend exists at all:
- No React/Vue/Next.js app
- No teacher login
- No dashboard UI
- No student list views
- No TEACHER-003 chat interface
```

#### ❌ **But Backend APIs Exist:**
```bash
# These work via API but no UI calls them:

GET /v1/teachers/{teacher_id}/students
→ Returns list of students

GET /v1/diagnostics/students/{student_id}/profile/current
→ Returns current gap profile

GET /v1/students/{student_id}
→ Returns student details
```

#### ❌ **TEACHER-003 Not Integrated:**
```python
# TEACHER-003 prompt exists but no endpoint to call it

# Would need:
POST /v1/teachers/{teacher_id}/chat
{
  "question": "I'm teaching fractions next week. Which students should I watch?"
}
→ Uses TEACHER-003 to generate answer
```

### Evidence:
- **Backend APIs:** 5 teacher-related endpoints ✅
- **TEACHER-003 Prompt:** Specified ✅
- **Frontend Application:** DOES NOT EXIST ❌
- **Teacher Login:** DOES NOT EXIST ❌
- **Dashboard UI:** DOES NOT EXIST ❌

### Time to Complete: **10-15 days**
1. Set up Next.js frontend (2 days)
2. Add teacher authentication (2 days)
3. Build dashboard UI (3 days)
4. Build student list view (2 days)
5. Integrate TEACHER-003 chat (2 days)
6. Build class overview analytics (2 days)
7. Test and deploy (2 days)

---

# 📈 COMPLETION STATUS SUMMARY

## By User Type:

### PARENT Experience:
```
✅ Can onboard                          100%
✅ Can opt-out anytime                  100%
❌ Cannot receive diagnostic             0%
❌ Cannot receive activities             0%
❌ Cannot complete check-ins             0%
❌ Messages not in L1                    0%

OVERALL PARENT EXPERIENCE: 33%
```

### STUDENT Experience:
```
✅ Record created in database          100%
❌ Never receives diagnostic             0%
❌ Never does activities                 0%
❌ No progress tracking                  0%

OVERALL STUDENT EXPERIENCE: 25%
```

### TEACHER Experience:
```
✅ Can register students via API        100%
⚠️ Can view gap profiles via API        70% (API yes, UI no)
❌ Cannot see dashboard                  0%
❌ Cannot ask TEACHER-003 questions      0%

OVERALL TEACHER EXPERIENCE: 15%
```

## By Flow:
```
✅ FLOW 1: Onboarding              100% ████████████████████
✅ FLOW 6: Opt-Out                 100% ████████████████████
⚠️ FLOW 2: Diagnostic               70% ██████████████░░░░░░
⚠️ FLOW 3: Gap Profile              80% ████████████████░░░░
⚠️ FLOW 4: Activity Generation      60% ████████████░░░░░░░░
❌ FLOW 5: Check-In Cycle            0% ░░░░░░░░░░░░░░░░░░░░
❌ FLOW 7: Teacher Dashboard         0% ░░░░░░░░░░░░░░░░░░░░

OVERALL MVP COMPLETION: 35%
```

---

# 🎯 PRIORITY IMPLEMENTATION ORDER

## PHASE 1: Core User Journey (7-10 days)

**Goal:** Parent can complete one full cycle: Onboard → Diagnose → Activity → Check-in

### Priority 1: Diagnostic WhatsApp Integration (3-5 days)
**Why First:** Blocks everything else. Without diagnostic, no gap profiles, no activities.

**Tasks:**
1. ✅ Add FLOW-DIAGNOSTIC to flow_executor.py
2. ✅ Trigger diagnostic after onboarding
3. ✅ Handle answer submissions via WhatsApp
4. ✅ Generate gap profile after diagnostic
5. ✅ Send gap profile message to parent

**Acceptance Criteria:**
- Parent completes onboarding → automatically gets diagnostic within 2 minutes
- Parent answers 6-12 questions via WhatsApp
- Parent receives dignity-first gap summary

**Estimated Hours:** 24-32 hours

---

### Priority 2: Activity Delivery (4-6 days)
**Why Second:** Demonstrates value to parents. This is what they signed up for.

**Tasks:**
1. ✅ Implement message scheduler (Celery + Redis)
2. ✅ Add FLOW-ACTIVITY-DELIVERY
3. ✅ Generate activity using ACT-001
4. ✅ Validate with GUARD-001
5. ✅ Schedule delivery for 1 day after gap profile

**Acceptance Criteria:**
- 24 hours after diagnostic, parent receives activity via WhatsApp
- Activity uses household materials
- Activity targets the root gap (not symptom)
- Message is Wolf/Aurino compliant

**Estimated Hours:** 32-40 hours

---

### Priority 3: Check-In Cycle (3-5 days)
**Why Third:** Completes the loop. Without this, one-time interaction only.

**Tasks:**
1. ✅ Create ActivityCompletion table
2. ✅ Schedule check-in 3 days after activity
3. ✅ Handle completion responses
4. ✅ Trigger new diagnostic after 3 completions
5. ✅ Handle "not yet" and "need help" responses

**Acceptance Criteria:**
- 3 days after activity, parent gets check-in message
- If parent says "done", activity marked complete
- After 3 completions, new diagnostic automatically triggered
- Cycle repeats indefinitely

**Estimated Hours:** 24-32 hours

---

## PHASE 2: Teacher Experience (10-15 days)

**Goal:** Teacher can view class progress and ask questions

### Priority 4: Teacher Dashboard MVP (10-15 days)
**Why Fourth:** Teacher needs to see impact. Also needed for UNICEF demo.

**Tasks:**
1. ✅ Set up Next.js frontend
2. ✅ Add teacher authentication
3. ✅ Build class overview dashboard
4. ✅ Build student list view
5. ✅ Show gap profiles per student
6. ✅ Show onboarding status (X/Y parents onboarded)

**Acceptance Criteria:**
- Teacher can log in
- Teacher sees list of students
- Teacher can click student → see current gap profile
- Teacher sees how many parents are onboarded

**Estimated Hours:** 60-80 hours

---

### Priority 5: TEACHER-003 Chat Interface (2-3 days)
**Why Fifth:** Differentiator for UNICEF pitch. "Reports ≠ conversations."

**Tasks:**
1. ✅ Add POST /v1/teachers/{id}/chat endpoint
2. ✅ Integrate TEACHER-003 prompt
3. ✅ Build chat UI component
4. ✅ Maintain conversation history
5. ✅ Handle follow-up questions

**Acceptance Criteria:**
- Teacher can type: "I'm teaching fractions next week. Which students need help?"
- AI responds with specific students, gap data, and recommendations
- Teacher can ask follow-up questions

**Estimated Hours:** 16-24 hours

---

## PHASE 3: Polish & L1 Support (5-7 days)

### Priority 6: L1 Message Translation (5-7 days)
**Why Sixth:** Critical for equity, but doesn't block core functionality.

**Tasks:**
1. ✅ Add message_templates table
2. ✅ Create translations for 5 languages (Twi, Ewe, Ga, Dagbani, English)
3. ✅ Add template selection logic based on parent.preferred_language
4. ✅ Translate all system messages
5. ✅ Test with native speakers

**Acceptance Criteria:**
- Parent who selected "Twi" receives all messages in Twi
- Translations are culturally appropriate
- Activities use local examples (kenkey, not pizza)

**Estimated Hours:** 40-56 hours

---

# 📅 REALISTIC TIMELINE TO MVP COMPLETE

```
Starting Point: Feb 16, 2026 (35% complete)
Target: MVP Demo-Ready

Week 1 (Feb 17-23):
  ✅ Priority 1: Diagnostic WhatsApp Integration
  → Demo: Parent completes onboarding → gets diagnostic

Week 2 (Feb 24 - Mar 2):
  ✅ Priority 2: Activity Delivery
  → Demo: Parent receives activity 24h after diagnostic

Week 3 (Mar 3-9):
  ✅ Priority 3: Check-In Cycle
  → Demo: Full cycle works (onboard → diagnose → activity → check-in → repeat)

Week 4-5 (Mar 10-23):
  ✅ Priority 4: Teacher Dashboard MVP
  → Demo: Teacher can view class, see gap patterns

Week 6 (Mar 24-30):
  ✅ Priority 5: TEACHER-003 Chat
  → Demo: Teacher asks questions, gets answers

Week 7-8 (Mar 31 - Apr 13):
  ✅ Priority 6: L1 Translation
  → Demo: Parent in Twi receives Twi messages

READY FOR PILOT: April 15, 2026 (100% MVP complete)
```

---

# 🚨 BLOCKERS & DEPENDENCIES

## Technical Blockers:

### 1. Message Scheduler Required
**Blocker for:** Activity Delivery, Check-In Cycle
**Current Status:** ❌ Not implemented
**Options:**
- Celery + Redis (recommended, 2 days setup)
- APScheduler (simpler, 1 day setup, less robust)
- Cloud Functions (Firebase/AWS Lambda, 1 day setup)

**Decision Needed:** Which scheduler to use?

### 2. WhatsApp Business API Limits
**Blocker for:** Scaling beyond 100 parents
**Current Status:** ⚠️ May hit limits
**Issue:** Template message approval takes 1-3 days from Meta
**Mitigation:** Pre-approve 5-10 template variations now

### 3. L1 Translation Resources
**Blocker for:** L1 message support
**Current Status:** ❌ No translators identified
**Need:** Native speakers of Twi, Ewe, Ga, Dagbani
**Timeline:** 1 week to find translators, 1 week to translate

## Dependencies:

```
FLOW 2 (Diagnostic) → FLOW 3 (Gap Profile) → FLOW 4 (Activity)
            ↓
         FLOW 5 (Check-In) ← loops back to FLOW 2

FLOW 7 (Teacher Dashboard) depends on all other flows existing
```

**Critical Path:** Must complete Flows 2-5 in order. Cannot skip.

---

# ✅ DEFINITION OF "MVP COMPLETE"

## Must Have (Non-Negotiable):

1. ✅ **Parent can onboard via WhatsApp** (DONE ✅)
2. ✅ **Student record created** (DONE ✅)
3. ✅ **Diagnostic runs automatically after onboarding**
4. ✅ **Parent receives dignity-first gap summary**
5. ✅ **Activity delivered 24h after diagnostic**
6. ✅ **Check-in sent 3 days after activity**
7. ✅ **Cycle repeats after 3 completions**
8. ✅ **Teacher can view class dashboard**
9. ✅ **Parent can opt-out anytime** (DONE ✅)

## Nice to Have (Not Blockers):

- ⚠️ L1 translations (can demo in English)
- ⚠️ TEACHER-003 chat (can show prompt spec)
- ⚠️ Voice note support (can add in Phase 1b)
- ⚠️ Exercise book scanner (Phase 1b)

## Demo Scenario (MVP Complete):

```
1. Teacher shares GapSense number with parents
2. Parent (Auntie Ama) sends "Hi" → Onboarding starts
3. Ama provides: Child name (Kwame), Age (7), Grade (B2), Language (English)
4. System creates Student record
5. 2 minutes later: Diagnostic starts automatically
6. Ama answers 6 questions with Kwame
7. System identifies gap: B2.1.1.1 (Place Value)
8. Ama receives: "Kwame is doing great with addition! Next building block: place value"
9. 24 hours later: Ama receives Stick Bundling activity
10. 3 days later: "How did it go?" check-in
11. Ama: "We did it!"
12. System: "Wonderful! Next activity coming soon"
13. After 3 activities: New diagnostic automatically triggered
14. Teacher opens dashboard → Sees: "15 students working on place value, 8 on fractions"
15. Teacher asks AI: "I'm teaching fractions next week. Who needs help?"
16. AI lists 8 students with B2.1.3.1 gaps

DEMO LENGTH: 10 minutes (compressed timeline)
ACTORS: 1 parent, 1 teacher, system
SCREENS: WhatsApp (parent), Dashboard (teacher)
```

---

# 📊 CURRENT vs COMPLETE MVP

## What Works Today (Feb 16):
```
Parent: Hi
System: [Welcome template] → 7-step onboarding → Student created ✅
Parent: STOP
System: Opted out ✅

[FLOW STOPS HERE]
```

## What Should Work (MVP Complete):
```
Parent: Hi
System: [Welcome] → Onboarding → Student created ✅
System: [2 min later] Quick learning check → 6 questions ✅
System: Gap found (B2.1.1.1) → Dignity-first summary ✅
System: [24h later] Activity delivered ✅
System: [3 days later] Check-in: "How did it go?" ✅
Parent: We did it!
System: [After 3 completions] New diagnostic ✅
[CYCLE REPEATS]

Teacher: [Opens dashboard]
System: Shows class gaps, student progress ✅
Teacher: "Who needs help with fractions?"
System: [TEACHER-003] Lists 8 students with recommendations ✅
```

---

**END OF DOCUMENT**

Last Updated: February 16, 2026
Next Update: After Priority 1 (Diagnostic Integration) complete
