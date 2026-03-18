# Requirements Document

## Introduction

Phase 3 of the GapSense improvement plan separates the current single-pass image analysis into a two-stage pipeline. Stage 1 performs dedicated OCR transcription of student exercise book photos into structured JSON. Stage 2 receives the clean transcription alongside RAG-retrieved curriculum context to perform learning-gap diagnosis on text rather than pixels. This separation improves diagnostic accuracy by giving the analysis model a reliable textual representation of student work, reducing hallucinated readings and misidentified handwriting. The transcription text also replaces the Phase 2 image-description approach for vector search queries, yielding more accurate curriculum retrieval.

## Glossary

- **Orchestrator**: The `ImageAnalysisOrchestrator` service that executes the multi-step image analysis pipeline
- **Pipeline**: The ordered sequence of steps executed by the Orchestrator for each image analysis request
- **Stage_1**: The dedicated transcription AI call using the TRANSCRIPTION-001 prompt that reads and transcribes student work from an image into structured JSON
- **Stage_2**: The diagnosis AI call using the enhanced ANALYSIS-001 prompt that reasons over transcription text and curriculum context to identify learning gaps
- **TRANSCRIPTION-001**: The prompt identifier for the Stage 1 transcription prompt in the prompt library
- **ANALYSIS-001**: The prompt identifier for the Stage 2 diagnosis prompt in the prompt library
- **Transcription_Result**: The structured JSON object produced by Stage 1 containing layout, detected metadata, and per-question transcription data
- **Transcription_Text**: A flat text string concatenated from question_text and student_work fields of the Transcription_Result, used as the vector search query
- **ImageAnalysisContext**: The dataclass that carries mutable pipeline state across all steps
- **Prompt_Service**: The service that renders prompts from the prompt library for AI calls
- **Cost_Calculator**: The service that computes token costs for AI usage logging
- **AIUsageLog**: The database record that tracks token counts and costs per AI call
- **Curriculum_Subgraph**: The RAG-retrieved subset of curriculum nodes and prerequisite relationships provided to Stage 2
- **Vector_Search**: The retrieval step that finds relevant curriculum nodes by embedding similarity against a query string
- **Image_Description**: The Phase 2 approach where Claude Haiku generates a textual description of the image for use as a vector search query

## Requirements

### Requirement 1: TRANSCRIPTION-001 Prompt Definition

**User Story:** As a GapSense developer, I want a dedicated transcription prompt in the prompt library, so that Stage 1 produces structured OCR output without any diagnostic reasoning.

#### Acceptance Criteria

1. THE Prompt_Service SHALL contain a prompt registered under the identifier TRANSCRIPTION-001
2. THE TRANSCRIPTION-001 prompt SHALL instruct the AI model to perform ONLY transcription of visible student work without correcting errors, inferring intent, or assessing correctness
3. THE TRANSCRIPTION-001 prompt SHALL instruct the AI model to follow the sequence: orient to page layout, anchor on question numbers, transcribe each question, note handwriting characteristics, and preserve mathematical notation
4. WHEN the Orchestrator invokes Stage_1, THE Orchestrator SHALL use model claude-sonnet-4-6 with temperature 0.1 and max_tokens 2048
5. THE TRANSCRIPTION-001 prompt SHALL require the AI model to return a JSON object containing the fields: layout, subject_detected, grade_detected, topic_detected, teacher_marks_present, questions (array), overall_legibility, handwriting_styles_detected, and ocr_notes
6. WHEN the AI model transcribes a question, THE TRANSCRIPTION-001 prompt SHALL require each question object to contain the fields: question_number, question_text, student_work, teacher_mark, teacher_score, has_diagram, and illegible_regions

### Requirement 2: Transcribe Image Pipeline Step

**User Story:** As a GapSense developer, I want a dedicated transcription step in the pipeline, so that the image is transcribed into structured text before curriculum retrieval and diagnosis.

#### Acceptance Criteria

1. THE Orchestrator SHALL execute a `_transcribe_image` step after `_fetch_image` and before `_build_curriculum_graph` in the Pipeline
2. WHEN `_transcribe_image` executes, THE Orchestrator SHALL send the fetched image to the AI client with the TRANSCRIPTION-001 prompt
3. WHEN Stage_1 returns a valid JSON response, THE Orchestrator SHALL parse the response and store the result in the ImageAnalysisContext transcription_result field
4. WHEN Stage_1 returns a valid JSON response, THE Orchestrator SHALL concatenate the question_text and student_work fields from each question into a flat string and store the result in the ImageAnalysisContext transcription_text field
5. IF Stage_1 returns an invalid response or an error occurs during transcription, THEN THE Orchestrator SHALL log a warning, set transcription_result to an empty dict, set transcription_text to an empty string, and allow the Pipeline to continue
6. IF Stage_1 fails, THEN THE Orchestrator SHALL NOT raise an exception or halt the Pipeline

### Requirement 3: ImageAnalysisContext Transcription Fields

**User Story:** As a GapSense developer, I want the pipeline context to carry transcription data, so that downstream steps can access the structured transcription and flat text.

#### Acceptance Criteria

1. THE ImageAnalysisContext SHALL contain a `transcription_text` field of type string with a default value of empty string
2. THE ImageAnalysisContext SHALL contain a `transcription_result` field of type dict with a default value of empty dict

### Requirement 4: Transcription-Based Vector Search Query

**User Story:** As a GapSense developer, I want the vector search query to use the transcription text instead of the image description, so that curriculum retrieval is more accurate.

#### Acceptance Criteria

1. WHEN transcription_text is non-empty, THE Orchestrator SHALL use transcription_text as the query input to Vector_Search in `_build_query_text`
2. WHEN transcription_text is empty, THE Orchestrator SHALL fall back to the Phase 2 Image_Description approach for building the vector search query
3. WHEN transcription_text is used as the query, THE Orchestrator SHALL NOT invoke the Claude Haiku image description call

### Requirement 5: Enhanced ANALYSIS-001 Prompt with Transcript Section

**User Story:** As a GapSense developer, I want the Stage 2 prompt to include the structured transcription, so that the diagnosis model reasons primarily on text rather than pixels.

#### Acceptance Criteria

1. WHEN transcription_result is non-empty, THE Prompt_Service SHALL include a "STAGE 1 TRANSCRIPTION" section in the ANALYSIS-001 user template before the prerequisite graph section
2. THE "STAGE 1 TRANSCRIPTION" section SHALL display the layout, topic_detected, overall_legibility, and formatted question details from the Transcription_Result
3. THE ANALYSIS-001 prompt SHALL instruct the AI model to use the transcript as the primary source of student work and the image as a fallback for unclear transcript regions
4. THE Orchestrator SHALL provide a `_format_transcript_for_prompt` helper method that formats the questions from Transcription_Result into a human-readable text block for prompt inclusion
5. WHEN transcription_result is empty, THE Prompt_Service SHALL render the ANALYSIS-001 template without the "STAGE 1 TRANSCRIPTION" section
6. WHEN Stage_2 is invoked, THE Orchestrator SHALL attach the original image to the AI call alongside the transcript-enhanced prompt

### Requirement 6: Updated Pipeline Step Order

**User Story:** As a GapSense developer, I want the pipeline to execute steps in the correct order, so that transcription is available before curriculum retrieval and diagnosis.

#### Acceptance Criteria

1. THE Orchestrator `run()` method SHALL execute steps in the order: load_student_context, fetch_image, transcribe_image, build_curriculum_graph, render_prompt, call_ai, dispatch_results
2. WHEN the Pipeline executes, THE Orchestrator SHALL complete `_transcribe_image` before invoking `_build_curriculum_graph`
3. WHEN the Pipeline executes, THE Orchestrator SHALL complete `_build_curriculum_graph` before invoking `_render_prompt`

### Requirement 7: Dual Cost Logging

**User Story:** As a GapSense operator, I want separate cost tracking for the transcription and diagnosis AI calls, so that I can monitor and optimize spending per stage.

#### Acceptance Criteria

1. WHEN Stage_1 completes, THE Orchestrator SHALL create a separate AIUsageLog record with prompt_id set to TRANSCRIPTION-001
2. WHEN Stage_2 completes, THE Orchestrator SHALL create a separate AIUsageLog record with prompt_id set to ANALYSIS-001
3. THE Orchestrator `_log_ai_cost` method SHALL accept an optional `prompt_id` parameter to override the default prompt identifier
4. THE AIUsageLog record for Stage_1 SHALL contain the token counts and computed cost specific to the TRANSCRIPTION-001 call
5. THE AIUsageLog record for Stage_2 SHALL contain the token counts and computed cost specific to the ANALYSIS-001 call

### Requirement 8: ANALYSIS-001 Output Schema Preservation

**User Story:** As a GapSense developer, I want the Stage 2 output schema to remain unchanged, so that downstream consumers are not affected by the two-stage refactor.

#### Acceptance Criteria

1. THE ANALYSIS-001 prompt SHALL NOT modify the output schema defined in Phase 1
2. THE ANALYSIS-001 prompt SHALL NOT increase the max_tokens parameter beyond the value set in Phase 1

### Requirement 9: Transcription Fidelity

**User Story:** As a GapSense developer, I want the transcription to faithfully reproduce student work including errors, so that the diagnosis model can accurately identify learning gaps.

#### Acceptance Criteria

1. THE TRANSCRIPTION-001 prompt SHALL instruct the AI model to transcribe student work exactly as written, preserving all spelling errors, mathematical mistakes, and incomplete work
2. THE TRANSCRIPTION-001 prompt SHALL instruct the AI model to mark regions that cannot be read as illegible rather than guessing content
3. THE TRANSCRIPTION-001 prompt SHALL instruct the AI model to preserve the original mathematical notation used by the student without converting to canonical forms
