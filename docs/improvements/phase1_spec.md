# Phase 1 Spec — GapSense Infrastructure Hardening
# Reference document for Claude Code implementation

---

## ProcessingLedger Table Schema

```sql
CREATE TABLE processing_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sqs_message_id VARCHAR(255) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    student_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '48 hours',
    CONSTRAINT uq_message_task UNIQUE (sqs_message_id, task_type)
);

CREATE INDEX idx_processing_ledger_expires ON processing_ledger (expires_at);
```

Alembic migration file name: `{timestamp}_add_processing_ledger.py`

Idempotency insert pattern:
```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(ProcessingLedger).values(
    sqs_message_id=task.message_id,
    task_type=task.task_type,
    student_id=payload.get("student_id"),
).on_conflict_do_nothing(
    index_elements=["sqs_message_id", "task_type"]
)
result = await db.execute(stmt)
if result.rowcount == 0:
    logger.info("task_duplicate_skipped", message_id=task.message_id)
    await self._delete_message(task.receipt_handle)
    return
```

---

## Exception Hierarchy

File: `gapsense/core/exceptions.py`

```python
class GapSenseError(Exception):
    """Base exception for all GapSense errors."""
    pass

class RetryableError(GapSenseError):
    """
    Transient error. The operation may succeed if retried.
    Examples: network timeout, DB connection reset, S3 throttle,
              AI client rate limit, temporary service unavailability.
    """
    pass

class PermanentError(GapSenseError):
    """
    Permanent error. Retrying will not help.
    Examples: student not found, malformed payload, unknown task type,
              curriculum graph empty, invalid country code.
    The task should be sent directly to DLQ.
    """
    pass

class CurriculumDataError(PermanentError):
    """Curriculum graph missing, empty, or invalid for country/subject."""
    pass

class StudentNotFoundError(PermanentError):
    """Student ID does not exist in the database."""
    pass

class MediaDownloadError(RetryableError):
    """S3 download failed — transient."""
    pass

class AIClientError(RetryableError):
    """AI API call failed — transient."""
    pass
```

---

## Corrected Model Strings

| Old string | Correct string |
|---|---|
| `claude-sonnet-4-5-20250929` | `claude-sonnet-4-6` |
| `claude-sonnet-4-5` | `claude-sonnet-4-6` |
| `claude-haiku-4-5` | `claude-haiku-4-5-20251001` |

Apply to:
- Prompt library JSON (`model` fields per prompt)
- `model_target` and `fallback_model` in metadata
- `model_allocation` section
- Any hardcoded model strings in `gapsense/ai/` directory

---

## FEW_SHOT_EXAMPLE_ANALYSIS_001

Insert this block into ANALYSIS-001 system prompt between
CURRICULUM CODE VALIDATION and OUTPUT FORMAT sections:

```
## EXAMPLE ANALYSIS (Ghana — B7 Mathematics)

To illustrate the expected reasoning quality, here is a worked example:

Image description: Student exercise book, B7 class. Question asks to find
the hypotenuse of a right triangle with legs 6cm and 8cm.
Student wrote: "6+8=14, so x=14cm"

Correct reasoning chain:
1. EXTRACT: Problem = find hypotenuse. Student answer = 14cm.
2. IDENTIFY: Incorrect. Correct answer = √(36+64) = √100 = 10cm.
3. ANALYZE: Student added the legs instead of applying Pythagoras' theorem.
   Specific error: treated hypotenuse as sum of legs (a+b=c) rather than
   applying a²+b²=c². This is a conceptual error, not computational.
   The student may know how to square numbers (6²=36 attempted would show
   procedural knowledge) but does not know the theorem relationship.
4. MAP: This maps to the Pythagoras theorem node in the prerequisite graph.
   Check the provided graph for the exact code before assigning.
5. CONFIDENCE: 0.85 — clear error pattern, single problem, recommend
   one more question to confirm theorem understanding vs. squaring ability.

Example correct output for this case:
{
  "image_quality": "clear",
  "problems_extracted": [{
    "problem": "Find x where triangle has legs 6cm and 8cm",
    "student_answer": "14cm",
    "correct_answer": "10cm",
    "is_correct": false,
    "error_pattern": "additive_hypotenuse: student summed legs instead of applying Pythagorean relationship",
    "related_node": "[exact code from provided prerequisite graph]",
    "related_misconception": "Hypotenuse = sum of legs rather than √(a²+b²)",
    "confidence": 0.85
  }],
  "overall_pattern": "Conceptual gap in Pythagorean theorem — student applies additive rather than quadratic relationship",
  "gap_node_ids": ["[code from graph if found, else empty]"],
  "suspected_gaps": ["[prerequisite node for squaring numbers if found in graph]"],
  "recommended_diagnostic_path": "Ask student to calculate 6² and 8² separately to test squaring knowledge, then present theorem formula explicitly",
  "language_barrier_detected": false,
  "confidence": 0.85,
  "retrieval_metadata": {
    "nodes_provided": 100,
    "image_quality_note": null
  },
  "transcription_attempt": {
    "problems_visible": 1,
    "illegible_regions": []
  }
}

CRITICAL NOTE ON HONESTY: If the prerequisite graph provided does NOT
contain a Pythagoras theorem node, the correct response is:
  "gap_node_ids": [],
  "suspected_gaps": [],
  "recommended_diagnostic_path": "Manual review required — error pattern identified but no matching curriculum node found in provided graph"

Never invent a code. An empty array with a clear recommended_diagnostic_path
is more valuable than a fabricated code.
```

---

## Session Factory Pattern

How to refactor WorkerService to use session_factory:

```python
# Before (wrong):
class WorkerService:
    def __init__(self, ..., db: Any = None):
        self._db = db  # shared — UNSAFE for concurrent use

# After (correct):
class WorkerService:
    def __init__(self, ..., session_factory: Any = None):
        self._session_factory = session_factory  # factory, not session

async def _process_message(self, msg: dict) -> None:
    async with self._semaphore:
        # Each task gets its own session
        async with self._session_factory() as db:
            task = WorkerTask(...)
            try:
                await self._route_task(task, db=db)
                await db.commit()
                await self._delete_message(task.receipt_handle)
            except PermanentError as exc:
                await db.rollback()
                await self._move_to_dlq(task, exc)
                await self._delete_message(task.receipt_handle)
            except Exception as exc:
                await db.rollback()
                await self._handle_failure(task, exc)
```

Pass `db` as explicit argument to all handlers that need it.
ImageAnalysisOrchestrator receives `db` in its `run()` method, not `__init__`.

---

## Test Cases Required

### test_idempotency_guard
```
Given: Two identical SQS messages (same message_id, same task_type)
When:  First message processed successfully
Then:  Second message is detected as duplicate, skipped, deleted without processing
Assert: AI client called exactly once, not twice
Assert: logger.info called with "task_duplicate_skipped"
```

### test_permanent_error_no_retry
```
Given: A task payload with invalid student_id (UUID that doesn't exist)
When:  Task is processed
Then:  StudentNotFoundError raised → caught as PermanentError
Assert: _requeue_with_backoff NOT called
Assert: _move_to_dlq called exactly once
Assert: retry_count on DLQ message = 0 (first attempt, went straight to DLQ)
```

### test_enqueue_before_delete_on_failure
```
Given: A task fails with RetryableError on first attempt
When:  _handle_failure is called
Then:  _requeue_with_backoff called BEFORE _delete_message
Assert: If _requeue_with_backoff raises, _delete_message is NOT called
```

### test_fifo_requeue_has_message_group_id
```
Given: A FIFO queue URL (ends with .fifo)
When:  _requeue_with_backoff is called
Then:  send_message kwargs include MessageGroupId = task.task_type
```

### test_tts_stub_raises_not_implemented
```
Given: A tts_generate task
When:  _handle_tts_generate is called
Then:  NotImplementedError raised
Assert: Task enters retry → DLQ cycle (does not silently succeed)
```

### test_ai_usage_log_commit_isolated
```
Given: AI call succeeds, cost calculation succeeds, DB commit fails
When:  _log_ai_cost is called
Then:  Error is caught and logged
Assert: Orchestrator continues to _dispatch_results
Assert: No unhandled exception propagates
```
