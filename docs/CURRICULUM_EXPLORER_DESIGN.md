# Curriculum explorer design

Status: design baseline for the next web milestone.

The current landing experience exposes a safe country and subject inventory. The next surface must
let educators inspect the curriculum hierarchy that question generation will consume, without
pretending that a phase-level folder is a reviewed level or publishing restricted source content.

## Two-level information architecture

### 1. Curriculum explorer

Route concept: `/curriculum` (the local prototype may initially implement this as a same-document
`#curriculum` surface).

The explorer provides:

- country and authority selection (Ghana/NaCCA or Uganda/NCDC);
- phase, official level, and subject selection using each country's terminology;
- a machine-generated matrix with `missing`, `located`, `extracted`, `structurally_validated`, and
  `human_reviewed` states;
- an explicit evidence-scope label (`phase_only` or `level`);
- a link into subject detail only when the selected combination has a safe local record.

### 2. Subject detail

Route concept: `/curriculum/{country}/{phase}/{level}/{subject}`.

The detail view is a teacher-readable lineage browser:

1. **Overview** — authority, curriculum version, phase/level, review state, and a plain-language
   explanation of what is and is not ready.
2. **Standards and indicators** — expandable strand → sub-strand → content standard → indicator
   tree, with stable codes and short approved labels.
3. **Prerequisites** — prerequisite graph and cascade paths, with the source and validation state
   of every edge.
4. **Assessment mapping** — question type, diagnostic purpose, misconception signal, difficulty,
   and answer/marking guidance where rights and review allow it.
5. **Sources and lineage** — source identifier, authority URL, retrieval date, SHA-256, extraction
   tool/version, and structural/human-review state.

## Example Ghana record

The existing Ghana primary Mathematics evidence demonstrates the intended lineage:

```text
curricula/ghana/primary/mathematics/
├── source_documents/
├── populated_nodes_complete.json
├── assessment_framework.json
├── prerequisite_graph_v1.2.json
├── cascade_paths.json
├── misconceptions.json
├── evidence_base.json
├── coverage_analysis.json
└── nacca_standards_mapping.json

populated_nodes_complete.json
  nodes_fully_populated
    B3.1.1.1
      nacca_content_standard: B3.N.1.1.CS1
      indicators
        B3.N.1.1.CS1.I1
          diagnostic_question_type
          diagnostic_prompt_example
          error_patterns
          difficulty_estimate
```

The web should display the stable codes, concise labels, and review metadata. It should consume
these records through a typed API rather than reading the repository directly from the browser.

## API boundary

The existing `GET /v1/curriculum/coverage` endpoint remains the overview contract. A future detail
contract should be read-only and allowlisted, for example:

```text
GET /v1/curriculum/ghana/primary/lower_primary/mathematics
```

The response should contain normalized, versioned metadata and approved derived nodes. It must not
return private filesystem paths, unbounded raw PDF text, hidden review notes, secrets, or a claim
of human approval that the data repository has not recorded.

## Teacher trust cues

- Every node carries its curriculum code and evidence state.
- A missing prerequisite edge is shown as unknown, never silently completed.
- Generated questions show the blueprint and source identifiers that organized them.
- “Located” is visibly different from “extracted” and “human reviewed.”
- Print/download output includes the same provenance boundary as the web view.

## Acceptance criteria

- A teacher can reach the explorer from the primary navigation on desktop and mobile.
- A teacher can reach a subject detail page from a matrix row when detail evidence exists.
- Keyboard, screen-reader, reduced-motion, and narrow-viewport behavior are tested.
- The API fails closed on malformed, missing, duplicate, or unauthorized detail records.
- Backend and frontend application-owned code remains at 100% line and branch coverage.
