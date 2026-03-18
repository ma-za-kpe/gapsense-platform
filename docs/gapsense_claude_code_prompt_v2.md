# GAPSENSE — Claude Code System Prompt
# Version: 2.0.0
# Last Updated: 2026-02-13
# Author: Maku Mazakpe
# Aligned to: GapSense v2.0 — The AI-Native Redesign

You are building **GapSense**, an AI-native foundational learning diagnostic platform for Ghana. GapSense makes invisible learning gaps visible — at school and at home — for teachers and parents in Ghana's primary, JHS, SHS, and TVET classrooms.

**Core design principle:** If you removed the AI, GapSense would cease to function. The AI is not a feature. The AI IS GapSense. Everything else is scaffolding.

**The Invisible Assessment Paradigm:** GapSense does NOT add another test. Diagnostic intelligence is extracted from artifacts that already exist — exercise books, classroom conversations, homework voice notes, market transactions. The AI observes what is already happening and surfaces what humans cannot see alone.

---

## ARCHITECTURE OVERVIEW

### Phase 1 (Current Build): Cloud-First

```
                      ┌─────────────────────────────────────────────┐
                      │              SCHOOL SIDE                     │
                      │                                             │
[Teacher Phone/Web] ──┤  Exercise Book Photo ──→ ANALYSIS-001      │
                      │  Conversation ─────────→ TEACHER-003       │
                      │  Voice Recording ──────→ (Phase 1b)        │
                      └─────────┬───────────────────────────────────┘
                                │
                                ▼
[Parent WhatsApp] → [Meta Cloud API] → [ALB] → [Fargate: web (FastAPI)]
                                                        │
                                                  [SQS FIFO Queue]
                                                        │
                                                  [Fargate: worker]
                                                   ↙         ↘
                                          [Anthropic API]  [WhatsApp API]
                                                   ↘         ↙
                                              [RDS PostgreSQL]
                                                        │
                                                  [S3: media]
```

### Phase 2 (Future): Dual-AI

```
[Teacher Phone] → [On-Device SLM (Gemma 3n)] → Exercise book analysis
                                               → Teacher conversation
                                               → Peer diagnostic games
                         ↕ sync when online
[Cloud (Anthropic)] → Cross-school analytics
                    → Parent WhatsApp generation
                    → Complex diagnostic reasoning
                    → TTS for L1 voice coaching
```

**Why cloud-first in Phase 1:** You cannot fine-tune an on-device SLM for Ghanaian exercise books without labeled data. The cloud model in Phase 1 generates that dataset. Every analysis it performs becomes training data for the Phase 2 on-device model.

### Tech Stack
- **Cloud**: AWS (af-south-1 Cape Town — ~50ms to Ghana)
- **Backend**: FastAPI (Python 3.12+), async everywhere
- **Database**: PostgreSQL 16 on RDS
- **AI**: Anthropic Claude Sonnet 4.5 (diagnostic reasoning, teacher conversation), Haiku 4.5 (parent messages, voice processing, compliance)
- **Messaging**: WhatsApp Cloud API (direct, no intermediary)
- **Queue**: SQS FIFO for async message processing
- **Auth**: AWS Cognito (JWT, phone-based OTP)
- **IaC**: AWS CDK (Python)
- **Local Dev**: Docker Compose + LocalStack

---

## REFERENCE DOCUMENTS

**Always read the relevant file before generating code for that module.** Do not invent schemas, endpoints, or prompts — use what's defined.

| Document | Path | Purpose |
|----------|------|---------|
| v2 Conceptual Design | `docs/GapSense_v2_AI_Native_Redesign.docx` | The product vision. Read §0-§4 for design principles. |
| Roadmap Bridge | `docs/gapsense_roadmap_bridge.md` | Maps deliverables to v2 phases. Explains cloud-first strategy. |
| NaCCA Prerequisite Graph v1.2 | `data/curriculum/prerequisite_graph.json` | 35 nodes (27 numeracy + 8 literacy), 6 cascade paths, misconceptions. **PROPRIETARY IP.** |
| Data Model | `docs/gapsense_data_model.sql` | 742-line PostgreSQL schema → translate to SQLAlchemy models |
| Prompt Library v1.1 | `data/prompts/prompt_library.json` | 13 AI prompts with I/O schemas, test cases, chaining workflows |
| API Specification | `docs/gapsense_api_spec.json` | OpenAPI 3.1 — 23 endpoints, 18 schemas |
| WhatsApp Flows | `docs/gapsense_whatsapp_flows.json` | 6 conversation flows, 5 message templates |
| Architecture Decisions | `docs/gapsense_adr.md` | 12 ADRs — do not contradict these |
| Project Structure | `docs/gapsense_project_structure.md` | Directory layout, module boundaries, naming conventions |
| Test Scenarios | `docs/gapsense_test_scenarios.json` | 18 acceptance scenarios across 5 categories |
| CDK Stack | `infra/gapsense_cdk_stack.py` | AWS infrastructure definition |
| Docker Setup | `Dockerfile` + `docker-compose.yml` | Container configuration |

---

## CRITICAL RULES

### 1. The Invisible Assessment Paradigm

The PRIMARY diagnostic pathway is NOT an explicit test session. It is:

```
Exercise book photo → ANALYSIS-001 → gap signals → update gap profile
Teacher conversation → TEACHER-003 → teacher observations + AI synthesis → update gap profile
Parent voice note → ANALYSIS-002 → cognitive process extraction → update gap profile
```

The DIAG-001 → DIAG-002 → DIAG-003 chain exists as a **Teacher Deep Dive** — an optional explicit diagnostic the teacher can trigger when they want focused assessment. It is NOT the default pathway. Most gap profile updates should come from passive observation of existing artifacts.

When building the diagnostic engine:
- Exercise book analysis (ANALYSIS-001) should be the easiest, most prominent pathway
- TEACHER-003 conversational interface is the primary teacher experience
- Explicit diagnostic sessions (DIAG-001/002/003) are accessible but secondary
- Gap profiles update incrementally from multiple sources, not just from formal sessions

### 2. NEVER Contradict the Architecture Decisions

Every decision in `gapsense_adr.md` was made deliberately. Do not:
- Switch from FastAPI to Django or Flask
- Use MongoDB instead of PostgreSQL
- Use OpenAI instead of Anthropic
- Use Turn.io or Twilio instead of direct WhatsApp Cloud API
- Use Redis/Celery instead of SQS
- Break the web/worker service split

If you think an ADR should change, flag it — don't silently deviate.

### 3. Follow the Data Model EXACTLY

The PostgreSQL schema in `gapsense_data_model.sql` is the source of truth. When generating SQLAlchemy models:
- Match every table, column, constraint, and index
- Use UUID primary keys (uuid4)
- Use `TIMESTAMPTZ` → `DateTime(timezone=True)`
- Use `JSONB` → `postgresql.JSONB` dialect
- Use `UUID[]` → `ARRAY(UUID)` dialect
- Preserve all CHECK constraints and comments

### 4. Use the Prompt Library — Do Not Invent Prompts

Every AI interaction uses a prompt from `prompt_library.json`. The prompts have:
- Specific system prompts with guardrails
- User templates with `{{placeholder}}` variables
- Output schemas the AI response must conform to
- Test cases for validation

When calling the Anthropic API:
- Use the system_prompt from the library verbatim
- Render the user_template with actual data
- Validate response against output_schema
- Use the specified model (Sonnet vs Haiku) and temperature
- Enable prompt caching for system_prompt + prerequisite graph context

### 5. Wolf/Aurino Compliance is NON-NEGOTIABLE

Every message sent to a parent MUST:
- Lead with what the child CAN do (strength-first)
- Contain exactly ONE activity
- Use locally available materials only (bottle caps, stones, sticks, coins, beans, paper)
- Be under 300 words (200 for semi-literate parents)
- Be in the parent's preferred language (en/tw/ee/ga/dag)
- Pass through GUARD-001 compliance check BEFORE sending

NEVER contain in parent-facing messages:
- Deficit language: "behind", "struggling", "failing", "weak", "poor", "below grade level", "deficit", "needs improvement"
- Jargon: "diagnostic", "assessment", "remediation", "curriculum", "prerequisite", "misconception"
- Comparisons to other children
- Parent's literacy level

If code generates a parent-facing message that violates these rules, that is a **critical bug**. The Wolf/Aurino research from Northern Ghana (2020-2021) proved that deficit messaging causes parents to DISENGAGE. This constraint protects children.

### 6. Teacher Experience = Conversation, Not Reports

The teacher's primary interface is TEACHER-003 — a conversational diagnostic partner. Think: experienced colleague in the staffroom, not inspector from the district office.

- TEACHER-003 responds to natural questions: "I'm teaching fractions next week", "Why does Kwame keep failing?", "Is Ama improving?"
- TEACHER-001 and TEACHER-002 generate formal reports ON DEMAND only
- Teacher conversations should feel like talking to a knowledgeable colleague who has read all the exercise books
- Always connect insights to action: "Here's what I'd try..." not just "Here's the data..."
- Respect teacher expertise. The AI has data; the teacher has classroom context.

### 7. Literacy AND Numeracy

The prerequisite graph v1.2 contains both:
- **27 numeracy nodes** (B1-B9, fully populated for B1-B2, skeleton for B3-B9)
- **8 literacy nodes** (B1-B3 English Language, all skeleton)
- **6 cascade paths** (4 numeracy + 2 literacy)

When building diagnostic features:
- Support BOTH domains in the graph traversal service
- Distinguish English proficiency gaps from fundamental reading skill deficits (a Twi-fluent student struggling in English needs different intervention)
- Literacy cascade path CP-005 (Decoding Collapse) traces from B1 letter-sound to B3 comprehension
- Writing analysis from exercise books (B3.5.2.1) is diagnostic gold — spelling errors reveal L1 interference patterns

### 8. Respect Module Boundaries

```
api/ → services/ → models/ + db/ + utils/
worker/ → services/ → models/ + db/ + utils/
```

- API handlers are thin — validation + call service + return response
- ALL business logic lives in services/
- Models have zero business logic
- The `ai/` module NEVER imports from `diagnostic/` or `engagement/`
- See `gapsense_project_structure.md` for full dependency rules

### 9. Async Everywhere

- All database operations: async SQLAlchemy (asyncpg driver)
- All HTTP calls (Anthropic, WhatsApp): httpx async client
- All SQS operations: aiobotocore
- Never use sync-over-async patterns
- Never block the event loop

### 10. Type Everything

- All function signatures have type hints
- All Pydantic models have field types
- MyPy strict mode must pass
- Use `from __future__ import annotations` in every file

---

## MODULE-SPECIFIC INSTRUCTIONS

### services/diagnostic_engine.py — The Heart

This module manages the gap profile lifecycle. Gap profiles update from MULTIPLE sources:

```python
# Source 1: Exercise book analysis (PRIMARY pathway)
async def process_exercise_book(student_id: UUID, image: bytes) -> GapProfileUpdate:
    analysis = await ai_service.invoke_prompt("ANALYSIS-001", {...})
    return update_gap_profile(student_id, analysis)

# Source 2: Teacher conversation (insights from TEACHER-003)
async def process_teacher_observation(student_id: UUID, observation: dict) -> GapProfileUpdate:
    # Teacher says "Kwame can't do 2-digit subtraction" → update profile
    return update_gap_profile(student_id, observation)

# Source 3: Parent voice note (home observations)
async def process_voice_note(student_id: UUID, transcription: str) -> GapProfileUpdate:
    analysis = await ai_service.invoke_prompt("ANALYSIS-002", {...})
    return update_gap_profile(student_id, analysis)

# Source 4: Explicit diagnostic session (OPTIONAL deep dive)
async def process_diagnostic_response(session_id: UUID, response: str) -> DiagnosticNextStep:
    # DIAG-001 → DIAG-002 → DIAG-003 chain
    # Only when teacher explicitly starts a diagnostic session
    ...
```

### services/graph_traversal.py — Prerequisite Graph Algorithms

Load the prerequisite graph from `data/curriculum/prerequisite_graph.json` at startup. Provide:

```python
def backward_trace(node_code: str, max_depth: int = 4) -> list[str]
def forward_impact(node_code: str) -> list[str]
def find_cascade_path(gap_nodes: list[str]) -> str | None
def priority_screening_order(grade: str, domain: str = "numeracy") -> list[str]  # supports literacy too
def get_severity(node_code: str) -> int
def get_domain(node_code: str) -> str  # "numeracy" or "literacy" based on strand
```

The graph is a DAG. Use iterative traversal (stack-based), not recursion. Graph covers both numeracy (strands 1-4) and literacy (strand 5).

### services/teacher_conversation.py — Teacher Partner

```python
async def respond_to_teacher(
    teacher_id: UUID,
    message: str,
    conversation_history: list[dict]
) -> TeacherResponse:
    # 1. Load teacher's class gap profiles
    # 2. Determine conversation mode (lesson planning, student concern, progress check, etc.)
    # 3. Call TEACHER-003 with full class context
    # 4. Return conversational response with suggested actions
```

This is the PRIMARY teacher interface. Design it to feel like a chat with a knowledgeable colleague.

### services/ai_service.py — Anthropic API Client

```python
class AIService:
    async def invoke_prompt(
        self,
        prompt_id: str,       # e.g., "DIAG-001", "TEACHER-003"
        variables: dict,      # Template variables
        cache_prefix: bool = True
    ) -> dict:
        # 1. Load prompt from prompt_library.json
        # 2. Render system_prompt (static, cacheable)
        # 3. Render user_template with variables
        # 4. Call Anthropic API with specified model + temperature
        # 5. Parse response, validate against output_schema
        # 6. Log to ai_reasoning_log for audit
        # 7. Return parsed result
```

Prompt caching: prerequisite graph JSON (~4000 tokens) + system prompt are the cached prefix. Student-specific context is the dynamic suffix. 90% cost reduction on cached tokens.

### services/whatsapp_service.py — WhatsApp Cloud API

```python
class WhatsAppService:
    async def send_text(self, phone: str, message: str) -> str
    async def send_buttons(self, phone: str, body: str, buttons: list[dict]) -> str
    async def send_list(self, phone: str, body: str, sections: list[dict]) -> str
    async def send_template(self, phone: str, template_name: str, params: list) -> str
    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None
    def parse_inbound(self, payload: dict) -> InboundMessage
```

Constraints: buttons max 3 (20 chars each), lists max 10 items (24 chars each), text max 4096 chars, no markdown rendering. Template messages required for initiating conversations or after 24h window.

### services/engagement_service.py — Parent Engagement Pipeline

EVERY outbound parent message flows through this pipeline:

```python
async def send_parent_message(parent: Parent, student: Student, profile: GapProfile) -> None:
    # 1. Generate activity (ACT-001)
    activity = await ai_service.invoke_prompt("ACT-001", {...})

    # 2. Format as WhatsApp message (PARENT-001) in parent's language
    message = await ai_service.invoke_prompt("PARENT-001", {...})

    # 3. COMPLIANCE CHECK — non-negotiable (GUARD-001 at temp=0.0)
    guard_result = await ai_service.invoke_prompt("GUARD-001", {
        "message_text": message["message_text"],
        "parent_name": parent.preferred_name,
        "literacy_level": parent.literacy_level,
        ...
    })

    # 4. If rejected: regenerate with guard feedback, NOT skip the check
    if not guard_result["approved"]:
        message = await regenerate_with_feedback(guard_result["issues"], ...)
        # Re-check after regeneration
        guard_result = await ai_service.invoke_prompt("GUARD-001", {...})
        if not guard_result["approved"]:
            logger.error("compliance_double_failure", ...)
            return  # DO NOT SEND. Flag for human review.

    # 5. Send via WhatsApp
    await whatsapp_service.send_text(parent.phone, message["message_text"])
```

### worker/ — SQS Background Worker

Polls SQS FIFO queue. Message types:
- `inbound_whatsapp`: Parse and route incoming WhatsApp message
- `exercise_book_analysis`: Run ANALYSIS-001 on uploaded photo
- `send_activity`: Generate and send parent activity (ACT-001 → PARENT-001 → GUARD-001)
- `send_check_in`: Send 3-5 day check-in (PARENT-002)
- `scheduled_reminder`: Re-engagement after inactivity
- `diagnostic_complete`: Post-session gap profile processing

### api/whatsapp.py — Webhook Handler

```python
@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    payload = await request.json()
    # ALWAYS return 200 immediately — Meta will block if slow
    await sqs_service.send_message(
        queue_url=settings.SQS_QUEUE_URL,
        message_body=json.dumps({"type": "inbound_whatsapp", "payload": payload}),
        message_group_id=extract_phone(payload),  # FIFO ordering per parent
    )
    return Response(status_code=200)
```

---

## TESTING INSTRUCTIONS

### Tier 1: Unit Tests (every commit)
- Mock all external services (Anthropic, WhatsApp, SQS)
- Test graph traversal for BOTH numeracy and literacy domains
- Test conversation state machine transitions
- Test compliance guard with known-good and known-bad messages
- Test gap profile update from multiple sources (exercise book, voice note, session)
- Use Factory Boy for test data

### Tier 2: Integration Tests (every PR)
- Test full exercise book → gap profile update pipeline
- Test teacher conversation flow (TEACHER-003)
- Test parent engagement cycle (activity → check-in → response → next activity)
- Test webhook handling end-to-end
- Test diagnostic session flow (when explicitly triggered)

### Tier 3: Prompt Evaluation (weekly)
- Load test cases from prompt library
- Call Anthropic API (NOT mocked) with test inputs
- Validate output against output_schema
- Alert if accuracy drops below 85%
- Run GUARD-001 on every message template — deployment blocker

---

## ENVIRONMENT VARIABLES

```env
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/gapsense
ANTHROPIC_API_KEY=sk-ant-...
WHATSAPP_API_TOKEN=EAAx...
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_VERIFY_TOKEN=your_verify_token

# AWS
AWS_REGION=af-south-1
SQS_QUEUE_URL=https://sqs.af-south-1.amazonaws.com/123/gapsense-messages.fifo
S3_MEDIA_BUCKET=gapsense-media

# Auth
COGNITO_USER_POOL_ID=af-south-1_xxx
COGNITO_CLIENT_ID=xxx

# App
ENVIRONMENT=local|staging|production
LOG_LEVEL=DEBUG|INFO
```

---

## DEPENDENCIES (pyproject.toml)

```toml
[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.34"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
asyncpg = "^0.30"
alembic = "^1.14"
pydantic = "^2.10"
pydantic-settings = "^2.7"
anthropic = "^0.43"
httpx = "^0.28"
aiobotocore = "^2.15"
python-jose = {extras = ["cryptography"], version = "^3.3"}
structlog = "^24.4"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.25"
pytest-cov = "^6.0"
factory-boy = "^3.3"
mypy = "^1.14"
ruff = "^0.9"
```

---

## COMMON PATTERNS

### Error Handling
```python
from gapsense.utils.errors import NotFoundError, ConflictError, ComplianceError

raise NotFoundError(f"Student {student_id} not found")
raise ComplianceError("Message failed Wolf/Aurino check", issues=guard_result["issues"])

@app.exception_handler(ComplianceError)
async def compliance_handler(request, exc):
    logger.error("compliance_violation", issues=exc.issues)
    return JSONResponse(status_code=422, content={"detail": str(exc), "issues": exc.issues})
```

### Structured Logging
```python
import structlog
logger = structlog.get_logger()

logger.info("gap_profile_updated", student_id=str(id), source="exercise_book", nodes_affected=["B2.1.1.1"])
logger.info("teacher_conversation", teacher_id=str(id), mode="lesson_planning", nodes_referenced=["B4.1.3.1"])
logger.error("guard_rejection", prompt_id="PARENT-001", issues=result["issues"])
```

### Database Sessions
```python
from gapsense.db.session import get_session

@router.get("/students/{student_id}")
async def get_student(student_id: UUID, session: AsyncSession = Depends(get_session)):
    student = await session.get(Student, student_id)
    if not student:
        raise NotFoundError(f"Student {student_id} not found")
    return student
```

---

## WHAT TO BUILD FIRST

Priority order — engine room first, channels second:

1. **Models + DB setup** — SQLAlchemy models from data model, Alembic migration, seed data
2. **Graph traversal service** — Load prerequisite graph (numeracy + literacy), implement traversal
3. **AI service** — Anthropic client with prompt loading, caching, validation
4. **Health + CRUD endpoints** — /health, Students, Parents, Schools, Teachers
5. **Exercise book analysis pipeline** — Photo upload → ANALYSIS-001 → gap profile update (PRIMARY diagnostic pathway)
6. **Teacher conversation interface** — TEACHER-003 endpoint (PRIMARY teacher experience)
7. **WhatsApp webhook + worker** — Inbound message routing, SQS processing
8. **Parent engagement pipeline** — ACT-001 → PARENT-001 → GUARD-001 → send (with compliance loop)
9. **Explicit diagnostic engine** — DIAG-001/002/003 chain (SECONDARY diagnostic, teacher-triggered)
10. **Conversation flows** — Onboarding, activity cycle, check-in, opt-out
11. **Teacher reports** — TEACHER-001/002 (ON DEMAND, not primary)
12. **Analytics + admin** — Aggregation, prompt management
13. **CDK deployment** — Ship it

Note the priority shift from v1: exercise book analysis and teacher conversation are now BEFORE the explicit diagnostic engine. This reflects v2's Invisible Assessment Paradigm.

---

## REMEMBER

GapSense exists because children exit primary school in Ghana without basic literacy and numeracy, and nobody can see it happening until it's too late. The teachers are overworked. The parents are motivated but unequipped. The system is blind.

You are building the eyes.

The diagnostic must be accurate — a wrong gap profile sends the wrong activity, wastes a parent's 3 minutes, and erodes trust. The parent messages must be dignifying — the Wolf/Aurino research proved that deficit messaging makes parents DISENGAGE, hurting the very children we're trying to help. The system must work on WhatsApp over a 2G connection in a rural Northern Region community.

Every exercise book a teacher photographs is diagnostic gold sitting on their desk. Every voice note a parent sends is a window into how a child thinks at home. Every conversation a teacher has with GapSense should feel like talking to a colleague who has read every page of every student's work.

Make the invisible gaps visible. Build with care.
