# WhatsApp E2E Flow Fix — Bugfix Design

## Overview

The WhatsApp end-to-end flow for exercise book upload → AI analysis → teacher notification is broken by five distinct bugs spanning two files. The fix strategy is minimal and surgical: correct constructor calls, fix media ID extraction logic, wire up the missing `process_analysis_result` call, add the missing `db` parameter to `WorkerService`, and optionally complete the scheduled message stub. No new modules or architectural changes are needed — all required downstream code (`ExerciseBookScanner.process_analysis_result`) already exists and is fully implemented.

## Glossary

- **Bug_Condition (C)**: The set of conditions that trigger crashes or silent failures in the WhatsApp webhook → worker pipeline
- **Property (P)**: The desired behavior — services instantiate correctly, media downloads succeed, and analysis results flow through to GapProfile updates and teacher notifications
- **Preservation**: Existing text message routing, Meta provider media downloads, Twilio adapter normalization, and factory singleton behavior must remain unchanged
- **`_handle_teacher_image`**: Function in `src/gapsense/webhooks/whatsapp.py` that processes exercise book images from teachers
- **`_handle_parent_voice`**: Function in `src/gapsense/webhooks/whatsapp.py` that processes voice messages from parents
- **`_handle_image_analyze`**: Method in `WorkerService` that runs AI analysis on exercise book images after SQS dequeue
- **`process_analysis_result`**: Method on `ExerciseBookScanner` that creates/updates GapProfiles and sends teacher summaries — already fully implemented but never called

## Bug Details

### Fault Condition

The bug manifests across three failure modes that collectively break the entire exercise book scanning feature:

1. **Constructor crashes** — `_handle_teacher_image` and `_handle_parent_voice` instantiate five services (`MediaService`, `WorkerService`, `GuardService`, `AsyncAIClient`, `PromptService`) with zero arguments, but each requires specific constructor parameters. This causes immediate `TypeError` on any image or voice webhook.

2. **Wrong media identifier** — The media ID extraction logic `image_content.get("id") or image_content.get("url")` always returns the Twilio message SID (which is stored in `"id"`) because it's truthy, preventing fallback to the actual media URL in `"url"`. This causes Twilio media downloads to fail.

3. **Severed pipeline** — `_handle_image_analyze` receives AI analysis JSON but stops after logging. It never calls `ExerciseBookScanner.process_analysis_result()`, so GapProfiles are never updated and teachers never receive results. Additionally, `WorkerService` lacks a `db` parameter needed to instantiate `ExerciseBookScanner`.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type WebhookEvent | WorkerTask
  OUTPUT: boolean

  // Bug 1: Constructor crashes on image/voice webhooks
  IF input.type == "webhook" AND input.message_type IN ["image", "voice"]:
    RETURN TRUE  // Always crashes due to missing constructor args

  // Bug 2: Twilio media ID extraction
  IF input.type == "webhook" AND input.provider == "twilio"
     AND input.message_type IN ["image", "voice"]
     AND input.content.get("id") IS NOT NONE:
    RETURN TRUE  // Message SID used instead of media URL

  // Bug 3: Missing analysis completion
  IF input.type == "worker_task" AND input.task_type == "image_analyze"
     AND input.ai_response IS NOT NONE AND input.ai_response.json_parsed IS NOT NONE:
    RETURN TRUE  // Analysis result never forwarded to process_analysis_result

  RETURN FALSE
END FUNCTION
```

### Examples

- **Constructor crash**: Teacher sends exercise book photo via Twilio → `MediaService()` called with no args → `TypeError: __init__() missing 1 required positional argument: 'settings'` → webhook returns 500
- **Wrong media ID**: Twilio delivers image with `{"id": "SM1234abcd", "url": "https://api.twilio.com/..."}` → code picks `"SM1234abcd"` as media_id → `download_media("SM1234abcd")` fails because it's a message SID, not a URL
- **Severed pipeline**: Worker dequeues `image_analyze` task → AI returns `{"gap_nodes": [...], "errors": [...]}` → worker logs "image_analyze_complete" → nothing else happens → teacher never gets results, GapProfile never created
- **Missing db**: Even if `_handle_image_analyze` called `process_analysis_result`, `WorkerService` has no `self._db` to pass to `ExerciseBookScanner` constructor

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Text messages from teachers must continue routing to `TeacherConversationPartner` without instantiating media/worker services
- Text messages from parents must continue routing to `FlowExecutor` for parent flow processing
- Meta WhatsApp image messages must continue using the Meta media ID (`image_content.get("id")`) for the two-step Meta download process
- Twilio webhook adapter must continue producing Meta-compatible format with `"object": "whatsapp_business_account"`
- `ExerciseBookScanner.handle_image_message` must continue to upload to S3, enqueue tasks, and send ack messages
- `WhatsAppClient.from_settings()` factory singleton must continue working unchanged
- Twilio provider API Key credential handling must remain unchanged

**Scope:**
All inputs that do NOT involve image/voice webhook processing or `image_analyze` worker tasks should be completely unaffected by this fix. This includes:
- Teacher and parent text message flows
- Status update webhooks
- Webhook verification (GET requests)
- All other worker task types (`tts_generate`, `voice_transcribe`)
- Meta provider media download path (uses `"id"` field correctly)

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **Constructor Signature Mismatches**: The `_handle_teacher_image` and `_handle_parent_voice` functions were written with bare constructor calls (`MediaService()`, `WorkerService()`, etc.) as if these were zero-arg factories. In reality, each service requires explicit dependency injection:
   - `MediaService(settings=settings)` — needs S3 bucket config
   - `AsyncAIClient(anthropic_api_key=settings.ANTHROPIC_API_KEY)` — needs API key
   - `PromptService(settings=settings)` — needs settings for prompt loading
   - `GuardService(ai_client=..., prompt_service=...)` — needs AI and prompt deps
   - `WorkerService(ai_client=..., media_service=..., guard_service=..., prompt_service=..., settings=..., db=...)` — needs all deps

2. **Twilio Media ID Extraction**: The `or` fallback pattern `image_content.get("id") or image_content.get("url")` is incorrect for Twilio. The Twilio adapter stores the message SID in `"id"` (always truthy) and the actual media URL in `"url"`. The code should prefer `"url"` when present (Twilio) and fall back to `"id"` (Meta).

3. **Incomplete Worker Handler**: `_handle_image_analyze` was implemented up to the AI call but the final step — forwarding results to `ExerciseBookScanner.process_analysis_result()` — was never wired up. The method exists and is fully implemented in `exercise_book_scanner.py` but is simply never called.

4. **Missing Database Session in WorkerService**: The `WorkerService.__init__` signature omits a `db: AsyncSession` parameter. Without it, the worker cannot instantiate `ExerciseBookScanner` (which requires `db` for GapProfile CRUD operations).

## Correctness Properties

Property 1: Fault Condition — Service Instantiation Succeeds

_For any_ webhook event where a teacher sends an image or a parent sends a voice message, the fixed `_handle_teacher_image` and `_handle_parent_voice` functions SHALL instantiate all five services (`MediaService`, `AsyncAIClient`, `PromptService`, `GuardService`, `WorkerService`) with their required constructor arguments, producing no `TypeError`.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 2: Fault Condition — Twilio Media URL Extraction

_For any_ Twilio webhook event containing an image or voice message where `content.get("url")` is a valid Twilio media URL, the fixed media ID extraction logic SHALL use the URL value (not the message SID from `content.get("id")`) so that `download_media` receives a downloadable URL.

**Validates: Requirements 2.7, 2.8**

Property 3: Fault Condition — Analysis Results Flow to GapProfile

_For any_ `image_analyze` worker task where the AI returns a valid JSON response, the fixed `_handle_image_analyze` SHALL call `ExerciseBookScanner.process_analysis_result()` with the correct `student_id`, `teacher_phone`, `analysis`, `country`, and `language` parameters, resulting in GapProfile creation/update and teacher notification.

**Validates: Requirements 2.9, 2.10**

Property 4: Preservation — Text Message Routing Unchanged

_For any_ webhook event that is a text message (not image or voice), the fixed code SHALL produce exactly the same routing behavior as the original code — teachers route to `TeacherConversationPartner`, parents route to `FlowExecutor` — with no new service instantiation or side effects.

**Validates: Requirements 3.1, 3.2**

Property 5: Preservation — Meta Provider Media Download Unchanged

_For any_ Meta WhatsApp webhook event containing an image or voice message, the fixed media ID extraction logic SHALL continue to use `content.get("id")` (the Meta media ID) for the two-step Meta download process, preserving existing Meta provider behavior.

**Validates: Requirements 3.3**

Property 6: Preservation — Non-Image Worker Tasks Unchanged

_For any_ worker task that is NOT `image_analyze` (e.g., `tts_generate`, `voice_transcribe`), the fixed `WorkerService` SHALL produce exactly the same behavior as the original, with no changes to routing or processing logic.

**Validates: Requirements 3.5, 3.6, 3.7**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `src/gapsense/webhooks/whatsapp.py`

**Function**: `_handle_teacher_image`

**Specific Changes**:
1. **Fix media ID extraction**: Change `media_id = image_content.get("id") or image_content.get("url")` to prefer `"url"` first: `media_id = image_content.get("url") or image_content.get("id")`. This ensures Twilio's media URL is used when present, while Meta's media ID (which has no `"url"` field) still works via fallback.
2. **Fix AsyncAIClient instantiation**: Pass `anthropic_api_key=settings.ANTHROPIC_API_KEY`
3. **Fix PromptService instantiation**: Pass `settings=settings`
4. **Fix GuardService instantiation**: Pass `ai_client=ai_client, prompt_service=prompt_service`
5. **Fix MediaService instantiation**: Pass `settings=settings`
6. **Fix WorkerService instantiation**: Pass `ai_client=ai_client, media_service=media_service, guard_service=guard_service, prompt_service=prompt_service, settings=settings, db=db`

**Function**: `_handle_parent_voice`

**Specific Changes**:
1. **Same media ID extraction fix** as `_handle_teacher_image`
2. **Same five constructor fixes** as `_handle_teacher_image`

---

**File**: `src/gapsense/services/worker_service.py`

**Function**: `__init__`

**Specific Changes**:
1. **Add `db` parameter**: Add `db: Any` parameter to constructor signature (after `settings`, before `max_concurrent`)
2. **Store as instance attribute**: Add `self._db = db`

**Function**: `_handle_image_analyze`

**Specific Changes**:
1. **Import ExerciseBookScanner**: Add `from gapsense.engagement.exercise_book_scanner import ExerciseBookScanner`
2. **After the existing `if response and response.json_parsed:` block**, instantiate `ExerciseBookScanner` with all required deps and call `process_analysis_result()`:
   ```python
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

**Function**: `_handle_scheduled_message` (lower priority)

**Specific Changes**:
1. **Replace stub comment** with actual WhatsApp delivery:
   ```python
   client = WhatsAppClient.from_settings()
   await client.send_text_message(
       to=payload.get("recipient_phone", ""),
       text=message,
   )
   ```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write unit tests that call `_handle_teacher_image`, `_handle_parent_voice`, and `_handle_image_analyze` with mocked dependencies and observe the failures. Run on UNFIXED code.

**Test Cases**:
1. **Constructor Crash Test**: Call `_handle_teacher_image` with a valid teacher, image content, and db session → expect `TypeError` from bare `MediaService()` call (will fail on unfixed code)
2. **Twilio Media ID Test**: Construct image_content with `{"id": "SM1234", "url": "https://api.twilio.com/media/..."}` and verify which value is passed to `download_media` → expect `"SM1234"` is incorrectly used (will fail on unfixed code)
3. **Missing process_analysis_result Test**: Mock AI client to return valid JSON, run `_handle_image_analyze` → verify `process_analysis_result` is never called (will fail on unfixed code)
4. **Missing db Parameter Test**: Attempt to instantiate `WorkerService` and access `self._db` → expect `AttributeError` (will fail on unfixed code)

**Expected Counterexamples**:
- `TypeError: MediaService.__init__() missing 1 required positional argument: 'settings'`
- `download_media` called with `"SM1234"` instead of `"https://api.twilio.com/media/..."`
- `process_analysis_result` call count is 0 after successful AI analysis
- `AttributeError: 'WorkerService' object has no attribute '_db'`

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed functions produce the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  IF input.type == "webhook":
    result := handle_teacher_image_fixed(input) OR handle_parent_voice_fixed(input)
    ASSERT no TypeError raised
    ASSERT download_media called with correct media URL (not message SID)
  IF input.type == "worker_task" AND input.task_type == "image_analyze":
    result := handle_image_analyze_fixed(input)
    ASSERT process_analysis_result called with correct args
    ASSERT GapProfile created or updated
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed code produces the same result as the original.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT handle_message_original(input) == handle_message_fixed(input)
  // Text messages, status updates, Meta media downloads, other worker tasks
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for text messages, Meta image messages, and other worker tasks, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Text Message Routing Preservation**: Verify teacher text messages route to `TeacherConversationPartner` and parent text messages route to `FlowExecutor` — unchanged by fix
2. **Meta Media ID Preservation**: Verify Meta image messages still use `content.get("id")` (Meta media ID) for download — the `url or id` reorder must not break Meta path
3. **Other Worker Task Preservation**: Verify `tts_generate` and `voice_transcribe` tasks process identically before and after fix
4. **Webhook Verification Preservation**: Verify GET verification endpoint is completely unaffected

### Unit Tests

- Verify each service constructor receives correct arguments in `_handle_teacher_image`
- Verify each service constructor receives correct arguments in `_handle_parent_voice`
- Verify media ID extraction returns URL for Twilio and ID for Meta
- Verify `WorkerService.__init__` accepts and stores `db` parameter
- Verify `_handle_image_analyze` calls `process_analysis_result` with correct arguments after successful AI response
- Verify `_handle_image_analyze` does NOT call `process_analysis_result` when AI response is None

### Property-Based Tests

- Generate random webhook payloads with varying `id`/`url` combinations and verify correct media identifier is selected based on provider
- Generate random AI analysis JSON responses and verify `process_analysis_result` is called with matching parameters
- Generate random text message webhooks and verify routing is unchanged (preservation)

### Integration Tests

- End-to-end: Twilio image webhook → service instantiation → media download → S3 upload → SQS enqueue → worker dequeue → AI analysis → `process_analysis_result` → GapProfile created → teacher notified
- End-to-end: Twilio voice webhook → service instantiation → media download → S3 upload → SQS enqueue
- Meta image webhook → verify Meta media ID path still works correctly
- Mixed traffic: interleave text and image messages, verify no cross-contamination
