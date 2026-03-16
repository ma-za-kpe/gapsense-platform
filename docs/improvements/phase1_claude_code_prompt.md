# GapSense Phase 1 — Claude Code Implementation Prompt
# Infrastructure Hardening + Prompt Surgery
# Estimated effort: 2-3 days | Risk: Very Low

---

## CONTEXT

You are implementing Phase 1 of a planned improvement to the GapSense AI diagnostic pipeline. GapSense is a WhatsApp-based educational diagnostic tool for African schools. Teachers photograph student exercise books; the system analyses them against a national curriculum graph and reports learning gaps.

The codebase uses:
- Python 3.11+, FastAPI, SQLAlchemy async ORM
- aiobotocore for SQS/S3
- structlog for logging
- Anthropic Claude API (claude-sonnet-4-6, claude-haiku-4-5-20251001)
- PostgreSQL via asyncpg
- Pydantic v2

Read the companion file `phase1_spec.md` before writing any code. It contains the full inventory of bugs and the exact contract for each fix.

---

## YOUR MISSION

Implement all changes described in `phase1_spec.md`. This phase has two parts:

### PART A — Infrastructure Bug Fixes (Fix E)

These are correctness bugs. They will cause data integrity failures at scale if not fixed.

**1. DB Session Concurrency**

File: `gapsense/worker/worker_service.py`

Problem: `self._db` is a single SQLAlchemy async session injected once into `WorkerService.__init__`. It is shared across all concurrent coroutines (up to 5 via semaphore). Async sessions are NOT safe for concurrent use.

Fix: Remove `db` from `WorkerService.__init__`. Instead, accept a `session_factory` (an `async_sessionmaker`). Inside `_process_message`, create a NEW session per task using `async with session_factory() as db:` and pass it down to the orchestrator. The session must be committed or rolled back and closed before the task exits.

Contract:
- `WorkerService.__init__` signature changes from `db: Any = None` to `session_factory: Any = None`
- Every handler that needed `self._db` now receives a fresh `db` scoped to that single task invocation
- No session leaks — all sessions closed even on exception
- Existing tests must be updated to pass a mock `session_factory`

**2. Idempotency Guard**

File: `gapsense/worker/worker_service.py`

Problem: If SQS redelivers a message (visibility timeout expired mid-processing), the pipeline runs twice on the same image. This causes duplicate `AIUsageLog` rows, duplicate WhatsApp messages to parents, and potentially contradictory gap profiles for the same student.

Fix: Before processing any task, write a deduplication record keyed on `(sqs_message_id, task_type)` to a new `ProcessingLedger` table. If the record already exists, log `task_duplicate_skipped` and delete the message without processing. If it does not exist, insert it and proceed.

The `ProcessingLedger` table schema is in `phase1_spec.md`. Write the Alembic migration for it.

Contract:
- Idempotency check happens BEFORE any DB queries, AI calls, or S3 downloads
- Uses `INSERT ... ON CONFLICT DO NOTHING` pattern — if insert returns 0 rows affected, skip
- Ledger records expire after 48 hours (add a cleanup job or rely on a TTL index)
- `message_id` field on `WorkerTask` must be non-nullable — validate at construction time

**3. Commit vs Flush on AIUsageLog**

File: `gapsense/engagement/image_analysis_orchestrator.py`

Problem: `_log_ai_cost` calls `await self._db.flush()` which sends SQL to the database but does NOT commit. If the session is closed or an exception occurs after flush, the AIUsageLog row is silently lost.

Fix: Replace `await self._db.flush()` with `await self._db.commit()`. The `_log_ai_cost` method already has a try/except — ensure the except branch calls `await self._db.rollback()` before logging the error.

Contract:
- Cost log commit is isolated — its failure must NOT abort the analysis pipeline
- After a failed cost log, the orchestrator continues to `_dispatch_results`
- Add a `logger.warning("ai_cost_log_failed_continuing")` so ops can monitor cost tracking gaps

**4. Stub Honesty**

File: `gapsense/worker/worker_service.py`

Problem: `_handle_tts_generate` and `_handle_voice_transcribe` log "complete" and return `None`. Enqueuing a TTS task "succeeds", the SQS message is deleted, and nothing happens. Silent data loss disguised as success.

Fix: Both stubs must raise `NotImplementedError` with a descriptive message:

```python
raise NotImplementedError(
    "tts_generate is not yet implemented. "
    "Enqueuing this task type will silently drop the request. "
    "Do not enqueue until TTS service is integrated."
)
```

This causes the task to fail, retry, and eventually land in the DLQ — which is visible. Ops will see DLQ depth rising if TTS tasks are being enqueued prematurely.

Additionally: remove `TASK_TYPES` frozenset from the module level OR use it in `_route_task` for validation. Currently it is defined and never referenced. If keeping it, wire it:

```python
if task.task_type not in TASK_TYPES:
    raise ValueError(f"Unknown task type: {task.task_type!r}. Valid: {TASK_TYPES}")
```

**5. Error Classification for Retry Logic**

File: `gapsense/worker/worker_service.py`

Problem: `_handle_failure` retries ALL exceptions up to `max_retries` times. A `ValueError("Student not found")` will retry 3 times with exponential backoff, potentially triggering 3 AI calls (if the error occurs after the AI call), before landing in DLQ. This wastes cost and latency.

Fix: Create two exception base classes:

```python
class RetryableError(Exception):
    """Transient error — retry with backoff. Network issues, DB timeouts."""
    pass

class PermanentError(Exception):
    """Permanent error — go straight to DLQ. Invalid payload, missing records."""
    pass
```

In `_handle_failure`:
- If `isinstance(error, PermanentError)`: skip retries, go straight to `_move_to_dlq`
- If `isinstance(error, RetryableError)` or unknown: use existing retry logic

In `_handle_image_analyze` (orchestrator):
- `ValueError(f"Student {student_id} not found")` → raise `PermanentError`
- `ValueError(f"Unknown task type")` → raise `PermanentError`
- Database connection errors → raise `RetryableError`
- S3 download errors → raise `RetryableError`
- AI client timeout → raise `RetryableError`

**6. Fix Delete-then-Requeue Race**

File: `gapsense/worker/worker_service.py`

Problem in `_handle_failure`:
```python
await self._delete_message(task.receipt_handle)  # message gone
# crash here = message lost forever
await self._requeue_with_backoff(new_task, visibility_timeout)
```

Fix: Reverse the order. Enqueue first, THEN delete. If enqueue fails, the original message remains in SQS and will be redelivered — which is correct behaviour.

```python
await self._requeue_with_backoff(new_task, visibility_timeout)  # enqueue first
await self._delete_message(task.receipt_handle)                  # then delete
```

**7. FIFO Queue Fix in `_requeue_with_backoff`**

File: `gapsense/worker/worker_service.py`

Problem: `enqueue()` adds `MessageGroupId` for FIFO queues but `_requeue_with_backoff` does not. Retries on a FIFO queue will throw `MissingParameter`.

Fix: Add the same FIFO detection to `_requeue_with_backoff`:

```python
if queue_url.endswith(".fifo"):
    send_kwargs["MessageGroupId"] = task.task_type
```

---

### PART B — Prompt Surgery (Fix C)

**8. Fix Model Strings**

File: `gapsense/prompts/prompt_library.json` (or wherever the library is stored)

Problem: `"model_target": "claude-sonnet-4-5-20250929"` is not a canonical API model string.

Fix:
- Replace all instances of `claude-sonnet-4-5` with `claude-sonnet-4-6`
- Replace all instances of `claude-haiku-4-5` with `claude-haiku-4-5-20251001`
- Verify against Anthropic API documentation

**9. Add Few-Shot Example to ANALYSIS-001**

File: The prompt library JSON / wherever ANALYSIS-001 system prompt is stored.

Add ONE concrete few-shot example to the ANALYSIS-001 system prompt, between the CURRICULUM CODE VALIDATION section and the OUTPUT FORMAT section. The example must:

- Use a Ghana curriculum scenario (B7-level mathematics)
- Show a student error in Pythagoras theorem
- Demonstrate the correct reasoning chain: error observed → error pattern identified → curriculum node matched → confidence assigned
- Show what an HONEST response looks like when the matching node is ambiguous (confidence < 0.70, gap_node_ids left empty, recommended_diagnostic_path populated instead)

The few-shot example is in `phase1_spec.md` under `FEW_SHOT_EXAMPLE_ANALYSIS_001`.

**10. Add `retrieval_metadata` to ANALYSIS-001 Output Schema**

File: Prompt library

Add two new fields to the ANALYSIS-001 `output_schema` and the JSON schema description in the system prompt:

```json
"retrieval_metadata": {
  "nodes_provided": "integer — how many nodes were in prerequisite_graph_json",
  "image_quality_note": "string|null — any note about image legibility issues"
},
"transcription_attempt": {
  "problems_visible": "integer — how many distinct problems the model could identify",
  "illegible_regions": ["string — description of any regions that could not be read"]
}
```

These fields prepare ANALYSIS-001 for the Phase 2 and Phase 3 upgrades without breaking the current schema.

**11. Strengthen Visual Analysis Rules**

File: Prompt library — ANALYSIS-001 system prompt

Add to the VISUAL ANALYSIS RULES section:

```
- Two-page spreads: Identify which page contains questions (typically left/printed)
  and which contains student work (typically right/handwritten).
  Analyse each separately before correlating.
- Multiple handwriting styles: If you detect more than one handwriting style,
  note this explicitly. Teacher annotations (ticks, crosses, scores) are NOT
  student work and must not be treated as student reasoning.
- Scattered layout: Students often answer questions wherever space exists,
  not adjacent to the question. Look for question numbers as anchors,
  not spatial proximity.
- If you cannot confidently read a specific region, set image_quality to
  "partially_readable" and describe the illegible region in illegible_regions.
  DO NOT guess. A partial diagnosis is more valuable than a confident wrong one.
```

---

## DELIVERABLES

After implementing all changes above:

1. All modified Python files with full implementations (no stubs, no TODOs)
2. Alembic migration for `ProcessingLedger` table
3. Updated `RetryableError` / `PermanentError` exception hierarchy in `gapsense/core/exceptions.py`
4. Updated ANALYSIS-001 prompt (full system prompt text, not a diff)
5. Updated prompt library JSON with corrected model strings
6. Unit tests for:
   - Idempotency guard (duplicate message → skip)
   - Error classification (PermanentError → no retry)
   - Delete-then-requeue order (enqueue before delete)
   - FIFO queue MessageGroupId on retry
7. A brief `PHASE1_CHANGES.md` documenting what changed and why, for handoff

---

## CONSTRAINTS

- Do not touch `ImageAnalysisOrchestrator._build_curriculum_graph` — that is Phase 2
- Do not touch the Mathpix integration — that is Phase 3
- Do not touch grade normalisation — that is Phase 4
- All changes must be backwards compatible — existing SQS messages in flight must still process
- Do not change the ANALYSIS-001 `output_schema` in a breaking way — add fields only
- Maintain structlog conventions throughout — no print statements, no bare logging

---

## DONE WHEN

- All 7 infrastructure fixes implemented and tested
- All 4 prompt changes implemented
- `ProcessingLedger` migration runs cleanly on a fresh DB
- Worker starts up without errors
- A TTS task enqueued reaches DLQ within one retry cycle (verifiable in tests)
- ANALYSIS-001 system prompt includes the few-shot example
- Model strings are canonical throughout
