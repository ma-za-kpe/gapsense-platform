# Requirements Document

## Introduction

Phase 1 of the GapSense improvement plan hardens the image analysis pipeline infrastructure and updates AI prompt content. GapSense is a WhatsApp-based educational diagnostic tool for African schools where teachers photograph student exercise books and the system analyses them against a national curriculum graph to report learning gaps. This phase addresses seven infrastructure bug fixes in the SQS-backed worker service and four prompt surgery items affecting model strings and the ANALYSIS-001 prompt. All changes are backwards compatible with in-flight SQS messages and do not touch curriculum graph building (Phase 2), OCR/Mathpix (Phase 3), or grade normalisation (Phase 4).

## Glossary

- **Worker_Service**: The SQS-backed background task processor (`WorkerService` class in `worker_service.py`) that polls SQS, routes tasks to handlers, and manages retries and dead-letter queue (DLQ) delivery.
- **Orchestrator**: The `ImageAnalysisOrchestrator` class that owns the six-step image analysis pipeline (load student context, fetch image, build curriculum graph, render prompt, call AI, dispatch results).
- **Session_Factory**: An `async_sessionmaker` instance that produces new `AsyncSession` objects on each call, replacing the shared `db` parameter pattern.
- **Processing_Ledger**: A new database table with a unique constraint on `(sqs_message_id, task_type)` used for SQS message deduplication (idempotency guard).
- **RetryableError**: A custom exception class indicating a transient failure that the Worker_Service should retry with exponential backoff.
- **PermanentError**: A custom exception class indicating a non-recoverable failure that the Worker_Service should route directly to the DLQ without retrying.
- **DLQ**: Dead-letter queue — an SQS queue where permanently failed messages are sent for manual inspection.
- **FIFO_Queue**: An SQS queue ending in `.fifo` that requires `MessageGroupId` on every `send_message` call.
- **ANALYSIS-001**: The primary AI prompt template for exercise book image analysis, defined in the prompt library JSON.
- **Prompt_Library**: The JSON file (`gapsense_prompt_library_v2.0_multicountry.json`) containing all AI prompt templates, model configurations, and country-specific settings.
- **AIUsageLog**: A database model that records AI API call costs, token usage, and latency for billing and monitoring.
- **Cost_Calculator**: The module (`cost_calculator.py`) that computes USD costs from token counts and model-specific pricing tables.

## Requirements

### Requirement 1: Session Factory Injection

**User Story:** As a platform engineer, I want the Worker_Service to accept a Session_Factory instead of a shared database session, so that each task gets an isolated database session and concurrent tasks cannot corrupt each other's transaction state.

#### Acceptance Criteria

1. THE Worker_Service constructor SHALL accept a `session_factory` parameter of type `async_sessionmaker` instead of the `db: Any = None` parameter.
2. WHEN the Worker_Service processes a message in `_process_message`, THE Worker_Service SHALL create a new `AsyncSession` from the Session_Factory for that task invocation.
3. THE Worker_Service SHALL pass the per-task session to the Orchestrator and to any other handler that requires database access.
4. WHEN a task completes or fails, THE Worker_Service SHALL close the per-task session.
5. THE `worker/main.py` entrypoint SHALL pass `AsyncSessionLocal` (the `async_sessionmaker` instance from `database.py`) as the `session_factory` argument when constructing the Worker_Service.
6. WHEN the Session_Factory parameter is `None`, THE Worker_Service SHALL still function for task types that do not require database access (e.g., `scheduled_message`).

### Requirement 2: SQS Message Idempotency Guard

**User Story:** As a platform engineer, I want the pipeline to deduplicate SQS messages, so that redelivered messages (e.g., after visibility timeout expiry) do not produce duplicate AIUsageLog rows, duplicate WhatsApp messages, or contradictory gap profiles.

#### Acceptance Criteria

1. THE system SHALL include a new `ProcessingLedger` database table with columns: `id` (UUID primary key), `sqs_message_id` (String, not null), `task_type` (String, not null), `status` (String, default `"processing"`), `started_at` (DateTime with timezone, server default NOW), and `completed_at` (DateTime with timezone, nullable).
2. THE Processing_Ledger table SHALL have a unique constraint on `(sqs_message_id, task_type)`.
3. WHEN the Worker_Service begins processing a message, THE Worker_Service SHALL attempt an INSERT into the Processing_Ledger with the SQS message ID and task type, using INSERT ON CONFLICT DO NOTHING semantics.
4. IF the INSERT returns zero rows affected (conflict detected), THEN THE Worker_Service SHALL skip processing, delete the SQS message, and log a warning with the duplicate `sqs_message_id`.
5. WHEN the task completes successfully, THE Worker_Service SHALL update the Processing_Ledger row to set `status` to `"completed"` and `completed_at` to the current timestamp.
6. IF the task fails permanently (moved to DLQ), THEN THE Worker_Service SHALL update the Processing_Ledger row to set `status` to `"failed"`.
7. THE system SHALL include an Alembic migration that creates the Processing_Ledger table.

### Requirement 3: AIUsageLog Commit Isolation Verification

**User Story:** As a platform engineer, I want to verify that the AIUsageLog commit in the Orchestrator is properly isolated, so that a cost-logging failure does not abort the image analysis pipeline.

#### Acceptance Criteria

1. THE Orchestrator `_log_ai_cost` method SHALL commit the AIUsageLog row in an isolated try/except block.
2. IF the commit fails, THEN THE Orchestrator SHALL rollback the session, log a warning via structlog, and continue the pipeline without re-raising the exception.
3. THE Orchestrator `_log_ai_cost` method SHALL NOT use `flush()` alone — the method SHALL use `commit()` to persist the AIUsageLog row.

### Requirement 4: Stub Handler Honesty

**User Story:** As a developer, I want unimplemented task handlers to raise `NotImplementedError` instead of silently returning `None`, so that stub invocations are immediately visible in logs and error tracking.

#### Acceptance Criteria

1. WHEN the `_handle_tts_generate` handler is invoked, THE Worker_Service SHALL raise `NotImplementedError` with a descriptive message indicating TTS generation is not yet implemented.
2. WHEN the `_handle_voice_transcribe` handler is invoked, THE Worker_Service SHALL raise `NotImplementedError` with a descriptive message indicating voice transcription is not yet implemented.
3. WHEN `_route_task` receives a `task_type` not present in the `TASK_TYPES` frozenset, THE Worker_Service SHALL raise `ValueError` with the unknown task type in the message.
4. THE `_route_task` method SHALL validate the incoming `task_type` against the `TASK_TYPES` frozenset before looking up the handler.

### Requirement 5: Error Classification Hierarchy

**User Story:** As a platform engineer, I want the Worker_Service to distinguish between retryable and permanent errors, so that permanent failures go directly to the DLQ without wasting retry attempts.

#### Acceptance Criteria

1. THE system SHALL define a `GapSenseError` base exception class in a new `gapsense/src/gapsense/core/exceptions.py` module.
2. THE system SHALL define a `RetryableError` exception class inheriting from `GapSenseError`, representing transient failures (e.g., network timeouts, rate limits, temporary service unavailability).
3. THE system SHALL define a `PermanentError` exception class inheriting from `GapSenseError`, representing non-recoverable failures (e.g., invalid payload, missing student record, schema validation errors).
4. WHEN `_handle_failure` receives a `PermanentError`, THE Worker_Service SHALL move the task directly to the DLQ without retrying, regardless of the current `retry_count`.
5. WHEN `_handle_failure` receives a `RetryableError` or any other exception, THE Worker_Service SHALL apply the existing retry logic with exponential backoff up to `max_retries`.

### Requirement 6: Safe Requeue Ordering (Delete-then-Requeue Race Fix)

**User Story:** As a platform engineer, I want the requeue operation to happen before the delete operation in `_handle_failure`, so that a crash between the two operations does not lose the message permanently.

#### Acceptance Criteria

1. WHEN `_handle_failure` decides to retry a task, THE Worker_Service SHALL enqueue the new message to SQS before deleting the original message.
2. WHEN `_handle_failure` decides to move a task to the DLQ, THE Worker_Service SHALL send the message to the DLQ before deleting the original message.
3. IF the requeue or DLQ send fails, THEN THE Worker_Service SHALL NOT delete the original message, allowing SQS to redeliver the original message after visibility timeout.

### Requirement 7: FIFO Queue Support in Requeue

**User Story:** As a platform engineer, I want `_requeue_with_backoff` to include `MessageGroupId` for FIFO queues, so that requeued messages are accepted by FIFO queues without errors.

#### Acceptance Criteria

1. WHEN the queue URL ends with `.fifo`, THE `_requeue_with_backoff` method SHALL include `MessageGroupId` set to the task's `task_type` in the `send_message` call.
2. WHEN the queue URL does not end with `.fifo`, THE `_requeue_with_backoff` method SHALL NOT include `MessageGroupId` in the `send_message` call.
3. WHEN the DLQ URL ends with `.fifo`, THE `_move_to_dlq` method SHALL include `MessageGroupId` set to the task's `task_type` in the `send_message` call.

### Requirement 8: AI Model String Update

**User Story:** As a platform engineer, I want all AI model identifier strings updated to the current model versions, so that the system uses the correct API endpoints and pricing.

#### Acceptance Criteria

1. THE `async_client.py` default model parameter SHALL use `claude-sonnet-4-6` instead of `claude-sonnet-4-5-20250929`.
2. THE `prompt_service.py` fallback model default SHALL use `claude-sonnet-4-6` instead of `claude-sonnet-4-5`.
3. THE `prompt_loader.py` fallback model default SHALL use `claude-sonnet-4-6` instead of `claude-sonnet-4-5`.
4. THE `models/prompts.py` `model_target` column default SHALL use `claude-sonnet-4-6` instead of `claude-sonnet-4-5`.
5. THE `models/diagnostics.py` `model_used` column comment SHALL reference `claude-sonnet-4-6` instead of `claude-sonnet-4-5`.
6. THE Cost_Calculator pricing table SHALL include entries for `claude-sonnet-4-6` and `claude-haiku-4-5-20251001`, with the `claude-haiku-4-5` key updated to `claude-haiku-4-5-20251001`.
7. THE Prompt_Library JSON files SHALL replace all occurrences of `claude-sonnet-4-5` with `claude-sonnet-4-6` in model fields.
8. THE Prompt_Library JSON metadata `model_target` SHALL use `claude-sonnet-4-6` instead of `claude-sonnet-4-5-20250929`.
9. THE Prompt_Library JSON metadata `fallback_model` SHALL remain `claude-haiku-4-5-20251001` (already correct).

### Requirement 9: ANALYSIS-001 Few-Shot Example

**User Story:** As a prompt engineer, I want a concrete few-shot example added to the ANALYSIS-001 prompt, so that the AI model produces more consistent reasoning chains and handles ambiguous curriculum nodes honestly.

#### Acceptance Criteria

1. THE ANALYSIS-001 system prompt SHALL include one complete few-shot example demonstrating a Ghana Basic 7 Pythagoras exercise book analysis.
2. THE few-shot example SHALL show the correct reasoning chain: visual observation, error identification, curriculum node mapping, and gap classification.
3. THE few-shot example SHALL demonstrate honest handling of an ambiguous curriculum node by stating uncertainty rather than guessing.
4. THE few-shot example SHALL be inserted between the CURRICULUM CODE VALIDATION section and the OUTPUT FORMAT section of the ANALYSIS-001 system prompt.

### Requirement 10: ANALYSIS-001 Output Schema Extension

**User Story:** As a platform engineer, I want `retrieval_metadata` and `transcription_attempt` fields added to the ANALYSIS-001 output schema, so that Phase 2 (retrieval-augmented curriculum lookup) and Phase 3 (OCR transcription) can consume these fields without a breaking schema change.

#### Acceptance Criteria

1. THE ANALYSIS-001 output schema SHALL include a `retrieval_metadata` field of type object, which is optional (nullable) and defaults to `null`.
2. THE ANALYSIS-001 output schema SHALL include a `transcription_attempt` field of type object, which is optional (nullable) and defaults to `null`.
3. THE schema changes SHALL be additive only — existing fields SHALL NOT be removed or have their types changed.
4. WHEN the AI model does not populate `retrieval_metadata` or `transcription_attempt`, THE Orchestrator SHALL treat missing or null values as valid.

### Requirement 11: Strengthened Visual Analysis Rules

**User Story:** As a prompt engineer, I want the ANALYSIS-001 prompt to include explicit rules for handling complex visual layouts, so that the AI model produces accurate analysis for two-page spreads, multiple handwriting styles, scattered layouts, and partially readable content.

#### Acceptance Criteria

1. THE ANALYSIS-001 system prompt SHALL include a rule instructing the AI to treat two-page spreads as a single continuous workspace and analyse both pages together.
2. THE ANALYSIS-001 system prompt SHALL include a rule instructing the AI to identify and separately attribute work from multiple distinct handwriting styles when detected.
3. THE ANALYSIS-001 system prompt SHALL include a rule instructing the AI to process scattered or non-linear layouts by grouping related work items before analysis.
4. THE ANALYSIS-001 system prompt SHALL include a rule instructing the AI to explicitly flag content that is partially readable and report a confidence level for any analysis derived from partially readable content.
