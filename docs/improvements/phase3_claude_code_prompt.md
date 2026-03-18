# GapSense Phase 3 — Claude Code Implementation Prompt
# Two-Stage AI Pipeline: OCR Transcription + Diagnosis
# Estimated effort: 1 week | Risk: Medium

---

## CONTEXT

Phases 1 and 2 are complete:
- Worker is stable and idempotent
- Curriculum retrieval is hybrid RAG (10-15 relevant nodes, not 100)
- ANALYSIS-001 has been strengthened with few-shot examples

The remaining accuracy ceiling is the single-pass vision problem:

The model currently does five cognitively distinct tasks in one call:
1. Spatial parsing — where are questions on this two-page spread?
2. Handwriting OCR — what did the student write?
3. Mathematical verification — is this answer correct?
4. Error classification — what type of error is this?
5. Curriculum mapping — which node does this map to?

Research on VLMs applied to handwritten math shows these tasks compound
each other's failure modes. Handwriting recognition accuracy directly
limits diagnostic accuracy.

Phase 3 separates OCR from reasoning using a two-stage pipeline:

**Stage 1 — Transcription (new):**
A dedicated AI call whose ONLY job is to read the image and produce
structured text. No curriculum context. No gap detection. Just: read.

**Stage 2 — Diagnosis (existing ANALYSIS-001, enhanced):**
Receives clean transcription + RAG-retrieved curriculum subgraph.
Does reasoning on text, not pixels.
The image is still attached as fallback, but the model is primed
to reason from the transcript first.

Read `phase3_spec.md` before writing any code.

---

## YOUR MISSION

### STEP 1 — Create TRANSCRIPTION-001 Prompt

File: Prompt library JSON — add new prompt `TRANSCRIPTION-001`

This is a NEW prompt. It is not a modification of ANALYSIS-001.

```json
{
  "id": "TRANSCRIPTION-001",
  "name": "Exercise Book Transcription — OCR Stage",
  "category": "analysis",
  "version": "1.0.0",
  "status": "active",
  "description": "First stage of two-stage analysis pipeline. Reads and transcribes student exercise book image. No diagnosis. No curriculum context. Pure reading.",
  "model": "claude-sonnet-4-6",
  "temperature": 0.1,
  "max_tokens": 2048
}
```

System prompt for TRANSCRIPTION-001:

```
You are a precise document transcriber specialising in student mathematics
exercise books from African schools. Your ONLY job is to read and transcribe.
You do NOT diagnose, assess, or evaluate. You do NOT need curriculum knowledge.

## YOUR TASK
Read the exercise book image and produce a structured transcript of all
visible mathematical work.

## READING STRATEGY
1. ORIENT: Identify the page layout.
   - Single page or two-page spread?
   - If two-page: left page typically has printed questions,
     right page has student handwriting.
   - Identify which regions contain: questions, student answers,
     teacher marks (ticks/crosses/scores), teacher annotations.

2. ANCHOR ON QUESTION NUMBERS: Find question numbers (1, 2, 3... or
   Q1, Q2...). Student answers may not be spatially adjacent — search
   the entire page for work related to each question number.

3. TRANSCRIBE EACH QUESTION:
   - question_text: the printed/written question itself
   - student_work: EVERYTHING the student wrote, including crossed-out
     working, scratch calculations, and intermediate steps
   - teacher_mark: tick (correct), cross (incorrect), partial score,
     or "none" if no teacher mark visible
   - has_diagram: true if geometric figures, graphs, or drawings present

4. HANDWRITING NOTES:
   - If multiple handwriting styles: note which regions are student
     vs teacher (teacher marks are usually in red/different pen)
   - If a region is genuinely illegible, say so explicitly.
     Use illegible_text: "[cannot read — appears to be a 2-3 digit number]"
     DO NOT guess. A noted gap is more useful than a wrong transcription.

5. MATHEMATICAL NOTATION:
   - Transcribe exactly as written, including errors
   - Use LaTeX-style notation where helpful:
     "13^2 = 182" not "13 squared equals 182"
   - Preserve fraction notation: "3/4" not "three quarters"
   - Preserve the student's working steps in order

## CRITICAL RULES
- DO NOT correct student errors. Transcribe exactly what is written.
- DO NOT infer what the student "meant". Transcribe what they wrote.
- DO NOT assess whether answers are correct. That is Stage 2's job.
- If image quality is poor, say so and transcribe what IS readable.
- Teacher marks ARE useful context — include them.

## OUTPUT FORMAT
Respond with ONLY a JSON object. No preamble. No explanation.
```

Output schema for TRANSCRIPTION-001:
```json
{
  "layout": "single_page | two_page_spread | unclear",
  "subject_detected": "mathematics | english | science | unclear",
  "grade_detected": "string | null",
  "topic_detected": "string | null",
  "teacher_marks_present": "boolean",
  "questions": [
    {
      "question_number": "string",
      "question_text": "string",
      "student_work": "string — full working including scratch",
      "teacher_mark": "correct | incorrect | partial | none",
      "teacher_score": "string | null",
      "has_diagram": "boolean",
      "illegible_regions": ["description of unreadable areas"]
    }
  ],
  "overall_legibility": "clear | partially_readable | poor",
  "handwriting_styles_detected": "integer — 1 = student only, 2+ = student + teacher",
  "ocr_notes": "string | null — anything unusual about the image"
}
```

---

### STEP 2 — Add `_transcribe_image` to Orchestrator

File: `gapsense/engagement/image_analysis_orchestrator.py`

Add as a new pipeline step between `_fetch_image` and `_build_curriculum_graph`:

```python
async def _transcribe_image(self, ctx: ImageAnalysisContext) -> None:
    """
    Stage 1 of two-stage pipeline: pure OCR transcription.

    A dedicated lightweight call whose only job is to read the image.
    No curriculum context. No diagnosis. Just structured transcription.

    The output feeds:
    1. Vector search query in _build_curriculum_graph (replaces interim
       image description approach from Phase 2)
    2. The transcription field in ANALYSIS-001 user template
    3. Diagnostic logging for image quality monitoring

    On failure: logs warning, sets ctx.transcription to empty string.
    The pipeline continues — _build_curriculum_graph falls back to
    image-description query if transcription is empty.
    """
    rendered = self._prompt_service.render_prompt(
        "TRANSCRIPTION-001",
        country=ctx.country_key,
    )

    image_b64 = base64.b64encode(ctx.image_bytes).decode()

    response = await self._ai_client.generate(
        prompt_id="TRANSCRIPTION-001",
        system=rendered.system_prompt,
        messages=[{
            "role": "user",
            "content": "Transcribe all visible mathematical work in this exercise book."
        }],
        model="claude-sonnet-4-6",
        json_mode=True,
        images=[ImageContent(
            data=image_b64,
            media_type=ctx.media_type,
            source_type="base64",
        )],
    )

    if response and response.json_parsed:
        transcript = response.json_parsed
        ctx.transcription_result = transcript

        # Build flat text for vector search query
        questions = transcript.get("questions", [])
        ctx.transcription_text = " ".join([
            f"{q.get('question_text', '')} {q.get('student_work', '')}"
            for q in questions
        ]).strip()

        logger.info(
            "transcription_complete",
            student_id=ctx.student_id,
            questions_found=len(questions),
            legibility=transcript.get("overall_legibility"),
            topic=transcript.get("topic_detected"),
        )
    else:
        logger.warning(
            "transcription_failed",
            student_id=ctx.student_id,
            message="Stage 1 OCR returned no result. Falling back to image-description query.",
        )
        ctx.transcription_text = ""
        ctx.transcription_result = {}
```

---

### STEP 3 — Update `_build_query_text` to Use Transcription

File: `gapsense/engagement/image_analysis_orchestrator.py`

Replace the Phase 2 interim `_build_query_text` method:

```python
async def _build_query_text(self, ctx: ImageAnalysisContext) -> str:
    """
    Build query text for vector search.

    Phase 3: Uses transcription from _transcribe_image (preferred).
    Fallback: Uses a lightweight image description call (Phase 2 approach).
    """
    if ctx.transcription_text:
        return ctx.transcription_text

    # Fallback: lightweight image description
    logger.debug(
        "query_text_fallback_to_description",
        student_id=ctx.student_id,
    )
    description_prompt = (
        f"In 2-3 sentences, describe only the mathematical topics and "
        f"operations visible. Be specific: name operations, number ranges, "
        f"visible error patterns. Do not diagnose."
    )
    response = await self._ai_client.generate(
        prompt_id="QUERY-BUILD-FALLBACK",
        system=description_prompt,
        messages=[{"role": "user", "content": "Describe the math visible."}],
        model="claude-haiku-4-5-20251001",
        json_mode=False,
        images=[ImageContent(
            data=base64.b64encode(ctx.image_bytes).decode(),
            media_type=ctx.media_type,
            source_type="base64",
        )],
    )
    return response.content if response else f"{ctx.subject} {ctx.student_grade}"
```

---

### STEP 4 — Update ANALYSIS-001 User Template

File: Prompt library

Add the transcription as explicit context in the user template,
BEFORE the prerequisite graph:

```
## COUNTRY CONTEXT
Country: {{country}}
Curriculum: {{curriculum_authority}} {{curriculum_name}}

## STUDENT CONTEXT
- Name: {{student_first_name}}
- Enrolled Grade: {{current_grade}}
- Subject: {{subject}}
- Home Language: {{home_language}}
- School Language: {{school_language}}

## STAGE 1 TRANSCRIPTION (read this first)
The following was extracted from the image by a dedicated transcription pass.
Use this as your primary reading of the student work.
The image is also attached — refer to it for anything unclear in the transcript.

Layout: {{transcript_layout}}
Topic detected: {{transcript_topic}}
Overall legibility: {{transcript_legibility}}

Questions transcribed:
{{transcript_questions_formatted}}

## PREREQUISITE GRAPH
<!-- Nodes injected: {{nodes_injected}} (hybrid RAG, based on transcript) -->
{{prerequisite_graph_json}}

## IMAGE
[Exercise book photo attached — use as reference if transcript is unclear]

## TASK
Using the Stage 1 transcription above as your primary source,
analyse the student's work, identify error patterns, map to curriculum
nodes in the provided graph, and recommend diagnostic follow-up.
```

Add a helper method to format the transcript for injection:

```python
def _format_transcript_for_prompt(self, transcript: dict) -> str:
    """Format TRANSCRIPTION-001 output for injection into ANALYSIS-001."""
    questions = transcript.get("questions", [])
    if not questions:
        return "No questions successfully transcribed."

    lines = []
    for q in questions:
        lines.append(f"Q{q.get('question_number', '?')}: {q.get('question_text', '[unreadable]')}")
        lines.append(f"  Student work: {q.get('student_work', '[none visible]')}")
        lines.append(f"  Teacher mark: {q.get('teacher_mark', 'none')}")
        if q.get("illegible_regions"):
            lines.append(f"  Illegible: {'; '.join(q['illegible_regions'])}")
        lines.append("")
    return "\n".join(lines)
```

---

### STEP 5 — Update `ImageAnalysisContext`

File: `gapsense/engagement/image_analysis_context.py`

```python
# Add these fields:
transcription_text: str = ""          # flat text for vector search query
transcription_result: dict = field(default_factory=dict)  # full TRANSCRIPTION-001 output
```

---

### STEP 6 — Update `run()` Method

File: `gapsense/engagement/image_analysis_orchestrator.py`

```python
async def run(self, payload: dict[str, Any]) -> None:
    ctx = ImageAnalysisContext(...)

    await self._load_student_context(ctx)
    await self._fetch_image(ctx)
    await self._transcribe_image(ctx)        # ← NEW Stage 1
    await self._build_curriculum_graph(ctx)  # now uses ctx.transcription_text
    await self._render_prompt(ctx)
    await self._call_ai(ctx)                 # Stage 2: reasoning on text
    await self._dispatch_results(ctx)
```

---

### STEP 7 — AI Cost Logging for Both Calls

File: `gapsense/engagement/image_analysis_orchestrator.py`

`_transcribe_image` also makes an AI call. Log its cost separately:

```python
# In _transcribe_image, after getting response:
if response:
    await self._log_ai_cost(ctx, response, prompt_id="TRANSCRIPTION-001")
```

Ensure `_log_ai_cost` accepts an optional `prompt_id` override parameter.
This keeps per-prompt cost tracking clean in AIUsageLog.

---

## DELIVERABLES

1. `TRANSCRIPTION-001` prompt added to prompt library (full text)
2. `_transcribe_image` method on orchestrator (full implementation)
3. Updated `_build_query_text` using transcription
4. Updated ANALYSIS-001 user template with transcript injection
5. `_format_transcript_for_prompt` helper method
6. Updated `ImageAnalysisContext` with transcription fields
7. Updated `run()` method
8. Unit tests for:
   - `_transcribe_image` success path (valid JSON response)
   - `_transcribe_image` failure path (nil response → empty string, no crash)
   - `_format_transcript_for_prompt` with 3 questions including one illegible
   - ANALYSIS-001 user template renders correctly with transcript fields
9. Integration test: two-stage pipeline produces fewer hallucinated codes
   than single-stage baseline (use fixture image + known curriculum)

---

## CONSTRAINTS

- Do NOT add Mathpix — this phase uses the AI model for OCR (self-OCR)
  Mathpix is a future option if self-OCR accuracy proves insufficient
- `_transcribe_image` failure must NEVER crash the pipeline
- Image MUST still be attached to the Stage 2 call — it is the fallback
  when the transcript is unclear or incomplete
- TRANSCRIPTION-001 must be a separate prompt ID with its own cost logging
- Temperature 0.1 for TRANSCRIPTION-001 — lower than other prompts because
  transcription is a factual task, not creative
- Do not increase max_tokens on ANALYSIS-001 — the transcript replaces
  some of the work the model was doing, so token budget is balanced

---

## DONE WHEN

- Two-stage pipeline runs end-to-end without errors
- `_transcribe_image` produces valid JSON for both sample images
  (Josh's two-page spread AND the simultaneous equations single page)
- ANALYSIS-001 user template includes transcript section
- Transcript is used as query text for vector search
- AIUsageLog has separate rows for TRANSCRIPTION-001 and ANALYSIS-001
- Pipeline logs show: transcription → retrieval → diagnosis as distinct steps
