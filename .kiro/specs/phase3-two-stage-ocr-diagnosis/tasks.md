# Implementation Plan: Phase 3 — Two-Stage OCR + Diagnosis

## Overview

Refactor the GapSense image analysis pipeline from single-pass (image → diagnosis) to two-stage (image → transcription → diagnosis). Implementation follows the pipeline data flow: context fields first, then prompt definition, then each pipeline step in execution order, then wiring in `run()`.

All code is Python. Tests use pytest + Hypothesis.

## Tasks

- [x] 1. Add transcription fields to ImageAnalysisContext
  - [x] 1.1 Add `transcription_text: str = ""` and `transcription_result: dict = field(default_factory=dict)` to `ImageAnalysisContext` in `gapsense/src/gapsense/services/image_analysis_context.py`
    - Place after the Step 2 fields (`media_type`) and before the Step 3 fields (`curriculum_graph_json`)
    - Rename the existing "Step 3" / "Step 4" / "Step 5" comments to "Step 4" / "Step 5" / "Step 6" to reflect the new 7-step pipeline
    - Add a comment block: `# ── Resolved in Step 3: transcribe_image (NEW) ──`
    - _Requirements: 3.1, 3.2_

- [x] 2. Add TRANSCRIPTION-001 prompt to the prompt library
  - [x] 2.1 Add the TRANSCRIPTION-001 entry to `gapsense-data/prompts/gapsense_prompt_library_v2.0_multicountry.json`
    - Add inside the `"prompts"` object alongside DIAG-001, ANALYSIS-001, etc.
    - Set `model: "claude-sonnet-4-6"`, `temperature: 0.1`, `max_tokens: 2048`
    - `user_template: null` (image is the only user input)
    - Write the `system_prompt` instructing the model to: orient to page layout, anchor on question numbers, transcribe each question exactly as written (preserving errors, mathematical notation, incomplete work), note handwriting characteristics, mark illegible regions rather than guessing, and return structured JSON only
    - The system prompt must define the output JSON schema with fields: `layout`, `subject_detected`, `grade_detected`, `topic_detected`, `teacher_marks_present`, `questions` (array of `{question_number, question_text, student_work, teacher_mark, teacher_score, has_diagram, illegible_regions}`), `overall_legibility`, `handwriting_styles_detected`, `ocr_notes`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 9.1, 9.2, 9.3_

- [x] 3. Update `_log_ai_cost` to accept optional `prompt_id` override
  - [x] 3.1 Modify `_log_ai_cost` signature in `gapsense/src/gapsense/services/image_analysis_orchestrator.py`
    - Add `prompt_id: str | None = None` parameter
    - When `prompt_id` is provided, use it instead of `response.prompt_id` when constructing the `AIUsageLog` record
    - Change the line `prompt_id=response.prompt_id` to `prompt_id=prompt_id or response.prompt_id`
    - _Requirements: 7.3_

  - [x] 3.2 Write property test for cost logging prompt_id override
    - **Property 5: Cost logging respects prompt_id override**
    - Generate random prompt_id strings and mock AI responses with random token counts
    - Call `_log_ai_cost` with the override prompt_id and verify the AIUsageLog record uses the override value
    - Verify `total_cost_usd == input_cost_usd + output_cost_usd`
    - **Validates: Requirements 7.3, 7.4, 7.5**

- [x] 4. Implement `_transcribe_image` method on the Orchestrator
  - [x] 4.1 Add `_transcribe_image` async method to `ImageAnalysisOrchestrator` in `gapsense/src/gapsense/services/image_analysis_orchestrator.py`
    - Render TRANSCRIPTION-001 prompt via `self._prompt_service.render_prompt("TRANSCRIPTION-001", country=ctx.country_key)`
    - Send image to AI client with `model=rendered.model`, `temperature=rendered.temperature`, `max_tokens=rendered.max_tokens`, `json_mode=True`
    - On success: parse JSON response into `ctx.transcription_result`
    - Concatenate `question_text` and `student_work` from each question into `ctx.transcription_text` (flat string, space-joined, skip empty values)
    - Log cost via `self._log_ai_cost(ctx, response, prompt_id="TRANSCRIPTION-001")`
    - Wrap entire method body in `try/except Exception`: on any failure, log warning, set `ctx.transcription_result = {}`, `ctx.transcription_text = ""`, return without raising
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 7.1, 7.4_

  - [x] 4.2 Write property test for transcription text concatenation
    - **Property 1: Transcription text concatenation preserves all content**
    - Generate random lists of question dicts with arbitrary `question_text` and `student_work` strings
    - Call the concatenation logic and assert every non-empty input fragment appears in the output
    - **Validates: Requirements 2.4**

  - [x] 4.3 Write property test for Stage 1 failure graceful degradation
    - **Property 2: Stage 1 failure never crashes the pipeline**
    - Generate random failure scenarios: None responses, malformed JSON, missing keys, exceptions
    - Call `_transcribe_image` with mocked AI client returning each failure
    - Assert `ctx.transcription_result == {}` and `ctx.transcription_text == ""` and no exception propagates
    - **Validates: Requirements 2.5, 2.6**

- [x] 5. Checkpoint — Verify transcription step works in isolation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Update `_build_query_text` to prefer transcription text
  - [x] 6.1 Modify `_build_curriculum_graph` in `gapsense/src/gapsense/services/image_analysis_orchestrator.py` to extract query-building into a `_build_query_text` method (or add the preference logic inline)
    - When `ctx.transcription_text` is non-empty, use it as the vector search query and skip the Claude Haiku image description call
    - When `ctx.transcription_text` is empty, fall back to the Phase 2 image description approach
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 6.2 Write property test for query text preference
    - **Property 3: Query text prefers transcription over image description**
    - Generate random non-empty strings for `transcription_text`
    - Call `_build_query_text` and assert the return value uses the transcription text
    - Assert the Haiku image description method was not called (mock verification)
    - **Validates: Requirements 4.1, 4.3**

- [x] 7. Implement `_format_transcript_for_prompt` and update `_render_prompt`
  - [x] 7.1 Add `_format_transcript_for_prompt` method to `ImageAnalysisOrchestrator`
    - Accept `transcription_result: dict`, return a formatted string
    - Include `layout`, `topic_detected`, `overall_legibility` header fields
    - For each question: display `question_number`, `question_text`, `student_work`, `teacher_mark`, `illegible_regions`
    - Return empty string if transcription_result is empty or has no questions
    - _Requirements: 5.4_

  - [x] 7.2 Update `_render_prompt` in `gapsense/src/gapsense/services/image_analysis_orchestrator.py`
    - When `ctx.transcription_result` is non-empty, call `_format_transcript_for_prompt` and pass the result as `transcript_section` in `extra_context`
    - When `ctx.transcription_result` is empty, set `transcript_section` to empty string
    - _Requirements: 5.1, 5.2, 5.5_

  - [x] 7.3 Write property test for transcript formatting completeness
    - **Property 4: Transcript formatting includes all required fields**
    - Generate random transcription results with varying numbers of questions and random field values
    - Call `_format_transcript_for_prompt` and assert the output contains every non-empty `layout`, `topic_detected`, `overall_legibility`, and per-question `question_number`, `question_text`, `student_work`
    - **Validates: Requirements 5.1, 5.2, 5.4**

- [x] 8. Update ANALYSIS-001 user template with transcript section
  - [x] 8.1 Modify the ANALYSIS-001 `user_template` in `gapsense-data/prompts/gapsense_prompt_library_v2.0_multicountry.json`
    - Add a `## STAGE 1 TRANSCRIPTION\n{{transcript_section}}` block after `## STUDENT CONTEXT` and before `## PREREQUISITE GRAPH`
    - _Requirements: 5.1, 5.2_

  - [x] 8.2 Add instruction to ANALYSIS-001 `system_prompt` about using transcript as primary source
    - Add: "If a STAGE 1 TRANSCRIPTION section is provided, use it as the primary source of student work. Use the attached image as a fallback for unclear transcript regions or diagram interpretation."
    - _Requirements: 5.3, 5.6_

  - [x] 8.3 Verify ANALYSIS-001 output schema and max_tokens are unchanged
    - Confirm `output_schema` matches the Phase 1 definition exactly
    - Confirm `max_tokens` remains 1536
    - _Requirements: 8.1, 8.2_

- [x] 9. Update `run()` method to wire in the new pipeline step
  - [x] 9.1 Modify `run()` in `gapsense/src/gapsense/services/image_analysis_orchestrator.py`
    - Insert `await self._transcribe_image(ctx)` after `_fetch_image` and before `_build_curriculum_graph`
    - Update step numbering in log messages: `_transcribe_image` is step 3, `_build_curriculum_graph` is step 4, `_render_prompt` is step 5, `_call_ai` is step 6, `_dispatch_results` is step 7
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 10. Checkpoint — Verify full pipeline integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Write unit tests for integration and edge cases
  - [x] 11.1 Write unit tests for TRANSCRIPTION-001 prompt registration
    - Verify `PromptService` can render TRANSCRIPTION-001 without error
    - Verify rendered prompt has `model="claude-sonnet-4-6"`, `temperature=0.1`, `max_tokens=2048`
    - _Requirements: 1.1, 1.4_

  - [x] 11.2 Write unit tests for ImageAnalysisContext defaults
    - Verify a fresh context has `transcription_text=""` and `transcription_result={}`
    - _Requirements: 3.1, 3.2_

  - [x] 11.3 Write unit tests for pipeline step order
    - Mock all pipeline steps, run the orchestrator, assert call order is `[load_student_context, fetch_image, transcribe_image, build_curriculum_graph, render_prompt, call_ai, dispatch_results]`
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 11.4 Write unit tests for transcript section in rendered prompt
    - With non-empty transcription_result, verify rendered ANALYSIS-001 prompt contains "STAGE 1 TRANSCRIPTION"
    - With empty transcription_result, verify rendered ANALYSIS-001 prompt does not contain "STAGE 1 TRANSCRIPTION"
    - _Requirements: 5.1, 5.5_

  - [x] 11.5 Write unit tests for dual cost logging
    - Run full pipeline with mocked AI, verify two AIUsageLog records created with prompt_ids "TRANSCRIPTION-001" and "ANALYSIS-001"
    - _Requirements: 7.1, 7.2, 7.4, 7.5_

  - [x] 11.6 Write unit tests for edge cases
    - Empty questions list produces `transcription_text=""`
    - Query fallback on empty transcription invokes the Haiku image description path
    - Image is still attached to Stage 2 call alongside transcript-enhanced prompt
    - _Requirements: 2.4, 4.2, 5.6_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate the 5 correctness properties from the design document
- Phase 1 tasks already handle adding `claude-sonnet-4-6` to the cost calculator pricing dict — no need to duplicate that here
- The current `_build_curriculum_graph` does a direct DB query (no vector search yet); task 6.1 adapts whatever query-building mechanism exists
