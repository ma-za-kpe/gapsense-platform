# Implementation Plan: Phase 1 Infrastructure Hardening

## Overview

Harden the GapSense SQS worker pipeline with session isolation, idempotency, error classification, safe requeue ordering, and FIFO support. Update AI model strings and ANALYSIS-001 prompt content. Infrastructure changes first, then prompt changes, then tests.

## Tasks

- [x] 1. Create exception hierarchy module
  - [x] 1.1 Create `gapsense/src/gapsense/core/exceptions.py` with `GapSenseError`, `RetryableError`, `PermanentError`, `StudentNotFoundError`, `CurriculumDataError`, `MediaDownloadError`, `AIClientError`
    - Each class has a docstring describing its purpose
    - `RetryableError` and `PermanentError` inherit from `GapSenseError`
    - Concrete errors inherit from the appropriate parent
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 2. Create ProcessingLedger model and Alembic migration
  - [x] 2.1 Create `gapsense/src/gapsense/core/models/processing_ledger.py` with the `ProcessingLedger` SQLAlchemy model
    - Columns: `id` (UUID PK), `sqs_message_id` (String 255, not null), `task_type` (String 64, not null), `status` (String 20, default "processing"), `student_id` (UUID nullable), `started_at` (DateTime TZ, server default NOW), `completed_at` (DateTime TZ, nullable), `expires_at` (DateTime TZ, server default NOW + 48h)
    - UniqueConstraint on `(sqs_message_id, task_type)` named `uq_ledger_msg_task`
    - Index on `expires_at` named `idx_ledger_expires`
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Add `ProcessingLedger` export to `gapsense/src/gapsense/core/models/__init__.py`
    - Import from `.processing_ledger` and add to `__all__`
    - _Requirements: 2.1_

  - [x] 2.3 Create Alembic migration for the `processing_ledger` table
    - Follow existing naming convention: `YYYYMMDD_HHMM_{revision}_add_processing_ledger.py`
    - Create table with all columns, unique constraint, and index
    - Include downgrade that drops the table
    - _Requirements: 2.7_

- [x] 3. Refactor WorkerService — session factory injection
  - [x] 3.1 Change `WorkerService.__init__` to accept `session_factory` parameter instead of `db`
    - Replace `db: Any = None` with `session_factory: Any = None`
    - Store as `self._session_factory`
    - _Requirements: 1.1_

  - [x] 3.2 Refactor `_process_message` to create per-task sessions from the session factory
    - When `self._session_factory` is not None, create a new `AsyncSession` via `async with self._session_factory() as db:`
    - Pass the per-task session to the idempotency guard and task routing
    - When `self._session_factory` is None, route task without db (for `scheduled_message` etc.)
    - Ensure session is closed after task completes or fails
    - _Requirements: 1.2, 1.3, 1.4, 1.6_

  - [x] 3.3 Update `_handle_image_analyze` to use `self._session_factory` instead of hardcoded `AsyncSessionLocal` import
    - _Requirements: 1.3_

  - [x] 3.4 Update `gapsense/src/gapsense/worker/main.py` to pass `session_factory=AsyncSessionLocal` instead of `db=None`
    - Import `AsyncSessionLocal` from `gapsense.core.database`
    - _Requirements: 1.5_

- [x] 4. Implement SQS message idempotency guard in WorkerService
  - [x] 4.1 Add idempotency check at the start of `_process_message` using `INSERT ... ON CONFLICT DO NOTHING`
    - Use `sqlalchemy.dialects.postgresql.insert` for the upsert
    - If `result.rowcount == 0` (duplicate), log warning, delete SQS message, and return early
    - _Requirements: 2.3, 2.4_

  - [x] 4.2 Update ledger status to `"completed"` with `completed_at` timestamp on successful task completion
    - _Requirements: 2.5_

  - [x] 4.3 Update ledger status to `"failed"` when task is moved to DLQ
    - _Requirements: 2.6_

- [x] 5. Implement stub handler honesty and unknown task type rejection
  - [x] 5.1 Change `_handle_tts_generate` to raise `NotImplementedError` with descriptive message
    - _Requirements: 4.1_

  - [x] 5.2 Change `_handle_voice_transcribe` to raise `NotImplementedError` with descriptive message
    - _Requirements: 4.2_

  - [x] 5.3 Add `task_type` validation in `_route_task` against `TASK_TYPES` frozenset before handler lookup
    - Raise `ValueError` with the unknown task type in the message
    - _Requirements: 4.3, 4.4_

- [x] 6. Implement error classification routing in `_handle_failure`
  - [x] 6.1 Import `PermanentError` and `RetryableError` from `gapsense.core.exceptions`
    - _Requirements: 5.4, 5.5_

  - [x] 6.2 Rewrite `_handle_failure` to check `isinstance(error, PermanentError)` first
    - If PermanentError: move to DLQ immediately regardless of retry_count
    - If RetryableError or other: apply existing retry logic with exponential backoff up to max_retries
    - _Requirements: 5.4, 5.5_

- [x] 7. Fix safe requeue ordering (delete-then-requeue race)
  - [x] 7.1 Reorder `_handle_failure` retry path: call `_requeue_with_backoff` BEFORE `_delete_message`
    - _Requirements: 6.1_

  - [x] 7.2 Reorder `_handle_failure` DLQ path: call `_move_to_dlq` BEFORE `_delete_message`
    - _Requirements: 6.2_

  - [x] 7.3 Wrap requeue/DLQ send in try/except — if send fails, do NOT delete original message
    - Log the error and let SQS redeliver after visibility timeout
    - _Requirements: 6.3_

- [x] 8. Add FIFO queue support to requeue and DLQ methods
  - [x] 8.1 Update `_requeue_with_backoff` to include `MessageGroupId=task.task_type` when `queue_url.endswith(".fifo")`
    - _Requirements: 7.1, 7.2_

  - [x] 8.2 Update `_move_to_dlq` to include `MessageGroupId=task.task_type` when `dlq_url.endswith(".fifo")`
    - _Requirements: 7.3_

- [x] 9. Verify AIUsageLog commit isolation in Orchestrator
  - [x] 9.1 Verify `_log_ai_cost` in `gapsense/src/gapsense/services/image_analysis_orchestrator.py` uses `commit()` (not just `flush()`), has try/except with rollback, logs warning, and does not re-raise
    - Fix if any of these conditions are not met
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 10. Checkpoint — Ensure all infrastructure changes are consistent
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Update AI model strings across codebase
  - [x] 11.1 Update `gapsense/src/gapsense/ai/async_client.py` default model from `claude-sonnet-4-5-20250929` to `claude-sonnet-4-6`
    - _Requirements: 8.1_

  - [x] 11.2 Update `gapsense/src/gapsense/ai/prompt_service.py` fallback model from `claude-sonnet-4-5` to `claude-sonnet-4-6`
    - _Requirements: 8.2_

  - [x] 11.3 Update `gapsense/src/gapsense/ai/prompt_loader.py` fallback model from `claude-sonnet-4-5` to `claude-sonnet-4-6`
    - _Requirements: 8.3_

  - [x] 11.4 Update `gapsense/src/gapsense/core/models/prompts.py` `model_target` column default from `claude-sonnet-4-5` to `claude-sonnet-4-6`
    - _Requirements: 8.4_

  - [x] 11.5 Update `gapsense/src/gapsense/core/models/diagnostics.py` `model_used` column comment from `claude-sonnet-4-5` to `claude-sonnet-4-6`
    - _Requirements: 8.5_

  - [x] 11.6 Update `gapsense/src/gapsense/ai/cost_calculator.py` pricing table
    - Add `claude-sonnet-4-6` entry with input $3.00/MTok, output $15.00/MTok
    - Add `claude-haiku-4-5-20251001` entry with input $1.00/MTok, output $5.00/MTok
    - Keep existing `claude-haiku-4-5` key for backwards compatibility
    - _Requirements: 8.6_

- [x] 12. Update prompt library JSON model strings
  - [x] 12.1 Replace all `claude-sonnet-4-5` with `claude-sonnet-4-6` in `gapsense-data/prompts/gapsense_prompt_library_v2.0_multicountry.json`
    - Update metadata `model_target` from `claude-sonnet-4-5-20250929` to `claude-sonnet-4-6`
    - Verify `fallback_model` remains `claude-haiku-4-5-20251001`
    - _Requirements: 8.7, 8.8, 8.9_

  - [x] 12.2 Replace all `claude-sonnet-4-5` with `claude-sonnet-4-6` in `gapsense-data/prompts/gapsense_prompt_library.json`
    - _Requirements: 8.7_

  - [x] 12.3 Replace all `claude-sonnet-4-5` with `claude-sonnet-4-6` in `gapsense-data/prompts/gapsense_prompt_library_v1.1.json`
    - _Requirements: 8.7_

  - [x] 12.4 Replace all `claude-sonnet-4-5` with `claude-sonnet-4-6` in `gapsense/data/prompts/gapsense_prompt_library_v2.0_multicountry.json`
    - _Requirements: 8.7_

  - [x] 12.5 Replace all `claude-sonnet-4-5` with `claude-sonnet-4-6` in `gapsense/data/prompts/gapsense_prompt_library_v1.1.json`
    - _Requirements: 8.7_

- [x] 13. ANALYSIS-001 prompt surgery — few-shot example
  - [x] 13.1 Add a complete Ghana Basic 7 Pythagoras few-shot example to the ANALYSIS-001 system prompt in `gapsense-data/prompts/gapsense_prompt_library_v2.0_multicountry.json`
    - Insert between CURRICULUM CODE VALIDATION and OUTPUT FORMAT sections
    - Show correct reasoning chain: visual observation → error identification → curriculum node mapping → gap classification
    - Demonstrate honest handling of an ambiguous curriculum node (state uncertainty rather than guessing)
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 13.2 Copy the updated ANALYSIS-001 prompt to `gapsense/data/prompts/gapsense_prompt_library_v2.0_multicountry.json`
    - _Requirements: 9.1_

- [x] 14. ANALYSIS-001 prompt surgery — output schema extension and visual rules
  - [x] 14.1 Add `retrieval_metadata` and `transcription_attempt` optional fields to the ANALYSIS-001 output schema
    - Both fields: type object, nullable, default null
    - Additive only — do not remove or change existing fields
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 14.2 Add strengthened visual analysis rules to the ANALYSIS-001 system prompt
    - Rule for two-page spreads: treat as single continuous workspace, analyse both pages together
    - Rule for multiple handwriting styles: identify and separately attribute work from distinct styles
    - Rule for scattered/non-linear layouts: group related work items before analysis
    - Rule for partially readable content: flag and report confidence level for analysis derived from it
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 14.3 Copy the updated prompt to `gapsense/data/prompts/gapsense_prompt_library_v2.0_multicountry.json`
    - _Requirements: 10.1, 11.1_

- [x] 15. Checkpoint — Ensure all prompt and model string changes are consistent
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Write unit and property tests for infrastructure changes
  - [x] 16.1 Create `gapsense/tests/unit/test_exceptions.py` — unit tests for exception hierarchy
    - Verify `isinstance` relationships: `RetryableError` is `GapSenseError`, `PermanentError` is `GapSenseError`, concrete errors inherit correctly
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 16.2 Write property tests for session lifecycle isolation in `gapsense/tests/unit/test_worker_service_pbt.py`
    - **Property 1: Session lifecycle isolation**
    - Verify new AsyncSession created before routing and closed after, for random task types and outcomes
    - **Validates: Requirements 1.2, 1.4**

  - [x] 16.3 Write property tests for duplicate message idempotency
    - **Property 2: Duplicate message idempotency**
    - Insert same `(sqs_message_id, task_type)` twice; second attempt skips processing and deletes message
    - **Validates: Requirements 2.4**

  - [x] 16.4 Write property tests for ledger status reflects task outcome
    - **Property 3: Ledger status reflects task outcome**
    - Verify ledger row is `"completed"` with non-null `completed_at` on success, `"failed"` on DLQ
    - **Validates: Requirements 2.5, 2.6**

  - [x] 16.5 Write property tests for cost logging isolation
    - **Property 4: Cost logging isolation**
    - Verify pipeline continues when `_log_ai_cost` commit raises, session is rolled back
    - **Validates: Requirements 3.2**

  - [x] 16.6 Write property tests for stub handler honesty
    - **Property 5: Stub handlers signal non-implementation**
    - Random WorkerTask payloads for tts/voice handlers always raise `NotImplementedError`
    - **Validates: Requirements 4.1, 4.2**

  - [x] 16.7 Write property tests for unknown task type rejection
    - **Property 6: Unknown task type rejection**
    - Random strings not in `TASK_TYPES` always raise `ValueError`
    - **Validates: Requirements 4.3**

  - [x] 16.8 Write property tests for error classification routing
    - **Property 7: Error classification routing**
    - PermanentError → DLQ regardless of retry_count; RetryableError/other → retry when under max, DLQ when at max
    - **Validates: Requirements 5.4, 5.5**

  - [x] 16.9 Write property tests for send-before-delete ordering
    - **Property 8: Send-before-delete ordering**
    - Verify SQS send call occurs before delete call in both retry and DLQ paths
    - **Validates: Requirements 6.1, 6.2**

  - [x] 16.10 Write property tests for failed send preserves original message
    - **Property 9: Failed send preserves original message**
    - When requeue/DLQ send raises, verify delete is never called
    - **Validates: Requirements 6.3**

  - [x] 16.11 Write property tests for FIFO MessageGroupId conditional inclusion
    - **Property 10: FIFO MessageGroupId conditional inclusion**
    - Random queue URLs with/without `.fifo` suffix; verify `MessageGroupId` included iff `.fifo`
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [x] 16.12 Write property tests for new model pricing coverage
    - **Property 11: New model pricing coverage**
    - `calculate_cost` with `claude-sonnet-4-6` and `claude-haiku-4-5-20251001` and random non-negative token counts returns non-zero costs
    - **Validates: Requirements 8.6**

  - [x] 16.13 Write property tests for null optional fields are valid
    - **Property 13: Null optional fields are valid**
    - Random AI responses with missing/null `retrieval_metadata` and `transcription_attempt` processed without error
    - **Validates: Requirements 10.4**

  - [x] 16.14 Write unit tests for model string updates
    - Verify each of the 6 Python files contains `claude-sonnet-4-6` (not `claude-sonnet-4-5`)
    - Verify cost_calculator has entries for `claude-sonnet-4-6` and `claude-haiku-4-5-20251001`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 16.15 Write unit tests for prompt content changes
    - Verify ANALYSIS-001 contains the few-shot example text
    - Verify ANALYSIS-001 output schema includes `retrieval_metadata` and `transcription_attempt`
    - Verify ANALYSIS-001 contains the four visual analysis rules
    - _Requirements: 9.1, 10.1, 10.2, 11.1, 11.2, 11.3, 11.4_

- [x] 17. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Infrastructure changes (tasks 1–10) are ordered for safe incremental integration
- Prompt and model string changes (tasks 11–15) are independent of infrastructure
- Property tests validate universal correctness properties from the design document
- All 11 requirements are covered across the task list
