# GAPSENSE — Claude Code System Prompt
# Version: 1.0.0
# Last Updated: 2026-02-13
# Author: Maku Mazakpe

You are building **GapSense**, an AI-powered foundational learning diagnostic platform for Ghana. GapSense identifies root learning gaps in primary and JHS students using the NaCCA Standards-Based Curriculum, then engages parents via WhatsApp with specific, dignity-preserving activities to close those gaps.

---

## ARCHITECTURE OVERVIEW

```
[Parent WhatsApp] → [Meta Cloud API] → [ALB] → [Fargate: web (FastAPI)]
                                                        ↓
                                                  [SQS FIFO Queue]
                                                        ↓
                                                  [Fargate: worker]
                                                   ↙         ↘
                                          [Anthropic API]  [WhatsApp API]
                                                   ↘         ↙
                                              [RDS PostgreSQL]
                                                        ↓
                                                  [S3: media]
```

- **Cloud**: AWS (af-south-1 Cape Town region)
- **Backend**: FastAPI (Python 3.12+), async everywhere
- **Database**: PostgreSQL 16 on RDS
- **AI**: Anthropic Claude Sonnet 4.5 (diagnostic), Haiku 4.5 (analysis, compliance)
- **Messaging**: WhatsApp Cloud API (direct, no intermediary)
- **Queue**: SQS FIFO for async WhatsApp processing
- **Auth**: AWS Cognito (JWT)
- **IaC**: AWS CDK (Python)
- **Local Dev**: Docker Compose

---

## REFERENCE DOCUMENTS

These files contain the detailed specifications. **Always read the relevant file before generating code for that module.** Do not invent schemas, endpoints, or prompts — use what's defined.

| Document | Path | Purpose |
|----------|------|---------|
| NaCCA Prerequisite Graph | `data/curriculum/prerequisite_graph.json` | The curriculum DAG — nodes, edges, misconceptions, cascades. **PROPRIETARY IP.** |
| Data Model | `gapsense_data_model.sql` | Complete PostgreSQL schema. Translate to SQLAlchemy models. |
| Prompt Library | `data/prompts/prompt_library.json` | All AI prompt templates with input/output schemas. |
| API Specification | `gapsense_api_spec.yaml` | OpenAPI 3.1 spec — every endpoint, schema, contract. |
| Architecture Decisions | `gapsense_adr.md` | Every technical decision and WHY. Do not contradict these. |
| Project Structure | `gapsense_project_structure.md` | Directory layout, module boundaries, naming conventions. |
| Test Scenarios | `gapsense_test_scenarios.json` | Acceptance test matrix — implement as pytest tests. |
| CDK Stack | `infra/gapsense_cdk_stack.py` | AWS infrastructure definition. |
| Docker Setup | `Dockerfile` + `docker-compose.yml` | Container configuration. |

---

## CRITICAL RULES

### 1. NEVER Contradict the Architecture Decisions
Every decision in `gapsense_adr.md` was made deliberately. Do not:
- Switch from FastAPI to Django or Flask
- Use MongoDB instead of PostgreSQL
- Use OpenAI instead of Anthropic
- Use Turn.io or Twilio instead of direct WhatsApp Cloud API
- Use Redis/Celery instead of SQS
- Break the web/worker service split

If you think an ADR should change, flag it — don't silently deviate.

### 2. Follow the Data Model EXACTLY
The PostgreSQL schema in `gapsense_data_model.sql` is the source of truth. When generating SQLAlchemy models:
- Match every table, column, constraint, and index
- Use UUID primary keys (uuid4)
- Use `TIMESTAMPTZ` → `DateTime(timezone=True)` in SQLAlchemy
- Use `JSONB` → `JSON` with `postgresql.JSONB` dialect
- Use `UUID[]` → `ARRAY(UUID)` with PostgreSQL dialect
- Preserve all CHECK constraints
- Preserve all comments

### 3. Use the Prompt Library — Do Not Invent Prompts
Every AI interaction must use a prompt from `prompt_library.json`. The prompts have:
- Specific system prompts with rules and guardrails
- User templates with `{{placeholder}}` variables
- Output schemas that the AI response must conform to
- Test cases for validation

When calling the Anthropic API:
- Use the system_prompt from the prompt library verbatim
- Render the user_template with actual data
- Validate the response against output_schema
- Use the specified model (Sonnet vs Haiku) and temperature

### 4. Match the API Specification
Every endpoint must match `gapsense_api_spec.yaml`:
- Same paths, methods, parameters
- Same request/response schemas
- Same status codes
- Same authentication requirements

### 5. Wolf/Aurino Compliance is NON-NEGOTIABLE
Every message sent to a parent MUST:
- Lead with what the child CAN do (strength-first)
- Contain exactly ONE activity
- Use locally available materials only
- Be under 300 words (200 for semi-literate)
- NEVER contain: "behind", "struggling", "failing", "weak", "poor", "below grade level", "deficit", "needs improvement"
- NEVER use jargon: "diagnostic", "assessment", "remediation", "curriculum", "prerequisite"
- Be in the parent's preferred language
- Pass through GUARD-001 compliance check before sending

If code generates a parent-facing message that violates these rules, that is a **critical bug**.

### 6. Respect Module Boundaries
```
api/ → services/ → models/ + db/ + utils/
worker/ → services/ → models/ + db/ + utils/
```
- API handlers are thin — validation + call service + return response
- ALL business logic lives in services/
- Models have zero business logic
- utils/ imports nothing from gapsense

### 7. Async Everywhere
- All database operations use async SQLAlchemy (asyncpg driver)
- All HTTP calls (Anthropic, WhatsApp) use httpx async client
- All SQS operations use aiobotocore
- Never use sync-over-async patterns
- Never block the event loop

### 8. Type Everything
- All function signatures have type hints
- All Pydantic models have field types
- MyPy strict mode must pass
- Use `from __future__ import annotations` in every file

---

## MODULE-SPECIFIC INSTRUCTIONS

### models/ — SQLAlchemy ORM Models
- Base class: `DeclarativeBase` from SQLAlchemy 2.0
- Use `Mapped[type]` and `mapped_column()` syntax
- Include `created_at` and `updated_at` on every model
- Use relationship() for FK relationships
- Match gapsense_data_model.sql exactly

### services/diagnostic_engine.py — Core Diagnostic Logic
This is the heart of GapSense. It manages:
1. Session creation with entry point selection
2. Question generation via AI (DIAG-001 prompt)
3. Response analysis via AI (DIAG-002 prompt)
4. Backward tracing through prerequisite graph
5. Root gap identification and confidence scoring
6. Gap profile generation

Key algorithm:
```python
async def process_response(session_id: UUID, response: str) -> DiagnosticNextStep:
    # 1. Load session state
    # 2. Analyse response using DIAG-002 (Haiku - fast)
    # 3. Update session: mark node as mastered/gap/uncertain
    # 4. If gap detected: trace backward to prerequisite
    # 5. If mastered: check if more screening needed
    # 6. If root gap found with confidence >= 0.80: generate final profile
    # 7. If < 0.80 confidence: generate next question using DIAG-001 (Sonnet)
    # 8. Return next_question or final_profile
```

### services/graph_traversal.py — Prerequisite Graph Algorithms
Load the prerequisite graph from `data/curriculum/prerequisite_graph.json` at startup. Provide:
```python
def backward_trace(node_code: str, max_depth: int = 4) -> list[str]
def forward_impact(node_code: str) -> list[str]
def find_cascade_path(gap_nodes: list[str]) -> str | None
def priority_screening_order(grade: str) -> list[str]
def get_severity(node_code: str) -> int
```
The graph is a DAG. Use iterative traversal, not recursion (stack overflow risk for deep chains).

### services/ai_service.py — Anthropic API Client
```python
class AIService:
    async def invoke_prompt(
        self,
        prompt_id: str,       # e.g., "DIAG-001"
        variables: dict,      # Template variables
        cache_prefix: bool = True  # Use prompt caching for system prompt + graph
    ) -> dict:
        # 1. Load prompt from prompt_library.json
        # 2. Render system_prompt (static, cacheable)
        # 3. Render user_template with variables
        # 4. Call Anthropic API with appropriate model + temperature
        # 5. Parse response, validate against output_schema
        # 6. Return parsed result
```

Use prompt caching: the prerequisite graph JSON + system prompt are the cached prefix. Student-specific context is the dynamic suffix.

### services/whatsapp_service.py — WhatsApp Cloud API Client
```python
class WhatsAppService:
    async def send_text(self, phone: str, message: str) -> str  # returns wa_message_id
    async def send_buttons(self, phone: str, body: str, buttons: list[dict]) -> str
    async def send_list(self, phone: str, body: str, sections: list[dict]) -> str
    async def send_template(self, phone: str, template_name: str, params: list) -> str
    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None
    def parse_inbound(self, payload: dict) -> InboundMessage
```

WhatsApp interactive message limits:
- Buttons: max 3 buttons, 20 chars each
- Lists: max 10 items per section, max 10 sections
- Template messages require pre-approval in Meta Business Manager

### services/conversation_manager.py — WhatsApp State Machine
States: `idle` → `onboarding` → `diagnostic` → `activity_cycle` → `dormant`

```python
async def handle_inbound(message: InboundMessage) -> None:
    parent = await get_or_create_parent(message.phone)
    state = await get_conversation_state(parent.id)

    if is_stop_word(message.text):
        await handle_opt_out(parent)
        return

    match state:
        case "idle" | None:
            await start_onboarding(parent, message)
        case "onboarding":
            await continue_onboarding(parent, message)
        case "diagnostic":
            await continue_diagnostic(parent, message)
        case "activity_cycle":
            await handle_activity_response(parent, message)
        case "dormant":
            await handle_reactivation(parent, message)
```

### services/parent_engagement.py — Message Generation
Every outbound parent message goes through:
1. Generate message using appropriate prompt (PARENT-001, PARENT-002, etc.)
2. Run GUARD-001 compliance check
3. If rejected: regenerate with feedback from guard
4. If approved: send via WhatsApp service
5. Log to parent_interactions table

```python
async def send_diagnostic_report(parent: Parent, student: Student, profile: GapProfile) -> None:
    # Generate using PARENT-001
    message = await ai_service.invoke_prompt("PARENT-001", {
        "parent_name": parent.preferred_name,
        "preferred_language": parent.preferred_language,
        "literacy_level": parent.literacy_level,
        "child_name": student.first_name,
        "current_grade": student.current_grade,
        "strengths_summary": profile.strengths_summary,
        # ... etc
    })

    # Compliance check
    guard_result = await ai_service.invoke_prompt("GUARD-001", {
        "message_text": message["message_text"],
        "parent_name": parent.preferred_name,
        "literacy_level": parent.literacy_level,
        # ...
    })

    if not guard_result["approved"]:
        # Regenerate with guard feedback
        ...

    # Send via WhatsApp
    await whatsapp_service.send_text(parent.phone, message["message_text"])
```

### worker/ — SQS Background Worker
The worker polls SQS FIFO queue and processes messages:
```python
async def main():
    while True:
        messages = await sqs_client.receive_message(queue_url, max_messages=10)
        for msg in messages:
            try:
                await dispatch(msg)
                await sqs_client.delete_message(queue_url, msg.receipt_handle)
            except Exception as e:
                logger.error(f"Worker error: {e}")
                # Message returns to queue after visibility timeout
```

Message types:
- `inbound_whatsapp`: Process incoming WhatsApp message
- `send_activity`: Generate and send parent activity
- `send_check_in`: Send 3-day check-in
- `scheduled_reminder`: Send re-engagement reminder
- `diagnostic_complete`: Post-diagnostic processing

### api/whatsapp.py — Webhook Handler
```python
@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    payload = await request.json()
    # ALWAYS return 200 immediately — Meta will block if slow
    # Enqueue to SQS for async processing
    await sqs_service.send_message(
        queue_url=settings.SQS_QUEUE_URL,
        message_body=json.dumps({"type": "inbound_whatsapp", "payload": payload}),
        message_group_id=extract_phone(payload),  # FIFO ordering per parent
    )
    return Response(status_code=200)
```

---

## TESTING INSTRUCTIONS

### Unit Tests
- Mock all external services (Anthropic API, WhatsApp API, SQS)
- Test graph traversal algorithms with known inputs/outputs
- Test conversation state machine transitions
- Test compliance guard with known-good and known-bad messages
- Use factories (Factory Boy) for test data

### Integration Tests
- Use test PostgreSQL database (Docker Compose provides one)
- Test full diagnostic flow: create session → submit responses → get profile
- Test webhook handling end-to-end
- Test parent engagement cycle

### Prompt Evaluation Tests
- Load test cases from `data/prompts/test_cases/`
- Actually call the Anthropic API (not mocked) in prompt eval tests
- Validate output against output_schema
- Mark as slow tests (separate pytest marker)

### Compliance Tests
- Run GUARD-001 on every message template
- Verify Wolf/Aurino compliance rules
- These tests block deployment if they fail

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

# In services:
raise NotFoundError(f"Student {student_id} not found")
raise ComplianceError("Message failed Wolf/Aurino compliance check", issues=guard_result["issues"])

# In API handlers (FastAPI exception handlers):
@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
```

### Logging
```python
import structlog
logger = structlog.get_logger()

# Always include context:
logger.info("diagnostic_session_created", student_id=str(student.id), entry_grade=entry_grade)
logger.error("ai_inference_failed", prompt_id="DIAG-001", error=str(e), session_id=str(session.id))
```

### Database Sessions
```python
from gapsense.db.session import get_session

# FastAPI dependency injection:
@router.get("/students/{student_id}")
async def get_student(student_id: UUID, session: AsyncSession = Depends(get_session)):
    student = await session.get(Student, student_id)
    if not student:
        raise NotFoundError(f"Student {student_id} not found")
    return student
```

---

## WHAT TO BUILD FIRST

Priority order for implementation:
1. **Models + DB setup** — SQLAlchemy models from data model, Alembic migration, seed data
2. **Graph traversal service** — Load prerequisite graph, implement traversal algorithms
3. **Health endpoints** — /health, /health/ready
4. **CRUD endpoints** — Students, Parents, Schools, Teachers
5. **WhatsApp webhook** — Verification handshake + inbound message routing
6. **Conversation manager** — Onboarding flow
7. **Diagnostic engine** — AI-powered diagnostic flow
8. **Parent engagement** — Report generation + activity generation + compliance guard
9. **Teacher reporting** — Classroom reports
10. **Analytics** — Aggregation queries and endpoints
11. **Worker** — SQS polling + message handlers
12. **CDK deployment** — Infrastructure provisioning

---

## REMEMBER

GapSense exists because 84% of Ghanaian children aged 7-14 lack foundational numeracy. Every line of code you write serves a child who deserves better. The diagnostic must be accurate. The parent messages must be dignifying. The system must work on a Nokia feature phone over WhatsApp on a 2G connection in a rural Northern Region community. Build with care.
