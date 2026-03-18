# GapSense Phase 4 — Claude Code Implementation Prompt
# Grade Normalisation + Ongoing Hardening
# Estimated effort: 3-4 days | Risk: Medium (data migration)

---

## CONTEXT

Phases 1-3 are complete. The pipeline is:
- Stable and idempotent (Phase 1)
- Using hybrid RAG retrieval (Phase 2)
- Using two-stage OCR + diagnosis (Phase 3)

Phase 4 closes the remaining technical debt items that underpin
long-term correctness and Uganda/Kenya/Nigeria expansion readiness.

The primary fix is grade normalisation — a data model inconsistency
that was papered over with comments and compensated by increasing
query limits. It affects diagnostic accuracy because:

1. Without grade normalisation, the RAG query has no grade filter —
   it retrieves indicators across ALL grades for a country/subject
2. A B7 student's image can surface B4 or B9 indicators in retrieval
3. The prerequisite walk can traverse into grade-inappropriate territory

Secondary fixes are operational hardening items that become important
at scale (Uganda pilot, Athlete + Her integration).

Read `phase4_spec.md` before writing any code.

---

## YOUR MISSION

### STEP 1 — Grade Normalisation

#### 1a. Create Canonical Grade Mapping

File: `gapsense/core/grade_utils.py`

```python
"""
Grade normalisation utilities.

Problem: student.current_grade stores grades in display format
(e.g. "JHS1", "P4", "Grade 6") but curriculum_nodes use
curriculum-authority format (e.g. "B7", "P4", "G6").

These formats vary by country AND by data source (some entered
by teachers, some imported from curriculum files).

This module provides a single source of truth for grade normalisation.
"""

GRADE_MAPS: dict[str, dict[str, str]] = {
    "ghana": {
        # Display → NaCCA curriculum code
        "B1": "B1", "Primary 1": "B1", "P1": "B1", "Grade 1": "B1",
        "B2": "B2", "Primary 2": "B2", "P2": "B2", "Grade 2": "B2",
        "B3": "B3", "Primary 3": "B3", "P3": "B3", "Grade 3": "B3",
        "B4": "B4", "Primary 4": "B4", "P4": "B4", "Grade 4": "B4",
        "B5": "B5", "Primary 5": "B5", "P5": "B5", "Grade 5": "B5",
        "B6": "B6", "Primary 6": "B6", "P6": "B6", "Grade 6": "B6",
        "B7": "B7", "JHS1": "B7", "JHS 1": "B7", "JSS1": "B7",
        "B8": "B8", "JHS2": "B8", "JHS 2": "B8", "JSS2": "B8",
        "B9": "B9", "JHS3": "B9", "JHS 3": "B9", "JSS3": "B9",
    },
    "uganda": {
        # Display → NCDC curriculum code
        "P1": "P1", "Primary 1": "P1", "Grade 1": "P1",
        "P2": "P2", "Primary 2": "P2", "Grade 2": "P2",
        "P3": "P3", "Primary 3": "P3", "Grade 3": "P3",
        "P4": "P4", "Primary 4": "P4", "Grade 4": "P4",
        "P5": "P5", "Primary 5": "P5", "Grade 5": "P5",
        "P6": "P6", "Primary 6": "P6", "Grade 6": "P6",
        "P7": "P7", "Primary 7": "P7", "Grade 7": "P7",
        "S1": "S1", "Senior 1": "S1", "Form 1": "S1",
        "S2": "S2", "Senior 2": "S2", "Form 2": "S2",
        "S3": "S3", "Senior 3": "S3", "Form 3": "S3",
        "S4": "S4", "Senior 4": "S4", "Form 4": "S4",
    },
    "kenya": {
        # Display → KICD CBC format
        "G1": "G1", "Grade 1": "G1", "Standard 1": "G1",
        "G2": "G2", "Grade 2": "G2", "Standard 2": "G2",
        "G3": "G3", "Grade 3": "G3", "Standard 3": "G3",
        "G4": "G4", "Grade 4": "G4", "Standard 4": "G4",
        "G5": "G5", "Grade 5": "G5", "Standard 5": "G5",
        "G6": "G6", "Grade 6": "G6", "Standard 6": "G6",
        "G7": "G7", "Grade 7": "G7",
        "G8": "G8", "Grade 8": "G8",
        "G9": "G9", "Grade 9": "G9",
    },
    "nigeria": {
        # Display → NERDC UBE format
        "P1": "P1", "Primary 1": "P1", "Basic 1": "P1",
        "P2": "P2", "Primary 2": "P2", "Basic 2": "P2",
        "P3": "P3", "Primary 3": "P3", "Basic 3": "P3",
        "P4": "P4", "Primary 4": "P4", "Basic 4": "P4",
        "P5": "P5", "Primary 5": "P5", "Basic 5": "P5",
        "P6": "P6", "Primary 6": "P6", "Basic 6": "P6",
        "JSS1": "JSS1", "JHS1": "JSS1", "Basic 7": "JSS1",
        "JSS2": "JSS2", "JHS2": "JSS2", "Basic 8": "JSS2",
        "JSS3": "JSS3", "JHS3": "JSS3", "Basic 9": "JSS3",
    }
}

def normalise_grade(grade: str, country: str) -> str | None:
    """
    Normalise a grade string to canonical curriculum format.

    Returns None if the grade cannot be recognised for this country.
    Caller should log a warning and proceed without grade filtering.

    Examples:
        normalise_grade("JHS1", "ghana") → "B7"
        normalise_grade("P4", "uganda") → "P4"
        normalise_grade("Grade 6", "kenya") → "G6"
    """
    country_map = GRADE_MAPS.get(country.lower(), {})
    normalised = country_map.get(grade.strip())
    if normalised is None:
        # Try case-insensitive match
        grade_lower = grade.strip().lower()
        for key, value in country_map.items():
            if key.lower() == grade_lower:
                return value
    return normalised


def grade_range_for_country(country: str) -> list[str]:
    """Return all canonical grade codes for a country in order."""
    return list(dict.fromkeys(GRADE_MAPS.get(country.lower(), {}).values()))


def adjacent_grades(grade: str, country: str, radius: int = 1) -> list[str]:
    """
    Return grades within `radius` steps of the given grade.
    Used to widen curriculum queries when exact grade filter yields no results.

    Example: adjacent_grades("B7", "ghana", radius=1) → ["B6", "B7", "B8"]
    """
    all_grades = grade_range_for_country(country)
    if grade not in all_grades:
        return [grade]
    idx = all_grades.index(grade)
    start = max(0, idx - radius)
    end = min(len(all_grades), idx + radius + 1)
    return all_grades[start:end]
```

#### 1b. Apply Normalisation in `_load_student_context`

File: `gapsense/engagement/image_analysis_orchestrator.py`

```python
async def _load_student_context(self, ctx: ImageAnalysisContext) -> None:
    # ... existing load logic ...

    raw_grade = student.current_grade
    ctx.student_grade_raw = raw_grade
    ctx.student_grade = normalise_grade(raw_grade, ctx.country_key)

    if ctx.student_grade is None:
        logger.warning(
            "grade_normalisation_failed",
            raw_grade=raw_grade,
            country=ctx.country_key,
            student_id=ctx.student_id,
            message="Grade could not be normalised. Grade filter disabled for this analysis.",
        )
        ctx.student_grade = raw_grade  # use raw as fallback — no filter applied

    # ... rest of load ...
```

#### 1c. Add Grade Filter to `_vector_search`

File: `gapsense/engagement/image_analysis_orchestrator.py`

Update `_vector_search` to filter by grade when available:

```python
async def _vector_search(
    self,
    query_vector: list[float],
    country: str,
    subject: str,
    grade: str | None = None,   # ← NEW
    top_k: int = 15,
) -> list[CurriculumIndicator]:

    # Build grade filter
    if grade:
        # Include adjacent grades (radius=1) to avoid over-filtering
        from gapsense.core.grade_utils import adjacent_grades
        target_grades = adjacent_grades(grade, country, radius=1)
        grade_filter = CurriculumNode.grade.in_(target_grades)
    else:
        grade_filter = True  # no filter

    result = await self._db.execute(
        select(CurriculumIndicator)
        .join(CurriculumNode, CurriculumIndicator.node_id == CurriculumNode.id)
        .where(
            CurriculumNode.country == country,
            CurriculumNode.subject == subject,
            CurriculumIndicator.embedding.is_not(None),
            grade_filter,
        )
        .order_by(
            CurriculumIndicator.embedding.cosine_distance(query_vector)
        )
        .limit(top_k)
    )
    # ... rest unchanged ...
```

#### 1d. Store Canonical Grade on Student Record at Write Time

File: Wherever students are created/updated (registration endpoint or import).

Add a `grade_canonical` field to the `Student` model:
```python
grade_canonical = Column(String(16), nullable=True)
```

At student create/update:
```python
from gapsense.core.grade_utils import normalise_grade
student.grade_canonical = normalise_grade(
    student.current_grade,
    student.school.country  # or however country is determined
)
```

This avoids normalising on every analysis — do it once at write time.

Migration: `{timestamp}_add_student_grade_canonical.py`

---

### STEP 2 — Visibility Timeout Extension

File: `gapsense/worker/worker_service.py`

Problem: Long-running `image_analyze` tasks (30-60s including OCR + AI)
can exceed SQS visibility timeout, causing redelivery mid-processing.
Idempotency (Phase 1) catches this, but the duplicate processing
attempt still wastes resources.

Fix: Implement a visibility timeout heartbeat for long-running tasks:

```python
async def _extend_visibility_timeout(
    self,
    receipt_handle: str,
    extension_seconds: int = 60,
) -> None:
    """Extend SQS message visibility to prevent redelivery during processing."""
    try:
        async with self._session.create_client(**self._client_kwargs()) as client:
            await client.change_message_visibility(
                QueueUrl=self._queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=extension_seconds,
            )
        logger.debug("visibility_timeout_extended", seconds=extension_seconds)
    except Exception as exc:
        logger.warning("visibility_extension_failed", error=str(exc))
        # Non-fatal — idempotency guard handles redelivery

async def _process_message_with_heartbeat(
    self,
    msg: dict,
    db: AsyncSession,
) -> None:
    """Process message with periodic visibility timeout extension."""
    receipt_handle = msg.get("ReceiptHandle")

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(
        self._heartbeat_loop(receipt_handle, interval=45, extension=90)
    )

    try:
        await self._process_message(msg, db)
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

async def _heartbeat_loop(
    self,
    receipt_handle: str,
    interval: int,
    extension: int,
) -> None:
    """Periodic visibility extension. Runs until cancelled."""
    while True:
        await asyncio.sleep(interval)
        await self._extend_visibility_timeout(receipt_handle, extension)
```

---

### STEP 3 — Metrics and Observability

File: `gapsense/worker/metrics.py`

Add Prometheus-style metrics (or structured log events if Prometheus
is not in the stack — confirm with existing telemetry setup):

```python
"""
GapSense Worker Metrics

Emit structured log events that can be aggregated into dashboards.
All events follow the pattern: {metric_name, value, dimensions, timestamp}

Key metrics to track:
  - task_processing_time_ms (by task_type)
  - task_success_rate (by task_type)
  - task_retry_count (by task_type)
  - curriculum_nodes_injected (per analysis)
  - transcription_quality (legibility distribution)
  - ai_cost_per_analysis_usd (rolling average)
  - vector_search_fallback_rate (indicates embedding job staleness)
  - prerequisite_edges_traversed (per analysis)
  - dlq_depth (alert if > 10 sustained)
"""

def emit_analysis_metrics(
    ctx: "ImageAnalysisContext",
    success: bool,
    latency_ms: float,
) -> None:
    """Emit structured metrics after each image analysis."""
    logger.info(
        "analysis_metrics",
        student_id=str(ctx.student_id),
        country=ctx.country_key,
        subject=ctx.subject,
        grade=ctx.student_grade,
        success=success,
        latency_ms=round(latency_ms, 2),
        nodes_injected=ctx.retrieval_metadata.get("total_nodes_injected", 0),
        seed_nodes=len(ctx.retrieval_metadata.get("seed_node_ids", [])),
        prerequisite_nodes=len(ctx.retrieval_metadata.get("prerequisite_node_ids", [])),
        transcription_legibility=ctx.transcription_result.get("overall_legibility"),
        questions_transcribed=len(ctx.transcription_result.get("questions", [])),
        gaps_found=len(ctx.ai_response.json_parsed.get("gap_node_ids", [])) if ctx.ai_response and ctx.ai_response.json_parsed else 0,
        ai_confidence=ctx.ai_response.json_parsed.get("confidence") if ctx.ai_response and ctx.ai_response.json_parsed else None,
    )
```

---

### STEP 4 — Athlete + Her Integration Readiness

File: `gapsense/core/partner_config.py`

GapSense is licensed to Athlete + Her for Uganda student-athletes.
This creates a multi-tenant requirement: same engine, different
curriculum (Uganda/NCDC), different grade ranges (S1-S4 focus),
different partner context in prompts.

Create a thin partner config layer:

```python
@dataclass
class PartnerConfig:
    partner_id: str           # "athlete_her", "viztaedu", "gapsense_direct"
    country: str              # "uganda", "ghana", etc.
    subject_focus: list[str]  # ["mathematics"] or ["mathematics", "literacy"]
    grade_focus: list[str]    # ["S1", "S2", "S3", "S4"] for Athlete+Her
    rate_limit_per_day: int   # analysis calls per day allowed
    whatsapp_sender_id: str   # which number to send from
    report_language: str      # primary language for teacher reports

PARTNER_CONFIGS: dict[str, PartnerConfig] = {
    "athlete_her": PartnerConfig(
        partner_id="athlete_her",
        country="uganda",
        subject_focus=["mathematics"],
        grade_focus=["S1", "S2", "S3", "S4"],
        rate_limit_per_day=500,
        whatsapp_sender_id="...",
        report_language="en",
    ),
    "viztaedu": PartnerConfig(
        partner_id="viztaedu",
        country="ghana",
        subject_focus=["mathematics", "literacy"],
        grade_focus=["B4", "B5", "B6", "B7", "B8", "B9"],
        rate_limit_per_day=2000,
        whatsapp_sender_id="...",
        report_language="en",
    ),
}
```

Pass `partner_config.grade_focus` to `_vector_search` as an override
when `ctx.student_grade` is in the partner's grade focus list.
This means Athlete + Her analyses will never retrieve primary school
nodes, even if the student's grade is unclear.

---

## DELIVERABLES

1. `gapsense/core/grade_utils.py` — full implementation
2. Updated `_load_student_context` with grade normalisation
3. Updated `_vector_search` with grade filter
4. `Student.grade_canonical` field + Alembic migration
5. Visibility timeout heartbeat in worker
6. `gapsense/worker/metrics.py` — metrics emission
7. `gapsense/core/partner_config.py` — partner config layer
8. Unit tests for:
   - `normalise_grade` — all formats for all 4 countries
   - `adjacent_grades` — correct radius at boundaries (B1 has no B0)
   - `_vector_search` with grade filter applied
   - Heartbeat cancels cleanly when task completes
9. Data migration script to backfill `grade_canonical` for existing students
10. `PHASE4_CHANGES.md` — summary for handoff

---

## CONSTRAINTS

- Grade normalisation must be ADDITIVE — do not remove `current_grade`
  field. Add `grade_canonical`. Keep both.
- The normalisation fallback (use raw grade, no filter) must be silent
  at info level — only warning if normalisation fails
- Partner config must not be stored in the prompt library —
  it is infrastructure, not prompt content
- Athlete + Her configuration must not hardcode Athlete + Her branding
  into GapSense core — it must be injected via partner_config
- All metrics must be structured log events — no side-effect API calls
  in the hot path (metrics cannot slow down analysis)

---

## DONE WHEN

- `normalise_grade("JHS1", "ghana")` returns `"B7"`
- `normalise_grade("JHS1", "uganda")` returns `None` (not a Uganda grade)
- `grade_canonical` column populated for all existing students
- `_vector_search` applies grade filter when `grade_canonical` is available
- Analysis logs show `grade` field in `analysis_metrics` events
- Heartbeat test: simulate 90-second task, assert no SQS redelivery
- Partner config loads for `athlete_her` and `viztaedu` without errors
- Metrics emitted for both success and failure analysis paths
