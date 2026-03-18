# GapSense Phase 2 — Claude Code Implementation Prompt
# Hybrid RAG Retrieval for Curriculum Graph
# Estimated effort: 1 week | Risk: Low-Medium

---

## CONTEXT

Phase 1 is complete. The worker is stable, sessions are scoped correctly,
idempotency is in place, and ANALYSIS-001 has been strengthened.

Phase 2 replaces the single biggest accuracy problem in GapSense:

**The current `_build_curriculum_graph` method dumps up to 100 curriculum
nodes as raw JSON into the prompt. This causes:**
- 15,000–25,000 tokens of noise per analysis call
- The model hallucinating curriculum codes under cognitive load
- The anti-hallucination rule in ANALYSIS-001 fighting against itself
- Prerequisite relationships being invisible to the model
- Grade-irrelevant nodes polluting the context

**The fix is Hybrid Retrieval:**
1. Vector search — find the 10-15 nodes semantically closest to the actual
   student work (queried against pre-embedded indicator descriptions)
2. Graph traversal — walk prerequisite edges 2 levels up from retrieved nodes
   to surface root-cause context that may not appear directly in the image

Read `phase2_spec.md` before writing any code. It contains the full schema,
embedding strategy, and retrieval algorithm specification.

---

## ARCHITECTURAL OVERVIEW

```
Before Phase 2:
  _build_curriculum_graph()
    → SELECT nodes WHERE country=X AND subject=Y LIMIT 100
    → json.dumps(100 nodes)         # ~20,000 tokens
    → inject into {{prerequisite_graph_json}}

After Phase 2:
  _build_curriculum_graph()
    → embed(ctx.transcription OR ctx.image_description)   # query vector
    → vector_search(query, top_k=15)                       # semantic match
    → walk_prerequisites(seed_nodes, depth=2)              # graph traversal
    → load_full_node_data(seed + prerequisite nodes)       # hydrate
    → json.dumps(10-20 nodes)       # ~2,500 tokens
    → inject into {{prerequisite_graph_json}}
```

---

## YOUR MISSION

### STEP 1 — Database Migration

File: `alembic/versions/{timestamp}_add_pgvector_embeddings.py`

Add `pgvector` extension and embedding column:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE curriculum_indicators
ADD COLUMN embedding vector(1536) NULL;

CREATE INDEX idx_curriculum_indicators_embedding
ON curriculum_indicators
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

COMMENT ON COLUMN curriculum_indicators.embedding IS
'OpenAI text-embedding-3-small embedding of indicator text chunk.
 Generated at curriculum import time by embedding_job.py.
 Format: indicator_code + title + error_patterns concatenated.
 Null until embedding job has run for this country/subject.';
```

Also create the `prerequisite_edges` table if it does not already exist
(check the existing schema first — it may be modelled differently):

```sql
CREATE TABLE IF NOT EXISTS curriculum_prerequisite_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_node_id UUID NOT NULL REFERENCES curriculum_nodes(id),
    to_node_id   UUID NOT NULL REFERENCES curriculum_nodes(id),
    country      VARCHAR(32) NOT NULL,
    edge_type    VARCHAR(32) NOT NULL DEFAULT 'prerequisite',
    CONSTRAINT uq_prerequisite_edge UNIQUE (from_node_id, to_node_id)
);

CREATE INDEX idx_prerequisite_edges_to_node
ON curriculum_prerequisite_edges (to_node_id, country);
```

The `from_node` is the prerequisite. `to_node` is the dependent.
"To learn to_node, you must first master from_node."

---

### STEP 2 — EmbeddingService

File: `gapsense/ai/embedding_service.py`

Create an `EmbeddingService` class:

```python
class EmbeddingService:
    """
    Generates and caches vector embeddings for curriculum content.

    Uses OpenAI text-embedding-3-small (1536 dimensions).
    Falls back to sentence-transformers all-MiniLM-L6-v2 (384 dims)
    if OPENAI_API_KEY is not set (for offline/low-cost environments).

    The model choice is fixed at service construction time. Do not
    mix embedding models — vectors from different models are not comparable.
    """

    def __init__(self, settings: Any) -> None: ...

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns a vector."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently. Uses batching."""
        ...

    def build_indicator_chunk(
        self,
        node_code: str,
        node_title: str,
        indicator_code: str,
        indicator_title: str,
        error_patterns: list[str],
    ) -> str:
        """
        Builds the text chunk that gets embedded for each indicator.
        Format matters — this is what semantic search queries against.

        IMPORTANT: This method must be deterministic and version-stable.
        If you change the format, all existing embeddings become stale
        and the embedding job must be re-run.

        Current format:
          Curriculum node: {node_code} — {node_title}
          Indicator: {indicator_code} — {indicator_title}
          Common errors: {'; '.join(error_patterns)}
        """
        ...
```

Why embed at indicator level (not node level):
- Error patterns are the semantic signal — they describe what wrong student
  work looks like in natural language
- A node may have 3-5 indicators with very different error patterns
- Indicator-level chunks give tighter semantic matches

The query vector is built from `ctx.transcription` (Phase 3) or from
a brief image description request (Phase 2 interim). See `phase2_spec.md`
for the interim query strategy before Mathpix is integrated.

---

### STEP 3 — Curriculum Embedding Job

File: `gapsense/jobs/embedding_job.py`

A standalone async script that runs at curriculum import time:

```python
async def run_embedding_job(
    country: str,
    subject: str,
    db: AsyncSession,
    embedding_service: EmbeddingService,
    force_refresh: bool = False,
) -> EmbeddingJobResult:
    """
    Generates embeddings for all curriculum indicators for a country/subject.

    Strategy:
    1. Query all indicators WHERE country=country AND subject=subject
       AND (embedding IS NULL OR force_refresh=True)
    2. Build text chunks using embedding_service.build_indicator_chunk()
    3. Embed in batches of 100 (OpenAI batch limit)
    4. Write embeddings back to curriculum_indicators table
    5. Return stats: total processed, skipped (already embedded), errors

    This job is IDEMPOTENT — safe to run multiple times.
    Existing embeddings are skipped unless force_refresh=True.
    Run after ANY curriculum data update.
    """
```

```python
@dataclass
class EmbeddingJobResult:
    country: str
    subject: str
    total_indicators: int
    newly_embedded: int
    already_embedded: int
    errors: int
    duration_seconds: float
```

Add a CLI entry point:
```
python -m gapsense.jobs.embedding_job \
  --country ghana \
  --subject mathematics \
  [--force-refresh]
```

---

### STEP 4 — Hybrid Retrieval in the Orchestrator

File: `gapsense/engagement/image_analysis_orchestrator.py`

Replace `_build_curriculum_graph` entirely:

```python
async def _build_curriculum_graph(self, ctx: ImageAnalysisContext) -> None:
    """
    Hybrid retrieval: vector search for relevance + graph traversal
    for prerequisite context.

    Replaces the brute-force SELECT LIMIT 100 approach.
    Token count drops from ~20,000 to ~2,500.
    All injected nodes are semantically relevant to the image content.
    Prerequisite chain is explicit, enabling root-cause tracing.
    """

    # Phase 2 interim: use brief image description as query
    # (Phase 3 will replace this with Mathpix LaTeX transcript)
    query_text = await self._build_query_text(ctx)

    # 1. Embed the query
    query_vector = await self._embedding_service.embed(query_text)

    # 2. Vector search — top-k semantically relevant indicators
    seed_indicators = await self._vector_search(
        query_vector=query_vector,
        country=ctx.country_key,
        subject=ctx.subject,
        top_k=15,
    )
    seed_node_ids = {ind.node_id for ind in seed_indicators}

    # 3. Graph traversal — walk prerequisites 2 levels up
    prerequisite_node_ids = await self._walk_prerequisites(
        node_ids=seed_node_ids,
        country=ctx.country_key,
        depth=2,
    )

    all_node_ids = seed_node_ids | prerequisite_node_ids

    # 4. Load full node data (with indicators + error patterns)
    nodes = await self._load_nodes_by_ids(all_node_ids)

    # 5. Warn if limit reached (should never happen with good retrieval)
    if len(nodes) > 25:
        logger.warning(
            "curriculum_graph_unexpectedly_large",
            node_count=len(nodes),
            student_id=ctx.student_id,
        )

    ctx.curriculum_graph_json = self._serialise_graph(nodes)
    ctx.retrieval_metadata = {
        "seed_node_ids": [str(n) for n in seed_node_ids],
        "prerequisite_node_ids": [str(n) for n in prerequisite_node_ids],
        "total_nodes_injected": len(nodes),
        "query_text_preview": query_text[:100],
    }

    logger.info(
        "curriculum_graph_built",
        seed_nodes=len(seed_node_ids),
        prerequisite_nodes=len(prerequisite_node_ids),
        total_nodes=len(nodes),
        student_id=ctx.student_id,
    )
```

**`_build_query_text` (Phase 2 interim):**

```python
async def _build_query_text(self, ctx: ImageAnalysisContext) -> str:
    """
    Phase 2 interim: asks the AI to briefly describe visible math content
    before running vector search.

    This is a lightweight call — small model, no curriculum context,
    no diagnosis. Just: "what mathematical topics are visible here?"

    Phase 3 will replace this with Mathpix OCR output (more accurate,
    no AI call needed for this step).
    """
    description_prompt = (
        f"You are looking at a {ctx.student_grade} student exercise book "
        f"from {ctx.country_key}. In 2-3 sentences, describe only the "
        f"mathematical topics and operations visible in the image. "
        f"Be specific: name operations, number ranges, and any visible "
        f"error patterns. Do not diagnose — just describe what you see."
    )
    # Use Haiku for speed and cost — this is a featherweight call
    response = await self._ai_client.generate(
        prompt_id="QUERY-BUILD",
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

**`_vector_search`:**

```python
async def _vector_search(
    self,
    query_vector: list[float],
    country: str,
    subject: str,
    top_k: int = 15,
) -> list[CurriculumIndicator]:
    """
    Cosine similarity search against embedded curriculum indicators.
    Returns top_k indicators most semantically similar to the query.
    Falls back gracefully if no embeddings exist for this country/subject.
    """
    from sqlalchemy import func, text

    result = await self._db.execute(
        select(CurriculumIndicator)
        .join(CurriculumNode, CurriculumIndicator.node_id == CurriculumNode.id)
        .where(
            CurriculumNode.country == country,
            CurriculumNode.subject == subject,
            CurriculumIndicator.embedding.is_not(None),
        )
        .order_by(
            CurriculumIndicator.embedding.cosine_distance(query_vector)
        )
        .limit(top_k)
    )
    indicators = result.scalars().all()

    if not indicators:
        logger.warning(
            "vector_search_no_results",
            country=country,
            subject=subject,
            message="No embeddings found. Has embedding_job run for this country/subject? Falling back to country+subject filter.",
        )
        # Graceful fallback — return first N indicators by node code order
        # This restores pre-Phase-2 behaviour rather than crashing
        fallback = await self._db.execute(
            select(CurriculumIndicator)
            .join(CurriculumNode, CurriculumIndicator.node_id == CurriculumNode.id)
            .where(
                CurriculumNode.country == country,
                CurriculumNode.subject == subject,
            )
            .order_by(CurriculumNode.code)
            .limit(top_k)
        )
        return fallback.scalars().all()

    return indicators
```

**`_walk_prerequisites`:**

```python
async def _walk_prerequisites(
    self,
    node_ids: set[UUID],
    country: str,
    depth: int = 2,
) -> set[UUID]:
    """
    Walk the prerequisite graph upward from seed nodes.

    For each seed node, find all nodes that are prerequisites of it
    (directly or transitively up to `depth` levels).

    Uses a recursive CTE for efficiency — single DB round trip.

    Example:
      Seed: B7.1.3.1 (Pythagoras theorem)
      Depth 1: B6.4.2.1 (squaring numbers), B5.3.1.1 (multiplication)
      Depth 2: B5.1.1.1 (place value) — root cause candidate

    Returns ONLY the prerequisite nodes, not the seeds themselves.
    Caller combines: all_nodes = seeds | prerequisites
    """
    if not node_ids:
        return set()

    # Recursive CTE: walk prerequisite_edges from seeds upward
    cte_query = text("""
        WITH RECURSIVE prereq_walk AS (
            -- Base case: direct prerequisites of seed nodes
            SELECT
                e.from_node_id AS node_id,
                1 AS depth
            FROM curriculum_prerequisite_edges e
            WHERE e.to_node_id = ANY(:seed_ids)
              AND e.country = :country

            UNION ALL

            -- Recursive case: prerequisites of prerequisites
            SELECT
                e.from_node_id,
                w.depth + 1
            FROM curriculum_prerequisite_edges e
            JOIN prereq_walk w ON e.to_node_id = w.node_id
            WHERE w.depth < :max_depth
              AND e.country = :country
        )
        SELECT DISTINCT node_id FROM prereq_walk
        WHERE node_id != ALL(:seed_ids)  -- exclude seeds (returned separately)
    """)

    result = await self._db.execute(
        cte_query,
        {
            "seed_ids": list(node_ids),
            "country": country,
            "max_depth": depth,
        }
    )
    return {row.node_id for row in result}
```

---

### STEP 5 — Update `ImageAnalysisContext`

File: `gapsense/engagement/image_analysis_context.py`

Add fields for retrieval metadata:

```python
# Add to ImageAnalysisContext dataclass:
retrieval_metadata: dict[str, Any] = field(default_factory=dict)
image_description: str = ""  # interim query text (Phase 2)
# transcription: str = ""    # Phase 3 Mathpix output (placeholder)
```

---

### STEP 6 — Inject `EmbeddingService` into Orchestrator

File: `gapsense/engagement/image_analysis_orchestrator.py`

Add to `__init__`:
```python
def __init__(
    self,
    db: Any,
    ai_client: Any,
    media_service: Any,
    guard_service: Any,
    prompt_service: Any,
    worker_service: Any,
    embedding_service: Any,   # ← NEW
) -> None:
    ...
    self._embedding_service = embedding_service
```

Update `WorkerService._handle_image_analyze` to pass `embedding_service`
when constructing the orchestrator.

---

### STEP 7 — Update ANALYSIS-001 User Template

File: Prompt library

Add retrieval metadata to user template so the model knows what it's working with:

```
## PREREQUISITE GRAPH
<!-- Nodes injected: {{nodes_injected}} (hybrid RAG retrieved) -->
<!-- Seed nodes (semantic match): {{seed_node_codes}} -->
<!-- Prerequisite nodes (graph walk): {{prerequisite_node_codes}} -->
<!-- Query basis: {{query_text_preview}} -->

{{prerequisite_graph_json}}
```

This makes the retrieval reasoning visible to the model and auditable in logs.

---

## DELIVERABLES

1. Alembic migration: pgvector extension + embedding column + prerequisite_edges table
2. `gapsense/ai/embedding_service.py` — full implementation
3. `gapsense/jobs/embedding_job.py` — full implementation with CLI
4. Updated `ImageAnalysisOrchestrator` with hybrid `_build_curriculum_graph`
5. Updated `ImageAnalysisContext` with retrieval_metadata field
6. Updated ANALYSIS-001 user template
7. Unit tests for:
   - `_vector_search` fallback when no embeddings exist
   - `_walk_prerequisites` at depth 1 and depth 2
   - `_build_query_text` returns non-empty string even if AI call fails
   - Full `_build_curriculum_graph` integration test with mock DB
8. Integration test: run full orchestrator against a fixture image,
   assert `len(injected_nodes) <= 20`

---

## CONSTRAINTS

- Do NOT add Mathpix — that is Phase 3
- The fallback in `_vector_search` must silently restore pre-Phase-2 behaviour
  — no crashes if embedding job has not been run yet
- pgvector ivfflat index requires at least 100 vectors to be effective.
  If fewer than 100 indicators are embedded, skip index creation and log a warning.
- EmbeddingService must handle OpenAI rate limits with exponential backoff
- All embedding dimensions must be consistent: either 1536 (OpenAI) or 384
  (MiniLM) — never mix. Store the model name in a settings constant.
- Do not change the ANALYSIS-001 output schema — that was done in Phase 1

---

## DONE WHEN

- Migration runs cleanly on fresh DB
- Embedding job runs successfully for ghana/mathematics and exits cleanly
- After embedding job, `_vector_search` returns results (not fallback)
- `_walk_prerequisites` returns correct ancestors for a known test node
- Full orchestrator integration test passes with <= 20 nodes injected
- Token count of `curriculum_graph_json` drops by >= 70% vs Phase 1 baseline
  (measure with tiktoken, log in tests)
- Fallback gracefully handles zero-embedding scenario without crashing
