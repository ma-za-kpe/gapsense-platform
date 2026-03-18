# Implementation Plan: Teacher Remediation Exercises

## Overview

Implement automatic generation of teacher-facing remediation sample questions after exercise book analysis. This involves adding the REMEDIATION-001 prompt, creating the RemediationEngine service, integrating it into ExerciseBookScanner, exposing exercises via the Reports API, and rendering them in the teacher dashboard.

## Tasks

- [ ] 1. Add REMEDIATION-001 prompt to the prompt library
  - [ ] 1.1 Add the REMEDIATION-001 entry to `gapsense/data/prompts/gapsense_prompt_library_v2.0_multicountry.json`
    - Add prompt with `category: "teacher_remediation"`, `status: "active"`, `model: "claude-sonnet-4-6"`, `temperature: 0.4`, `max_tokens: 2048`
    - Template parameters: `country`, `curriculum_authority`, `gap_node_code`, `gap_node_title`, `student_grade`, `error_patterns`, `misconception_description`
    - System prompt instructs 3–5 questions per gap node, classroom-appropriate, with teacher notes explaining targeted misconceptions
    - Output format: JSON array of `{question, expected_answer, teacher_note, gap_node_code}` objects
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ] 1.2 Copy the prompt library to `gapsense-data/prompts/gapsense_prompt_library_v2.0_multicountry.json`
    - Ensure both copies are byte-identical
    - _Requirements: 1.5_

  - [ ]* 1.3 Write property test: prompt library copies are identical
    - **Property 1: Prompt library copies are identical**
    - **Validates: Requirements 1.5**

- [ ] 2. Implement RemediationEngine service
  - [ ] 2.1 Create `gapsense/src/gapsense/engagement/remediation_engine.py`
    - Define `RemediationExercise` dataclass with fields: `question`, `expected_answer`, `teacher_note`, `gap_node_code`
    - Implement `RemediationEngine` class with `__init__` accepting `ai_client`, `prompt_service`, `guard_service`
    - Implement `generate_exercises()` method:
      - Render REMEDIATION-001 prompt with gap node details, grade, country
      - Call AI client with `json_mode=True`
      - Parse response, validate each exercise has required fields (filter out malformed)
      - Concatenate exercise text, pass to `GuardService.check()`
      - Return exercises if guard passes, empty list if guard fails
      - Wrap entire flow in try/except — log errors, return `[]` on any failure (fail-open)
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 7.1, 7.2_

  - [ ]* 2.2 Write property test: rendered prompt contains all gap node data
    - **Property 3: Rendered prompt contains all gap node data**
    - **Validates: Requirements 2.2**

  - [ ]* 2.3 Write property test: exercise objects have required schema fields
    - **Property 5: Exercise objects have required schema fields**
    - Generate random AI responses, verify schema validation filters correctly
    - **Validates: Requirements 3.2**

  - [ ]* 2.4 Write property test: guard service gates exercise storage
    - **Property 10: Guard service gates exercise storage**
    - Generate random exercises + guard pass/fail, verify storage outcome
    - **Validates: Requirements 7.1, 7.2**

- [ ] 3. Integrate RemediationEngine into ExerciseBookScanner
  - [ ] 3.1 Modify `ExerciseBookScanner` to accept `RemediationEngine` dependency
    - Add `remediation_engine` parameter to `__init__`
    - In `process_analysis_result()`, after saving GapProfile and before sending notification:
      - Extract gap node details (codes, titles, error patterns, misconceptions) from the profile
      - Call `remediation_engine.generate_exercises()` with gap node details, student grade, country
      - Store returned exercises in `analysis_metadata["remediation_exercises"]`
      - Commit the updated profile
    - If GapProfile has zero gap nodes, set `"remediation_exercises": []` and skip engine call
    - _Requirements: 2.1, 2.4, 3.1, 3.3_

  - [ ]* 3.2 Write property test: exercise generation and storage round trip
    - **Property 2: Exercise generation and storage round trip**
    - Generate random gap node lists, mock AI to return valid exercises, verify storage
    - **Validates: Requirements 2.1, 3.1**

  - [ ]* 3.3 Write property test: AI failure does not block pipeline
    - **Property 4: AI failure does not block pipeline**
    - Generate random failure modes, verify pipeline completion and notification sent
    - **Validates: Requirements 2.3**

- [ ] 4. Checkpoint - Ensure backend tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run: `docker compose exec web pytest gapsense/tests/unit/test_remediation_engine.py -v`

- [ ] 5. Expose remediation exercises via Reports API
  - [ ] 5.1 Modify student report endpoint in `gapsense/src/gapsense/web/demo.py`
    - `GET /demo/api/reports/{teacher_phone}/student/{student_id}`: include `remediation_exercises` array from `analysis_metadata` in the response
    - When no exercises exist, return `remediation_exercises: []`
    - _Requirements: 6.1, 6.3_

  - [ ] 5.2 Modify teacher dashboard endpoint in `gapsense/src/gapsense/web/demo.py`
    - `GET /demo/api/reports/{teacher_phone}`: add `remediation_exercise_count` integer to each student object
    - Add `remediation_exercise_count` to the `latest_analysis` object
    - When no exercises exist, return `remediation_exercise_count: 0`
    - _Requirements: 6.2, 6.3_

  - [ ]* 5.3 Write property test: API response includes exercises and correct count
    - **Property 9: API response includes exercises and correct count**
    - For any GapProfile with N exercises, verify student report includes all N and dashboard includes count = N
    - **Validates: Requirements 6.1, 6.2**

- [ ] 6. Checkpoint - Ensure backend and API tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run: `docker compose exec web pytest gapsense/tests/ -v -k remediation`

- [ ] 7. Display remediation exercises on student detail page
  - [ ] 7.1 Create `RemediationExercises` component in the student detail page
    - File: `gap-sense-frontend/app/demo/reports/[phone]/student/[id]/page.tsx` (or extracted component)
    - Render a "Remediation Exercises" section after the gap nodes card
    - Group exercises by `gap_node_code`, display gap node title as group heading
    - Each exercise shows: question text, expected answer, teacher note
    - Hide section entirely when `remediation_exercises` is empty or absent
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 7.2 Write property test: rendered exercises display all fields
    - **Property 6: Rendered exercises display all fields**
    - Generate random exercise arrays, render component, verify all fields present
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 7.3 Write property test: exercises are grouped by gap node code
    - **Property 7: Exercises are grouped by gap node code**
    - Generate random exercises with multiple gap codes, verify grouping
    - **Validates: Requirements 4.3**

- [ ] 8. Surface remediation exercises on teacher dashboard overview
  - [ ] 8.1 Add exercise count and badge to student cards on teacher dashboard
    - File: `gap-sense-frontend/app/demo/reports/[phone]/page.tsx` (or extracted component)
    - Display exercise count in latest analysis section (e.g., "5 remediation exercises available")
    - Show visual indicator (badge/icon) on student cards when `remediation_exercise_count > 0`
    - _Requirements: 5.1, 5.2_

  - [ ]* 8.2 Write property test: dashboard shows exercise count for students with exercises
    - **Property 8: Dashboard shows exercise count for students with exercises**
    - Generate random student data with varying counts, verify badge rendering
    - **Validates: Requirements 5.1, 5.2**

- [ ] 9. Wire up RemediationEngine dependency injection
  - [ ] 9.1 Register `RemediationEngine` in the service/dependency wiring
    - Instantiate `RemediationEngine` with existing `AsyncAIClient`, `PromptService`, and `GuardService`
    - Pass it to `ExerciseBookScanner` constructor
    - Ensure all existing tests still pass with the new dependency
    - _Requirements: 2.1_

- [ ] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run backend: `docker compose exec web pytest gapsense/tests/ -v -k remediation`
  - Run frontend: `cd gap-sense-frontend && npm test -- --run`

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Both prompt library copies must stay in sync (Property 1)
- All error paths are fail-open for exercises but fail-closed for content safety (guard rejection)
- No database migrations needed — exercises stored in existing JSONB field
