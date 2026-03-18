# Requirements Document

## Introduction

After the exercise book analysis pipeline (Phase 3) completes and a GapProfile is created, the system should generate teacher-facing remediation sample questions for the identified gap nodes and display them in the teacher dashboard report. The MVP scope is teacher-only. The design should accommodate future parent delivery via WhatsApp but that is out of scope for now.

## Glossary

- **Remediation_Engine**: The backend service component responsible for generating remediation sample questions from a GapProfile using AI prompts.
- **Teacher_Dashboard**: The Next.js frontend at `/demo/reports/{phone}` and `/demo/reports/{phone}/student/{id}` that displays student gap analysis and remediation exercises to teachers.
- **GapProfile**: The SQLAlchemy model (`gap_profiles` table) representing a student's learning gap profile, including `analysis_metadata` (JSONB) and `recommended_activity` (Text) fields.
- **REMEDIATION-001**: A new prompt in the GapSense prompt library, tailored for generating teacher-facing sample remediation questions (distinct from ACT-001 which generates parent-facing 3-minute household activities).
- **ExerciseBookScanner**: The existing service (`exercise_book_scanner.py`) that processes exercise book image analysis results and saves GapProfiles.
- **Prompt_Library**: The JSON prompt configuration file (`gapsense_prompt_library_v2.0_multicountry.json`) that defines all AI prompts. Two copies must stay in sync: `gapsense/data/prompts/` and `gapsense-data/prompts/`.
- **Reports_API**: The FastAPI endpoints at `/api/reports/{teacher_phone}` and `/api/reports/{teacher_phone}/student/{student_id}` that serve teacher dashboard data.

## Requirements

### Requirement 1: Create REMEDIATION-001 Prompt

**User Story:** As a system designer, I want a dedicated teacher-facing remediation prompt, so that generated exercises are appropriate for classroom use rather than parent home activities.

#### Acceptance Criteria

1. THE Prompt_Library SHALL contain a REMEDIATION-001 prompt entry with `category` set to `"teacher_remediation"` and `status` set to `"active"`.
2. THE REMEDIATION-001 prompt SHALL instruct the AI to generate 3–5 sample remediation questions per gap node, each with a question stem, expected correct answer, and a brief teacher note explaining the targeted misconception.
3. THE REMEDIATION-001 prompt SHALL accept country, curriculum_authority, gap_node_code, gap_node_title, student_grade, error_patterns, and misconception_description as template parameters.
4. THE REMEDIATION-001 prompt SHALL instruct the AI to produce output in a structured JSON format containing an array of exercise objects.
5. WHEN the REMEDIATION-001 prompt is added to one copy of the Prompt_Library, THE Prompt_Library SHALL be updated identically in both `gapsense/data/prompts/` and `gapsense-data/prompts/`.

### Requirement 2: Generate Remediation Exercises After Analysis

**User Story:** As a teacher, I want remediation exercises generated automatically after exercise book analysis, so that I can immediately see actionable practice questions for each student's gaps.

#### Acceptance Criteria

1. WHEN the ExerciseBookScanner finishes saving a GapProfile with one or more gap nodes, THE Remediation_Engine SHALL invoke the REMEDIATION-001 prompt to generate remediation exercises for the identified gap nodes.
2. THE Remediation_Engine SHALL pass the gap node codes, gap node titles, student grade, and any error patterns from the analysis metadata to the REMEDIATION-001 prompt.
3. IF the AI call to generate remediation exercises fails, THEN THE Remediation_Engine SHALL log the error and continue the pipeline without blocking teacher notification.
4. THE Remediation_Engine SHALL complete exercise generation within the same request lifecycle as `process_analysis_result`, before the teacher notification is sent.

### Requirement 3: Store Remediation Exercises in GapProfile

**User Story:** As a system designer, I want remediation exercises persisted in the GapProfile, so that the dashboard can retrieve them without re-generating.

#### Acceptance Criteria

1. WHEN remediation exercises are generated, THE Remediation_Engine SHALL store the exercises array in the GapProfile `analysis_metadata` JSONB field under the key `"remediation_exercises"`.
2. THE stored `remediation_exercises` array SHALL contain objects with at minimum the fields: `question`, `expected_answer`, `teacher_note`, and `gap_node_code`.
3. IF no remediation exercises are generated (due to AI failure or zero gap nodes), THEN THE GapProfile `analysis_metadata` SHALL contain `"remediation_exercises": []`.

### Requirement 4: Display Remediation Exercises in Student Detail Report

**User Story:** As a teacher, I want to see sample remediation questions on the student detail report page, so that I can use them in class or assign them to the student.

#### Acceptance Criteria

1. WHEN a student detail report is loaded and the GapProfile contains a non-empty `remediation_exercises` array in `analysis_metadata`, THE Teacher_Dashboard SHALL render a "Remediation Exercises" section on the student detail page.
2. THE Teacher_Dashboard SHALL display each exercise with its question text, expected answer, teacher note, and the associated gap node code.
3. THE Teacher_Dashboard SHALL group exercises by gap node code and display the gap node title as a group heading.
4. WHEN the `remediation_exercises` array is empty or absent, THE Teacher_Dashboard SHALL not render the "Remediation Exercises" section.

### Requirement 5: Surface Remediation Exercises in Teacher Dashboard Overview

**User Story:** As a teacher, I want a preview of remediation exercises on the main dashboard, so that I can quickly see what practice material is available for recently analyzed students.

#### Acceptance Criteria

1. WHEN the latest analysis section is displayed on the teacher dashboard and the corresponding GapProfile contains remediation exercises, THE Teacher_Dashboard SHALL display a count of available remediation exercises (e.g., "5 remediation exercises available").
2. WHEN a student card on the teacher dashboard has remediation exercises available, THE Teacher_Dashboard SHALL display a visual indicator (e.g., a badge or icon) showing that remediation exercises exist for that student.

### Requirement 6: Expose Remediation Exercises via Reports API

**User Story:** As a frontend developer, I want the reports API to include remediation exercises in its response, so that the dashboard can render them.

#### Acceptance Criteria

1. THE Reports_API endpoint `/api/reports/{teacher_phone}/student/{student_id}` SHALL include the `remediation_exercises` array from `analysis_metadata` in the student report response.
2. THE Reports_API endpoint `/api/reports/{teacher_phone}` SHALL include a `remediation_exercise_count` integer field for each student object and for the `latest_analysis` object.
3. WHEN no remediation exercises exist for a student, THE Reports_API SHALL return `remediation_exercises` as an empty array and `remediation_exercise_count` as `0`.

### Requirement 7: GUARD-001 Validation of Generated Exercises

**User Story:** As a system designer, I want generated remediation exercises validated through the existing guard service, so that inappropriate or fabricated content is filtered out before storage.

#### Acceptance Criteria

1. WHEN remediation exercises are generated, THE Remediation_Engine SHALL pass the combined exercise text through the existing GuardService `check` method before storing.
2. IF the GuardService rejects the generated exercises, THEN THE Remediation_Engine SHALL log the guard violations and store an empty `remediation_exercises` array.
