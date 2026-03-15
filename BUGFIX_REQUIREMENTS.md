# Bugfix Requirements Document

## Introduction

The end-to-end flow for exercise book upload → AI analysis → teacher notification is broken due to multiple critical bugs:

1. **Constructor signature mismatches** — Five services (`MediaService`, `WorkerService`, `GuardService`, `AsyncAIClient`, `PromptService`) are instantiated without their required arguments in both `_handle_teacher_image` and `_handle_parent_voice`, causing `TypeError` crashes on webhook processing

2. **Twilio media ID extraction bug** — The webhook adapter sets `image.id = message_sid` instead of the actual media URL, so `download_media` receives a message SID instead of the Twilio media URL, causing download failures

3. **Missing image analysis completion** — The `WorkerService._handle_image_analyze` method downloads images, sends them to AI, receives analysis results, then stops without calling `ExerciseBookScanner.process_analysis_result()`, so GapProfiles are never updated and teachers never receive analysis summaries

4. **Missing database session** — `WorkerService` lacks a database session parameter, so it cannot instantiate `ExerciseBookScanner` which requires database access to create/update GapProfiles

This document specifies the current defects, expected correct behavior, and regression-prevention requirements for unchanged functionality.

---

## Bug Analysis

### Current Behavior (Defect)

#### Constructor Signature Mismatches (Critical - Blocks Webhook Processing)

**1.1** WHEN a teacher sends an exercise book image via WhatsApp (Twilio or Meta) THEN the system crashes with `TypeError` because `MediaService()` is instantiated without the required `settings` argument in `_handle_teacher_image`

Location: `src/gapsense/webhooks/whatsapp.py:_handle_teacher_image`

**1.2** WHEN a teacher sends an exercise book image via WhatsApp THEN the system crashes with `TypeError` because `WorkerService()` is instantiated without the required `ai_client`, `media_service`, `guard_service`, `prompt_service`, and `settings` arguments in `_handle_teacher_image`

Location: `src/gapsense/webhooks/whatsapp.py:_handle_teacher_image`

**1.3** WHEN a teacher sends an exercise book image via WhatsApp THEN the system crashes with `TypeError` because `GuardService()` is instantiated without the required `ai_client` and `prompt_service` arguments in `_handle_teacher_image`

Location: `src/gapsense/webhooks/whatsapp.py:_handle_teacher_image`

**1.4** WHEN a teacher sends an exercise book image via WhatsApp THEN the system crashes with `TypeError` because `AsyncAIClient()` is instantiated without the required `anthropic_api_key` argument in `_handle_teacher_image`

Location: `src/gapsense/webhooks/whatsapp.py:_handle_teacher_image`

**1.5** WHEN a teacher sends an exercise book image via WhatsApp THEN the system crashes with `TypeError` because `PromptService()` is instantiated without the required `settings` argument in `_handle_teacher_image`

Location: `src/gapsense/webhooks/whatsapp.py:_handle_teacher_image`

**1.6** WHEN a parent sends a voice message via WhatsApp THEN the system crashes with the same `TypeError` constructor mismatches as 1.1-1.5 because `_handle_parent_voice` instantiates `MediaService()`, `WorkerService()`, `GuardService()`, `AsyncAIClient()`, and `PromptService()` without required arguments

Location: `src/gapsense/webhooks/whatsapp.py:_handle_parent_voice`

---

#### Media ID Extraction (Critical - Blocks Twilio Media Download)

**1.7** WHEN a teacher sends an exercise book image via Twilio WhatsApp THEN the system attempts to download media using the Twilio message SID (e.g., "SM1234567890abcdef") instead of the actual media URL because `image_content.get("id")` returns the message SID which is always truthy, preventing fallback to `image_content.get("url")` where the actual Twilio media URL is stored

Location: `src/gapsense/webhooks/whatsapp.py:_handle_teacher_image` (media_id extraction logic)

**1.8** WHEN a parent sends a voice message via Twilio WhatsApp THEN the system attempts to download media using the Twilio message SID instead of the actual media URL (same root cause as 1.7)

Location: `src/gapsense/webhooks/whatsapp.py:_handle_parent_voice` (media_id extraction logic)

---

#### Image Analysis Flow - Missing Completion Step (Critical - Breaks Exercise Book Feature)

**1.9** WHEN `WorkerService._handle_image_analyze` completes AI analysis of an exercise book image THEN it only logs the result and never calls `ExerciseBookScanner.process_analysis_result()`, causing:
   - ❌ GapProfile is never created or updated with detected learning gaps
   - ❌ Teacher never receives the analysis summary message via WhatsApp
   - ❌ The entire exercise book scanning feature is non-functional from the teacher's perspective

Current flow:
```
1. WhatsApp Message (Image) arrives
   └─> webhooks/whatsapp.py:_handle_teacher_image()
       ├─> Downloads image from WhatsApp API
       └─> Calls ExerciseBookScanner.handle_image_message()
           ├─> ✅ Uploads image to S3 (MediaService)
           ├─> ✅ Enqueues 'image_analyze' task to SQS
           └─> ✅ Sends "📸 Analyzing..." ack to teacher

2. WorkerService polls SQS
   └─> worker_service.py:_handle_image_analyze()
       ├─> ✅ Downloads image from S3
       ├─> ✅ Sends to AI with ANALYSIS-001 prompt
       ├─> ✅ Receives JSON: {gap_nodes, errors, patterns, focus_areas}
       └─> ❌ STOPS HERE - Just logs the result

3. ❌ MISSING LINK ❌
   Should call ExerciseBookScanner.process_analysis_result()
   ├─> Create/update GapProfile with detected gaps
   ├─> Build teacher summary message
   ├─> Pass through GuardService
   └─> Send summary to teacher via WhatsApp
```

Location: `src/gapsense/services/worker_service.py:217-250` (ends with logger.info, no callback)

**1.10** WHEN `WorkerService` is instantiated THEN it does not accept or store a database session parameter, so even if `_handle_image_analyze` called `process_analysis_result()`, it would fail because `ExerciseBookScanner` requires a database session to:
   - Query for existing GapProfile
   - Create or update GapProfile with detected gaps
   - Commit changes to the database

Location: `src/gapsense/services/worker_service.py:41-66` (constructor signature)

---

#### Scheduled Message Delivery (Non-Critical - Feature Not Used Yet)

**1.11** WHEN `WorkerService._handle_scheduled_message` processes a scheduled message task THEN it validates the message through `GuardService` but never sends it via WhatsApp, with only a comment `# WhatsApp delivery would happen here` at line 268

Location: `src/gapsense/services/worker_service.py:252-274`

Impact: Low priority since no code currently enqueues `scheduled_message` tasks

---

### Expected Behavior (Correct)

#### Constructor Fixes

**2.1** WHEN a teacher sends an exercise book image via WhatsApp THEN the system SHALL instantiate `MediaService` with the application `settings` object so S3 upload can proceed

**2.2** WHEN a teacher sends an exercise book image via WhatsApp THEN the system SHALL instantiate `WorkerService` with all required dependencies (`ai_client`, `media_service`, `guard_service`, `prompt_service`, `settings`, `db`) so SQS task enqueuing and processing can proceed

**2.3** WHEN a teacher sends an exercise book image via WhatsApp THEN the system SHALL instantiate `GuardService` with `ai_client` and `prompt_service` so compliance checking can proceed

**2.4** WHEN a teacher sends an exercise book image via WhatsApp THEN the system SHALL instantiate `AsyncAIClient` with the `anthropic_api_key` from settings so AI calls can proceed

**2.5** WHEN a teacher sends an exercise book image via WhatsApp THEN the system SHALL instantiate `PromptService` with the application `settings` object so prompt rendering can proceed

**2.6** WHEN a parent sends a voice message via WhatsApp THEN the system SHALL instantiate all services with their required constructor arguments (same fixes as 2.1-2.5)

---

#### Media ID Extraction Fixes

**2.7** WHEN a teacher sends an exercise book image via Twilio WhatsApp THEN the system SHALL use the Twilio media URL (from `image_content.get("url")`) for media download instead of the message SID, so the image bytes are correctly downloaded from Twilio's API

Implementation: Check if provider is Twilio before using `image_content.get("id")`, or always prefer `image_content.get("url")` if present, falling back to `image_content.get("id")` for Meta

**2.8** WHEN a parent sends a voice message via Twilio WhatsApp THEN the system SHALL use the Twilio media URL for audio download instead of the message SID (same fix as 2.7)

---

#### Image Analysis Completion Fixes

**2.9** WHEN `WorkerService._handle_image_analyze` receives AI analysis results THEN it SHALL:
   1. Instantiate `ExerciseBookScanner` with all required dependencies (db, media_service, worker_service, guard_service, ai_client, prompt_service)
   2. Call `scanner.process_analysis_result()` with:
      - `student_id` from task payload
      - `teacher_phone` from task payload
      - `analysis` JSON from AI response
      - `country` from task payload (default "GH")
      - `language` from task payload (default "en")
   3. Allow `process_analysis_result()` to:
      - Create or update GapProfile with detected gaps
      - Build teacher summary message
      - Validate through GuardService
      - Send summary to teacher via WhatsApp

**2.10** WHEN `WorkerService` is instantiated THEN it SHALL:
   1. Accept a `db: AsyncSession` parameter in the constructor
   2. Store it as `self._db` for use in async handlers
   3. Pass it to `ExerciseBookScanner` when instantiating in `_handle_image_analyze`

---

#### Scheduled Message Fix (Lower Priority)

**2.11** WHEN `WorkerService._handle_scheduled_message` processes a validated message THEN it SHALL send the message via `WhatsAppClient.from_settings().send_text_message()` to the recipient phone number from the task payload

---

### Unchanged Behavior (Regression Prevention)

**3.1** WHEN a teacher sends a text message via WhatsApp THEN the system SHALL CONTINUE TO route to `TeacherConversationPartner` without instantiating media/worker services

**3.2** WHEN a parent sends a text message via WhatsApp THEN the system SHALL CONTINUE TO route to `FlowExecutor` for parent flow processing

**3.3** WHEN a Meta WhatsApp webhook delivers an image message THEN the system SHALL CONTINUE TO use the Meta media ID (from `image_content.get("id")`) for the two-step Meta download process

**3.4** WHEN the Twilio webhook adapter normalizes an incoming message THEN the system SHALL CONTINUE TO produce Meta-compatible webhook format with `"object": "whatsapp_business_account"`

**3.5** WHEN `ExerciseBookScanner.handle_image_message` is called with valid dependencies THEN the system SHALL CONTINUE TO:
   - Upload image to S3 via MediaService
   - Enqueue `image_analyze` task to SQS with payload: `{s3_key, student_id, teacher_phone, country}`
   - Send "📸 Analyzing..." acknowledgment to teacher

**3.6** WHEN `WhatsAppClient.from_settings()` is called THEN the system SHALL CONTINUE TO return the configured provider via the factory singleton

**3.7** WHEN the factory creates a Twilio provider with API Key credentials THEN the system SHALL CONTINUE TO use `TWILIO_API_KEY_SID` as auth username and `TWILIO_API_KEY_SECRET` as auth token

---

## Required Code Changes Summary

### File: `src/gapsense/webhooks/whatsapp.py`

**Changes in `_handle_teacher_image`:**
1. Pass `settings` to `MediaService(settings=settings)`
2. Pass all dependencies to `WorkerService(...)`
3. Pass `ai_client`, `prompt_service` to `GuardService(...)`
4. Pass `anthropic_api_key` to `AsyncAIClient(anthropic_api_key=settings.ANTHROPIC_API_KEY)`
5. Pass `settings` to `PromptService(settings=settings)`
6. Fix media ID extraction: prefer `image_content.get("url")` for Twilio, fallback to `image_content.get("id")` for Meta

**Changes in `_handle_parent_voice`:**
1. Same constructor fixes as `_handle_teacher_image` (items 1-5 above)
2. Same media ID extraction fix (item 6 above)

### File: `src/gapsense/services/worker_service.py`

**Changes in `__init__` (constructor):**
1. Add `db: AsyncSession` parameter
2. Store as `self._db = db`

**Changes in `_handle_image_analyze`:**
1. Import `ExerciseBookScanner` from `gapsense.engagement.exercise_book_scanner`
2. After AI analysis completes (line 250), add:
   ```python
   if response and response.json_parsed:
       scanner = ExerciseBookScanner(
           db=self._db,
           media_service=self._media_service,
           worker_service=self,
           guard_service=self._guard_service,
           ai_client=self._ai_client,
           prompt_service=self._prompt_service,
       )

       await scanner.process_analysis_result(
           student_id=student_id,
           teacher_phone=payload.get("teacher_phone", ""),
           analysis=response.json_parsed,
           country=country,
           language=payload.get("language", "en"),
       )
   ```

**Changes in `_handle_scheduled_message` (optional - lower priority):**
1. After `guard_result.passed` check, replace comment with:
   ```python
   from gapsense.engagement.whatsapp_client import WhatsAppClient

   client = WhatsAppClient.from_settings()
   await client.send_text_message(
       to=payload.get("recipient_phone", ""),
       text=message,
   )
   ```

---

## Testing Requirements

### Unit Tests
- Verify `WorkerService` accepts `db` parameter
- Verify `_handle_image_analyze` calls `process_analysis_result` with correct arguments
- Mock `ExerciseBookScanner.process_analysis_result` and verify it's called

### Integration Tests
1. Send Twilio WhatsApp image message → verify image downloads correctly
2. Send Meta WhatsApp image message → verify image downloads correctly
3. Process `image_analyze` task → verify GapProfile created/updated
4. Process `image_analyze` task → verify teacher receives WhatsApp summary
5. Send Twilio WhatsApp voice message → verify audio downloads correctly

### End-to-End Test
1. Teacher sends exercise book image via WhatsApp
2. Verify image uploaded to S3
3. Verify task enqueued to SQS
4. Verify teacher receives "📸 Analyzing..." ack
5. Worker processes task
6. Verify AI analysis completes
7. Verify GapProfile created in database
8. Verify teacher receives analysis summary via WhatsApp

---

## Acceptance Criteria

✅ Teachers can send exercise book images via WhatsApp (Twilio or Meta) without crashes

✅ Images are downloaded from WhatsApp, uploaded to S3, and analyzed by AI

✅ GapProfiles are created or updated with detected learning gaps

✅ Teachers receive analysis summary messages after processing completes

✅ Parent voice messages can be uploaded and processed without crashes

✅ All existing text message flows continue to work (no regressions)

✅ Meta and Twilio provider-specific logic remains correct
