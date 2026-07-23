# GapSense Architecture Decision Record (ADR)
## Version 1.0.0 | 2026-02-13 | Maku Mazakpe | Proprietary IP

---

## ADR-001: Cloud Provider — AWS
**Decision:** AWS (Cape Town af-south-1 region)
**Rationale:** Lowest latency to Ghana (~50ms vs 150ms+ GCP Europe). Fargate for serverless containers. RDS PostgreSQL managed. SQS for webhook queuing. S3 for media. UNICEF/World Bank projects commonly on AWS.
**Rejected:** GCP (no Africa region), Azure (less mature), DigitalOcean (too limited).
**Cost estimate:** ~$50-80/month MVP (Fargate + RDS t3.micro + SQS + S3).

## ADR-002: Backend Framework — FastAPI
**Decision:** FastAPI with SQLAlchemy 2.0 async + Pydantic v2
**Rationale:** Async-native (critical for 2-10s Claude API calls). Built-in OpenAPI generation matches API-first design. Type hints help Claude Code generate better code. Lightweight for Fargate cold starts.
**Rejected:** Django (sync-first, ORM blocks), Flask (too minimal), Node/Express (team is Python-first).

## ADR-003: Database — PostgreSQL 16+ on RDS
**Decision:** PostgreSQL with JSONB for AI logs, UUID PKs, array types for node lists, pg_trgm for search.
**Rationale:** Data is fundamentally relational (students→parents, sessions→questions→nodes). JSONB gives flexibility without sacrificing referential integrity. Arrays avoid junction tables for simple lists.
**Rejected:** MongoDB (graph is relational, JOINs needed for analytics), DynamoDB (complex query patterns), SQLite (no concurrency).

## ADR-004: WhatsApp — Direct Cloud API (MVP)
**Decision:** WhatsApp Cloud API direct integration. Evaluate Turn.io at 10,000+ daily messages.
**Rationale:** No per-message cost. Full control over webhook handling. Template management via Meta Business Suite. ViztaEdu may have existing WhatsApp Business Account.
**Trade-off:** More engineering than Turn.io, but better for AI-driven conversation flows.

## ADR-005: AI Provider — Anthropic Claude
**Decision:** Sonnet 4.5 for diagnostics, Haiku 4.5 for parent messages.
**Rationale:** Superior structured JSON output. Stronger multilingual (Twi/Ewe/Ga). Better at complex multi-constraint prompts (Wolf/Aurino + diagnostic + anti-fabrication). Vision for exercise book photos.
**Model allocation:** Sonnet = accuracy-critical (DIAG-001/002/003, ANALYSIS-001). Haiku = speed/cost-critical (PARENT-001/002/003, ANALYSIS-002).
**Cost:** ~$20-30/month at MVP scale (500 sessions + 1500 parent messages).
**Fallback:** Queue in SQS on timeout (>5s). Never block parent interaction.

## ADR-006: Prompt Caching
**Decision:** Anthropic cache_control for system prompts + graph context.
**Rationale:** System prompt + graph = ~4,000 tokens. Cached once per session = 90% cost reduction on cached tokens. Graph is same across students = high cache hit rate.

## ADR-007: Cloud-Only for MVP
**Decision:** All processing in cloud. On-device (Flutter + TFLite) for Phase 2.
**Rationale:** MVP is WhatsApp-first — no app. Cloud allows rapid prompt iteration. No app download barrier.
**Phase 2:** Flutter app, offline diagnostics, on-device photo processing, sync when online.

## ADR-008: Data Privacy
**Decision:** Defense-in-depth. Minimal data collection. Ghana Data Protection Act 2012 compliance.
**Implementation:** RDS encryption (AES-256). TLS 1.3 everywhere. AI logs encrypted with KMS. No last names/addresses/IDs. Parent literacy_level NEVER shared. 2-year retention then anonymize. Right to deletion via WhatsApp.
**UNICEF compliance:** Consent via opt-in. Data controller = ViztaEdu/GapSense entity. No cross-border transfer without consent.

## ADR-009: Message Queuing — SQS
**Decision:** SQS with dead-letter queue for WhatsApp webhook processing.
**Architecture:** Webhook → validate → SQS → return 200 immediately. Worker dequeues → Claude API → send reply. Failed → DLQ → alert.
**Rationale:** Decouples receipt from processing. Handles bursts. 30s visibility timeout matches AI processing time.

## ADR-010: Modular Monolith
**Decision:** Single deployable with clean module boundaries. Extract to microservices only if scaling demands.
**Rationale:** 1-2 developers. Single DB. Single Fargate task = simpler everything. FastAPI router groups = natural modules.
**Extraction trigger:** If any module needs independent scaling (e.g., webhooks at 10K msg/day).

## ADR-011: Three-Tier Testing
- **Tier 1 — Unit (pytest):** Models, validators, graph traversal. Every commit.
- **Tier 2 — Integration:** API endpoints, webhook simulation, AI flow with mocked responses. Every PR.
- **Tier 3 — Prompt validation:** Test cases from Prompt Library against live Claude. Weekly or after prompt changes. Alert if accuracy < 85%.

## ADR-012: Monitoring — CloudWatch + Custom Metrics
**Metrics:** diagnostic.session.duration, diagnostic.confidence.mean, engagement.activity.completion_rate, ai.prompt.latency, ai.prompt.error_rate, whatsapp.delivery.rate.
**Alerts:** AI error > 5%, SQS DLQ depth > 0, RDS connection exhaustion.
