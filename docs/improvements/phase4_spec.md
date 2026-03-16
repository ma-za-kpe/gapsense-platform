# Phase 4 Spec — Grade Normalisation + Hardening
# Reference document for Claude Code implementation

---

## Grade Data Audit (Run Before Implementation)

Before writing any migration, run this query to understand what
grade formats actually exist in production:

```sql
SELECT
    current_grade,
    COUNT(*) AS student_count,
    STRING_AGG(DISTINCT s.school_id::text, ', ') AS schools
FROM students s
GROUP BY current_grade
ORDER BY student_count DESC;
```

Cross-reference with the GRADE_MAPS in grade_utils.py.
Any formats NOT in the map need to be added before migration.

Log the audit results in PHASE4_CHANGES.md.

---

## Backfill Migration Strategy

```python
# Safe backfill — does not overwrite manually corrected values
# Run in batches of 1000 to avoid lock contention

UPDATE students
SET grade_canonical = CASE current_grade
    -- Ghana
    WHEN 'JHS1'    THEN 'B7'
    WHEN 'JHS2'    THEN 'B8'
    WHEN 'JHS3'    THEN 'B9'
    WHEN 'Primary 1' THEN 'B1'
    -- ... complete mapping from grade_utils.py ...
    ELSE NULL  -- unknown formats → NULL (normalisation will log warning)
END
WHERE grade_canonical IS NULL  -- only backfill nulls
  AND country = 'ghana';       -- run per country

-- Repeat for uganda, kenya, nigeria
```

After migration:
```sql
SELECT
    country,
    COUNT(*) AS total,
    COUNT(grade_canonical) AS normalised,
    COUNT(*) - COUNT(grade_canonical) AS still_null
FROM students
GROUP BY country;
```

Target: < 5% still_null per country after backfill.
Any remaining nulls should be investigated — likely data entry errors.

---

## CurriculumNode.grade Column

Verify that `curriculum_nodes` table has a `grade` column.
If grades are encoded in the `code` field only (e.g. "B7.1.1.1"),
extract grade from code during migration:

```sql
ALTER TABLE curriculum_nodes ADD COLUMN IF NOT EXISTS grade VARCHAR(16);

UPDATE curriculum_nodes
SET grade = CASE
    WHEN code LIKE 'B1.%' THEN 'B1'
    WHEN code LIKE 'B2.%' THEN 'B2'
    WHEN code LIKE 'B7.%' THEN 'B7'
    -- ... etc ...
    WHEN code LIKE 'P1.%' THEN 'P1'
    -- ... etc ...
END
WHERE grade IS NULL AND country = 'ghana';
```

This grade column is what `_vector_search` filters on.

---

## Partner Config Placement

Partner configs belong in settings/environment, not in code constants.
The dataclass in `partner_config.py` is the schema.
Actual values come from:

Option A: Database table `partner_configs` (preferred for multi-tenant)
Option B: YAML config file loaded at startup (simpler for MVP)

For Phase 4, use Option B (YAML). Option A can be implemented
when partner count exceeds 5.

```yaml
# config/partners.yaml
partners:
  athlete_her:
    country: uganda
    subject_focus: [mathematics]
    grade_focus: [S1, S2, S3, S4]
    rate_limit_per_day: 500
    whatsapp_sender_id: "${ATHLETE_HER_WHATSAPP_ID}"
    report_language: en

  viztaedu:
    country: ghana
    subject_focus: [mathematics, literacy]
    grade_focus: [B4, B5, B6, B7, B8, B9]
    rate_limit_per_day: 2000
    whatsapp_sender_id: "${VIZTAEDU_WHATSAPP_ID}"
    report_language: en
```

Load in app startup:
```python
import yaml

with open("config/partners.yaml") as f:
    raw = yaml.safe_load(f)
    PARTNER_CONFIGS = {
        k: PartnerConfig(**v)
        for k, v in raw["partners"].items()
    }
```

---

## SQS Visibility Timeout Recommendation

Current default SQS visibility timeout should be set to:
- Standard queue: 120 seconds (covers Phase 3 two-stage pipeline)
- FIFO queue: 120 seconds

The heartbeat extends by 90 seconds every 45 seconds.
This means effectively infinite processing time for valid tasks.

Configure at the SQS queue level (infrastructure/Terraform), not in code.
The code heartbeat is a safety net, not a substitute for correct queue config.

---

## Metrics Dashboard Queries

After Phase 4, these queries give operational visibility:

### Daily analysis volume by country:
```sql
SELECT
    DATE(created_at) as date,
    JSON_EXTRACT(log_context, '$.country') as country,
    COUNT(*) as analyses,
    AVG(CAST(JSON_EXTRACT(log_context, '$.latency_ms') AS FLOAT)) as avg_latency_ms,
    SUM(CAST(JSON_EXTRACT(log_context, '$.success') AS INTEGER)) as successes
FROM application_logs
WHERE event_name = 'analysis_metrics'
GROUP BY date, country
ORDER BY date DESC, country;
```

### Node injection quality over time:
```sql
SELECT
    DATE(created_at) as date,
    AVG(CAST(JSON_EXTRACT(log_context, '$.nodes_injected') AS INTEGER)) as avg_nodes,
    AVG(CAST(JSON_EXTRACT(log_context, '$.ai_confidence') AS FLOAT)) as avg_confidence
FROM application_logs
WHERE event_name = 'analysis_metrics'
GROUP BY date
ORDER BY date DESC;
```

Target: avg_nodes < 20 (Phase 2 RAG working), avg_confidence > 0.70

### Grade normalisation coverage:
```sql
SELECT
    country,
    ROUND(100.0 * COUNT(grade_canonical) / COUNT(*), 1) as pct_normalised
FROM students
GROUP BY country;
```

Target: > 95% per country after backfill.

---

## Sequencing Note

Phase 4 items can be done in parallel streams:

Stream A (data): Grade normalisation → backfill migration → vector search update
Stream B (ops):  Heartbeat → metrics → partner config

These streams are independent. Assign to different developers if available.
Stream A should complete first — it directly improves diagnostic accuracy.
Stream B is operational hardening — important but not accuracy-critical.
