# Implementation Plan: Phase 4 — Grade Normalisation + Ongoing Hardening

## Overview

Two streams implemented sequentially. Stream A (tasks 1–6) builds grade normalisation from the foundation module up through pipeline integration and database persistence. Stream B (tasks 7–12) adds operational hardening: partner config, SQS heartbeat, and structured metrics. Each task builds on the previous and references specific requirements and design properties.

## Tasks

- [ ] 1. Create `grade_utils.py` module with grade maps and core functions
  - [ ] 1.1 Create `gapsense/src/gapsense/core/grade_utils.py` with `GRADE_MAPS`, `GRADE_SEQUENCES`, `normalise_grade`, `grade_range_for_country`, and `adjacent_grades`
    - Define `GRADE_MAPS` dict mapping country keys to display-grade → canonical-grade dicts for Ghana, Uganda, Kenya, Nigeria per design data model tables
    - Define `GRADE_SEQUENCES` dict mapping country keys to ordered canonical grade lists
    - Implement `normalise_grade(grade: str, country: str) -> str | None` with case-insensitive lookup via `grade.strip().lower()`
    - Implement `grade_range_for_country(country: str) -> list[str]` returning `GRADE_SEQUENCES.get(country, [])`
    - Implement `adjacent_grades(grade: str, country: str, radius: int = 1) -> list[str]` with boundary clamping
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.1–2.5, 3.1–3.5, 4.1–4.4, 5.1–5.5_

  - [ ]* 1.2 Write property tests for grade_utils (Properties 1–5)
    - Create `tests/unit/test_grade_utils_pbt.py` using Hypothesis
    - **Property 1: Canonical grade round-trip** — for any country and canonical grade, `normalise_grade(canonical, country)` returns the same canonical grade
    - **Validates: Requirement 1.8**
    - **Property 2: Case-insensitive normalisation** — for any valid display grade, upper/lower/mixed case all return the same canonical grade
    - **Validates: Requirements 1.2, 1.3**
    - **Property 3: Unrecognised grades return None** — for any string not in any grade map, `normalise_grade` returns None
    - **Validates: Requirement 1.4**
    - **Property 4: Adjacent grades within radius bounds** — every returned grade is at most `radius` positions away, and the input grade is always included
    - **Validates: Requirements 1.6, 1.7**
    - **Property 5: Adjacent grades boundary clamping** — result length equals `min(i+r, n-1) - max(i-r, 0) + 1`
    - **Validates: Requirements 1.6, 1.7**

  - [ ]* 1.3 Write unit tests for grade_utils (country-specific maps)
    - Create `tests/unit/test_grade_utils.py`
    - Test Ghana: B1–B9 identity, Primary 1–6 → B1–B6, JHS1–JHS3 → B7–B9, JHS 1–JHS 3 → B7–B9, grade_range returns exact sequence
    - Test Uganda: P1–P7 identity, Primary 1–7 → P1–P7, S1–S4 identity, Senior 1–4 → S1–S4, grade_range returns exact sequence
    - Test Kenya: G1–G9 identity, Grade 1–9 → G1–G9, Standard 1–6 → G1–G6, grade_range returns exact sequence
    - Test Nigeria: P1–P6 identity, Primary 1–6 → P1–P6, JSS1–JSS3 identity, JSS 1–JSS 3 → JSS1–JSS3, grade_range returns exact sequence
    - _Requirements: 2.1–2.5, 3.1–3.5, 4.1–4.4, 5.1–5.5_

- [ ] 2. Add Phase 4 fields to `ImageAnalysisContext`
  - [ ] 2.1 Add `student_grade_raw` and `partner_config` fields to `ImageAnalysisContext`
    - Add `student_grade_raw: str = ""` field to the dataclass in `gapsense/src/gapsense/services/image_analysis_context.py`
    - Add `partner_config: PartnerConfig | None = None` field (forward reference or import from `gapsense.core.partner_config`)
    - _Requirements: 6.5, 13.5_

- [ ] 3. Integrate grade normalisation into `_load_student_context`
  - [ ] 3.1 Modify `_load_student_context` in `image_analysis_orchestrator.py` to normalise grade
    - After loading the student, store `student.current_grade` in `ctx.student_grade_raw`
    - Call `normalise_grade(student.current_grade, ctx.country_key)` and store result in `ctx.student_grade`
    - When `normalise_grade` returns None, log warning with raw grade and country, fall back to `student.current_grade`
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 3.2 Write property test for student context grade normalisation (Property 6)
    - Add to `tests/unit/test_orchestrator_phase4_pbt.py`
    - **Property 6: Student context preserves raw grade and normalises** — after `_load_student_context`, `ctx.student_grade_raw == student.current_grade` and `ctx.student_grade` equals normalised or raw fallback
    - **Validates: Requirements 6.1, 6.2, 6.4**

- [ ] 4. Add grade filter to `_build_curriculum_graph`
  - [ ] 4.1 Modify `_build_curriculum_graph` to filter by adjacent grades
    - Determine effective grade: use `ctx.partner_config.grade_focus` if present, else `ctx.student_grade`
    - Compute `adjacent_grades(effective_grade, ctx.country_key, radius=1)` when effective grade is set
    - Add `WHERE grade IN (...)` clause to the CurriculumNode query when allowed_grades is non-empty
    - When grade is None or adjacent_grades returns empty, apply no grade filter
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 4.2 Write property test for grade-filtered vector search (Property 7)
    - Add to `tests/unit/test_orchestrator_phase4_pbt.py`
    - **Property 7: Grade-filtered vector search returns only adjacent-grade nodes** — all returned nodes have grade in `adjacent_grades(grade, country, radius=1)`
    - **Validates: Requirement 7.2**

  - [ ]* 4.3 Write property test for partner grade_focus override (Property 8)
    - Add to `tests/unit/test_orchestrator_phase4_pbt.py`
    - **Property 8: Partner grade_focus overrides student grade** — when partner has grade_focus, effective grade for search is grade_focus, not student grade
    - **Validates: Requirements 7.4, 13.3**

- [ ] 5. Checkpoint — Stream A core logic
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Add `grade_canonical` column to Student model with Alembic migration
  - [ ] 6.1 Add `grade_canonical` column to `Student` model
    - Add `grade_canonical: Mapped[str | None] = mapped_column(String(16), nullable=True)` to `gapsense/src/gapsense/core/models/students.py`
    - _Requirements: 8.1_

  - [ ] 6.2 Create Alembic migration to add column and backfill
    - Create migration in `gapsense/alembic/versions/` that adds `grade_canonical` column to `students` table
    - Include data migration step using `op.execute()` with raw SQL to backfill existing rows using grade map logic
    - _Requirements: 8.4, 8.5_

  - [ ]* 6.3 Write property test for grade_canonical consistency (Property 9)
    - Add to `tests/unit/test_grade_utils_pbt.py`
    - **Property 9: Student grade_canonical consistency** — for any student with current_grade and known country, grade_canonical equals `normalise_grade(current_grade, country)`
    - **Validates: Requirements 8.2, 8.3**

- [ ] 7. Update `country_utils.py` for multi-country support
  - [ ] 7.1 Modify `get_country_from_student` to accept `fallback_country` parameter
    - Add `fallback_country: str = "ghana"` parameter to replace hardcoded default
    - Implement progressive resolution: school country → fallback_country → "ghana" default
    - Add entries for Uganda, Kenya, Nigeria to `_COUNTRY_DEFAULTS`
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [ ]* 7.2 Write property test for country resolution fallback (Property 13)
    - Add to `tests/unit/test_country_utils_pbt.py`
    - **Property 13: Country resolution progressive fallback** — returns school country if available, else fallback_country; never returns hardcoded "ghana" when different fallback provided
    - **Validates: Requirements 14.1, 14.2, 14.3**

- [ ] 8. Create `PartnerConfig` dataclass and YAML partner registry
  - [ ] 8.1 Create `gapsense/src/gapsense/core/partner_config.py` with `PartnerConfig` dataclass
    - Frozen dataclass with fields: partner_id, country, subject_focus, grade_focus, rate_limit_per_day, whatsapp_sender_id, report_language
    - Default values per design: rate_limit_per_day=1000, whatsapp_sender_id="", report_language="en"
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ] 8.2 Create `gapsense/src/gapsense/core/partner_registry.py` with `load_partner_registry` and `get_partner`
    - `load_partner_registry(yaml_path)` parses YAML, constructs PartnerConfig instances, raises on missing file or parse error
    - Log warning and skip entries missing required fields (partner_id, country)
    - `get_partner(partner_id) -> PartnerConfig | None`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ] 8.3 Create `config/partners.yaml` with sample partner entries
    - Include example entries for Ghana and Uganda partners per design schema
    - _Requirements: 12.1_

  - [ ]* 8.4 Write property test for partner registry round-trip (Property 12)
    - Create `tests/unit/test_partner_registry_pbt.py`
    - **Property 12: Partner registry round-trip** — for any valid YAML entry, `get_partner(partner_id)` returns PartnerConfig matching YAML values
    - **Validates: Requirements 12.2, 12.3**

  - [ ]* 8.5 Write unit tests for partner config and registry
    - Create `tests/unit/test_partner_config.py` — test dataclass fields, frozen immutability, defaults
    - Create `tests/unit/test_partner_registry.py` — test missing YAML raises, missing required fields logs warning and skips, valid load
    - _Requirements: 11.1, 12.4, 12.5_

- [ ] 9. Inject partner config into pipeline
  - [ ] 9.1 Modify orchestrator to look up partner config from task payload
    - In `_load_student_context` or pipeline entry, extract `partner_id` from task payload
    - Call `get_partner(partner_id)` and store result in `ctx.partner_config`
    - When no partner_id or no match, proceed with `ctx.partner_config = None`
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ]* 9.2 Write unit tests for partner injection
    - Add to `tests/unit/test_orchestrator_phase4.py`
    - Test partner lookup from payload, storage in context, default when missing
    - _Requirements: 13.1, 13.2, 13.4_

- [ ] 10. Checkpoint — Stream A complete + partner config
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Add SQS visibility timeout heartbeat to WorkerService
  - [ ] 11.1 Implement `_extend_visibility_timeout` and `_heartbeat_loop` on `WorkerService`
    - `_extend_visibility_timeout(receipt_handle, extension_seconds=60)` calls SQS ChangeMessageVisibility
    - `_heartbeat_loop(receipt_handle, interval=45, extension=90)` runs as async loop, catches CancelledError cleanly, logs warning on SQS errors
    - _Requirements: 9.1, 9.2, 9.5, 9.6_

  - [ ] 11.2 Implement `_process_message_with_heartbeat` wrapper
    - Start heartbeat loop as `asyncio.create_task` before processing
    - Cancel heartbeat task in `finally` block (success or failure)
    - Wire into existing message processing flow
    - _Requirements: 9.3, 9.4_

  - [ ]* 11.3 Write property test for heartbeat cancellation (Property 10)
    - Add to `tests/unit/test_worker_heartbeat_pbt.py`
    - **Property 10: Heartbeat cancellation on all outcomes** — for any message outcome (success or exception), heartbeat task is cancelled after processing
    - **Validates: Requirement 9.4**

  - [ ]* 11.4 Write unit tests for heartbeat
    - Create `tests/unit/test_worker_heartbeat.py`
    - Test `_extend_visibility_timeout` calls SQS API, `_heartbeat_loop` calls extend at interval, heartbeat started on processing, error logs warning without raising, cancellation exits cleanly
    - _Requirements: 9.1, 9.2, 9.3, 9.5, 9.6_

- [ ] 12. Add structured analysis metrics
  - [ ] 12.1 Create `gapsense/src/gapsense/core/metrics.py` with `emit_analysis_metrics`
    - `emit_analysis_metrics(ctx: ImageAnalysisContext, success: bool, latency_ms: float)` emits structured log event named "analysis_metrics"
    - Extract all 13 fields from context: student_id, country, subject, grade, success, latency_ms, nodes_injected, seed_nodes, prerequisite_nodes, transcription_legibility, questions_transcribed, gaps_found, ai_confidence
    - No external API calls — structured logging only
    - _Requirements: 10.1, 10.2, 10.3, 10.5_

  - [ ] 12.2 Integrate metrics emission into orchestrator pipeline
    - Call `emit_analysis_metrics` after pipeline completes (success or failure) with final context, success status, and total latency
    - _Requirements: 10.4_

  - [ ]* 12.3 Write property test for metrics event fields (Property 11)
    - Add to `tests/unit/test_metrics_pbt.py`
    - **Property 11: Metrics event contains all required fields** — for any ImageAnalysisContext, emitted log event contains all 13 required fields
    - **Validates: Requirement 10.3**

  - [ ]* 12.4 Write unit tests for metrics
    - Create `tests/unit/test_metrics.py`
    - Test function signature, event name "analysis_metrics", pipeline calls on success and failure
    - _Requirements: 10.1, 10.2, 10.4_

- [ ] 13. Final checkpoint — all streams complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Stream A (tasks 1–7) should complete before Stream B (tasks 8–12) per design guidance
- Each property test references its design property number and validated requirements
- Checkpoints at tasks 5, 10, and 13 for incremental validation
- All code is Python; tests use Hypothesis for property-based testing
