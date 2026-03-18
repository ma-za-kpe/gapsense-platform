# Implementation Plan: MVP Core Services

## Overview

Incremental implementation of the 13 foundational services following the critical dependency chain: Config → AI Client → Schema Migration → Prompt Service → Curriculum Loader → Guard Service → Media Service → Worker Service → Feature integrations → App Startup. Each task builds on previous steps, with property-based tests (Hypothesis) validating correctness properties from the design document.

## Tasks

- [x] 1. Configuration update for multi-country data paths (Req 3)
  - [x] 1.1 Add v2.0 data path properties to Settings
    - Add `prompt_library_path`, `curricula_base_path`, `cultural_context_path`, `languages_base_path` computed properties to `gapsense/src/gapsense/config.py`
    - Retain `prerequisite_graph_path` for backward compatibility
    - Update `validate_data_path` validator to check for `curricula/` (plural) instead of `curriculum/` (singular)
    - Raise `ValueError` with descriptive message when `curricula/` directory does not exist
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 1.2 Write unit tests for Settings v2.0 paths
    - Test all four new path properties resolve correctly relative to `GAPSENSE_DATA_PATH`
    - Test validator raises `ValueError` when `curricula/` directory is missing
    - Test backward compatibility of `prerequisite_graph_path`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 2. Async AI Client with retry and multimodal support (Req 1)
  - [x] 2.1 Implement AsyncAIClient class
    - Create `gapsense/src/gapsense/ai/client.py` with `AsyncAIClient`, `ImageContent`, and `AIResponse` dataclasses
    - Use shared `AsyncAnthropic` client instance with connection pooling
    - Implement `async generate()` with `asyncio.Semaphore(max_concurrent)` for concurrency control
    - Implement `asyncio.wait_for(timeout_seconds)` for per-request timeouts (default 30s)
    - Implement exponential backoff retry (1s, 2s, 4s) on transient errors (429, 500, 502, 503, 529), max 3 retries
    - Implement Grok fallback when Anthropic fails after all retries
    - Return `None` when all providers fail
    - Support `json_mode` parameter for structured JSON responses
    - Support `images` parameter for multimodal (image + text) content blocks
    - Log provider, prompt_id, latency_ms, token usage, and success/failure for every call
    - Implement `async close()` to release HTTP connection pools
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_

  - [x] 2.2 Write property test: AI Client Retry Count (Property 1)
    - **Property 1: AI Client Retry Count**
    - For any sequence of transient errors, verify total attempts = `min(N+1, 4)` when N < 4, exactly 4 when N >= 4
    - Mock Anthropic API to return configurable transient error sequences
    - Use `@settings(max_examples=100)`
    - **Validates: Requirements 1.3**

  - [x] 2.3 Write property test: Provider Cascade Fallback (Property 2)
    - **Property 2: Provider Cascade Fallback**
    - For any AI request, when Anthropic fails after retries, verify Grok is attempted; when both fail, verify `None` returned
    - Result is non-None iff at least one provider succeeded
    - **Validates: Requirements 1.7, 1.8**

  - [x] 2.4 Write property test: AI Concurrency Limit (Property 3)
    - **Property 3: AI Concurrency Limit**
    - For any batch of N simultaneous requests exceeding the concurrency limit, verify in-flight count never exceeds semaphore limit
    - **Validates: Requirements 1.9**

  - [x] 2.5 Write property test: AI Call Logging Completeness (Property 4)
    - **Property 4: AI Call Logging Completeness**
    - For any AI call (success or failure), verify log record contains provider, prompt_id, latency_ms, token usage, success/failure
    - **Validates: Requirements 1.10**

- [x] 3. Checkpoint — Config and AI Client foundation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Database schema migration for multi-country support (Req 4)
  - [x] 4.1 Create Alembic migration script
    - Create migration in `gapsense/src/gapsense/alembic/versions/` that:
    - Adds `country` (String(5), default "GH"), `subject` (String(50), default "mathematics"), `level` (String(20), default "primary") columns to `curriculum_nodes` table
    - Adds composite index on `(country, subject, level, grade)`
    - Makes `session_id` nullable on `gap_profiles` table
    - Adds `source` (String(30), default "diagnostic") column to `gap_profiles` table
    - Adds check constraint: when `session_id IS NULL`, `source` must be non-empty and not "diagnostic"
    - Migration must be reversible (downgrade support)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_

  - [x] 4.2 Update SQLAlchemy models
    - Update `CurriculumNode` model with `country`, `subject`, `level` mapped columns and composite index
    - Update `GapProfile` model with nullable `session_id` and `source` column with default "diagnostic"
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [x] 4.3 Write property test: GapProfile Source Constraint (Property 18)
    - **Property 18: GapProfile Source Constraint**
    - For any GapProfile with `session_id=None`, verify `source` is non-empty and not "diagnostic"
    - Use Hypothesis strategies to generate GapProfile instances with various session_id/source combinations
    - **Validates: Requirements 4.8**

- [x] 5. Multi-country Prompt Service with template resolution (Req 2)
  - [x] 5.1 Implement PromptService class
    - Create `gapsense/src/gapsense/ai/prompt_service.py` with `PromptService` and `RenderedPrompt` dataclass
    - Load prompts from v2.0 library at `prompt_library_path`
    - Load `CountryConfig` from prompt library `country_config` section and `curricula/{country}/country_config.json`
    - Load `CulturalContext` from `cultural_context/{country}.json`
    - Load `L1LanguageContext` from `languages/{country}/{language}.json`
    - Implement `render_prompt()` with template resolution order: raw prompt → country placeholders → L1 injection → extra_context → validate zero unresolved placeholders
    - Raise `ValueError` with supported options for unsupported country or language
    - Implement `get_supported_countries()`, `get_supported_languages()`, `list_prompts()`
    - All 13 prompts accessible: DIAG-001 through GUARD-001
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

  - [x] 5.2 Write property test: Prompt Template Resolution Round-Trip (Property 5)
    - **Property 5: Prompt Template Resolution Round-Trip**
    - For any valid prompt template and any supported country config (with optional language), verify rendered output has zero unresolved `{{...}}` placeholders
    - Use Hypothesis strategies for `CountryConfig` and prompt template combinations
    - **Validates: Requirements 2.5, 2.6, 2.10**

  - [x] 5.3 Write property test: Unsupported Country/Language Rejection (Property 6)
    - **Property 6: Unsupported Country/Language Rejection**
    - For any country not in supported list or language not in country's supported list, verify `ValueError` raised with valid options
    - **Validates: Requirements 2.7, 2.8**

- [x] 6. Multi-country Curriculum Loader (Req 5)
  - [x] 6.1 Implement CurriculumLoader class
    - Create `gapsense/src/gapsense/services/curriculum_loader.py` with `CurriculumLoader`, `LoadSummary`, `CountrySummary` dataclasses
    - Walk `curricula/{country}/{level}/{subject}/` directory tree to discover JSON files
    - Parse object-based JSON (`{"B2.1.1.1": {...}}`) format
    - Populate `country`, `subject`, `level` on each `CurriculumNode` from directory path
    - Read `country_config.json` per country for active levels and subjects
    - Implement upsert logic: update existing nodes by code+country, create new ones
    - Log and skip invalid JSON files, continue loading remaining files
    - Load prerequisite relationships, misconceptions, indicators, cascade paths when present
    - Return `LoadSummary` with totals and per-country/subject breakdown
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [x] 6.2 Write property test: Curriculum Loader Path-to-Column Mapping (Property 7)
    - **Property 7: Curriculum Loader Path-to-Column Mapping**
    - For any file at `curricula/{country}/{level}/{subject}/file.json`, verify loaded CurriculumNodes have correct `country`, `level`, `subject` from path
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [x] 6.3 Write property test: Curriculum Loader Idempotence (Property 8)
    - **Property 8: Curriculum Loader Idempotence**
    - For any set of curriculum files, loading twice produces same row count as loading once; second load yields zero new nodes
    - **Validates: Requirements 5.5**

  - [x] 6.4 Write property test: Curriculum Loader Error Resilience (Property 9)
    - **Property 9: Curriculum Loader Error Resilience**
    - For any mix of valid and invalid JSON files, verify all valid files processed and `total_errors` equals number of invalid files
    - **Validates: Requirements 5.6, 5.7**

- [x] 7. Checkpoint — Data layer and prompt service
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. GUARD-001 Compliance Gate (Req 6)
  - [x] 8.1 Implement GuardService class
    - Create `gapsense/src/gapsense/services/guard_service.py` with `GuardService` and `GuardResult` dataclass
    - Accept `AsyncAIClient` and `PromptService` as dependencies
    - Implement `async check()` that sends message + student context + language to AI_Client using GUARD-001 prompt
    - Parse structured response for pass/fail and violation list
    - Return original message unchanged on pass; return violations and block on fail
    - Implement fail-closed: when AI client returns `None`, block message and log `compliance-check-unavailable`
    - Log prompt_id, pass/fail, latency_ms, and violation categories for every check
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [x] 8.2 Write property test: Guard Service Pass-Through Invariant (Property 10)
    - **Property 10: Guard Service Pass-Through Invariant**
    - For any message that passes GUARD-001, verify `original_message` equals input, `passed=True`, and `violations` is empty
    - **Validates: Requirements 6.3**

  - [x] 8.3 Write property test: Guard Service Fail-Closed (Property 11)
    - **Property 11: Guard Service Fail-Closed**
    - For any message when AI client returns `None`, verify `passed=False` and `ai_available=False`
    - **Validates: Requirements 6.5**

  - [x] 8.4 Write property test: Guard Service Logging Completeness (Property 12)
    - **Property 12: Guard Service Logging Completeness**
    - For any guard check (pass or fail), verify log contains prompt_id, pass/fail, latency_ms, violation categories
    - **Validates: Requirements 6.7**

- [x] 9. S3 Media Service (Req 7)
  - [x] 9.1 Implement MediaService class
    - Create `gapsense/src/gapsense/services/media_service.py` with `MediaService`
    - Implement `async upload()` with S3 key format `{country}/{student_id}/{media_type}/{timestamp}_{filename}`
    - Validate content types: images (`image/jpeg`, `image/png`, `image/webp`), audio (`audio/ogg`, `audio/mpeg`, `audio/wav`, `audio/mp4`)
    - Enforce size limits: 10 MB images, 25 MB audio
    - Implement retry (up to 2 retries with exponential backoff) on S3 upload failure
    - Implement `generate_download_url()` with configurable expiry (default 1 hour)
    - Implement `generate_upload_url()` with configurable expiry (default 15 minutes)
    - Implement `async download()` for retrieving files from S3
    - Use `S3_ENDPOINT_URL` env var for LocalStack in dev, default AWS endpoint in production
    - Implement `async verify_connectivity()` for health checks
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [x] 9.2 Write property test: Media Upload Validation (Property 13)
    - **Property 13: Media Upload Validation**
    - For any upload, verify rejection of invalid content types and files exceeding size limits
    - Use Hypothesis strategies for content types and file sizes
    - **Validates: Requirements 7.4, 7.5, 7.8**

  - [x] 9.3 Write property test: S3 Key Format (Property 14)
    - **Property 14: S3 Key Format**
    - For any upload params (country, student_id, media_type, filename), verify S3 key matches `{country}/{student_id}/{media_type}/{timestamp}_{filename}`
    - **Validates: Requirements 7.1**

  - [x] 9.4 Write property test: Media Upload Retry (Property 15)
    - **Property 15: Media Upload Retry**
    - For any sequence of S3 failures, verify at most 3 total attempts (1 initial + 2 retries)
    - **Validates: Requirements 7.6**

- [x] 10. Worker Service for background processing (Req 8)
  - [x] 10.1 Implement WorkerService class
    - Create `gapsense/src/gapsense/services/worker_service.py` with `WorkerService` and `WorkerTask` dataclass
    - Accept `AsyncAIClient`, `MediaService`, `GuardService`, `PromptService`, `Settings` as dependencies
    - Implement long-polling SQS consumer with `async start()` and `async stop()`
    - Implement `async enqueue()` to send tasks to SQS queue
    - Implement task routing for: `tts_generate`, `image_analyze`, `scheduled_message`, `voice_transcribe`
    - `tts_generate`: invoke TTS_Service, upload result to S3 via MediaService
    - `image_analyze`: download image from S3, send to AI_Client with ANALYSIS-001 prompt, store results
    - `scheduled_message`: pass through GuardService before WhatsApp delivery
    - `voice_transcribe`: download audio from S3, transcribe via STT_Service, store transcript
    - Re-enqueue failed tasks with incremented `retry_count` and exponential backoff visibility timeout
    - Move tasks exceeding 3 retries to dead-letter queue with failure logging
    - Use `asyncio.Semaphore` for concurrent task processing (default limit 5)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

  - [x] 10.2 Write property test: Worker Task Retry Lifecycle (Property 16)
    - **Property 16: Worker Task Retry Lifecycle**
    - For any failed task with `retry_count < max_retries`, verify re-enqueue with `retry_count + 1` and backoff; for `retry_count >= max_retries`, verify DLQ move
    - **Validates: Requirements 8.7, 8.8**

  - [x] 10.3 Write property test: Worker Concurrency Limit (Property 17)
    - **Property 17: Worker Concurrency Limit**
    - For any batch exceeding concurrency limit, verify concurrent processing count never exceeds the limit
    - **Validates: Requirements 8.9**

- [x] 11. Checkpoint — Service layer complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Exercise Book Scanner integration (Req 9)
  - [x] 12.1 Implement exercise book scan flow
    - Add exercise book scan handler to FlowExecutor that identifies image messages from teachers
    - Upload image to S3 via MediaService, enqueue `image_analyze` task to WorkerService
    - Implement `image_analyze` handler in WorkerService: download image, send to AI_Client with ANALYSIS-001 prompt (multimodal), parse structured JSON response (errors, patterns, gap node codes, focus areas)
    - Create/update GapProfile with `source="exercise_book"` from analysis results
    - Send teacher summary via WhatsApp after GuardService validation
    - Handle image quality issues: if AI returns unreadable indicator, ask teacher to retake photo
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [x] 13. Parent Activity Delivery with TTS voice notes (Req 10)
  - [x] 13.1 Implement parent activity delivery flow
    - Add activity generation to FlowExecutor using PARENT-001 prompt (personalized from GapProfile + parent language)
    - Generate 3-minute activity using ACT-001 prompt with Cultural_Context household materials
    - Pass activity text through GuardService (GUARD-001) before delivery
    - Enqueue `tts_generate` task to convert activity to L1 voice note
    - Implement `tts_generate` handler in WorkerService: invoke TTS_Service, upload audio to S3, send voice note via WhatsApp
    - Send text version alongside voice note in parent's preferred language
    - Schedule delivery at configured optimal time (default 6:30 PM local) based on country timezone
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 14. Teacher Conversation Partner (Req 11)
  - [x] 14.1 Implement teacher conversation flow
    - Add teacher conversation handler to FlowExecutor that routes teacher text messages
    - Use TEACHER-001 prompt to analyze teacher question with class aggregate gap data
    - Use TEACHER-002 prompt to generate pedagogical response with actionable strategies
    - Use TEACHER-003 prompt to format response for WhatsApp delivery
    - Retrieve individual student GapProfile when teacher asks about specific student
    - Aggregate GapProfile data across class when teacher asks about class-wide patterns
    - Maintain conversation history for multi-turn teacher dialogue
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

- [x] 15. Voice Micro-Coaching for parents (Req 12)
  - [x] 15.1 Implement voice micro-coaching flow
    - Add voice message handler to FlowExecutor that enqueues `voice_transcribe` task for parent voice messages
    - Implement `voice_transcribe` handler in WorkerService: download audio from S3, transcribe via STT_Service, store transcript
    - Send transcript to AI_Client with ANALYSIS-002 prompt for coaching analysis
    - Parse structured response: engagement assessment, coaching feedback, follow-up activity
    - Pass coaching response through GuardService (GUARD-001) before delivery
    - Send coaching feedback to parent in preferred language via WhatsApp
    - Update ParentInteraction record with transcript, sentiment score, coaching response
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 16. Checkpoint — Feature integrations complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Application Startup and service initialization (Req 13)
  - [x] 17.1 Update lifespan handler and health check
    - Update `gapsense/src/gapsense/main.py` lifespan handler to:
    - Initialize `AsyncAIClient` as shared singleton with connection pooling
    - Initialize `PromptService` and load all v2.0 prompts, country configs, cultural contexts, language files
    - Initialize `MediaService` and verify S3 connectivity
    - Initialize `GuardService` with AI client and prompt service dependencies
    - Verify database connectivity
    - Store all services in `app.state` for dependency injection
    - On shutdown: close AI client connection pool, release all resources
    - Refuse to start if database or prompt library fails to initialize (raise exception with descriptive error)
    - Update health check endpoint to report: database status, prompt library (version + prompt count), AI client readiness, S3 connectivity
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 17.2 Write property test: Health Check Response Completeness (Property 19)
    - **Property 19: Health Check Response Completeness**
    - For any health check call, verify response contains status entries for: database, prompt_library (version + count), AI client readiness, S3 connectivity
    - **Validates: Requirements 13.4**

  - [x] 17.3 Write property test: Startup Failure Blocks Application (Property 20)
    - **Property 20: Startup Failure Blocks Application**
    - For any startup where database or prompt library fails, verify application raises exception and refuses to start
    - **Validates: Requirements 13.6**

- [x] 18. Shared test fixtures and Hypothesis strategies
  - [x] 18.1 Create conftest.py with shared fixtures and custom strategies
    - Create `tests/conftest.py` with shared pytest fixtures for async test support
    - Create custom Hypothesis strategies for: `CountryConfig`, `L1LanguageContext`, `PromptTemplate`, `WorkerTask`, `ImageContent`, `AIResponse`, `GuardResult`
    - Add fixtures for mock `AsyncAIClient`, `PromptService`, `MediaService`, `GuardService`
    - Add database test fixtures with Alembic migration support
    - _Requirements: all (testing infrastructure)_

- [x] 19. Final checkpoint — All services implemented and tested
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at natural dependency boundaries
- Property tests validate the 20 correctness properties from the design document using Hypothesis
- The dependency chain ensures no task references services not yet implemented
- Python 3.12+ / FastAPI / SQLAlchemy 2.0 async / Alembic / pytest + Hypothesis throughout
