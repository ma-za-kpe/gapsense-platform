# GapSense — Image Analysis Pipeline Improvement Plan
# Master Reference Document

---

## Overview

This document coordinates four phases of improvement to the GapSense
image analysis pipeline. Each phase has a Claude Code prompt and a
companion spec file. Read both before implementing any phase.

---

## File Index

| Phase | Claude Code Prompt | Spec File | Risk |
|-------|-------------------|-----------|------|
| Phase 1 | `phase1_claude_code_prompt.md` | `phase1_spec.md` | Very Low |
| Phase 2 | `phase2_claude_code_prompt.md` | `phase2_spec.md` | Low-Medium |
| Phase 3 | `phase3_claude_code_prompt.md` | `phase3_spec.md` | Medium |
| Phase 4 | `phase4_claude_code_prompt.md` | `phase4_spec.md` | Medium |

---

## What Each Phase Fixes

### Phase 1 — Infrastructure Hardening + Prompt Surgery
**Fixes:** Worker bugs, silent failures, wrong model strings, weak prompt

- DB session concurrency (CRITICAL — data corruption risk)
- Idempotency guard (CRITICAL — duplicate diagnosis risk)
- AIUsageLog commit vs flush (silent cost tracking loss)
- Stub honesty — TTS/STT silently succeed instead of raising
- Error classification — permanent vs retryable errors
- Delete-then-requeue race condition
- FIFO queue retry bug
- ANALYSIS-001 few-shot example
- Model string corrections
- Visual analysis rules strengthened

**Does not touch:** Retrieval, OCR, grade data

---

### Phase 2 — Hybrid RAG Retrieval
**Fixes:** 100-node context dump → 10-15 relevant nodes

- pgvector extension + embedding column migration
- EmbeddingService (OpenAI or local MiniLM)
- Curriculum embedding job (runs at import time)
- `_build_curriculum_graph` → hybrid vector + graph traversal
- Prerequisite edges table + recursive CTE walk
- ANALYSIS-001 user template updated with retrieval metadata

**Requires Phase 1 complete.**
**Does not touch:** OCR stage, grade normalisation

---

### Phase 3 — Two-Stage OCR + Diagnosis
**Fixes:** Single-pass vision → dedicated transcription + reasoning

- TRANSCRIPTION-001 prompt (new)
- `_transcribe_image` orchestrator step (new)
- Transcript fed to vector search query (replaces image description)
- ANALYSIS-001 user template updated with transcript injection
- Dual cost logging (TRANSCRIPTION-001 + ANALYSIS-001)

**Requires Phase 2 complete.**
**Does not touch:** Grade normalisation, partner config

---

### Phase 4 — Grade Normalisation + Ongoing Hardening
**Fixes:** Grade format inconsistency, operational readiness

- `grade_utils.py` — canonical grade mapping for all 4 countries
- `Student.grade_canonical` field + backfill migration
- Grade filter in vector search
- SQS visibility timeout heartbeat
- Structured metrics emission
- Partner config layer (Athlete + Her, ViztaEdu)

**Requires Phase 2 complete (grade filter feeds vector search).**
**Can run in parallel with Phase 3.**

---

## How to Use These Prompts with Claude Code

### Setup
```bash
# Ensure Claude Code has access to the full GapSense codebase
# before starting any phase

claude-code --workspace /path/to/gapsense
```

### Per Phase
1. Open the Claude Code prompt file for the phase
2. Copy the entire contents into Claude Code's context
3. Also paste the companion spec file contents
4. Tell Claude Code: "Implement everything in this prompt.
   Read the spec file carefully before writing any code."
5. Review all generated files before merging

### Phase Validation
Each prompt has a "DONE WHEN" section. Use it as your acceptance
criteria before marking a phase complete and starting the next.

---

## Architecture State After All Four Phases

```
WhatsApp Image Received
        │
        ▼
SQS → WorkerService
  │   ├── Idempotency check (Phase 1)
  │   ├── Session factory per task (Phase 1)
  │   └── Error classification (Phase 1)
        │
        ▼
ImageAnalysisOrchestrator.run()
  │
  ├── _load_student_context()
  │     └── normalise_grade() → grade_canonical (Phase 4)
  │
  ├── _fetch_image()
  │     └── S3 download + MIME detection
  │
  ├── _transcribe_image()  ← Phase 3 (NEW)
  │     ├── TRANSCRIPTION-001 prompt
  │     ├── Returns: structured transcript per question
  │     └── ctx.transcription_text for vector query
  │
  ├── _build_curriculum_graph()  ← Phase 2 (REPLACED)
  │     ├── embed(ctx.transcription_text)
  │     ├── vector_search(grade_filter=ctx.grade_canonical)  ← Phase 4
  │     ├── walk_prerequisites(depth=2)
  │     └── 10-15 relevant nodes (not 100)
  │
  ├── _render_prompt()
  │     └── ANALYSIS-001 with transcript + RAG subgraph
  │
  ├── _call_ai()  ← Stage 2: reasoning on text
  │     └── _log_ai_cost() with commit() (Phase 1)
  │
  └── _dispatch_results()
        └── ExerciseBookScanner.process_analysis_result()

Metrics emitted after each analysis (Phase 4)
Partner config applied throughout (Phase 4)
```

---

## Dependency Map

```
Phase 1  ──────────────────────────────► Phase 2
         (must complete first)
                    │
                    ▼
                Phase 3     Phase 4
                    │           │
                    └─────┬─────┘
                          ▼
                    Production Ready
                    (Uganda Pilot +
                     Athlete + Her)
```

Phase 4 has two parallel streams:
- Stream A (grade normalisation) → depends on Phase 2
- Stream B (ops hardening) → independent, can start anytime

---

## Cost Projections After All Phases

Per image analysis:

| Phase | Stage 1 | Stage 2 | Total |
|-------|---------|---------|-------|
| Baseline (current) | — | ~$0.022 | ~$0.022 |
| After Phase 2 (RAG) | — | ~$0.015 | ~$0.015 |
| After Phase 3 (two-stage) | ~$0.008 | ~$0.012 | ~$0.020 |

Cost is broadly neutral with significant accuracy gains.
At 1,000 analyses/day: ~$20/day. Well within educational SaaS margins.

---

## Key Decisions Locked

These decisions were made during the design process and are not
up for re-evaluation during implementation:

1. **pgvector over external vector DB** — we're already on Postgres,
   no new infrastructure needed at GapSense's current scale.

2. **Self-OCR (Claude) over Mathpix for Phase 3** — ship faster,
   evaluate accuracy, add Mathpix later if needed. Architecture
   supports drop-in replacement.

3. **Indicator-level embeddings not node-level** — error patterns
   are the semantic signal; node-level averages them into noise.

4. **depth=2 for prerequisite walk** — covers root cause in >90%
   of Ghana/Uganda primary math cases. Configurable per environment.

5. **top_k=15 for vector search** — empirical sweet spot.
   Monitor and adjust if diagnostic accuracy diverges.

6. **Grade filter uses adjacent_grades(radius=1)** — prevents
   over-filtering when grade boundary cases arise.
