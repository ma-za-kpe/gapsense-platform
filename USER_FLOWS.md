# GapSense User Flows & Data Flows

**Complete audit of all user flows, data flows, and E2E test requirements**

Last Updated: 2025-03-15

---

## Table of Contents

1. [Teacher Flows](#teacher-flows)
2. [Parent Flows](#parent-flows)
3. [Background Worker Flows](#background-worker-flows)
4. [Data Flow Patterns](#data-flow-patterns)
5. [System Integration Points](#system-integration-points)
6. [E2E Test Requirements](#e2e-test-requirements)
7. [Known Issues & Gaps](#known-issues--gaps)

---

## Teacher Flows

### 1. FLOW-TEACHER-ONBOARD (Manual Entry)

**Description:** Teacher registers their class roster via WhatsApp

**Entry Point:** Teacher sends "START", "hi", or "hello" to WhatsApp number

**Flow Steps:**
```
1. COLLECT_SCHOOL
   Input: School name OR invitation code (e.g., "St. Mary's JHS" or "STMARYS-ABC123")
   Validation: validate_school_name() or validate_invitation_code()
   DB: Creates School if doesn't exist, or links to existing via invitation
   State: conversation_state.step = "COLLECT_CLASS"

2. COLLECT_CLASS
   Input: Class name (e.g., "JHS 1A", "B4")
   Validation: validate_class_name()
   DB: Sets teacher.class_name, teacher.grade_taught
   State: conversation_state.step = "COLLECT_STUDENT_COUNT"

3. COLLECT_STUDENT_COUNT
   Input: Number (e.g., "42")
   Validation: validate_student_count() (1-200)
   State: conversation_state.step = "COLLECT_STUDENT_LIST"

4. COLLECT_STUDENT_LIST
   Input: Multi-line student names
   Format: "1. Kwame Mensah\n2. Akosua Boateng\n..." or "Name\nName\n..."
   Validation: _parse_student_names() + validate_student_name() per name
   Warnings: Count mismatch, duplicate names
   State: conversation_state.step = "CONFIRM_STUDENT_CREATION"

5. CONFIRM_STUDENT_CREATION
   Input: Button response ("confirm_yes" or "confirm_no")
   Action: If yes, creates Student records with:
     - full_name, first_name, current_grade
     - school_id (from teacher.school_id)
     - teacher_id (teacher.id)
     - primary_parent_id = NULL (awaiting parent linkage)
   DB: Marks teacher.onboarded_at, clears conversation_state
   State: Flow complete
```

**Data Flow:**
```
WhatsApp → webhook → TeacherFlowExecutor.process_teacher_message()
  → _start_teacher_onboarding() or _continue_teacher_onboarding()
    → _collect_school_name() | _collect_class_name() | _collect_student_count() | _collect_student_list() | _confirm_student_creation()
      → DB: School, Teacher, Student records created
      → WhatsApp: Confirmation message sent
```

**Database Changes:**
- `schools`: 1 record (if new school)
- `teachers`: Updates school_id, class_name, grade_taught, onboarded_at, conversation_state
- `students`: N records (one per student)
- `school_invitations`: Updates teachers_joined counter (if invitation code used)

**Error Handling:**
- Session expiry: > 24 hours since last_active_at → clears conversation_state
- Commands: RESTART, CANCEL, HELP, STATUS
- Validation errors: Re-prompts with specific error message

**File:** `src/gapsense/engagement/teacher_flows.py`

---

### 2. FLOW-TEACHER-ONBOARD (Invitation Code)

**Description:** School admin generates invitation code, teacher uses it for instant school linkage

**Entry Point:** Teacher sends invitation code (e.g., "STMARYS-ABC123")

**Flow Steps:**
```
1. COLLECT_SCHOOL (with invitation code)
   Input: "STMARYS-ABC123" (format: 1-8 chars, dash, 6 alphanumeric)
   Validation:
     - Format check: validate_invitation_code()
     - DB lookup: SchoolInvitation.invitation_code
     - Expiry check: expires_at > now
     - Capacity check: teachers_joined < max_teachers
   Action:
     - Links teacher to school instantly
     - Increments invitation.teachers_joined
     - Stores "joined_via_code" in conversation_state.data
   State: Skip to "COLLECT_CLASS" (bypasses manual school entry)

2-5. [Same as manual onboarding]
```

**Data Flow:**
```
WhatsApp → webhook → TeacherFlowExecutor._collect_school_name()
  → Regex match: r"\b([A-Z0-9]{1,8}-[A-Z0-9]{6})\b"
    → DB: Query SchoolInvitation
      → Validate: is_active, expires_at, max_teachers
        → Link: teacher.school_id = invitation.school_id
          → Increment: invitation.teachers_joined += 1
            → DB commit
              → WhatsApp: "✅ Welcome to {school.name}! You've successfully joined using invitation code {code}."
```

**Database Changes:**
- `teachers`: Updates school_id, conversation_state
- `school_invitations`: Increments teachers_joined

**File:** `src/gapsense/engagement/teacher_flows.py:229-366`, `src/gapsense/engagement/invitation_codes.py`

---

### 3. FLOW-EXERCISE-BOOK-SCAN

**Description:** Teacher sends exercise book image for AI analysis

**Entry Point:** Teacher (onboarded) sends image message via WhatsApp

**Flow Steps:**
```
1. Image Message Received
   Webhook: POST /v1/webhooks/whatsapp
   Adapter: Normalizes Twilio/Meta format
   Handler: _handle_teacher_image()

2. Media Download
   Provider: TwilioWhatsAppProvider.download_media() or MetaWhatsAppProvider.download_media()
   Input: media_id (Meta) or media_url (Twilio)
   ⚠️ BUG: Twilio uses image_content.get("id") which returns message_sid, should use image_content.get("url")
   Output: image_bytes

3. Database Lookup
   Query: Most recent student for teacher
   SQL: SELECT * FROM students WHERE teacher_id = ? ORDER BY created_at DESC LIMIT 1

4. Service Instantiation
   ⚠️ CRITICAL BUG: All services instantiated without required constructor args
   - ExerciseBookScanner(db, media_service, worker_service, guard_service, ai_client, prompt_service)
   - MediaService() ❌ Missing settings
   - WorkerService() ❌ Missing ai_client, media_service, guard_service, prompt_service, settings, db
   - GuardService() ❌ Missing ai_client, prompt_service
   - AsyncAIClient() ❌ Missing anthropic_api_key
   - PromptService() ❌ Missing settings

5. Image Processing (if constructors fixed)
   ExerciseBookScanner.handle_image_message()
     → MediaService.upload() → S3
     → WorkerService.enqueue() → SQS task "image_analyze"
     → WhatsApp: "📸 Analyzing the exercise book page. I'll send you the results shortly."

6. Background Processing
   WorkerService polls SQS → _handle_image_analyze()
     → MediaService.download(s3_key) → image_bytes
     → PromptService.render_prompt("ANALYSIS-001")
     → AsyncAIClient.generate() with ANALYSIS-001 + image
     → AI returns: {gap_node_ids, errors, patterns, focus_areas, unreadable}
     → ⚠️ CRITICAL BUG: Flow stops here - just logs result
     → ❌ MISSING: ExerciseBookScanner.process_analysis_result() never called

7. Result Processing (MISSING - should happen)
   ExerciseBookScanner.process_analysis_result()
     → Check if image unreadable → send "too blurry" message
     → Create/update GapProfile with detected gaps
     → Build teacher summary message
     → GuardService.check() → validate summary
     → WhatsApp: Send summary to teacher
```

**Data Flow (Current - BROKEN):**
```
WhatsApp Image
  → Webhook /v1/webhooks/whatsapp
    → TwilioWebhookAdapter (if Twilio) or direct Meta format
      → whatsapp.py:_handle_teacher_image()
        ⚠️ TypeError: Services instantiated without args
          ❌ Flow crashes here
```

**Data Flow (After Fix):**
```
WhatsApp Image
  → Webhook → Download image → ExerciseBookScanner.handle_image_message()
    → MediaService.upload() → S3: {country}/{student_id}/images/{filename}
    → WorkerService.enqueue() → SQS: {"task_type": "image_analyze", "payload": {...}}
    → WhatsApp: "📸 Analyzing..."

SQS Queue
  → WorkerService._handle_image_analyze()
    → MediaService.download(s3_key) → image_bytes
    → AI with ANALYSIS-001 → {gap_node_ids, errors, patterns}
    ⚠️ Currently stops here

[MISSING] After AI Analysis
  → ExerciseBookScanner.process_analysis_result()
    → DB: Create/update GapProfile
      - student_id, source="exercise_book", gap_nodes=[UUID, ...]
    → GuardService.check(summary) → validate
    → WhatsApp: "📊 Exercise Book Analysis Complete\nFound 5 error(s):\n  • ..."
```

**Database Changes (After Fix):**
- `gap_profiles`: Creates or updates with source="exercise_book", gap_nodes=[...]
- No changes currently due to bugs

**Files:**
- Entry: `src/gapsense/webhooks/whatsapp.py:_handle_teacher_image` (lines 300-350)
- Scanner: `src/gapsense/engagement/exercise_book_scanner.py`
- Worker: `src/gapsense/services/worker_service.py:_handle_image_analyze` (lines 217-250)

**Known Issues:**
1. Constructor signature mismatches (BUGFIX_REQUIREMENTS.md #1.1-1.5)
2. Twilio media ID extraction (BUGFIX_REQUIREMENTS.md #1.7)
3. Missing completion callback (BUGFIX_REQUIREMENTS.md #1.9)
4. Missing database session in worker (BUGFIX_REQUIREMENTS.md #1.10)

---

### 4. FLOW-TEACHER-CONVERSATION

**Description:** AI-powered pedagogical conversation for teachers

**Entry Point:** Onboarded teacher sends text message (not in active flow, not a command)

**Flow Steps:**
```
1. Message Routing
   Webhook → TeacherFlowExecutor.process_teacher_message()
   Check: teacher.onboarded_at is not NULL
   Check: No active flow (conversation_state is None or flow != "FLOW-TEACHER-ONBOARD")
   Route: TeacherConversationPartner.handle_teacher_message()

2. Conversation History
   Get or create ConversationHistory for teacher_id
   Add user turn: {"role": "user", "content": message}
   Max 20 turns (40 messages) stored in memory

3. Class Gap Context Aggregation
   Query: All GapProfiles for teacher's students
   SQL: SELECT gap_profiles.* FROM gap_profiles
        JOIN students ON gap_profiles.student_id = students.id
        WHERE students.teacher_id = ? AND gap_profiles.is_current = TRUE
   Aggregate: Count gap_nodes across all students
   Format: "Class: N students with gap profiles\n  Gap {uuid}: 15/30 (50%)\n..."

4. AI Analysis (TEACHER-001)
   Prompt: TEACHER-001 + class_gap_data
   Input: Full conversation history (multi-turn)
   Model: Configured in prompt library
   Output: Analysis of teacher's question/need

5. AI Response Generation (TEACHER-002)
   Prompt: TEACHER-002
   Input: "Analysis: {step 4 output}\n\nTeacher question: {message}"
   Output: Pedagogical response with guidance

6. WhatsApp Formatting (TEACHER-003)
   Prompt: TEACHER-003
   Input: Response from step 5
   Output: WhatsApp-friendly formatted text (emoji, line breaks, etc.)

7. Delivery
   WhatsApp: Send formatted response to teacher.phone
   History: Add assistant turn: {"role": "assistant", "content": response}
```

**Data Flow:**
```
WhatsApp Text
  → Webhook → TeacherFlowExecutor
    → Check: onboarded, no active flow
      → TeacherConversationPartner.handle_teacher_message()
        → _get_class_gap_context() → DB: Query GapProfiles
        → AI: TEACHER-001 (analysis)
        → AI: TEACHER-002 (response)
        → AI: TEACHER-003 (format)
        → WhatsApp: Send response
```

**Database Reads:**
- `gap_profiles` JOIN `students`: Aggregate gap data for class

**Database Writes:**
- None (conversation history stored in memory only)

**File:** `src/gapsense/engagement/teacher_conversation.py`

---

## Parent Flows

### 5. FLOW-ONBOARD (Parent Onboarding)

**Description:** Parent links to their child's student record and completes onboarding

**Entry Point:** Parent sends first message to WhatsApp number

**Flow Steps:**
```
1. AWAITING_OPT_IN
   Message: "Welcome to GapSense! 📚\n\nAre you ready to begin? Reply YES to continue."
   Input: Button response or text "yes"
   Action:
     - parent.opted_in = True
     - parent.opted_in_at = now
   State: conversation_state.step = "AWAITING_STUDENT_SELECTION"

2. AWAITING_STUDENT_SELECTION
   Query: Unlinked students (primary_parent_id IS NULL, is_active = TRUE)
   Limit: 100 students (shows first 50 in message)
   Message: "Great! 🎉 Which child is yours?\n\n1. Kwame Mensah (Grade JHS1, Accra Academy JHS)\n..."
   State: Stores student_ids_map {"1": "uuid", "2": "uuid", ...} in conversation_state.data
   Input: Number (e.g., "1", "5")
   Validation: Number must be in student_ids_map
   State: conversation_state.step = "CONFIRM_STUDENT_SELECTION"

3. CONFIRM_STUDENT_SELECTION
   Message: "You selected: {student.full_name}\nGrade: {grade}\n\nIs this your child?"
   Buttons: "Yes, that's correct" | "No, go back"
   Input: Button response
   Action (if "confirm_no"): Return to AWAITING_STUDENT_SELECTION with fresh list
   Action (if "confirm_yes"): Save selected_student_id in conversation_state.data
   State: conversation_state.step = "AWAITING_DIAGNOSTIC_CONSENT"

4. AWAITING_DIAGNOSTIC_CONSENT
   Message: "To help {name} learn, we'll send a quick diagnostic quiz...\n\nDo you consent?"
   Buttons: "Yes, proceed" | "No, skip for now"
   Input: Button response
   Action:
     - parent.diagnostic_consent = True/False
     - parent.diagnostic_consent_at = now
   State: conversation_state.step = "AWAITING_LANGUAGE"

5. AWAITING_LANGUAGE
   Message: "One last question: What language would you like me to use?"
   Buttons: "English" | "Twi (Akan)" | "Ga"
   Input: Button response (lang_en, lang_tw, lang_ga, etc.)
   Action:
     - parent.preferred_language = language_code
     - student.primary_parent_id = parent.id (LINK PARENT TO STUDENT)
     - student.home_language = language_code
     - parent.onboarded_at = now
     - parent.conversation_state = None (clear state)
   Trigger: _create_diagnostic_session_if_consented() → creates DiagnosticSession if parent consented
   State: Flow complete
```

**Data Flow:**
```
WhatsApp "START"
  → Webhook → Parent.lookup_or_create(phone)
    → FlowExecutor.process_message()
      → Check: parent.opted_in == False
        → _start_onboarding()
          → WhatsApp: Welcome + opt-in buttons

WhatsApp Button "yes_start"
  → _onboard_opt_in()
    → parent.opted_in = True
    → _show_student_selection_list()
      → DB: Query unlinked students
      → WhatsApp: Numbered list

WhatsApp "1"
  → _onboard_select_student()
    → Validate number in student_ids_map
    → WhatsApp: Confirmation buttons

WhatsApp Button "confirm_yes"
  → _onboard_confirm_student_selection()
    → WhatsApp: Diagnostic consent buttons

WhatsApp Button "consent_yes"
  → _onboard_collect_consent()
    → parent.diagnostic_consent = True
    → WhatsApp: Language selection buttons

WhatsApp Button "lang_en"
  → _onboard_collect_language()
    → student.primary_parent_id = parent.id (CRITICAL LINK)
    → parent.onboarded_at = now
    → _create_diagnostic_session_if_consented()
      → DB: Create DiagnosticSession(status="pending")
    → WhatsApp: "All set! 🌟"
```

**Database Changes:**
- `parents`: Updates opted_in, opted_in_at, diagnostic_consent, diagnostic_consent_at, preferred_language, onboarded_at, conversation_state
- `students`: Updates primary_parent_id (CRITICAL LINKAGE), home_language
- `diagnostic_sessions`: Creates 1 record if parent consented (status="pending")

**File:** `src/gapsense/engagement/flow_executor.py:370-1390`

---

### 6. FLOW-DIAGNOSTIC (Adaptive Diagnostic Assessment)

**Description:** Parent answers adaptive diagnostic questions to identify student's learning gaps

**Entry Point:** Parent completes onboarding with diagnostic consent, or pending DiagnosticSession exists

**Flow Steps:**
```
1. Session Start
   Trigger: FlowExecutor checks for pending DiagnosticSession
   Query: SELECT * FROM diagnostic_sessions WHERE student_id = ? AND status = 'pending'
   Action:
     - session.status = "in_progress"
     - session.started_at = now
     - parent.conversation_state = {flow: "FLOW-DIAGNOSTIC", step: "AWAITING_ANSWER", data: {session_id: ...}}

2. Question Generation Loop (AWAITING_ANSWER)
   Engine: AdaptiveDiagnosticEngine.get_next_node()
     - Uses prerequisite graph to select next node
     - Considers previous answers (session.tested_nodes, session.correct_nodes)
   Generator: QuestionGenerator.generate_question(node, question_number)
     - Uses AI or falls back to templates
     - Returns: {question_text, question_type, expected_answer, question_media_url}
   DB: Create DiagnosticQuestion record
   State: Store current_question_id, current_node_code in conversation_state.data
   WhatsApp: "Question {N} for {student.first_name}:\n\n{question_text}"

3. Answer Collection (AWAITING_ANSWER)
   Input: Text response from parent
   Validate: QuestionGenerator.check_answer(expected_answer, student_response)
   DB: Update DiagnosticQuestion:
     - student_response = answer_text
     - answered_at = now
     - is_correct = True/False
   Update Session Stats:
     - session.total_questions += 1
     - session.correct_answers += 1 (if correct)
   Adaptive Update: AdaptiveDiagnosticEngine.update_session_state(node_id, is_correct)
     - Updates session.tested_nodes, session.correct_nodes arrays

4. Loop or Complete
   Check: AdaptiveDiagnosticEngine.get_next_node()
   If next_node exists: Go to step 2 (send next question)
   If next_node is None: Go to step 5 (complete session)

5. Session Completion
   Action:
     - session.status = "completed"
     - session.completed_at = now
     - parent.conversation_state = None (clear state)
   Analysis: GapProfileAnalyzer.generate_gap_profile()
     - Analyzes all answers
     - Identifies gap_nodes (prerequisites for incorrect answers)
     - Identifies mastered_nodes (correct answers + prerequisites)
   DB: Create GapProfile record:
     - student_id, session_id, source="diagnostic"
     - gap_nodes=[UUID, ...], mastered_nodes=[UUID, ...]
     - is_current=True (previous profiles set to False)
   Trigger: ParentActivityDelivery.deliver_activity()
     - Generates first personalized activity
   WhatsApp: "Diagnostic complete for {name}! 🎉\nQuestions answered: {N}\nCorrect: {N} ({%})\n..."
```

**Data Flow:**
```
No Active Flow + Pending Session
  → FlowExecutor.process_message()
    → _get_pending_diagnostic_session() → DiagnosticSession found
      → _diagnostic_start_session()
        → session.status = "in_progress"
        → _diagnostic_send_question()
          → AdaptiveDiagnosticEngine.get_next_node()
          → QuestionGenerator.generate_question()
          → DB: Create DiagnosticQuestion
          → WhatsApp: Question

WhatsApp Answer
  → FlowExecutor._continue_diagnostic()
    → _diagnostic_collect_answer()
      → QuestionGenerator.check_answer() → is_correct
      → DB: Update DiagnosticQuestion.is_correct, student_response
      → session.total_questions += 1
      → AdaptiveDiagnosticEngine.update_session_state()
      → _diagnostic_send_question() (loop) OR _diagnostic_complete_session()

Session Complete
  → _diagnostic_complete_session()
    → session.status = "completed"
    → GapProfileAnalyzer.generate_gap_profile()
      → DB: Create GapProfile
    → ParentActivityDelivery.deliver_activity()
      → AI: Generate activity
      → Guard: Validate
      → SQS: Enqueue TTS
      → WhatsApp: Send text activity
    → WhatsApp: "Diagnostic complete! 🎉"
```

**Database Changes:**
- `diagnostic_sessions`: Updates status, started_at, completed_at, total_questions, correct_answers, tested_nodes, correct_nodes
- `diagnostic_questions`: Creates N records (one per question)
- `gap_profiles`: Creates 1 record (marks previous as is_current=False)
- `parent_interactions`: May create records (depending on implementation)

**Files:**
- Flow: `src/gapsense/engagement/flow_executor.py:1484-1798`
- Engine: `src/gapsense/diagnostic/adaptive_engine.py`
- Generator: `src/gapsense/diagnostic/question_generator.py`
- Analyzer: `src/gapsense/diagnostic/gap_profile_analyzer.py`

---

### 7. FLOW-OPT-OUT (Parent Opt-Out)

**Description:** Parent opts out of all communications (Wolf/Aurino compliance)

**Entry Point:** Parent sends opt-out keyword

**Keywords:**
```
English: "stop", "unsubscribe", "cancel", "quit", "opt out", "optout"
Twi: "gyae", "gyina"
Ewe: "tɔtɔ", "tɔe"
Ga: "tsia"
Dagbani: "nyɛli"
```

**Flow Steps:**
```
1. Keyword Detection
   Check: message.lower() in OPT_OUT_KEYWORDS
   Priority: Takes precedence over all other flows

2. Opt-Out Action
   DB:
     - parent.opted_out = True
     - parent.opted_out_at = now
     - parent.conversation_state = None (clear any active flow)

3. Confirmation Message
   WhatsApp: "We've stopped all messages. Your data will be removed.\n\nIf you ever want to restart, just send us 'Hi'. Thank you, {name}. 🙏"

4. Flow Complete
   No further messages sent to this parent until they re-engage
```

**Data Flow:**
```
WhatsApp "STOP"
  → FlowExecutor.process_message()
    → _is_opt_out_message() → True
      → _handle_opt_out()
        → parent.opted_out = True
        → parent.conversation_state = None
        → DB commit
        → WhatsApp: Confirmation
        → Flow complete
```

**Database Changes:**
- `parents`: Updates opted_out, opted_out_at, conversation_state

**Wolf/Aurino Compliance:**
- Instant opt-out (no confirmation required)
- No friction
- L1-first keywords

**File:** `src/gapsense/engagement/flow_executor.py:200-273`

---

### 8. Parent Voice Message (Micro-Coaching)

**Description:** Parent sends voice message about learning activity, receives coaching feedback

**Entry Point:** Parent (onboarded) sends audio/voice message via WhatsApp

**Flow Steps:**
```
1. Voice Message Received
   Webhook: POST /v1/webhooks/whatsapp
   Handler: _handle_parent_voice()

2. Media Download
   Provider: WhatsAppClient.download_media(media_id or media_url)
   ⚠️ BUG: Same Twilio media ID extraction issue as teacher image
   Output: audio_bytes

3. Service Instantiation
   ⚠️ CRITICAL BUG: Same constructor signature mismatches as teacher image flow
   - VoiceMicroCoaching(db, ai_client, prompt_service, guard_service, media_service, worker_service)
   - MediaService() ❌ Missing settings
   - WorkerService() ❌ Missing all dependencies
   - GuardService() ❌ Missing ai_client, prompt_service
   - AsyncAIClient() ❌ Missing anthropic_api_key
   - PromptService() ❌ Missing settings

4. Audio Processing (if constructors fixed)
   VoiceMicroCoaching.handle_voice_message()
     → MediaService.upload() → S3
     → WorkerService.enqueue() → SQS task "voice_transcribe"
     → WhatsApp: "🎤 Got your voice message! I'm listening and will respond shortly."

5. Background Transcription (placeholder)
   WorkerService._handle_voice_transcribe()
     → MediaService.download(s3_key) → audio_bytes
     → STT_Service.transcribe() → transcript (PLACEHOLDER - not implemented)
     → VoiceMicroCoaching.process_transcript() → coaching feedback

6. Coaching Analysis
   VoiceMicroCoaching.process_transcript()
     → AI: ANALYSIS-002 with transcript
     → Output: {engagement_assessment, coaching_feedback, follow_up_activity, sentiment_score}
     → GuardService.check(coaching_text)
     → WhatsApp: Send coaching feedback to parent
     → DB: Update ParentInteraction record
```

**Data Flow (Current - BROKEN):**
```
WhatsApp Voice
  → Webhook → _handle_parent_voice()
    ⚠️ TypeError: Services instantiated without args
      ❌ Flow crashes here
```

**Data Flow (After Fix):**
```
WhatsApp Voice
  → Webhook → Download audio → VoiceMicroCoaching.handle_voice_message()
    → MediaService.upload() → S3: {country}/{student_id}/audio/{filename}
    → WorkerService.enqueue() → SQS: {"task_type": "voice_transcribe", "payload": {...}}
    → WhatsApp: "🎤 Got your voice message!"

SQS Queue
  → WorkerService._handle_voice_transcribe()
    → MediaService.download(s3_key) → audio_bytes
    → STT_Service.transcribe() → transcript
    → VoiceMicroCoaching.process_transcript()
      → AI: ANALYSIS-002 → coaching analysis
      → GuardService.check() → validate
      → WhatsApp: "Great job! I heard you working on..."
      → DB: Update ParentInteraction
```

**Database Changes (After Fix):**
- `parent_interactions`: Updates voice_transcript, sentiment_score, coaching_response

**Files:**
- Entry: `src/gapsense/webhooks/whatsapp.py:_handle_parent_voice`
- Coaching: `src/gapsense/engagement/voice_micro_coaching.py`
- Worker: `src/gapsense/services/worker_service.py:_handle_voice_transcribe` (lines 276-289)

**Known Issues:**
1. Constructor signature mismatches (BUGFIX_REQUIREMENTS.md #1.6)
2. Twilio media ID extraction (BUGFIX_REQUIREMENTS.md #1.8)
3. STT integration placeholder (not implemented)

---

## Background Worker Flows

### 9. TASK: tts_generate (TTS Voice Note Generation)

**Description:** Generates TTS audio from text and uploads to S3

**Trigger:** ParentActivityDelivery.deliver_activity() enqueues task

**Payload:**
```json
{
  "text": "Activity text to synthesize",
  "language": "en",
  "country": "GH",
  "student_id": "uuid",
  "parent_phone": "+233..."
}
```

**Processing:**
```
WorkerService._handle_tts_generate()
  → [PLACEHOLDER] TTS_Service.synthesize(text, language) → audio_bytes
  → [PLACEHOLDER] MediaService.upload() → S3: {country}/{student_id}/audio/tts_{lang}.ogg
  → [PLACEHOLDER] WhatsAppClient.send_audio_message() → Deliver voice note to parent
```

**Status:** Placeholder implementation (no actual TTS service integrated)

**File:** `src/gapsense/services/worker_service.py:194-215`

---

### 10. TASK: image_analyze (Exercise Book Analysis)

**Description:** Analyzes uploaded exercise book image with AI

**Trigger:** ExerciseBookScanner.handle_image_message() enqueues task

**Payload:**
```json
{
  "s3_key": "GH/student-uuid/images/exercise_book_abc123.jpg",
  "student_id": "uuid",
  "teacher_phone": "+233...",
  "country": "GH"
}
```

**Processing (Current - INCOMPLETE):**
```
WorkerService._handle_image_analyze()
  → MediaService.download(s3_key) → image_bytes
  → PromptService.render_prompt("ANALYSIS-001", country)
  → AsyncAIClient.generate() with image (base64)
  → AI returns: {gap_node_ids, errors, patterns, focus_areas, unreadable}
  → logger.info("image_analyze_complete", gaps_found=N)
  ❌ STOPS HERE - No callback to process results
```

**Processing (After Fix):**
```
WorkerService._handle_image_analyze()
  → [Same as above]
  → ExerciseBookScanner.process_analysis_result()
    → Check if image.unreadable → WhatsApp: "Image too blurry"
    → DB: Create/update GapProfile with gap_nodes
    → Build teacher summary
    → GuardService.check(summary)
    → WhatsApp: Send summary to teacher
```

**Required Changes:**
1. Add `db: AsyncSession` parameter to WorkerService constructor
2. Import ExerciseBookScanner
3. Call `scanner.process_analysis_result()` after AI completes

**File:** `src/gapsense/services/worker_service.py:217-250`

**Critical Issue:** BUGFIX_REQUIREMENTS.md #1.9, #1.10

---

### 11. TASK: scheduled_message (Scheduled Message Delivery)

**Description:** Delivers pre-scheduled messages to parents

**Trigger:** (Not currently used - future feature)

**Payload:**
```json
{
  "message": "Message text to deliver",
  "country": "GH",
  "language": "en",
  "student_context": {"student_id": "uuid"},
  "recipient_phone": "+233..."
}
```

**Processing (Current - INCOMPLETE):**
```
WorkerService._handle_scheduled_message()
  → GuardService.check(message, student_context, country, language)
  → If passed: logger.info("scheduled_message_delivered")
  → ❌ Comment: "# WhatsApp delivery would happen here"
  → No actual WhatsApp message sent
```

**Processing (After Fix):**
```
WorkerService._handle_scheduled_message()
  → GuardService.check()
  → If passed:
    → WhatsAppClient.from_settings()
    → client.send_text_message(to=recipient_phone, text=message)
    → logger.info("scheduled_message_delivered")
```

**File:** `src/gapsense/services/worker_service.py:252-274`

**Issue:** Incomplete implementation (BUGFIX_REQUIREMENTS.md #1.11)

---

### 12. TASK: voice_transcribe (Voice Transcription)

**Description:** Transcribes parent voice message using STT

**Trigger:** VoiceMicroCoaching.handle_voice_message() enqueues task

**Payload:**
```json
{
  "s3_key": "GH/student-uuid/audio/voice_abc123.ogg",
  "parent_id": "uuid",
  "student_id": "uuid",
  "country": "GH",
  "language": "en"
}
```

**Processing (Current - PLACEHOLDER):**
```
WorkerService._handle_voice_transcribe()
  → MediaService.download(s3_key) → audio_bytes
  → [PLACEHOLDER] STT_Service.transcribe(audio_bytes, language) → transcript
  → logger.info("voice_transcribe_complete")
```

**Processing (After STT Integration):**
```
WorkerService._handle_voice_transcribe()
  → MediaService.download(s3_key) → audio_bytes
  → STT_Service.transcribe() → transcript
  → VoiceMicroCoaching.process_transcript()
    → AI: ANALYSIS-002 → coaching feedback
    → GuardService.check()
    → WhatsApp: Send coaching to parent
    → DB: Update ParentInteraction
```

**File:** `src/gapsense/services/worker_service.py:276-289`

**Status:** Placeholder implementation (no STT service integrated)

---

## Data Flow Patterns

### Pattern 1: WhatsApp → Database (Conversational State)

**Flow:**
```
1. WhatsApp Message
   ↓
2. Webhook POST /v1/webhooks/whatsapp
   ↓
3. TwilioWebhookAdapter (if Twilio) → Normalize to Meta format
   ↓
4. webhook_router.process_message()
   ↓
5. Parent/Teacher Lookup
   - Parent.lookup_or_create(phone)
   - Teacher.lookup_by_phone(phone)
   ↓
6. Route to Flow Executor
   - FlowExecutor.process_message() (parents)
   - TeacherFlowExecutor.process_teacher_message() (teachers)
   ↓
7. Check Session Expiry
   - _check_session_expiry() → Clear state if > 24hr
   ↓
8. Update Session Tracking
   - parent.last_message_at = now
   - parent.session_expires_at = now + 24hr
   - teacher.last_active_at = now
   ↓
9. Check for Commands/Opt-Out
   - Commands: RESTART, CANCEL, HELP, STATUS
   - Opt-out keywords (L1-first)
   ↓
10. Route to Current Flow Step
    - Get conversation_state.flow, conversation_state.step
    - Call step handler
   ↓
11. Process User Input
    - Validation
    - Database updates
    - conversation_state modification
   ↓
12. Generate Response
    - WhatsAppClient.send_text_message() or send_button_message()
   ↓
13. Commit Database Changes
    - conversation_state updated
    - Related records created/updated
```

**Key Tables:**
- `parents`: conversation_state, last_message_at, session_expires_at
- `teachers`: conversation_state, last_active_at
- Flow-specific: schools, students, diagnostic_sessions, etc.

---

### Pattern 2: WhatsApp Media → S3 → SQS → Worker

**Flow:**
```
1. WhatsApp Media Message (Image/Voice)
   ↓
2. Webhook → _handle_teacher_image() or _handle_parent_voice()
   ↓
3. WhatsApp Media Download
   - TwilioWhatsAppProvider.download_media(url) [direct download]
   - MetaWhatsAppProvider.download_media(id) [2-step: get URL → download]
   ↓ audio_bytes or image_bytes

4. S3 Upload
   - MediaService.upload(bytes, country, student_id, media_type, filename)
   - S3 key format: "{country}/{student_id}/{media_type}/{filename}"
   ↓ s3_key

5. SQS Task Enqueue
   - WorkerService.enqueue(WorkerTask(task_type, payload))
   - SQS message: {"task_type": "...", "payload": {...}, "retry_count": 0}
   ↓

6. WhatsApp Acknowledgment
   - "📸 Analyzing..." (image)
   - "🎤 Got your voice message!" (voice)
   ↓

7. Worker Polls SQS (Long Polling)
   - WorkerService._poll_once() every 20 seconds
   - Receives up to 10 messages
   ↓

8. Worker Processes Task
   - _route_task() → _handle_image_analyze() or _handle_voice_transcribe()
   - Download from S3
   - Process with AI
   - ⚠️ MISSING: Callback to send results to user
   ↓

9. Delete SQS Message (on success)
   - _delete_message(receipt_handle)

10. [MISSING] Complete Flow
    - Update database (GapProfile, ParentInteraction)
    - Send results to WhatsApp
```

**Services Involved:**
- `WhatsAppClient`: Media download
- `MediaService`: S3 upload/download
- `WorkerService`: SQS enqueue/poll
- `ExerciseBookScanner`: Image processing coordination
- `VoiceMicroCoaching`: Voice processing coordination

**S3 Bucket Structure:**
```
gapsense-media-{env}/
├── GH/
│   ├── {student_id_1}/
│   │   ├── images/
│   │   │   └── exercise_book_abc123.jpg
│   │   └── audio/
│   │       ├── voice_def456.ogg
│   │       └── tts_en.ogg
│   └── {student_id_2}/
│       └── ...
├── UG/
└── KE/
```

**SQS Queue Format:**
```json
{
  "task_type": "image_analyze",
  "payload": {
    "s3_key": "GH/uuid/images/exercise_book.jpg",
    "student_id": "uuid",
    "teacher_phone": "+233...",
    "country": "GH"
  },
  "retry_count": 0,
  "max_retries": 3
}
```

---

### Pattern 3: AI Generation → Guard → WhatsApp

**Flow:**
```
1. Generate Content
   - ParentActivityDelivery: PARENT-001 + ACT-001 → activity_text
   - TeacherConversationPartner: TEACHER-001/002/003 → response_text
   - VoiceMicroCoaching: ANALYSIS-002 → coaching_text
   - ExerciseBookScanner: ANALYSIS-001 → teacher_summary
   ↓

2. Guard Validation
   - GuardService.check(content, student_context, country, language)
   - AI: GUARD-001 prompt
   - Returns: GuardResult(passed, violations, risk_score)
   ↓

3. Routing
   If passed:
     → Continue to delivery
   If blocked:
     → Log violation
     → Return error
     → Do NOT send to user
   ↓

4. WhatsApp Delivery
   - WhatsAppClient.send_text_message(to, text)
   - Provider: TwilioWhatsAppProvider or MetaWhatsAppProvider
   ↓

5. Log Success/Failure
   - logger.info("message_sent", message_id=...)
   - logger.error("send_failed", error=...)
```

**Guard Violations Example:**
```json
{
  "passed": false,
  "violations": [
    "CULTURAL_INAPPROPRIATENESS: Reference to pork in Muslim context",
    "DATA_EXPOSURE: Mentioned student's last name"
  ],
  "risk_score": 0.85
}
```

**Services:**
- `AsyncAIClient`: AI generation
- `PromptService`: Prompt rendering
- `GuardService`: Validation
- `WhatsAppClient`: Delivery

---

### Pattern 4: Diagnostic → GapProfile → Activity

**Flow:**
```
1. Diagnostic Session Complete
   - session.status = "completed"
   - session.completed_at = now
   ↓

2. Generate Gap Profile
   - GapProfileAnalyzer.generate_gap_profile()
   - Analyzes all DiagnosticQuestions for session
   - Identifies gap_nodes (prerequisites for incorrect answers)
   - Identifies mastered_nodes (correct answers + prerequisites)
   ↓

3. Create GapProfile Record
   - student_id, session_id, source="diagnostic"
   - gap_nodes = [UUID, UUID, ...]
   - mastered_nodes = [UUID, UUID, ...]
   - uncertain_nodes = []
   - is_current = True (set previous profiles to False)
   - DB: Insert gap_profiles
   ↓

4. Trigger Activity Delivery
   - ParentActivityDelivery.deliver_activity(parent, student, gap_profile)
   ↓

5. Generate Personalized Activity
   - AI: PARENT-001 + gap_summary → activity plan
   - AI: ACT-001 → specific 3-minute activity
   ↓

6. Validate & Deliver
   - GuardService.check(activity_text)
   - If passed:
     → SQS: Enqueue tts_generate task
     → WhatsApp: Send text version immediately
   ↓

7. Parent Receives
   - Text activity message
   - [Future] Voice note with TTS
```

**Database Changes:**
```sql
-- Mark previous profiles as not current
UPDATE gap_profiles
SET is_current = FALSE
WHERE student_id = ? AND is_current = TRUE;

-- Insert new profile
INSERT INTO gap_profiles (
  student_id, session_id, source,
  gap_nodes, mastered_nodes, is_current
) VALUES (?, ?, 'diagnostic', ?, ?, TRUE);

-- Enqueue TTS task
INSERT INTO sqs_messages (task_type, payload)
VALUES ('tts_generate', ?);
```

---

### Pattern 5: Teacher → Student → Parent Linkage

**Flow:**
```
1. Teacher Onboarding
   - FLOW-TEACHER-ONBOARD
   - Teacher creates Student records
   - student.teacher_id = teacher.id
   - student.primary_parent_id = NULL (awaiting parent)
   - student.is_active = TRUE
   ↓ Student records exist, unlinked

2. Parent Onboarding
   - FLOW-ONBOARD
   - Parent selects from unlinked students
   - Query: SELECT * FROM students
            WHERE primary_parent_id IS NULL
            AND is_active = TRUE
   ↓ Parent chooses their child

3. Confirmation Step
   - CONFIRM_STUDENT_SELECTION
   - Parent confirms selection
   - Prevents accidental linking
   ↓

4. Critical Linkage
   - student.primary_parent_id = parent.id
   - student.home_language = parent.preferred_language
   - parent.onboarded_at = now
   - DB: Commit transaction
   ↓ PARENT AND STUDENT ARE NOW LINKED

5. Diagnostic Trigger
   - If parent.diagnostic_consent = True:
     → Create DiagnosticSession(status="pending")
   - Next message triggers diagnostic start
   ↓

6. Three-Way Relationship
   Teacher ←→ Student ←→ Parent
   - Teacher sees student in their class
   - Parent receives diagnostic & activities for student
   - Both can view student's gap profile
```

**Database Relationships:**
```sql
-- Teacher has many Students
students.teacher_id → teachers.id

-- Student has one Parent
students.primary_parent_id → parents.id

-- Student has many GapProfiles
gap_profiles.student_id → students.id

-- Student has many DiagnosticSessions
diagnostic_sessions.student_id → students.id
```

**Critical Constraint:**
- One student can have only ONE primary_parent_id
- Parent selection must check for race conditions:
  ```python
  if selected_student.primary_parent_id is not None:
      return error("Student already has a parent linked")
  ```

---

## System Integration Points

### WhatsApp Provider Abstraction

**Architecture:**
```
WhatsAppClient (interface)
  ├── factory.py → get_whatsapp_client()
  ├── TwilioWhatsAppProvider
  │   └── Uses REST API + HTTP Basic Auth
  └── MetaWhatsAppProvider
      └── Uses Graph API + Bearer Token
```

**Provider Selection:**
```python
# .env
WHATSAPP_PROVIDER=twilio  # or "meta"

# Runtime
client = WhatsAppClient.from_settings()
# Returns singleton instance based on provider config
```

**Method Compatibility:**
| Method | Twilio | Meta | Notes |
|--------|--------|------|-------|
| send_text_message() | ✅ | ✅ | Both support plain text |
| send_button_message() | ⚠️ Fallback | ✅ Native | Twilio uses numbered list |
| send_list_message() | ⚠️ Fallback | ✅ Native | Twilio uses numbered list |
| send_template() | ✅ Content SID | ✅ Template name | Different formats |
| download_media() | ✅ Direct URL | ✅ 2-step | Different auth |
| mark_as_read() | ❌ No-op | ✅ Supported | Twilio doesn't support |

**Webhook Normalization:**
```
Twilio Webhook (form-encoded)
  ↓
TwilioWebhookAdapter.normalize_to_meta_format()
  ↓
Meta-compatible JSON
  {
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "256779401600",
            "type": "text",
            "text": {"body": "Hello"}
          }]
        }
      }]
    }]
  }
  ↓
webhook_router.process_message()
```

**Media Download Differences:**
```python
# Twilio: Direct URL download
media_url = "https://api.twilio.com/2010-04-01/Accounts/.../Media/..."
image_bytes = await client.get(media_url, auth=(sid, token))

# Meta: 2-step (get URL, then download)
media_id = "abc123"
# Step 1: Get URL
url = await graph_api.get(f"/{media_id}", headers={"Authorization": f"Bearer {token}"})
# Step 2: Download
image_bytes = await client.get(url["url"], headers={"Authorization": f"Bearer {token}"})
```

**⚠️ CRITICAL BUG:**
```python
# Current code (BROKEN for Twilio):
media_id = image_content.get("id") or image_content.get("url")
# Twilio: id = "SM123..." (message_sid) ❌
# Should use: image_content.get("url") for Twilio

# Fixed code:
if WHATSAPP_PROVIDER == "twilio":
    media_id = image_content.get("url")  # Direct media URL
else:
    media_id = image_content.get("id")   # Meta media ID
```

---

### AI Provider Integration

**Components:**
- `AsyncAIClient`: Anthropic Claude API wrapper
- `PromptService`: Loads prompts from gapsense_prompt_library_v2.0_multicountry.json
- `GuardService`: GUARD-001 validation

**Prompt Flow:**
```
1. Load Prompt
   PromptService.render_prompt("PARENT-001", country="GH", language="en")
   → Reads from JSON: prompts/PARENT-001
   → Returns: RenderedPrompt(system_prompt, model, temperature, max_tokens)

2. Generate Content
   AsyncAIClient.generate(
     prompt_id="PARENT-001",
     system=rendered.system_prompt,
     messages=[...],
     model=rendered.model,
     temperature=rendered.temperature
   )
   → POST https://api.anthropic.com/v1/messages
   → Returns: AIResponse(text, usage, json_parsed)

3. Guard Validation
   GuardService.check(content, student_context, country, language)
   → Renders GUARD-001 prompt
   → AI analyzes for violations
   → Returns: GuardResult(passed, violations, risk_score)
```

**Prompt Categories:**
- **PARENT-XXX**: Parent engagement (activities, explanations)
- **ACT-XXX**: Specific activity generation
- **TEACHER-XXX**: Teacher pedagogical support
- **ANALYSIS-XXX**: Image/voice analysis
- **GUARD-XXX**: Safety & compliance validation

**Rate Limiting:**
```python
# Settings
ANTHROPIC_MAX_REQUESTS_PER_MINUTE = 50
ANTHROPIC_MAX_CONCURRENT_REQUESTS = 10

# Implementation
AsyncAIClient uses asyncio.Semaphore(max_concurrent)
+ token bucket for RPM limiting
```

---

### Database Session Management

**Pattern:**
```python
# Dependency injection in FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# Route handler
@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # db session available here
    executor = FlowExecutor(db=db)
    await executor.process_message(...)
```

**Transaction Management:**
```python
# Explicit commits in flow executors
parent.conversation_state = {"flow": "FLOW-ONBOARD", ...}
flag_modified(parent, "conversation_state")
await self.db.commit()

# Rollback on errors
try:
    # ... database operations
    await self.db.commit()
except Exception as e:
    await self.db.rollback()
    logger.error(...)
```

**⚠️ CRITICAL BUG:**
```python
# WorkerService doesn't receive db session
class WorkerService:
    def __init__(self, ai_client, media_service, ...):
        # ❌ No db parameter

    async def _handle_image_analyze(self, task):
        # Can't call ExerciseBookScanner.process_analysis_result()
        # because it requires db session to create GapProfile
```

**Required Fix:**
```python
class WorkerService:
    def __init__(self, *, db: AsyncSession, ai_client, ...):
        self._db = db  # Store session

    async def _handle_image_analyze(self, task):
        scanner = ExerciseBookScanner(
            db=self._db,  # Pass session
            ...
        )
        await scanner.process_analysis_result(...)
```

---

## E2E Test Requirements

### Teacher Flow E2E Tests

#### TEST-TEACHER-001: Complete Onboarding (Manual Entry)

**Scenario:** Teacher onboards with manual school entry and creates class roster

**Setup:**
```python
# Prerequisites
- Clean database
- Twilio webhook configured
- WhatsApp test number available
```

**Test Steps:**
```
1. Send "START" to WhatsApp number
   Expected: Welcome message + school name prompt
   Verify: Parent record created with conversation_state.flow = "FLOW-TEACHER-ONBOARD"

2. Send "Accra Academy JHS"
   Expected: "Great! School: Accra Academy JHS ✅\n\nWhat class do you teach?"
   Verify: School created in DB, teacher.school_id set, step = "COLLECT_CLASS"

3. Send "JHS 1A"
   Expected: "Perfect! Class: JHS 1A ✅\n\nHow many students?"
   Verify: teacher.class_name = "JHS 1A", teacher.grade_taught = "JHS1", step = "COLLECT_STUDENT_COUNT"

4. Send "3"
   Expected: "Got it! 3 students ✅\n\nNow, please send me the list of student names..."
   Verify: conversation_state.data.student_count = 3, step = "COLLECT_STUDENT_LIST"

5. Send "1. Kwame Mensah\n2. Akosua Boateng\n3. Kofi Asante"
   Expected: Button message with preview + confirmation
   Verify: conversation_state.data.parsed_names = ["Kwame Mensah", "Akosua Boateng", "Kofi Asante"]

6. Click "Yes, create profiles" button
   Expected: "Perfect! ✅ I've created profiles for all 3 students..."
   Verify DB:
     - 3 Student records created
     - student.teacher_id = teacher.id
     - student.primary_parent_id IS NULL
     - teacher.onboarded_at IS NOT NULL
     - teacher.conversation_state IS NULL
```

**Database Assertions:**
```python
# After test completion
assert db.query(School).count() == 1
assert db.query(Teacher).count() == 1
assert db.query(Student).count() == 3

teacher = db.query(Teacher).first()
assert teacher.onboarded_at is not None
assert teacher.conversation_state is None
assert teacher.class_name == "JHS 1A"

students = db.query(Student).filter_by(teacher_id=teacher.id).all()
assert len(students) == 3
assert all(s.primary_parent_id is None for s in students)
assert all(s.is_active is True for s in students)
```

**Cleanup:**
```python
# Delete test data
db.query(Student).delete()
db.query(Teacher).delete()
db.query(School).delete()
db.commit()
```

---

#### TEST-TEACHER-002: Onboarding with Invitation Code

**Scenario:** Teacher uses school-generated invitation code for instant linking

**Setup:**
```python
# Create test school and invitation
school = School(name="Test School", district_id=1, is_active=True)
db.add(school)
db.flush()

invitation = SchoolInvitation(
    school_id=school.id,
    invitation_code="TESTSCH-ABC123",
    is_active=True,
    max_teachers=10,
    teachers_joined=0,
    expires_at=(datetime.now(UTC) + timedelta(days=30)).isoformat()
)
db.add(invitation)
db.commit()
```

**Test Steps:**
```
1. Send "START"
   Expected: School name prompt

2. Send "TESTSCH-ABC123"
   Expected: "✅ Welcome to Test School!\n\nYou've successfully joined using invitation code TESTSCH-ABC123.\n\nWhat class do you teach?"
   Verify DB:
     - teacher.school_id = school.id
     - invitation.teachers_joined = 1
     - conversation_state.data.joined_via_code = "TESTSCH-ABC123"
     - step = "COLLECT_CLASS"

3-6. [Complete onboarding as normal]
```

**Database Assertions:**
```python
teacher = db.query(Teacher).first()
assert teacher.school_id == school.id

invitation = db.query(SchoolInvitation).filter_by(invitation_code="TESTSCH-ABC123").first()
assert invitation.teachers_joined == 1

# Check conversation state captured the code
# (before completion clears it)
```

---

#### TEST-TEACHER-003: Exercise Book Image Analysis (After Bugfix)

**Scenario:** Teacher sends exercise book image, receives AI analysis summary

**Setup:**
```python
# Create teacher with onboarded student
teacher = create_test_teacher(onboarded=True)
student = create_test_student(teacher_id=teacher.id)

# Mock services (after bugfix applied)
# Ensure all services have correct constructors
```

**Test Steps:**
```
1. Teacher sends image message via WhatsApp
   Webhook payload: {
     "type": "image",
     "image": {"id": "media_id_123", "mime_type": "image/jpeg"}
   }

2. Verify immediate response
   Expected: "📸 Analyzing the exercise book page. I'll send you the results shortly."

3. Verify S3 upload
   Check: S3 bucket has key "GH/{student_id}/images/exercise_book_*.jpg"

4. Verify SQS task enqueued
   Check: SQS message with task_type="image_analyze"
   Payload: {s3_key, student_id, teacher_phone, country}

5. Simulate worker processing
   WorkerService._poll_once() → _handle_image_analyze()
   Mock AI response: {
     "gap_node_ids": ["uuid1", "uuid2"],
     "errors": [{"description": "Addition error in question 3"}],
     "patterns": ["Carries not completed"],
     "focus_areas": ["Place value", "Column addition"]
   }

6. Verify GapProfile created
   Check DB: gap_profiles table
   Assert:
     - student_id = student.id
     - source = "exercise_book"
     - gap_nodes = [uuid1, uuid2]
     - is_current = True

7. Verify teacher receives summary
   Expected WhatsApp: "📊 Exercise Book Analysis Complete\n\nFound 1 error(s):\n  • Addition error in question 3\n\nPatterns identified: Carries not completed\n\nRecommended focus: Place value, Column addition"
```

**Database Assertions:**
```python
gap_profile = db.query(GapProfile).filter_by(student_id=student.id, is_current=True).first()
assert gap_profile is not None
assert gap_profile.source == "exercise_book"
assert len(gap_profile.gap_nodes) == 2
```

**S3 Assertions:**
```python
# Check S3 upload
s3_client = boto3.client('s3')
objects = s3_client.list_objects_v2(Bucket='gapsense-media-local', Prefix=f'GH/{student.id}/images/')
assert objects['KeyCount'] == 1
```

**SQS Assertions:**
```python
# Check SQS message
sqs_client = boto3.client('sqs')
messages = sqs_client.receive_message(QueueUrl=settings.SQS_QUEUE_URL)
assert len(messages['Messages']) == 1
body = json.loads(messages['Messages'][0]['Body'])
assert body['task_type'] == 'image_analyze'
```

---

### Parent Flow E2E Tests

#### TEST-PARENT-001: Complete Onboarding & Diagnostic

**Scenario:** Parent onboards, selects child, consents to diagnostic, completes assessment

**Setup:**
```python
# Create teacher with students
teacher = create_test_teacher(onboarded=True)
student1 = create_test_student(teacher_id=teacher.id, full_name="Kwame Mensah", current_grade="JHS1")
student2 = create_test_student(teacher_id=teacher.id, full_name="Akosua Boateng", current_grade="JHS1")

# Load curriculum data for diagnostic
await load_test_curriculum(country="GH", subject="mathematics", grade="JHS1")
```

**Test Steps:**
```
ONBOARDING PHASE

1. Parent sends "Hi" (first message ever)
   Expected: Welcome message with opt-in prompt
   Verify: Parent record created, conversation_state.flow = "FLOW-ONBOARD", step = "AWAITING_OPT_IN"

2. Parent clicks "Yes, start" button
   Expected: Student selection list with Kwame and Akosua
   Verify: parent.opted_in = True, parent.opted_in_at set, step = "AWAITING_STUDENT_SELECTION"

3. Parent sends "1" (selects Kwame)
   Expected: Confirmation message "You selected: Kwame Mensah\nGrade: JHS1\n\nIs this your child?"
   Verify: conversation_state.data.selected_student_id = student1.id, step = "CONFIRM_STUDENT_SELECTION"

4. Parent clicks "Yes, that's correct"
   Expected: Diagnostic consent message
   Verify: step = "AWAITING_DIAGNOSTIC_CONSENT"

5. Parent clicks "Yes, proceed" (consent)
   Expected: Language selection message
   Verify: parent.diagnostic_consent = True, parent.diagnostic_consent_at set, step = "AWAITING_LANGUAGE"

6. Parent clicks "English"
   Expected: "All set! 🌟\n\nYou're now linked to Kwame (Grade JHS1)..."
   Verify DB:
     - student1.primary_parent_id = parent.id ✅ CRITICAL LINK
     - student1.home_language = "en"
     - parent.onboarded_at set
     - parent.conversation_state = None
     - DiagnosticSession created with status="pending"

DIAGNOSTIC PHASE

7. Parent sends any message (triggers diagnostic start)
   Expected: First diagnostic question "Question 1 for Kwame:\n\nWhat is 5 + 3?"
   Verify DB:
     - session.status = "in_progress"
     - session.started_at set
     - DiagnosticQuestion created with question_order=1
     - conversation_state.flow = "FLOW-DIAGNOSTIC", step = "AWAITING_ANSWER"

8. Parent sends "8" (correct answer)
   Expected: Next question "Question 2 for Kwame:\n\nWhat is 12 - 7?"
   Verify DB:
     - Previous question: is_correct = True
     - session.total_questions = 1, session.correct_answers = 1
     - session.correct_nodes updated with node for question 1
     - New DiagnosticQuestion created with question_order=2

9. Parent sends "6" (incorrect, correct is 5)
   Expected: Next question (adaptive algorithm selects easier prerequisite)
   Verify DB:
     - Previous question: is_correct = False
     - session.total_questions = 2, session.correct_answers = 1
     - session.tested_nodes includes both nodes

10. [Continue for N more questions until adaptive engine decides to stop]

11. Diagnostic completion triggered
    Expected: "Diagnostic complete for Kwame! 🎉\nQuestions answered: N\nCorrect answers: X (Y%)\n..."
    Verify DB:
      - session.status = "completed", session.completed_at set
      - GapProfile created with source="diagnostic", gap_nodes=[...], is_current=True
      - parent.conversation_state = None
      - First activity delivered (text message sent)
```

**Database Assertions:**
```python
# After onboarding
parent = db.query(Parent).filter_by(phone=test_phone).first()
assert parent.opted_in is True
assert parent.onboarded_at is not None
assert parent.diagnostic_consent is True
assert parent.preferred_language == "en"

student = db.query(Student).get(student1.id)
assert student.primary_parent_id == parent.id  # CRITICAL
assert student.home_language == "en"

# After diagnostic
session = db.query(DiagnosticSession).filter_by(student_id=student.id).first()
assert session.status == "completed"
assert session.total_questions > 0
assert session.correct_answers >= 0

gap_profile = db.query(GapProfile).filter_by(student_id=student.id, is_current=True).first()
assert gap_profile is not None
assert gap_profile.source == "diagnostic"
assert len(gap_profile.gap_nodes) > 0 or len(gap_profile.mastered_nodes) > 0
```

**WhatsApp Message Assertions:**
```python
# Verify all messages sent
messages_sent = get_whatsapp_test_messages(to=parent.phone)
assert len(messages_sent) >= 15  # Onboarding + diagnostic + activity

# Check final messages
assert "Diagnostic complete" in messages_sent[-2]
assert "activity" in messages_sent[-1].lower()  # First activity delivered
```

---

#### TEST-PARENT-002: Opt-Out Flow

**Scenario:** Parent opts out at any time (Wolf/Aurino compliance)

**Test Steps:**
```
1. Setup: Parent is mid-onboarding (step = "AWAITING_STUDENT_SELECTION")

2. Parent sends "STOP" (English keyword)
   Expected: "We've stopped all messages. Your data will be removed.\n\nIf you ever want to restart, just send us 'Hi'. Thank you, friend. 🙏"
   Verify DB:
     - parent.opted_out = True
     - parent.opted_out_at set
     - parent.conversation_state = None (flow cleared)

3. Attempt to send message to opted-out parent
   Expected: No message sent (should be blocked at routing layer)

4. Parent sends "Hi" again (re-engagement)
   Expected: Onboarding starts fresh
   Verify: parent.opted_out = False (re-engagement allowed)
```

**L1-First Keyword Tests:**
```python
# Test all L1 keywords
keywords = ["stop", "gyae", "tɔtɔ", "tsia", "nyɛli"]
for keyword in keywords:
    parent = create_test_parent()
    send_message(parent.phone, keyword)

    parent.refresh()
    assert parent.opted_out is True
```

---

#### TEST-PARENT-003: Voice Message Coaching (After Bugfix)

**Scenario:** Parent sends voice message about activity, receives coaching feedback

**Setup:**
```python
# Create onboarded parent with linked student
parent, student = create_onboarded_parent_with_student()

# Mock voice file
audio_bytes = load_test_audio("parent_voice_sample.ogg")
```

**Test Steps:**
```
1. Parent sends voice message
   Webhook payload: {
     "type": "audio",
     "audio": {"id": "audio_id_123", "mime_type": "audio/ogg"}
   }

2. Verify immediate ack
   Expected: "🎤 Got your voice message! I'm listening and will respond shortly."

3. Verify S3 upload
   Check: S3 key "GH/{student_id}/audio/voice_*.ogg"

4. Verify SQS task
   Check: task_type="voice_transcribe", payload={s3_key, parent_id, student_id, country, language}

5. Simulate worker transcription
   Mock STT output: "I tried to help Kwame with the counting activity but he got confused with the numbers."

6. Simulate coaching analysis
   Mock AI ANALYSIS-002 output: {
     "engagement_assessment": "Parent is actively engaged but needs guidance on number sequencing",
     "coaching_feedback": "Great job working with Kwame on counting! Try using physical objects...",
     "follow_up_activity": "Count 10 objects together",
     "sentiment_score": 0.7
   }

7. Verify coaching sent
   Expected WhatsApp: "Great job working with Kwame on counting! Try using physical objects...\n\n📝 Try this next: Count 10 objects together"

8. Verify ParentInteraction updated
   Check DB:
     - voice_transcript = "I tried to help..."
     - sentiment_score = 0.7
     - coaching_response = "Great job working..."
```

**Database Assertions:**
```python
interaction = db.query(ParentInteraction).filter_by(parent_id=parent.id).order_by(ParentInteraction.created_at.desc()).first()
assert interaction.voice_transcript is not None
assert interaction.sentiment_score == 0.7
assert "Great job" in interaction.coaching_response
```

---

### Integration Test Suites

#### SUITE-001: WhatsApp Provider Compatibility

**Purpose:** Verify both Twilio and Meta providers work correctly

**Tests:**
```
TEST-PROVIDER-001: Text Message (Twilio)
TEST-PROVIDER-002: Text Message (Meta)
TEST-PROVIDER-003: Button Message (Twilio fallback to numbered list)
TEST-PROVIDER-004: Button Message (Meta native)
TEST-PROVIDER-005: Image Download (Twilio direct URL)
TEST-PROVIDER-006: Image Download (Meta 2-step)
TEST-PROVIDER-007: Voice Download (Twilio)
TEST-PROVIDER-008: Voice Download (Meta)
TEST-PROVIDER-009: Template Message (Twilio Content SID)
TEST-PROVIDER-010: Template Message (Meta template name)
TEST-PROVIDER-011: Webhook Normalization (Twilio → Meta format)
TEST-PROVIDER-012: Webhook Normalization (Meta passthrough)
```

**Example Test:**
```python
@pytest.mark.parametrize("provider", ["twilio", "meta"])
async def test_text_message_delivery(provider):
    """Test text message delivery via both providers"""
    # Setup
    settings.WHATSAPP_PROVIDER = provider
    client = get_whatsapp_client()

    # Send message
    message_id = await client.send_text_message(
        to="+256779401600",
        text="Test message"
    )

    # Verify
    assert message_id is not None
    assert message_id.startswith("SM" if provider == "twilio" else "wamid.")
```

---

#### SUITE-002: Background Worker Processing

**Purpose:** Verify all worker task types process correctly

**Tests:**
```
TEST-WORKER-001: image_analyze - Success path
TEST-WORKER-002: image_analyze - Unreadable image
TEST-WORKER-003: image_analyze - Retry on failure
TEST-WORKER-004: image_analyze - DLQ after max retries
TEST-WORKER-005: voice_transcribe - Success path
TEST-WORKER-006: voice_transcribe - Invalid audio format
TEST-WORKER-007: tts_generate - Success path (once implemented)
TEST-WORKER-008: scheduled_message - Success path (after bugfix)
TEST-WORKER-009: Concurrent task processing (10 tasks)
TEST-WORKER-010: Visibility timeout backoff
```

**Example Test:**
```python
async def test_image_analyze_success():
    """Test complete image analysis flow"""
    # Setup
    student = create_test_student()
    teacher = create_test_teacher()

    # Upload test image to S3
    s3_key = await upload_test_image(student_id=student.id)

    # Enqueue task
    task = WorkerTask(
        task_type="image_analyze",
        payload={
            "s3_key": s3_key,
            "student_id": str(student.id),
            "teacher_phone": teacher.phone,
            "country": "GH"
        }
    )
    await worker_service.enqueue(task)

    # Process task
    await worker_service._poll_once()

    # Verify GapProfile created
    gap_profile = db.query(GapProfile).filter_by(
        student_id=student.id,
        source="exercise_book"
    ).first()
    assert gap_profile is not None

    # Verify teacher received message
    messages = get_sent_messages(to=teacher.phone)
    assert any("📊 Exercise Book Analysis Complete" in msg for msg in messages)
```

---

#### SUITE-003: Error Recovery & Edge Cases

**Purpose:** Verify system handles errors gracefully

**Tests:**
```
TEST-ERROR-001: Session expiry after 24 hours
TEST-ERROR-002: Duplicate parent registration (same phone)
TEST-ERROR-003: Student already linked (race condition)
TEST-ERROR-004: Invalid button response
TEST-ERROR-005: Malformed student name list
TEST-ERROR-006: Guard service blocks inappropriate content
TEST-ERROR-007: AI service unavailable (graceful degradation)
TEST-ERROR-008: Database connection failure (retry logic)
TEST-ERROR-009: S3 upload failure (error handling)
TEST-ERROR-010: WhatsApp API rate limiting
TEST-ERROR-011: Command handling (RESTART, CANCEL, HELP, STATUS)
TEST-ERROR-012: Invitation code expired
TEST-ERROR-013: Invitation code at max capacity
```

**Example Test:**
```python
async def test_session_expiry():
    """Test conversation state clears after 24 hours"""
    # Setup parent mid-onboarding
    parent = create_test_parent()
    parent.conversation_state = {
        "flow": "FLOW-ONBOARD",
        "step": "AWAITING_STUDENT_SELECTION",
        "data": {}
    }
    parent.last_message_at = datetime.now(UTC) - timedelta(hours=25)
    db.commit()

    # Send new message
    await process_message(parent, "Hi")

    # Verify state cleared and onboarding restarted
    parent.refresh()
    assert parent.conversation_state.get("step") == "AWAITING_OPT_IN"  # Fresh start
```

---

## Known Issues & Gaps

### Critical Bugs (Block Core Functionality)

#### BUG-001: Service Constructor Signature Mismatches
**Severity:** CRITICAL
**Affected Flows:** Exercise Book Scan, Parent Voice Coaching
**Location:** `src/gapsense/webhooks/whatsapp.py:_handle_teacher_image`, `_handle_parent_voice`

**Issue:**
```python
# Current (BROKEN):
scanner = ExerciseBookScanner(
    db=db,
    media_service=MediaService(),  # ❌ Missing settings
    worker_service=WorkerService(),  # ❌ Missing 5 dependencies
    guard_service=GuardService(),  # ❌ Missing 2 dependencies
    ai_client=AsyncAIClient(),  # ❌ Missing api_key
    prompt_service=PromptService(),  # ❌ Missing settings
)
# Crashes with TypeError
```

**Fix Required:** See BUGFIX_REQUIREMENTS.md #1.1-1.6

---

#### BUG-002: Image Analysis Missing Completion Callback
**Severity:** CRITICAL
**Affected Flows:** Exercise Book Scan
**Location:** `src/gapsense/services/worker_service.py:217-250`

**Issue:**
```python
# Worker downloads image, sends to AI, gets analysis... then stops
if response and response.json_parsed:
    logger.info("image_analyze_complete", gaps_found=...)
    # ❌ FLOW STOPS HERE

# MISSING:
# ExerciseBookScanner.process_analysis_result() never called
# GapProfile never created
# Teacher never receives summary
```

**Impact:** Exercise book scanning completely non-functional
**Fix Required:** See BUGFIX_REQUIREMENTS.md #1.9, #1.10

---

#### BUG-003: Twilio Media ID Extraction
**Severity:** CRITICAL
**Affected Flows:** Exercise Book Scan (Twilio), Parent Voice (Twilio)
**Location:** `src/gapsense/webhooks/whatsapp.py`

**Issue:**
```python
# Current (BROKEN for Twilio):
media_id = image_content.get("id") or image_content.get("url")

# Twilio adapter sets:
image_content = {
    "id": "SM1234567890abcdef",  # ❌ Message SID, not media URL
    "url": "https://api.twilio.com/2010-04-01/Accounts/.../Media/..."  # ✅ Actual media URL
}

# So download_media(media_id="SM123...") fails
```

**Fix Required:** Prefer `image_content.get("url")` for Twilio
**See:** BUGFIX_REQUIREMENTS.md #1.7, #1.8

---

### High Priority Gaps (Missing Functionality)

#### GAP-001: WorkerService Missing Database Session
**Severity:** HIGH
**Affected Flows:** Exercise Book Scan, Parent Voice Coaching

**Issue:** WorkerService can't call methods that require database access (e.g., `process_analysis_result()`)

**Fix Required:** Add `db: AsyncSession` parameter to constructor
**See:** BUGFIX_REQUIREMENTS.md #1.10

---

#### GAP-002: Scheduled Message Delivery Incomplete
**Severity:** MEDIUM
**Affected Flows:** Scheduled messages (future feature)
**Location:** `src/gapsense/services/worker_service.py:252-274`

**Issue:**
```python
if guard_result.passed:
    logger.info("scheduled_message_delivered")
    # WhatsApp delivery would happen here  ❌
```

**Fix Required:** Add WhatsAppClient.send_text_message() call
**See:** BUGFIX_REQUIREMENTS.md #1.11

---

#### GAP-003: TTS Service Not Implemented
**Severity:** MEDIUM
**Affected Flows:** Daily activity delivery (voice notes)
**Location:** `src/gapsense/services/worker_service.py:194-215`

**Issue:** Placeholder comments, no actual TTS integration

**Required:** Integrate TTS service (AWS Polly, Google TTS, or ElevenLabs)

---

#### GAP-004: STT Service Not Implemented
**Severity:** MEDIUM
**Affected Flows:** Parent voice coaching
**Location:** `src/gapsense/services/worker_service.py:276-289`

**Issue:** Placeholder comments, no actual STT integration

**Required:** Integrate STT service (AWS Transcribe, Google STT, or Whisper API)

---

#### GAP-005: L1 Translations Missing
**Severity:** HIGH
**Wolf/Aurino Compliance:** VIOLATION
**Affected:** All parent-facing messages

**Issue:** All messages hardcoded in English
**Required:** Implement translation system for Twi, Ewe, Ga, Dagbani

**Code Comments:**
```python
# flow_executor.py:7-16
"""
TODO: L1-FIRST TRANSLATIONS NEEDED (Wolf/Aurino Compliance VIOLATION)
    ⚠️ CRITICAL: All messages in this file are currently hardcoded in English.
    This violates L1-first principle. Must add translations for:
    - Twi (tw)
    - Ewe (ee)
    - Ga (ga)
    - Dagbani (dag)
"""
```

---

### Medium Priority Gaps

#### GAP-006: Adaptive Diagnostic Algorithm Needs Tuning
**Severity:** MEDIUM
**Affected:** Diagnostic assessment quality

**Issue:** AdaptiveDiagnosticEngine.get_next_node() uses basic prerequisite traversal
**Improvement:** Implement IRT-based adaptive algorithm (2PL or 3PL model)

---

#### GAP-007: No Curriculum Data Validation
**Severity:** MEDIUM
**Affected:** Diagnostic question generation

**Issue:** No checks for:
- Missing prerequisite relationships
- Orphaned nodes
- Circular dependencies

**Required:** Add curriculum validation on load

---

#### GAP-008: No Rate Limiting on WhatsApp Sends
**Severity:** MEDIUM
**Wolf/Aurino Compliance:** Risk of spam

**Issue:** No per-parent rate limiting
**Required:** Implement max N messages per day per parent

---

### Low Priority Gaps

#### GAP-009: No Parent Dashboard/Web Interface
**Severity:** LOW
**Affected:** Parent visibility into progress

**Current:** WhatsApp-only
**Future:** Web dashboard for progress tracking

---

#### GAP-010: No Teacher Dashboard
**Severity:** LOW
**Affected:** Teacher class management

**Current:** WhatsApp-only
**Future:** Web dashboard for class roster, gap heatmaps

---

### Testing Gaps

#### GAP-TEST-001: No E2E Tests Implemented
**Severity:** CRITICAL
**Status:** This document defines E2E test requirements, but none implemented yet

**Required:** Implement all TEST-* cases defined in this document

---

#### GAP-TEST-002: No Load Testing
**Severity:** HIGH
**Required:** Test with 1000 concurrent parent conversations

---

#### GAP-TEST-003: No Provider Failover Testing
**Severity:** MEDIUM
**Required:** Test switching between Twilio and Meta providers

---

## Summary

**Total User Flows Documented:** 12
**Total Data Flow Patterns:** 5
**Total E2E Tests Defined:** 50+
**Critical Bugs:** 3
**High Priority Gaps:** 5
**Medium Priority Gaps:** 3

**Next Steps:**
1. Fix critical bugs (BUG-001, BUG-002, BUG-003) per BUGFIX_REQUIREMENTS.md
2. Implement E2E test framework
3. Implement TEST-TEACHER-001, TEST-PARENT-001 (core flows)
4. Add L1 translations (GAP-005)
5. Integrate TTS/STT services (GAP-003, GAP-004)
