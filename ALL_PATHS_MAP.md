# GapSense - Complete Path Map

**Generated:** 2026-02-16
**Purpose:** Comprehensive documentation of all user flows, state transitions, and navigation paths

---

## 1. CONVERSATION FLOWS (WhatsApp State Machines)

### **FLOW-ONBOARD** (Parent Onboarding) ✅ 100% Complete
**Entry:** Parent sends first message OR teacher invites parent
**Exit:** Parent linked to student, onboarded_at set
**File:** `src/gapsense/engagement/flow_executor.py:370-1389`

**State Transitions:**
```
START
  ↓
AWAITING_OPT_IN (Step 1)
  │ ← Send welcome message
  │ → Parent clicks "Yes, let's start!" button
  ↓
AWAITING_STUDENT_SELECTION (Step 2)
  │ ← Show list of unlinked students
  │ → Parent replies with number (e.g., "1")
  ↓
CONFIRM_STUDENT_SELECTION (Step 3 - Phase C)
  │ ← Show "Is this your child?" with confirm/cancel buttons
  │ → Parent clicks "Yes, that's correct"
  ↓
AWAITING_DIAGNOSTIC_CONSENT (Step 4)
  │ ← Ask "Do you consent to diagnostic assessment?"
  │ → Parent clicks "Yes, proceed" OR "No, skip"
  ↓
AWAITING_LANGUAGE (Step 5)
  │ ← Ask "What language would you like me to use?"
  │ → Parent clicks "English" | "Twi" | "Ga"
  ↓
COMPLETE
  ├─ parent.onboarded_at = NOW
  ├─ student.primary_parent_id = parent.id
  ├─ student.home_language = selected_language
  └─ Auto-create DiagnosticSession (if consent given)
```

**Exit Paths:**
- **Success:** Parent linked to student, conversation_state cleared
- **Decline (not_now):** conversation_state cleared, no linkage
- **No students available:** Error message, conversation_state cleared
- **Race condition:** Student already linked, error message

---

### **FLOW-DIAGNOSTIC** (Adaptive Assessment) ✅ 70% Complete
**Entry:** Auto-triggered after onboarding (if consent given) OR parent messages when pending session exists
**Exit:** DiagnosticSession completed, GapProfile generated
**File:** `src/gapsense/engagement/flow_executor.py:1484-1757`

**State Transitions:**
```
START (pending session detected)
  ↓
IN_PROGRESS (session.status = "in_progress")
  │ ← Send first question from AdaptiveDiagnosticEngine
  │ → Set conversation_state["flow"] = "FLOW-DIAGNOSTIC"
  ↓
AWAITING_ANSWER (Step 1) ◄─────┐
  │ ← Display question           │
  │ → Parent sends text answer   │
  ↓                               │
PROCESS_ANSWER                   │
  ├─ Save answer to DB           │
  ├─ Analyze correctness         │
  ├─ Update session tracking     │
  ├─ session.nodes_tested.append()    │
  ├─ session.nodes_gap OR nodes_mastered │
  └─ Commit to DB                │
  ↓                               │
GET_NEXT_NODE                    │
  ├─ AdaptiveDiagnosticEngine.get_next_node() │
  │   ├─ Phase 1: Screening (6 priority nodes) │
  │   ├─ Phase 2: Backward tracing (prerequisites) │
  │   └─ Phase 3: Cross-check (different cascade) │
  │                               │
  ├─ IF next_node exists: ────────┘
  │    Send next question (loop)
  │
  └─ IF no next_node OR max_questions (15):
       ↓
COMPLETE_SESSION
  ├─ session.status = "completed"
  ├─ session.completed_at = NOW
  ├─ Generate GapProfile (AI analysis via DIAG-003)
  ├─ Save gap_profile to DB ✅ FIXED
  ├─ Send completion message with score
  └─ Clear conversation_state
```

**Adaptive Algorithm** (AdaptiveDiagnosticEngine):
```
Phase 1: SCREENING (Questions 1-12)
  - Test 6 priority nodes × 2 questions each
  - Nodes: B2.1.1.1, B1.1.2.2, B2.1.2.2, B2.1.3.1, B3.1.3.1, B4.1.3.1

Phase 2: BACKWARD TRACING
  - IF gap detected → Find deepest gap (highest severity)
  - Trace prerequisites backward (follow graph edges)
  - Test prerequisite nodes until mastery found (anchor)

Phase 3: CROSS-CHECK
  - IF multiple cascades detected → Test nodes from different cascade
  - Confirm root gap consistency

STOP: Max 15 questions OR no more nodes to test
```

**Exit Paths:**
- **Success:** GapProfile saved, completion message sent
- **Abandoned:** (Not yet implemented - would need timeout logic)
- **No curriculum data:** Completion message with 0 questions

---

### **FLOW-OPT-OUT** (Parent Opt-Out) ✅ 100% Complete
**Entry:** Parent sends opt-out keyword (STOP, gyae, tɔtɔ, etc.)
**Exit:** Parent opted out, all messages stopped
**File:** `src/gapsense/engagement/flow_executor.py:218-272`

**State Transitions:**
```
DETECT_OPT_OUT
  ├─ Check message against OPT_OUT_KEYWORDS
  │  - English: stop, unsubscribe, cancel, quit, opt out
  │  - Twi: gyae, gyina
  │  - Ewe: tɔtɔ, tɔe
  │  - Ga: tsia
  │  - Dagbani: nyɛli
  │
  └─ IF keyword detected:
       ↓
IMMEDIATE_OPT_OUT (Wolf/Aurino compliance)
  ├─ parent.opted_out = True
  ├─ parent.opted_out_at = NOW
  ├─ parent.conversation_state = None (clear any active flow)
  ├─ Send confirmation message
  └─ COMPLETE
```

**Features:**
- **Instant:** No confirmation required (Wolf/Aurino dignity principle)
- **Multi-language:** Supports 5 Ghanaian languages
- **Frictionless:** Single keyword stops all messages
- **Reversible:** "Send 'Hi' to restart" in confirmation message

---

### **FLOW-TEACHER-ONBOARD** (Teacher Registration) ✅ 100% Complete
**Entry:** Teacher sends message with invitation code OR teacher starts registration
**Exit:** Teacher linked to school, class roster uploaded
**File:** `src/gapsense/engagement/teacher_flows.py:141-838`

**State Transitions:**
```
START
  ↓
COLLECT_INVITATION_CODE (Step 1)
  │ ← Ask "Enter your school invitation code"
  │ → Teacher replies with code (e.g., "STMARYS-ABC123")
  ↓
VALIDATE_CODE
  ├─ Look up SchoolInvitation by code
  ├─ Check is_active = True
  ├─ Check teachers_joined < max_teachers
  │
  └─ IF valid:
       ↓
COLLECT_NAME (Step 2)
  │ ← Ask "What's your full name?"
  │ → Teacher replies (e.g., "Ms. Adwoa Mensah")
  ↓
COLLECT_GRADE (Step 3)
  │ ← Ask "What grade do you teach?"
  │ → Teacher replies (e.g., "JHS 1")
  ↓
COLLECT_CLASS_NAME (Step 4)
  │ ← Ask "What's your class name?" (optional)
  │ → Teacher replies (e.g., "JHS 1A") OR skips
  ↓
UPLOAD_ROSTER (Step 5)
  │ ← Ask "Upload student roster (CSV or photo)"
  │ → Teacher sends CSV file OR photo
  ↓
PROCESS_ROSTER
  ├─ Parse CSV OR extract text from photo (OCR)
  ├─ Create Student records (unlinked, primary_parent_id = NULL)
  ├─ Link students to teacher
  ├─ teacher.onboarded_at = NOW
  └─ Send confirmation with student count
       ↓
COMPLETE
```

**Exit Paths:**
- **Success:** Teacher onboarded, students created
- **Invalid code:** Error message, restart flow
- **Code expired/full:** Error message, contact school
- **Roster parse error:** Ask to resend in correct format

---

## 2. API ENDPOINTS (REST)

### **Health & Admin**
- `GET /` - Health check
- `GET /health` - Detailed health status
- `GET /docs` - Swagger UI (auto-generated)

### **School Registration** ✅ Complete
- `GET /api/v1/schools/search?q={query}` - Search GES schools (autocomplete)
- `POST /api/v1/schools/register` - Register new school, generate invitation code

### **Teacher Management** ✅ Complete
- `POST /api/v1/teachers/` - Create teacher (internal use)
- `GET /api/v1/teachers/{teacher_id}` - Get teacher details
- `PUT /api/v1/teachers/{teacher_id}` - Update teacher
- `GET /api/v1/teachers/{teacher_id}/students` - Get teacher's student roster

### **Parent Management** ✅ Complete
- `POST /api/v1/parents/` - Create parent (internal use)
- `GET /api/v1/parents/{parent_id}` - Get parent details
- `GET /api/v1/parents/{parent_id}/children` - Get parent's linked students

### **Diagnostic Management** ⚠️ Partial
- `POST /api/v1/diagnostics/sessions` - Start diagnostic session (internal)
- `GET /api/v1/diagnostics/sessions/{session_id}` - Get session details
- `GET /api/v1/diagnostics/gap-profiles/{student_id}` - Get current gap profile

### **WhatsApp Webhook** ✅ Complete
- `GET /api/v1/webhook/whatsapp` - Webhook verification (Meta requirement)
- `POST /api/v1/webhook/whatsapp` - Receive incoming messages

**Message Types Handled:**
- `text` - Regular text messages
- `interactive` - Button/list responses
- `image` - Photo uploads (teacher roster)
- `document` - File uploads (CSV roster)

---

## 3. DATABASE STATE TRANSITIONS

### **Parent Lifecycle**
```
CREATED (phone only)
  ↓
OPTED_IN (parent.opted_in = True, opted_in_at set)
  ↓
ONBOARDED (parent.onboarded_at set, linked to student)
  ↓
ACTIVE (receiving diagnostics, activities)
  ↓
OPTED_OUT (parent.opted_out = True, opted_out_at set)
```

### **Student Lifecycle**
```
CREATED_BY_TEACHER (primary_parent_id = NULL, unlinked)
  ↓
LINKED_TO_PARENT (primary_parent_id = parent.id)
  ↓
DIAGNOSTIC_PENDING (DiagnosticSession.status = "pending")
  ↓
DIAGNOSTIC_IN_PROGRESS (DiagnosticSession.status = "in_progress")
  ↓
DIAGNOSTIC_COMPLETE (DiagnosticSession.status = "completed")
  ↓
GAP_PROFILE_GENERATED (GapProfile created, is_current = True)
  ↓
RECEIVING_ACTIVITIES (ParentActivity records created)
```

### **DiagnosticSession Lifecycle**
```
PENDING (created after onboarding, not yet started)
  ↓
IN_PROGRESS (first question sent, started_at set)
  ↓
COMPLETED (all questions answered, completed_at set)
  │
  OR
  │
ABANDONED (parent stopped responding - not yet implemented)
  │
  OR
  │
TIMED_OUT (session expired - not yet implemented)
```

---

## 4. ERROR RECOVERY PATHS

### **Commands** (Available in any flow)
- `/restart` - Clear conversation state, start fresh
- `/cancel` - Cancel current flow, go back to main menu
- `/help` - Show available commands and current state
- `/status` - Show current flow and step

### **Session Expiry** (Phase D.5)
```
IF last_message_at > 24 hours ago:
  ├─ Clear conversation_state
  ├─ Log expiry event
  └─ Next message starts new flow
```

### **Race Conditions** (Phase E)
- Student already linked → Error message, clear state
- Invitation code consumed → Error message, contact school
- Duplicate message handling → Idempotency via message_id

---

## 5. PLANNED FLOWS (Not Yet Implemented)

### **FLOW-ACTIVITY** (Content Delivery) ❌ 0% Complete
**Purpose:** Deliver personalized learning activities to parents
**Entry:** After GapProfile generated
**Planned States:**
```
ACTIVITY_READY
  ↓
SEND_ACTIVITY (daily, 3-minute tasks)
  ↓
COLLECT_COMPLETION (parent confirms done)
  ↓
TRACK_PROGRESS (ParentActivity.completed_at)
  ↓
SEND_NEXT_ACTIVITY (adaptive based on progress)
```

### **FLOW-CHECK-IN** (Progress Monitoring) ❌ 0% Complete
**Purpose:** Check on parent/student progress, adjust activities
**Entry:** Scheduled (weekly)
**Planned States:**
```
SEND_CHECK_IN_QUESTION
  ↓
COLLECT_RESPONSE (how is child doing?)
  ↓
ANALYZE_SENTIMENT (AI analysis)
  ↓
ADJUST_DIFFICULTY (if needed)
  ↓
SEND_ENCOURAGEMENT
```

### **FLOW-RE-DIAGNOSTIC** (Follow-up Assessment) ❌ 0% Complete
**Purpose:** Re-assess after 4-6 weeks to measure progress
**Entry:** Scheduled or parent-initiated
**Similar to FLOW-DIAGNOSTIC but:**
- Compare to previous GapProfile
- Focus on previously-identified gaps
- Measure improvement velocity

---

## 6. INTEGRATION POINTS

### **External Services**
- **WhatsApp Cloud API** (Meta)
  - Send messages: `https://graph.facebook.com/v18.0/{phone_number_id}/messages`
  - Webhook: Receives incoming messages

- **Anthropic Claude API** (AI Generation)
  - DIAG-001: Question generation
  - DIAG-002: Response analysis
  - DIAG-003: Gap profile analysis

- **xAI Grok API** (Fallback)
  - Same prompts as Claude
  - OpenAI-compatible endpoint

### **Internal Dependencies**
- **Curriculum Graph** (PostgreSQL)
  - 27 nodes, 47 prerequisite edges
  - Loaded from `gapsense-data/curriculum/*.json`

- **Prompt Library** (JSON)
  - Loaded at startup from `gapsense-data/prompts/gapsense_prompt_library.json`
  - In-memory singleton for fast access

---

## 7. NAVIGATION SUMMARY

### **Entry Points:**
1. **Parent sends "Hi"** → FLOW-ONBOARD
2. **Parent sends opt-out keyword** → FLOW-OPT-OUT (immediate)
3. **Teacher sends invitation code** → FLOW-TEACHER-ONBOARD
4. **Parent messages with pending diagnostic** → FLOW-DIAGNOSTIC (auto-start)
5. **Parent sends /help** → Help message
6. **Parent sends /restart** → Clear state, start fresh

### **Decision Tree:**
```
Incoming WhatsApp Message
  │
  ├─ Is opt-out keyword? → FLOW-OPT-OUT
  │
  ├─ Is command (/restart, /help)? → Handle command
  │
  ├─ Has active conversation_state?
  │   ├─ flow = "FLOW-ONBOARD" → Continue onboarding
  │   ├─ flow = "FLOW-DIAGNOSTIC" → Continue diagnostic
  │   └─ flow = "FLOW-TEACHER-ONBOARD" → Continue teacher onboarding
  │
  ├─ No active state BUT has pending diagnostic? → Start FLOW-DIAGNOSTIC
  │
  └─ No active state, not onboarded? → Start FLOW-ONBOARD
```

---

## 8. CRITICAL PATH (MVP Launch)

**Minimum viable flow for launch:**
```
1. School Registration (Web UI or API) ✅
   ↓
2. Teacher Onboarding (WhatsApp) ✅
   ↓
3. Teacher Uploads Roster ✅
   ↓
4. Parent Onboarding (WhatsApp) ✅
   ↓
5. Diagnostic Auto-Trigger ✅
   ↓
6. Adaptive Assessment (15 questions) ✅
   ↓
7. Gap Profile Generation ✅
   ↓
8. Activity Delivery ❌ NOT IMPLEMENTED
   ↓
9. Progress Tracking ❌ NOT IMPLEMENTED
```

**Current Status:** Steps 1-7 functional (70% complete)
**Blocking Launch:** Steps 8-9 required for value delivery

---

## NOTES

- All flows support 24-hour session window (WhatsApp limitation)
- L1-first translations NOT yet implemented (English only)
- Template messages NOT registered with Meta (using text messages)
- Integration tests partially failing (curriculum fixtures needed)

**Last Updated:** 2026-02-16
**Next Review:** After Phase 4 (Activity Delivery) implementation
