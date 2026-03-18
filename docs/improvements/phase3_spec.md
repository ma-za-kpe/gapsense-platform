# Phase 3 Spec — Two-Stage Pipeline
# Reference document for Claude Code implementation

---

## Why Self-OCR Before Mathpix

Mathpix is the best available tool for handwritten STEM OCR.
It should be the long-term solution.

However, starting with self-OCR (using Claude for Stage 1) has
strategic advantages for Phase 3:

1. Zero new external dependencies — ship faster
2. TRANSCRIPTION-001 can be evaluated and iterated on before
   committing to a paid API contract
3. The orchestrator architecture is identical either way —
   Mathpix is a drop-in replacement for `_transcribe_image`
4. Self-OCR already understands layout context, teacher marks,
   and multi-handwriting-style pages — Mathpix is purely math OCR

### When to switch to Mathpix:

Trigger: Self-OCR confidence on handwritten math is consistently < 0.75
Evidence: Measure `transcript_questions[*].student_work` accuracy against
          manually transcribed ground truth for 50 images.
If accuracy < 75%: implement Mathpix integration.

Mathpix integration is a 1-day task at that point because the
orchestrator interface is already defined.

---

## Mathpix Future Integration (Reference Only — Do Not Implement in Phase 3)

```python
# Future _transcribe_image using Mathpix:
async def _transcribe_image_mathpix(self, ctx: ImageAnalysisContext) -> None:
    import httpx

    response = await httpx.AsyncClient().post(
        "https://api.mathpix.com/v3/text",
        headers={
            "app_id": self._settings.MATHPIX_APP_ID,
            "app_key": self._settings.MATHPIX_APP_KEY,
        },
        json={
            "src": f"data:{ctx.media_type};base64,{base64.b64encode(ctx.image_bytes).decode()}",
            "formats": ["text", "data"],
            "data_options": {
                "include_latex": True,
            }
        },
        timeout=30.0,
    )
    result = response.json()
    ctx.transcription_text = result.get("text", "")
    ctx.transcription_confidence = result.get("confidence", 0.0)
    ctx.is_handwritten = result.get("is_handwritten", True)
```

Mathpix returns LaTeX per line with confidence scores.
The self-OCR approach returns structured JSON with question-level grouping.
Mathpix output would need to be restructured to match the
`transcription_result` schema before injection into ANALYSIS-001.

---

## Cost Impact of Two-Stage Pipeline

Per analysis request:

| | Phase 2 (single-stage) | Phase 3 (two-stage) |
|---|---|---|
| Stage 1 (transcription) | — | ~500 input + 800 output tokens (Sonnet) |
| Stage 2 (diagnosis) | ~3,000 input + 500 output | ~2,500 input + 500 output |
| Image tokens | ~1,000 | ~1,000 (Stage 1) + ~1,000 (Stage 2) |
| **Total tokens** | ~4,500 | ~5,800 |
| **Approximate cost** | ~$0.018 | ~$0.023 |

Cost increase: ~28% per analysis.

Accuracy improvement expected: significant.
The tradeoff is favourable given that wrong diagnoses cost teacher time
and parent trust — far more expensive than $0.005 per image.

---

## Transcript Quality Monitoring

Add to logging pipeline:

```python
# After _transcribe_image:
logger.info(
    "transcription_quality",
    student_id=ctx.student_id,
    questions_found=len(transcript.get("questions", [])),
    legibility=transcript.get("overall_legibility"),
    illegible_count=sum(
        len(q.get("illegible_regions", []))
        for q in transcript.get("questions", [])
    ),
    handwriting_styles=transcript.get("handwriting_styles_detected", 1),
    topic=transcript.get("topic_detected"),
)
```

Build a dashboard query:
```sql
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_analyses,
    AVG(CASE WHEN log_data->>'legibility' = 'clear' THEN 1 ELSE 0 END) as pct_clear,
    AVG(CAST(log_data->>'questions_found' AS INTEGER)) as avg_questions_per_image,
    AVG(CAST(log_data->>'illegible_count' AS INTEGER)) as avg_illegible_regions
FROM ai_usage_logs
WHERE prompt_id = 'TRANSCRIPTION-001'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

This tells you whether image quality is improving or degrading over time
as more teachers are onboarded — crucial for deciding when to switch
to Mathpix.

---

## Two Sample Image Analysis

### Image 1 — Josh's two-page spread

Expected TRANSCRIPTION-001 output:
```json
{
  "layout": "two_page_spread",
  "subject_detected": "mathematics",
  "grade_detected": "Year 9",
  "topic_detected": "Compound Measures, Pythagoras, Simultaneous-adjacent topics",
  "teacher_marks_present": true,
  "questions": [
    {
      "question_number": "1",
      "question_text": "Find the HCF of 28 and 42",
      "student_work": "2e, 42 [factor tree showing 2|2, 5|2, ...] 14",
      "teacher_mark": "partial",
      "teacher_score": "2",
      "has_diagram": false,
      "illegible_regions": ["factor tree branches partially obscured"]
    },
    {
      "question_number": "4",
      "question_text": "Find the size of side x [right triangle, legs 6 and 8]",
      "student_work": "12^2 = 144, 13^2 = [circled 182, crossed out] 169, 182 - 144 = 38",
      "teacher_mark": "partial",
      "teacher_score": "2/2",
      "has_diagram": true,
      "illegible_regions": []
    }
  ],
  "overall_legibility": "partially_readable",
  "handwriting_styles_detected": 3,
  "ocr_notes": "Three distinct handwriting styles: printed questions (left page), student work (right page, blue pen), teacher marks and feedback (green pen). Teacher feedback text: 'This is not good enough Josh, you need to put in more effort. Correct your questions please!'"
}
```

### Image 2 — Simultaneous Equations

Expected TRANSCRIPTION-001 output:
```json
{
  "layout": "single_page",
  "subject_detected": "mathematics",
  "grade_detected": null,
  "topic_detected": "Simultaneous Equations",
  "teacher_marks_present": false,
  "questions": [
    {
      "question_number": "1",
      "question_text": "Worked example: 2x + 7b = 24 (equation 1), 2x + 4b = 18 (equation 2)",
      "student_work": "Equation 1 - Equation 2: 3b = 6 ÷ 3, b = 2. Sub b=2 into equation 2: 2x + 4×2 = 18, 2x + 8 = 18, 2x = 10 ÷ 2, x = 5. Therefore b=2, x=5.",
      "teacher_mark": "none",
      "teacher_score": null,
      "has_diagram": false,
      "illegible_regions": []
    }
  ],
  "overall_legibility": "clear",
  "handwriting_styles_detected": 1,
  "ocr_notes": "Single handwriting style throughout. Annotations in yellow highlighter: 'you can sub into equation 1 or 2 your choice!' and 'check your answer by subbing back in'. This appears to be a teacher-written worked example, not student-attempted work."
}
```

Note: Image 2 will produce `"teacher_marks_present": false` but the
`ocr_notes` will indicate it's a worked example. ANALYSIS-001 Stage 2
should therefore produce low `confidence` and note that no student errors
are visible — not fabricate gaps. The few-shot example in Phase 1 covers
this honest-response pattern.
