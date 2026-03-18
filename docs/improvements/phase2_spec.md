# Phase 2 Spec — Hybrid RAG Retrieval
# Reference document for Claude Code implementation

---

## Embedding Strategy

### What gets embedded (per indicator):

```
Curriculum node: {node_code} — {node_title}
Indicator: {indicator_code} — {indicator_title}
Common errors: {ep1}; {ep2}; {ep3}
```

### Why indicator level, not node level:

A CurriculumNode might be "Number Operations — B7.1.1"
Its indicators are:
  - B7.1.1.1: Adding integers with carrying
  - B7.1.1.2: Subtracting with regrouping
  - B7.1.1.3: Multiplying two-digit numbers

These are semantically distinct. Node-level embedding averages them into
noise. Indicator-level embedding preserves specificity.

The error patterns are the highest-signal text:
  "student writes carry digit in wrong column" ← semantically matches
  an image where the teacher has circled a misplaced carry mark.

### Embedding model decision:

| Model | Dimensions | Cost | Offline | Recommendation |
|-------|-----------|------|---------|----------------|
| OpenAI text-embedding-3-small | 1536 | ~$0.00002/1k tokens | No | **Production** |
| OpenAI text-embedding-3-large | 3072 | ~$0.00013/1k tokens | No | Overkill |
| all-MiniLM-L6-v2 (sentence-transformers) | 384 | Free | Yes | **Dev/offline** |
| bge-small-en-v1.5 | 384 | Free | Yes | Alternative offline |

Decision: Use OpenAI in production (set via EMBEDDING_MODEL=openai).
Use MiniLM locally (set via EMBEDDING_MODEL=minilm).
Store model name in `curriculum_indicators.embedding_model` column.
NEVER mix models — add a validation check at embedding job start.

### Estimated embedding job scale:

Ghana mathematics full curriculum:
- ~150 curriculum nodes
- ~450 indicators (3 per node average)
- ~450 text chunks to embed
- At batch size 100: 5 API calls
- Total cost: ~$0.01 (negligible)
- Time: ~10 seconds

All 4 countries × 2 subjects (math + literacy):
- ~3,600 indicators
- ~$0.08 total
- ~80 seconds

This is a one-time cost per curriculum import. Not per-request.

---

## Retrieval Parameters

### top_k = 15 rationale:

- Too few (< 8): Risk of missing the actual gap node if error pattern
  wording doesn't closely match indicator text
- Sweet spot (10-15): Covers the gap + 2-3 adjacent nodes for context
- Too many (> 20): Starts approaching the noise problem we're solving

Start with top_k=15. Monitor diagnostic accuracy. Adjust if needed.

### depth = 2 rationale:

- Depth 1: Direct prerequisites (the "you need X to do Y" relationship)
- Depth 2: Grandparent prerequisites (the root cause level)
- Depth 3+: Rarely relevant — too far removed from the presented work
- Most root causes in Ghana primary/JHS math are within 2 hops

Example chain:
  B7.1.3.1 (Pythagoras) ← depth 0 (seed)
  B6.4.2.1 (Squaring)   ← depth 1
  B5.3.1.1 (Times tables) ← depth 2  ← this is often the real root cause

---

## pgvector Setup Notes

### IVFFlat vs HNSW index:

IVFFlat: Better for batch ingestion, slightly slower queries.
HNSW: Better query performance, more memory.

For GapSense scale (~3,600 total indicators):
- IVFFlat with lists=100 is more than sufficient
- HNSW would be appropriate at 100k+ vectors

### Cosine vs L2 distance:

Use cosine distance (`vector_cosine_ops`) for text embeddings.
OpenAI embeddings are normalised — cosine and dot product are equivalent.
L2 (Euclidean) is less appropriate for semantic similarity tasks.

### Query syntax (SQLAlchemy + pgvector):

```python
from pgvector.sqlalchemy import Vector

# In model:
class CurriculumIndicator(Base):
    embedding = Column(Vector(1536), nullable=True)

# In query:
from sqlalchemy import func
.order_by(CurriculumIndicator.embedding.cosine_distance(query_vector))
```

Install: `pip install pgvector` (adds SQLAlchemy support automatically)

---

## Fallback Behaviour Specification

The fallback must be TRANSPARENT — log clearly when it triggers:

```
Scenario 1: Embeddings exist → use vector search (normal path)
Scenario 2: No embeddings for country/subject → fallback to code-ordered
            SELECT with limit 20. Log warning. Continue.
Scenario 3: pgvector extension not installed → catch OperationalError,
            fallback to code-ordered SELECT. Log error. Alert ops.
Scenario 4: Embedding service unavailable → skip query building step,
            use "{subject} {grade}" as query text, proceed with
            vector search using generic embedding.
```

Never let retrieval failure crash the orchestrator.
A degraded analysis is better than no analysis.

---

## Prerequisite Edge Data Source

Before the recursive CTE can work, prerequisite edges must exist in the DB.

Check whether edges are already stored in the existing schema:
- Look for `prerequisites` or `prerequisite_nodes` fields on `CurriculumNode`
- Look for an existing adjacency table

If edges are stored as an array field on CurriculumNode (common pattern):
```python
# Migration: Extract edges from array into dedicated table
# This runs once and can be scripted as part of the migration
INSERT INTO curriculum_prerequisite_edges (from_node_id, to_node_id, country)
SELECT
    prereq.id AS from_node_id,
    n.id AS to_node_id,
    n.country
FROM curriculum_nodes n
CROSS JOIN LATERAL unnest(n.prerequisite_node_ids) AS prereq_id
JOIN curriculum_nodes prereq ON prereq.id = prereq_id
ON CONFLICT DO NOTHING;
```

If no edge data exists at all:
- Add this as a data quality note
- The graph traversal step will return empty set (graceful — no crash)
- Only vector search results will be used
- Log `"prerequisite_edges_empty"` warning

---

## Token Count Validation

Add this assertion to the integration test:

```python
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4")  # Claude uses similar tokenisation

before_tokens = len(enc.encode(old_curriculum_json))   # baseline: ~18,000
after_tokens  = len(enc.encode(ctx.curriculum_graph_json))  # target: < 4,000

assert after_tokens < before_tokens * 0.30, (
    f"Token reduction insufficient: {before_tokens} → {after_tokens}. "
    f"Expected < 30% of original."
)
```

Log token counts per analysis call for ongoing monitoring:
```python
logger.info(
    "curriculum_graph_token_count",
    tokens=after_tokens,
    nodes=len(nodes),
    student_id=ctx.student_id,
)
```
