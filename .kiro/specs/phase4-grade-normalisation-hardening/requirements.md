# Requirements Document

## Introduction

Phase 4 is the final phase of the GapSense improvement plan. It addresses remaining technical debt that limits accuracy and operational resilience: grade normalisation for precise curriculum retrieval across four countries (Ghana, Uganda, Kenya, Nigeria), SQS visibility timeout heartbeat to prevent message redelivery during long-running two-stage analyses, structured operational metrics for observability, and YAML-based multi-tenant partner configuration to replace hardcoded country assumptions. These changes build on the infrastructure hardening (Phase 1), hybrid RAG retrieval (Phase 2), and two-stage OCR + diagnosis pipeline (Phase 3) already in place.

## Glossary

- **Orchestrator**: The `ImageAnalysisOrchestrator` service that executes the multi-step image analysis pipeline
- **Pipeline**: The ordered sequence of steps executed by the Orchestrator for each image analysis request
- **ImageAnalysisContext**: The dataclass that carries mutable pipeline state across all pipeline steps
- **Grade_Utils**: The `gapsense/core/grade_utils.py` module providing canonical grade mapping, normalisation, and adjacency functions
- **Canonical_Grade**: A normalised grade code used as the single source of truth for curriculum lookups (e.g., "B7" for Ghana JHS1, "P3" for Uganda Primary 3)
- **Grade_Map**: A per-country dictionary mapping display-grade strings (case-insensitive) to Canonical_Grade codes
- **Adjacent_Grades**: The set of Canonical_Grade codes within a configurable radius of a given grade in a country's ordered grade sequence
- **Vector_Search**: The retrieval step that finds relevant curriculum nodes by embedding similarity against a query string
- **Worker_Service**: The `WorkerService` class that polls SQS and delegates task processing
- **Heartbeat_Loop**: An async coroutine that periodically extends SQS message visibility timeout to prevent redelivery during long-running tasks
- **Metrics_Emitter**: The module responsible for emitting structured log events containing per-analysis operational metrics
- **Partner_Config**: A dataclass representing a single partner's configuration loaded from YAML
- **Partner_Registry**: The in-memory collection of Partner_Config instances loaded at application startup from `config/partners.yaml`
- **Student**: The `Student` ORM model representing a student being assessed
- **CurriculumNode**: The ORM model representing a learning objective in the prerequisite graph, with a `grade` column

## Requirements

### Requirement 1: Canonical Grade Mapping Module

**User Story:** As a GapSense developer, I want a centralised grade mapping module, so that grade normalisation logic is reusable across the codebase and testable in isolation.

#### Acceptance Criteria

1. THE Grade_Utils module SHALL expose a `GRADE_MAPS` constant of type `dict[str, dict[str, str]]` mapping country keys ("ghana", "uganda", "kenya", "nigeria") to dictionaries that map display-grade strings to Canonical_Grade codes
2. THE Grade_Utils module SHALL expose a `normalise_grade(grade: str, country: str) -> str | None` function that returns the Canonical_Grade for a given display grade and country
3. WHEN `normalise_grade` receives a display grade, THE Grade_Utils module SHALL perform case-insensitive matching against the Grade_Map for the specified country
4. WHEN `normalise_grade` cannot find a match for the given grade and country, THE Grade_Utils module SHALL return None
5. THE Grade_Utils module SHALL expose a `grade_range_for_country(country: str) -> list[str]` function that returns all Canonical_Grade codes for a country in ascending educational order
6. THE Grade_Utils module SHALL expose an `adjacent_grades(grade: str, country: str, radius: int = 1) -> list[str]` function that returns Canonical_Grade codes within the specified radius of the given grade in the country's ordered sequence
7. WHEN `adjacent_grades` receives a grade near the start or end of the sequence, THE Grade_Utils module SHALL return only the grades that exist within the range without raising an error
8. FOR ALL valid Canonical_Grade codes for a country, normalising the Canonical_Grade through `normalise_grade` SHALL return the same Canonical_Grade (round-trip property)

### Requirement 2: Ghana Grade Map

**User Story:** As a GapSense developer, I want the Ghana grade map defined, so that Ghanaian student grades are normalised to B1-B9 codes.

#### Acceptance Criteria

1. THE Grade_Map for Ghana SHALL map display grades "B1" through "B9" to Canonical_Grade codes "B1" through "B9"
2. THE Grade_Map for Ghana SHALL map display grades "Primary 1" through "Primary 6" to Canonical_Grade codes "B1" through "B6"
3. THE Grade_Map for Ghana SHALL map display grades "JHS1" through "JHS3" to Canonical_Grade codes "B7" through "B9"
4. THE Grade_Map for Ghana SHALL map display grades "JHS 1" through "JHS 3" (with space) to Canonical_Grade codes "B7" through "B9"
5. THE `grade_range_for_country("ghana")` function SHALL return the list ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"]

### Requirement 3: Uganda Grade Map

**User Story:** As a GapSense developer, I want the Uganda grade map defined, so that Ugandan student grades are normalised to P1-P7 and S1-S4 codes.

#### Acceptance Criteria

1. THE Grade_Map for Uganda SHALL map display grades "P1" through "P7" to Canonical_Grade codes "P1" through "P7"
2. THE Grade_Map for Uganda SHALL map display grades "Primary 1" through "Primary 7" to Canonical_Grade codes "P1" through "P7"
3. THE Grade_Map for Uganda SHALL map display grades "S1" through "S4" to Canonical_Grade codes "S1" through "S4"
4. THE Grade_Map for Uganda SHALL map display grades "Senior 1" through "Senior 4" to Canonical_Grade codes "S1" through "S4"
5. THE `grade_range_for_country("uganda")` function SHALL return the list ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "S1", "S2", "S3", "S4"]

### Requirement 4: Kenya Grade Map

**User Story:** As a GapSense developer, I want the Kenya grade map defined, so that Kenyan student grades are normalised to G1-G9 codes.

#### Acceptance Criteria

1. THE Grade_Map for Kenya SHALL map display grades "G1" through "G9" to Canonical_Grade codes "G1" through "G9"
2. THE Grade_Map for Kenya SHALL map display grades "Grade 1" through "Grade 9" to Canonical_Grade codes "G1" through "G9"
3. THE Grade_Map for Kenya SHALL map display grades "Standard 1" through "Standard 6" to Canonical_Grade codes "G1" through "G6"
4. THE `grade_range_for_country("kenya")` function SHALL return the list ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"]

### Requirement 5: Nigeria Grade Map

**User Story:** As a GapSense developer, I want the Nigeria grade map defined, so that Nigerian student grades are normalised to P1-P6 and JSS1-JSS3 codes.

#### Acceptance Criteria

1. THE Grade_Map for Nigeria SHALL map display grades "P1" through "P6" to Canonical_Grade codes "P1" through "P6"
2. THE Grade_Map for Nigeria SHALL map display grades "Primary 1" through "Primary 6" to Canonical_Grade codes "P1" through "P6"
3. THE Grade_Map for Nigeria SHALL map display grades "JSS1" through "JSS3" to Canonical_Grade codes "JSS1" through "JSS3"
4. THE Grade_Map for Nigeria SHALL map display grades "JSS 1" through "JSS 3" (with space) to Canonical_Grade codes "JSS1" through "JSS3"
5. THE `grade_range_for_country("nigeria")` function SHALL return the list ["P1", "P2", "P3", "P4", "P5", "P6", "JSS1", "JSS2", "JSS3"]

### Requirement 6: Grade Normalisation in Student Context Loading

**User Story:** As a GapSense developer, I want the pipeline to normalise the student grade during context loading, so that downstream steps use a consistent canonical grade for curriculum retrieval.

#### Acceptance Criteria

1. WHEN `_load_student_context` executes, THE Orchestrator SHALL call `normalise_grade(student.current_grade, country)` and store the result in `ctx.student_grade`
2. WHEN `_load_student_context` executes, THE Orchestrator SHALL store the original `student.current_grade` value in `ctx.student_grade_raw`
3. WHEN `normalise_grade` returns None, THE Orchestrator SHALL log a warning containing the raw grade value and country
4. WHEN `normalise_grade` returns None, THE Orchestrator SHALL set `ctx.student_grade` to the raw `student.current_grade` value as a fallback
5. THE ImageAnalysisContext SHALL contain a `student_grade_raw` field of type string with a default value of empty string

### Requirement 7: Grade-Filtered Vector Search

**User Story:** As a GapSense developer, I want the vector search to filter curriculum nodes by adjacent grades, so that retrieval returns only grade-relevant content and improves diagnostic accuracy.

#### Acceptance Criteria

1. THE Vector_Search function SHALL accept an optional `grade` parameter of type `str | None`
2. WHEN `grade` is a valid Canonical_Grade, THE Vector_Search function SHALL filter candidate curriculum nodes to those whose grade is in the set returned by `adjacent_grades(grade, country, radius=1)`
3. WHEN `grade` is None, THE Vector_Search function SHALL apply no grade filter and search all curriculum nodes for the given country and subject
4. WHEN a Partner_Config specifies a `grade_focus` value, THE Orchestrator SHALL use the `grade_focus` value to override the student grade for the Vector_Search grade filter
5. THE grade filter SHALL be applied before the cosine similarity ranking step so that only grade-relevant nodes are scored

### Requirement 8: Student Grade Canonical Column

**User Story:** As a GapSense developer, I want a `grade_canonical` column on the Student model, so that normalised grades are persisted and available without re-computation.

#### Acceptance Criteria

1. THE Student model SHALL contain a `grade_canonical` column of type `String(16)` that is nullable
2. WHEN a Student record is created, THE application SHALL compute `normalise_grade(current_grade, country)` and store the result in `grade_canonical`
3. WHEN a Student record's `current_grade` is updated, THE application SHALL recompute `normalise_grade(current_grade, country)` and update `grade_canonical`
4. THE Alembic migration SHALL add the `grade_canonical` column to the `students` table
5. THE Alembic migration SHALL backfill `grade_canonical` for all existing Student records using the `normalise_grade` function

### Requirement 9: SQS Visibility Timeout Heartbeat

**User Story:** As a GapSense operator, I want the worker to extend SQS message visibility during long-running analyses, so that messages are not redelivered while processing is still in progress.

#### Acceptance Criteria

1. THE Worker_Service SHALL expose an `_extend_visibility_timeout(receipt_handle: str, extension_seconds: int = 60)` method that calls the SQS ChangeMessageVisibility API
2. THE Worker_Service SHALL expose a `_heartbeat_loop(receipt_handle: str, interval: int = 45, extension: int = 90)` async method that periodically calls `_extend_visibility_timeout` at the specified interval
3. WHEN `_process_message` begins processing a task, THE Worker_Service SHALL start the Heartbeat_Loop as a concurrent async task
4. WHEN `_process_message` completes processing (success or failure), THE Worker_Service SHALL cancel the Heartbeat_Loop task
5. IF the Heartbeat_Loop encounters an error extending visibility, THEN THE Worker_Service SHALL log a warning and continue processing without raising an exception
6. IF the Heartbeat_Loop is cancelled, THEN THE Worker_Service SHALL exit the loop cleanly without logging an error

### Requirement 10: Structured Analysis Metrics

**User Story:** As a GapSense operator, I want structured metrics emitted after each analysis, so that I can monitor pipeline health, accuracy, and performance across countries and grades.

#### Acceptance Criteria

1. THE Metrics_Emitter SHALL expose an `emit_analysis_metrics(ctx: ImageAnalysisContext, success: bool, latency_ms: float)` function
2. WHEN `emit_analysis_metrics` is called, THE Metrics_Emitter SHALL emit a single structured log event with the event name "analysis_metrics"
3. THE structured log event SHALL contain the fields: student_id, country, subject, grade, success, latency_ms, nodes_injected, seed_nodes, prerequisite_nodes, transcription_legibility, questions_transcribed, gaps_found, and ai_confidence
4. WHEN the Pipeline completes (success or failure), THE Orchestrator SHALL call `emit_analysis_metrics` with the final context, success status, and total latency
5. THE Metrics_Emitter SHALL NOT make any external API calls or perform any I/O operations beyond structured logging

### Requirement 11: Partner Configuration Dataclass

**User Story:** As a GapSense developer, I want a typed partner configuration dataclass, so that partner-specific settings are validated and accessible throughout the pipeline.

#### Acceptance Criteria

1. THE Partner_Config dataclass SHALL contain the fields: partner_id (str), country (str), subject_focus (str | None), grade_focus (str | None), rate_limit_per_day (int), whatsapp_sender_id (str), and report_language (str)
2. THE Partner_Config module SHALL be located at `gapsense/core/partner_config.py`
3. THE Partner_Config module SHALL NOT be stored in the prompt library directory
4. THE Partner_Config dataclass SHALL NOT contain any partner branding or display content

### Requirement 12: YAML-Based Partner Registry

**User Story:** As a GapSense operator, I want partner configurations loaded from a YAML file, so that adding or modifying partners does not require code changes or redeployment.

#### Acceptance Criteria

1. THE Partner_Registry SHALL load partner configurations from a YAML file at the path `config/partners.yaml`
2. WHEN the application starts, THE Partner_Registry SHALL parse the YAML file and construct a Partner_Config instance for each entry
3. THE Partner_Registry SHALL expose a `get_partner(partner_id: str) -> Partner_Config | None` function to retrieve a partner configuration by identifier
4. IF the YAML file is missing or contains invalid entries, THEN THE Partner_Registry SHALL log an error and raise an exception at startup rather than silently using defaults
5. IF a partner entry in the YAML file is missing required fields, THEN THE Partner_Registry SHALL reject that entry and log a warning identifying the partner_id and missing fields

### Requirement 13: Partner Configuration Injection into Pipeline

**User Story:** As a GapSense developer, I want partner configuration injected into the analysis pipeline, so that partner-specific overrides (grade focus, rate limits) are applied during analysis.

#### Acceptance Criteria

1. WHEN the Orchestrator receives a task payload containing a `partner_id` field, THE Orchestrator SHALL look up the corresponding Partner_Config from the Partner_Registry
2. WHEN a Partner_Config is found, THE Orchestrator SHALL store the Partner_Config in the ImageAnalysisContext
3. WHEN a Partner_Config specifies a non-null `grade_focus`, THE Orchestrator SHALL use `grade_focus` as the grade filter for Vector_Search instead of the student's canonical grade
4. WHEN no `partner_id` is provided or no matching Partner_Config is found, THE Orchestrator SHALL proceed with default pipeline behaviour without partner overrides
5. THE ImageAnalysisContext SHALL contain a `partner_config` field of type `Partner_Config | None` with a default value of None

### Requirement 14: Country Utils Multi-Country Support

**User Story:** As a GapSense developer, I want `country_utils.py` to resolve country from student context rather than defaulting to Ghana, so that multi-country deployments return accurate country keys.

#### Acceptance Criteria

1. WHEN a Student has a school with a known country association, THE `get_country_from_student` function SHALL return the country key derived from the school's location
2. WHEN a Student has no school or the school has no country association, THE `get_country_from_student` function SHALL fall back to the `country_code` provided in the task payload
3. THE `get_country_from_student` function SHALL accept an optional `fallback_country` parameter to replace the hardcoded "ghana" default
4. THE `_COUNTRY_DEFAULTS` mapping SHALL include entries for all four supported countries: Ghana, Uganda, Kenya, and Nigeria
