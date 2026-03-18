# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** — WhatsApp E2E Flow Bugs
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate all three bug categories exist
  - **Scoped PBT Approach**: Scope properties to the concrete failing cases for each bug
  - **Bug 1 — Constructor Crashes**: Call `_handle_teacher_image` with a valid teacher, image content, settings, and db session. Assert no `TypeError` is raised. On unfixed code, `MediaService()` (and the other four services) are called with zero args → `TypeError`. Repeat for `_handle_parent_voice`.
  - **Bug 2 — Twilio Media ID Extraction**: Construct `image_content = {"id": "SM1234abcd", "url": "https://api.twilio.com/media/..."}`. Run the media ID extraction logic. Assert the result equals the URL, not the message SID. On unfixed code, `id or url` returns `"SM1234abcd"` because it's truthy.
  - **Bug 3 — Missing process_analysis_result**: Mock AI client to return valid JSON `{"gap_nodes": [...]}`. Run `_handle_image_analyze`. Assert `ExerciseBookScanner.process_analysis_result` is called with correct args (`student_id`, `teacher_phone`, `analysis`, `country`, `language`). On unfixed code, the call never happens.
  - **Bug 4 — Missing db param**: Instantiate `WorkerService` and assert `self._db` is accessible. On unfixed code, `AttributeError`.
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found:
    - `TypeError: MediaService.__init__() missing 1 required positional argument: 'settings'`
    - `download_media` called with `"SM1234abcd"` instead of `"https://api.twilio.com/media/..."`
    - `process_analysis_result` call count is 0 after successful AI analysis
    - `AttributeError: 'WorkerService' object has no attribute '_db'`
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** — Unchanged Text Routing, Meta Media ID, and Non-Image Worker Tasks
  - **IMPORTANT**: Follow observation-first methodology
  - **Step 1 — Observe on UNFIXED code**:
    - Observe: Teacher text messages route to `TeacherConversationPartner` — no media/worker services instantiated
    - Observe: Parent text messages route to `FlowExecutor` for parent flow processing
    - Observe: Meta image messages use `image_content.get("id")` (Meta media ID) for the two-step download — `url` field is absent in Meta payloads, so `url or id` still returns `id`
    - Observe: `tts_generate` and `voice_transcribe` worker tasks process identically through existing handlers
    - Observe: `WhatsAppClient.from_settings()` factory singleton returns configured provider
  - **Step 2 — Write property-based tests capturing observed behavior**:
    - Property: For all text message webhooks (teacher or parent), the message routes to the correct conversation handler and no `MediaService`/`WorkerService`/`GuardService`/`AsyncAIClient`/`PromptService` constructors are called
    - Property: For all Meta image webhooks where `image_content` has `"id"` but no `"url"`, the media ID extraction returns the Meta media ID value
    - Property: For all non-`image_analyze` worker tasks, the task dispatches to the correct handler without touching `ExerciseBookScanner`
  - **Step 3 — Verify tests PASS on UNFIXED code**
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6, 3.7_

- [x] 3. Fix WhatsApp E2E flow bugs

  - [x] 3.1 Fix constructor signatures in `_handle_teacher_image`
    - Instantiate `AsyncAIClient(anthropic_api_key=settings.ANTHROPIC_API_KEY)`
    - Instantiate `PromptService(settings=settings)`
    - Instantiate `GuardService(ai_client=ai_client, prompt_service=prompt_service)`
    - Instantiate `MediaService(settings=settings)`
    - Instantiate `WorkerService(ai_client=ai_client, media_service=media_service, guard_service=guard_service, prompt_service=prompt_service, settings=settings, db=db)`
    - Fix media ID extraction: change `image_content.get("id") or image_content.get("url")` to `image_content.get("url") or image_content.get("id")`
    - _Bug_Condition: isBugCondition(input) where input.type == "webhook" AND input.message_type IN ["image", "voice"]_
    - _Expected_Behavior: All five services instantiate without TypeError; Twilio media URL used for download_
    - _Preservation: Text message routing unchanged; Meta media ID path unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7_

  - [x] 3.2 Fix constructor signatures in `_handle_parent_voice`
    - Apply the same five constructor fixes as 3.1
    - Apply the same media ID extraction fix as 3.1
    - _Bug_Condition: isBugCondition(input) where input.type == "webhook" AND input.message_type == "voice"_
    - _Expected_Behavior: All five services instantiate without TypeError; Twilio media URL used for download_
    - _Preservation: Text message routing unchanged; Meta media ID path unchanged_
    - _Requirements: 2.6, 2.8_

  - [x] 3.3 Add `db` parameter to `WorkerService.__init__` and wire up `process_analysis_result`
    - Add `db` parameter to `WorkerService.__init__` signature (after `settings`)
    - Store as `self._db = db`
    - In `_handle_image_analyze`, after AI analysis completes with valid JSON, instantiate `ExerciseBookScanner` with `db=self._db, media_service=self._media_service, worker_service=self, guard_service=self._guard_service, ai_client=self._ai_client, prompt_service=self._prompt_service`
    - Call `await scanner.process_analysis_result(student_id=student_id, teacher_phone=payload.get("teacher_phone", ""), analysis=response.json_parsed, country=country, language=payload.get("language", "en"))`
    - _Bug_Condition: isBugCondition(input) where input.type == "worker_task" AND input.task_type == "image_analyze"_
    - _Expected_Behavior: process_analysis_result called → GapProfile created/updated → teacher notified_
    - _Preservation: Non-image_analyze worker tasks unchanged_
    - _Requirements: 2.9, 2.10_

  - [x] 3.4 (Optional) Complete scheduled message delivery stub
    - In `_handle_scheduled_message`, after `guard_result.passed`, send via `WhatsAppClient.from_settings().send_text_message(to=payload.get("recipient_phone", ""), text=message)`
    - _Requirements: 2.11_

  - [x] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** — WhatsApp E2E Flow Bugs Fixed
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior for all bug conditions
    - When this test passes, it confirms: constructors receive correct args, Twilio media URL is used, `process_analysis_result` is called, and `WorkerService` has `_db`
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms all bugs are fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

  - [x] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** — Unchanged Text Routing, Meta Media ID, and Non-Image Worker Tasks
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm text message routing, Meta media ID extraction, and non-image worker tasks are all unchanged

- [x] 4. Checkpoint — Ensure all tests pass
  - Run full test suite including exploration tests, preservation tests, and any existing unit tests
  - Verify no regressions in `tests/unit/test_whatsapp_client.py` or other existing test files
  - Ensure all tests pass, ask the user if questions arise
