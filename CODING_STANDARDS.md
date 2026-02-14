# GapSense Coding Standards
**Version 1.0 | February 2026 | 7-Day Sprint Edition**

---

## Mission-Critical Context

**This is not typical software. GapSense directly impacts vulnerable children.**

- **Wolf/Aurino compliance failures** → Parents disengage → Children suffer
- **Diagnostic bugs** → Wrong gap identified → Wasted parent effort, eroded trust
- **Proprietary IP leaks** → Business destroyed (prerequisite graph = moat)
- **Data breaches** → Ghana Data Protection Act violations, UNICEF trust lost
- **Performance failures** → WhatsApp blocks us (>3s webhook response)

**Every line of code carries responsibility.**

---

## Repository Structure (Two-Repo Strategy)

### Repo 1: `gapsense-platform` (Code - Potentially Open Source Later)
```
gapsense-platform/
├── src/gapsense/          # All application code
├── tests/                 # Test suite
├── infrastructure/        # AWS CDK
├── docker/                # Docker configs
├── docs/                  # Documentation
├── .github/               # CI/CD workflows
└── README.md
```

**What goes here:**
- ✅ All Python code
- ✅ API specifications (OpenAPI)
- ✅ Infrastructure as code
- ✅ Docker/compose files
- ✅ Tests
- ✅ Documentation (architecture, ADRs)

**What NEVER goes here:**
- ❌ Prerequisite graph JSON
- ❌ Prompt library JSON
- ❌ Business documents (.docx)
- ❌ API keys, credentials
- ❌ Real student data

### Repo 2: `gapsense-data` (Proprietary IP - PRIVATE FOREVER)
```
gapsense-data/
├── curriculum/
│   ├── prerequisite_graph_v1.2.json       # CORE IP - 35 nodes, 6 cascades
│   ├── misconceptions_database.json
│   └── cascade_paths.json
├── prompts/
│   ├── prompt_library_v1.1.json           # CORE IP - 13 prompts
│   └── test_cases/
├── business/
│   ├── *.docx files                        # Strategy, partnership docs
│   └── term_sheets/
├── seed_data/
│   ├── regions.json
│   └── districts.json
└── README.md (explains how to sync with platform)
```

**Access control:**
- Private GitHub repo with restricted access
- 2FA mandatory for all contributors
- No cloning on shared/public machines
- Encrypted at rest (repo settings)

**How they connect:**
```bash
# In gapsense-platform development:
export GAPSENSE_DATA_PATH=/path/to/gapsense-data
python scripts/load_curriculum.py  # Reads from $GAPSENSE_DATA_PATH
```

**Production:**
- Data repo deployed separately via AWS Secrets Manager or S3 (encrypted)
- Platform code never contains hardcoded IP

---

## 1. Testing Strategy (Sprint-Adapted TDD)

**Not pure TDD. Strategic TDD.**

### Tier 1: MUST TEST (Blocking - CI Fails Without These)
These protect children and the business:

```python
# tests/unit/test_guard_compliance.py
def test_guard_rejects_deficit_language():
    """GUARD-001 MUST block 'behind', 'struggling', 'failing'"""
    message = "Kwame is behind in mathematics"
    result = await ai_service.invoke_prompt('GUARD-001', {...})
    assert result['approved'] == False
    assert 'deficit_language' in result['issues']

def test_guard_requires_strength_first():
    """GUARD-001 MUST require strength-first framing"""
    message = "Help Kwame with counting: ..."  # No strength mentioned
    result = await ai_service.invoke_prompt('GUARD-001', {...})
    assert result['approved'] == False

# tests/unit/test_graph_traversal.py
def test_backward_trace_place_value_collapse():
    """Ensure backward tracing finds B2.1.1.1 from B4.1.1.1"""
    path = graph_service.backward_trace("B4.1.1.1", max_depth=4)
    assert "B2.1.1.1" in path
    assert path.index("B2.1.1.1") < path.index("B4.1.1.1")

def test_cascade_detection():
    """Ensure cascade path matching works"""
    gaps = ["B2.1.1.1", "B4.1.1.1"]
    cascade = graph_service.find_cascade_path(gaps)
    assert cascade == "Place Value Collapse"

# tests/integration/test_diagnostic_engine.py
async def test_full_diagnostic_session_traces_backward():
    """End-to-end: B5 student with place value gap"""
    session = await diagnostic_engine.create_session(
        student_id=test_student.id,
        entry_grade="B5"
    )

    # Simulate responses (from test scenario TS-DIAG-001)
    responses = [
        ("B4.1.1.1", "Write 14,031 in expanded form", "1+4+0+3+1", False),
        ("B2.1.1.1", "In 347, what does the 4 mean?", "4", False),
        # ... full test scenario
    ]

    for node, question, answer, correct in responses:
        result = await diagnostic_engine.process_response(session.id, answer)

    profile = await db.get(GapProfile, session.gap_profile_id)
    assert profile.primary_root_gap == "B2.1.1.1"
    assert profile.cascade_path == "Place Value Collapse"
```

### Tier 2: SHOULD TEST (Important, Not Blocking)
```python
# tests/unit/test_ai_service.py
# Prompt loading, template rendering, response parsing

# tests/unit/test_whatsapp_service.py
# Message formatting, button construction (mock HTTP)

# tests/integration/test_parent_engagement.py
# Onboarding flow, activity delivery
```

### Tier 3: CAN SKIP (For 7-Day Sprint)
- CRUD endpoints (trivial, covered by integration tests)
- Health check endpoints
- Simple getters/setters
- Database model properties

### Test Running
```bash
# Fast tests (unit only)
pytest tests/unit -v

# Critical compliance tests (MUST pass before deploy)
pytest tests/unit/test_guard_compliance.py -v --strict

# Full suite
pytest tests/ -v --cov=src/gapsense --cov-report=html

# CI requirement: >70% coverage on critical modules
# diagnostic/, engagement/, curriculum/, ai/
```

---

## 2. Domain-Driven Design (Already in Architecture)

**The specifications already follow DDD. Just implement correctly.**

### Bounded Contexts (Module Boundaries)
```python
gapsense/
├── curriculum/        # NaCCA graph, traversal algorithms
├── diagnostic/        # Session management, question generation
├── engagement/        # Parent messaging, activity delivery
├── webhooks/          # WhatsApp integration
├── teachers/          # Teacher reports
├── analytics/         # Aggregation
└── core/              # Shared: models, schemas, config
```

**Rules:**
- `curriculum/` has NO dependencies on other modules (pure graph logic)
- `diagnostic/` depends on `curriculum/` and `ai/` only
- `engagement/` depends on `diagnostic/` and `ai/` only
- `webhooks/` coordinates but contains no business logic
- `ai/` depends on NOTHING (pure Anthropic wrapper)

### Entities (Have Identity, Lifecycle)
```python
class Student(Base):
    id: UUID  # Identity
    # Lifecycle: created → has_gap_profile → engaged_parent → ...

class DiagnosticSession(Base):
    id: UUID
    # Lifecycle: created → in_progress → completed → profiled
```

### Value Objects (Immutable, No Identity)
```python
@dataclass(frozen=True)
class NodeCode:
    code: str  # e.g., "B2.1.1.1"

    def __post_init__(self):
        if not re.match(r'^B\d+\.\d+\.\d+\.\d+$', self.code):
            raise ValueError(f"Invalid node code: {self.code}")

@dataclass(frozen=True)
class GapConfidence:
    value: float  # 0.0 to 1.0

    def __post_init__(self):
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be 0-1: {self.value}")

    @property
    def is_sufficient(self) -> bool:
        return self.value >= 0.80
```

### Aggregates (Transaction Boundaries)
```python
# DiagnosticSession is an aggregate root
# It owns DiagnosticQuestions
# You don't create questions directly, you do:
session.add_question(question)
# Not: db.add(DiagnosticQuestion(...))
```

### Services (Orchestrate Business Logic)
```python
# diagnostic/engine.py
class DiagnosticEngine:
    """Orchestrates the diagnostic session workflow"""

    async def create_session(self, student_id: UUID, entry_grade: str) -> DiagnosticSession:
        """Creates session, generates first question"""

    async def process_response(self, session_id: UUID, response: str) -> DiagnosticNextStep:
        """Analyzes response, decides next action (trace back or continue)"""

    async def finalize_profile(self, session_id: UUID) -> GapProfile:
        """Generates final gap profile from session data"""
```

**Not controllers, not DAOs, not utilities. Domain services.**

---

## 3. SOLID Principles (Applied to GapSense)

### S - Single Responsibility Principle
```python
# BAD: God class
class DiagnosticService:
    def create_session(self): ...
    def analyze_response(self): ...
    def send_parent_message(self): ...  # NO - different responsibility
    def generate_teacher_report(self): ...  # NO

# GOOD: Focused services
class DiagnosticEngine:
    def create_session(self): ...
    def analyze_response(self): ...

class ParentEngagementService:
    def send_diagnostic_report(self): ...
    def send_activity(self): ...

class TeacherReportService:
    def generate_class_report(self): ...
```

### O - Open/Closed Principle
```python
# Extendable without modifying
class PromptInvoker:
    async def invoke(self, prompt_id: str, variables: dict) -> dict:
        prompt = self.prompt_library[prompt_id]
        # Base implementation

# Future: Add caching decorator without changing PromptInvoker
@with_cache
class CachedPromptInvoker(PromptInvoker):
    async def invoke(self, prompt_id: str, variables: dict) -> dict:
        # Check cache first
        return await super().invoke(prompt_id, variables)
```

### L - Liskov Substitution Principle
```python
# All message senders should be substitutable
class MessageSender(ABC):
    @abstractmethod
    async def send(self, recipient: str, content: str) -> str:
        """Returns message_id"""

class WhatsAppSender(MessageSender):
    async def send(self, phone: str, content: str) -> str:
        # Send via WhatsApp Cloud API

class SMSSender(MessageSender):  # Future
    async def send(self, phone: str, content: str) -> str:
        # Send via Africa's Talking

# Code using MessageSender works with both
async def deliver_message(sender: MessageSender, recipient: str, msg: str):
    await sender.send(recipient, msg)
```

### I - Interface Segregation Principle
```python
# Don't force clients to depend on methods they don't use
class GraphReader(Protocol):
    def get_node(self, code: str) -> Node: ...
    def get_prerequisites(self, code: str) -> list[str]: ...

class GraphWriter(Protocol):
    def add_node(self, node: Node) -> None: ...
    def add_prerequisite(self, source: str, target: str) -> None: ...

# Diagnostic engine only needs GraphReader, not GraphWriter
class DiagnosticEngine:
    def __init__(self, graph: GraphReader):  # Not full graph service
        self.graph = graph
```

### D - Dependency Inversion Principle
```python
# BAD: Depend on concrete implementation
class DiagnosticEngine:
    def __init__(self):
        self.ai_client = AnthropicClient()  # Concrete dependency

# GOOD: Depend on abstraction
class AIProvider(Protocol):
    async def generate(self, prompt: str, **kwargs) -> dict: ...

class DiagnosticEngine:
    def __init__(self, ai_provider: AIProvider):
        self.ai_provider = ai_provider  # Can swap for OpenAI, local model, etc.
```

---

## 4. Clean Code Practices

### Naming
```python
# GOOD: Intention-revealing
def backward_trace_to_root_gap(node_code: str) -> list[str]:
    """Traces backward through prerequisite graph until root gap found"""

# BAD: Abbreviations, unclear
def bwd_trc(nc: str) -> list[str]:
    """What does this do?"""

# GOOD: Pronounceable
class DiagnosticSessionResponse:
    student_answer: str
    expected_answer: str
    is_correct: bool

# BAD: Unpronounceable
class DgSsnRsp:
    stdans: str
    expans: str
    crct: bool

# Domain language: Use NaCCA terminology
class CurriculumNode:  # Not "LearningUnit"
    content_standard: str  # Not "topic"
    indicator: str  # Not "subtopic"
```

### Functions
```python
# GOOD: Small, single purpose, clear
async def validate_parent_message_compliance(
    message: str,
    parent: Parent
) -> ComplianceResult:
    """Validates message against Wolf/Aurino principles.

    Args:
        message: The message text to validate
        parent: Parent context (language, literacy level)

    Returns:
        ComplianceResult with approved=True/False and issues list

    Raises:
        AIServiceError: If GUARD-001 prompt fails
    """
    guard_result = await self.ai_service.invoke_prompt('GUARD-001', {
        'message_text': message,
        'parent_name': parent.preferred_name,
        'literacy_level': parent.literacy_level,
        'preferred_language': parent.preferred_language
    })

    return ComplianceResult(
        approved=guard_result['approved'],
        issues=guard_result.get('issues', [])
    )

# BAD: Too long, multiple responsibilities
async def handle_stuff(data: dict) -> dict:
    # 200 lines of mixed concerns
    # Validation + DB access + AI call + logging + ...
```

### Type Hints (Mandatory)
```python
from __future__ import annotations  # Every file
from typing import Protocol, Literal
from uuid import UUID

# GOOD: Full type coverage
async def create_diagnostic_session(
    student_id: UUID,
    entry_grade: Literal["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"],
    entry_nodes: list[str] | None = None
) -> DiagnosticSession:
    ...

# BAD: No types
async def create_diagnostic_session(student_id, entry_grade, entry_nodes=None):
    ...

# Run MyPy strict mode
# mypy src/gapsense --strict
```

### No Magic Numbers/Strings
```python
# BAD
if confidence > 0.8:
    ...
if parent.literacy_level == "low":
    ...

# GOOD
CONFIDENCE_THRESHOLD = 0.80  # Per ADR-003
LITERACY_LEVEL_LOW = "low"
LITERACY_LEVEL_MEDIUM = "medium"
LITERACY_LEVEL_HIGH = "high"

if confidence >= CONFIDENCE_THRESHOLD:
    ...
if parent.literacy_level == LITERACY_LEVEL_LOW:
    ...

# Even better: Use Enums
class LiteracyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

### Comments (When and How)
```python
# GOOD: Explain WHY, not WHAT
# Wolf/Aurino research shows deficit language causes parent disengagement
# So we run GUARD-001 at temp=0.0 for deterministic compliance checking
guard_result = await self.ai_service.invoke_prompt('GUARD-001', {...})

# BAD: Explain obvious code
# Loop through students
for student in students:
    ...

# GOOD: Warn about non-obvious behavior
# Meta requires webhook response within 3 seconds or they'll retry/block
# So we enqueue to SQS and return 200 immediately
await sqs_service.send_message(queue_url, payload)
return Response(status_code=200)

# GOOD: Mark technical debt
# TODO(maku): Replace with batch insert when dataset > 1000 nodes
for node in nodes:
    await db.add(node)
```

### Docstrings (Google Style - Mandatory for Public APIs)
```python
async def backward_trace(
    node_code: str,
    max_depth: int = 4,
    graph: GraphReader | None = None
) -> list[str]:
    """Traces backward through prerequisite graph to find root gaps.

    Implements the backward tracing algorithm from ADR-005. Given a node
    where a student shows a gap, traces backward through prerequisite edges
    until finding the deepest node the student has NOT mastered.

    Args:
        node_code: The starting node (e.g., "B4.1.3.1")
        max_depth: Maximum depth to trace (default 4 prevents infinite loops)
        graph: Graph reader to use (defaults to global graph service)

    Returns:
        List of node codes in trace order, from deepest to starting node.
        Example: ["B1.1.3.1", "B2.1.3.1", "B4.1.3.1"]

    Raises:
        NodeNotFoundError: If node_code doesn't exist in graph
        GraphTraversalError: If cycle detected or max_depth exceeded

    Example:
        >>> await backward_trace("B4.1.3.1")
        ["B1.1.3.1", "B2.1.3.1", "B3.1.3.1", "B4.1.3.1"]
    """
```

---

## 5. Async & Concurrency

### The Golden Rule: Never Block the Event Loop
```python
# BAD: Blocking I/O in async function
async def get_student(student_id: UUID):
    with open('data/students.json') as f:  # BLOCKS!
        data = json.load(f)
    return data

# GOOD: Use async I/O
async def get_student(student_id: UUID):
    async with aiofiles.open('data/students.json') as f:
        data = await f.read()
        return json.loads(data)

# BAD: Sync database in async function
async def save_student(student: Student):
    session.add(student)  # If this is sync SQLAlchemy
    session.commit()

# GOOD: Async database
async def save_student(student: Student):
    async with get_session() as session:
        session.add(student)
        await session.commit()
```

### Connection Pooling
```python
# Database (AsyncSession with pool)
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,  # Concurrent connections
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

# HTTP Client (shared across app)
class AIService:
    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_connections=20)
        )
```

### Background Work Goes to SQS, Not FastAPI
```python
# BAD: FastAPI background task (loses work if container dies)
@app.post("/diagnostics/sessions")
async def create_session(data: SessionCreate, background_tasks: BackgroundTasks):
    session = await diagnostic_engine.create_session(...)
    background_tasks.add_task(send_parent_notification, session.id)
    return session

# GOOD: Enqueue to SQS (durable, worker processes)
@app.post("/diagnostics/sessions")
async def create_session(data: SessionCreate):
    session = await diagnostic_engine.create_session(...)

    await sqs_service.send_message(
        queue_url=settings.SQS_QUEUE_URL,
        message_body=json.dumps({
            "type": "diagnostic_complete",
            "session_id": str(session.id)
        })
    )

    return session
```

### Rate Limiting (Anthropic API)
```python
# Anthropic limits: 50 requests/minute (Sonnet), 200/min (Haiku)
# Use token bucket or async semaphore

class AIService:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

    async def invoke_prompt(self, prompt_id: str, variables: dict):
        async with self.semaphore:
            # Only 10 concurrent Claude API calls
            response = await self.anthropic.messages.create(...)
            return response
```

---

## 6. Security & Privacy (Ghana Data Protection Act)

### Minimal Data Collection
```python
# GOOD: What we store
class Student(Base):
    id: UUID
    first_name: str  # "Kwame" only
    current_grade: str
    home_language: str
    school_id: UUID

# BAD: What we DON'T store
# last_name: str  # No
# date_of_birth: date  # No - just age range
# national_id: str  # NEVER
# home_address: str  # NEVER
# parent_income: Decimal  # NEVER
```

### Encryption
```python
# At rest: RDS, S3 (AWS KMS)
database = rds.DatabaseInstance(
    self, "GapSenseDB",
    storage_encrypted=True,
    # ...
)

media_bucket = s3.Bucket(
    self, "MediaBucket",
    encryption=s3.BucketEncryption.S3_MANAGED,
    # ...
)

# In transit: TLS 1.3 everywhere
# Enforced at ALB level
```

### Input Validation (Pydantic)
```python
class StudentCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    current_grade: Literal["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"]
    home_language: Literal["en", "tw", "ee", "ga", "dag"]
    school_id: UUID

    @field_validator('first_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        # No validation beyond basic - names are diverse
        return v.strip()

# FastAPI validates automatically
@app.post("/students", response_model=Student)
async def create_student(data: StudentCreate):
    # data is already validated
    ...
```

### No PII in Logs
```python
import structlog

logger = structlog.get_logger()

# BAD
logger.info("parent_message_sent", phone="+233241234567", message=message_text)

# GOOD
logger.info("parent_message_sent",
    parent_id=str(parent.id),  # UUID, not phone
    message_length=len(message_text),
    language=parent.preferred_language
)

# GOOD: Redaction for debugging
def redact_phone(phone: str) -> str:
    """Redacts phone number for logging"""
    return phone[:4] + "****" + phone[-2:]

logger.debug("whatsapp_delivery", phone=redact_phone(phone))
```

### Right to Deletion
```python
@app.delete("/students/{student_id}")
async def delete_student(student_id: UUID, current_user: User = Depends(get_current_user)):
    """Deletes student data per Ghana Data Protection Act Article 31.

    - Soft delete: Sets deleted_at timestamp
    - Anonymizes after 30 days: Removes names, replaces with "DELETED_USER"
    - Keeps diagnostic data for research (anonymized)
    - Purges PII completely
    """
    student = await db.get(Student, student_id)

    # Authorization check
    if not user_can_delete(current_user, student):
        raise HTTPException(403)

    # Soft delete
    student.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    # Enqueue for anonymization (30 days later)
    await sqs_service.send_message(
        queue_url=settings.ANONYMIZATION_QUEUE_URL,
        message_body=json.dumps({
            "type": "anonymize_student",
            "student_id": str(student_id),
            "delete_after": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        })
    )
```

### 2-Year Retention Policy
```python
# RDS lifecycle policy (in CDK)
# Manual process: Quarterly anonymization job
# Anonymize records older than 2 years:
# - student.first_name → "ANONYMIZED"
# - parent.phone → NULL
# - Keep diagnostic_sessions (for research)
# - Keep gap_profiles (anonymized)
```

---

## 7. Proprietary Code Protection

### Separate Repos (Already Explained Above)
- `gapsense-platform`: Code
- `gapsense-data`: IP (prerequisite graph, prompts, business docs)

### .gitignore (Aggressive)
```gitignore
# gapsense-platform/.gitignore

# Environment variables
.env
.env.*
!.env.example

# Proprietary data (should never exist here, but double-check)
data/curriculum/*.json
data/prompts/*.json
*.docx

# Credentials
secrets/
credentials/
*.pem
*.key

# Temporary files
*.log
*.tmp
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

### Pre-commit Hooks (Block Sensitive Files)
```bash
# .git/hooks/pre-commit (or use pre-commit framework)
#!/bin/bash

# Block commits containing sensitive patterns
if git diff --cached --name-only | grep -qE 'prerequisite_graph|prompt_library'; then
    echo "ERROR: Attempting to commit proprietary IP files!"
    echo "These files belong in gapsense-data repo, not gapsense-platform."
    exit 1
fi

# Block API keys
if git diff --cached -U0 | grep -qE 'sk-ant-|ANTHROPIC_API_KEY.*=.*sk-'; then
    echo "ERROR: API key detected in commit!"
    exit 1
fi

# Block actual phone numbers in code (test data should use fake numbers)
if git diff --cached -U0 | grep -qE '\+233[0-9]{9}'; then
    echo "WARNING: Possible real phone number detected."
    echo "Use test phone numbers like +233000000000"
    exit 1
fi

exit 0
```

### Environment Variables (Never Commit)
```bash
# .env.example (committed)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/gapsense
ANTHROPIC_API_KEY=sk-ant-your-key-here
WHATSAPP_API_TOKEN=your-token-here
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_VERIFY_TOKEN=your-verify-token
AWS_REGION=af-south-1
SQS_QUEUE_URL=https://sqs.af-south-1.amazonaws.com/123/gapsense-messages.fifo
ENVIRONMENT=local
LOG_LEVEL=DEBUG

# .env (NEVER committed, in .gitignore)
DATABASE_URL=postgresql+asyncpg://gapsense:actual_password@localhost:5432/gapsense
ANTHROPIC_API_KEY=sk-ant-actual-key-xxxxx
# ... real values
```

### Code Reviews Check for Leaks
Before any commit to main:
- ✅ No hardcoded API keys
- ✅ No prerequisite graph data in code
- ✅ No prompt text in code (load from JSON)
- ✅ No real phone numbers
- ✅ No student/parent PII in test fixtures

---

## 8. AI Integration Standards

### Prompt Caching (Critical for Cost)
```python
# GOOD: Caching system prompt + graph
response = await self.anthropic.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    temperature=0.2,
    system=[
        {
            "type": "text",
            "text": prompt['system_prompt'],  # ~2000 tokens
            "cache_control": {"type": "ephemeral"}
        },
        {
            "type": "text",
            "text": json.dumps(prerequisite_graph),  # ~2000 tokens
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[{"role": "user", "content": user_prompt}]  # Dynamic, not cached
)

# Cost savings: 90% reduction on cached tokens
# $15/MTok (regular) → $1.50/MTok (cached read) → $0.15/MTok (cached write)
```

### Temperature Settings (Per Prompt Type)
```python
PROMPT_TEMPERATURES = {
    'DIAG-001': 0.2,   # Diagnostic reasoning - low randomness
    'DIAG-002': 0.2,   # Response analysis - deterministic
    'DIAG-003': 0.3,   # Profile generation - slightly more creative
    'PARENT-001': 0.4, # Parent messages - warm but controlled
    'PARENT-002': 0.4, # Activities - slightly creative
    'ACT-001': 0.5,    # Activity generation - creative but safe
    'GUARD-001': 0.0,  # Compliance check - FULLY DETERMINISTIC
    'TEACHER-001': 0.3, # Reports - factual
    'TEACHER-003': 0.4, # Conversation - natural
}
```

### GUARD-001 is Non-Negotiable
```python
async def send_parent_message(parent: Parent, message: str) -> None:
    """Sends message to parent via WhatsApp.

    CRITICAL: ALL parent messages MUST pass GUARD-001 validation.
    This is non-negotiable. Failure to comply risks parent disengagement.
    """
    # First validation
    guard_result = await self.ai_service.invoke_prompt('GUARD-001', {
        'message_text': message,
        'parent_name': parent.preferred_name,
        'literacy_level': parent.literacy_level,
        'preferred_language': parent.preferred_language
    })

    if not guard_result['approved']:
        logger.warning("guard_rejection",
            issues=guard_result['issues'],
            parent_id=str(parent.id)
        )

        # Regenerate with feedback
        message = await self.regenerate_message_with_feedback(
            original_message=message,
            issues=guard_result['issues'],
            parent=parent
        )

        # Re-validate
        guard_result = await self.ai_service.invoke_prompt('GUARD-001', {...})

        if not guard_result['approved']:
            # DOUBLE REJECTION - DO NOT SEND
            logger.error("guard_double_rejection",
                parent_id=str(parent.id),
                issues=guard_result['issues']
            )
            # Alert human for review
            await self.alert_compliance_team(message, guard_result)
            raise ComplianceError(
                "Message failed Wolf/Aurino compliance check twice. "
                "Blocked to prevent harm. Human review required."
            )

    # Only send if approved
    await self.whatsapp_service.send_text(parent.phone, message)

    # Log for audit
    await self.log_interaction(parent.id, message, guard_result)
```

### Output Validation
```python
from jsonschema import validate, ValidationError

async def invoke_prompt(self, prompt_id: str, variables: dict) -> dict:
    """Invokes AI prompt with output schema validation."""
    prompt = self.prompts['prompts'][prompt_id]

    # Call Anthropic
    response = await self._call_anthropic(prompt, variables)

    # Parse JSON
    try:
        result = json.loads(response.content[0].text)
    except json.JSONDecodeError as e:
        logger.error("ai_invalid_json", prompt_id=prompt_id, error=str(e))
        raise AIOutputError(f"AI returned invalid JSON for {prompt_id}")

    # Validate against schema
    try:
        validate(instance=result, schema=prompt['output_schema'])
    except ValidationError as e:
        logger.error("ai_schema_violation",
            prompt_id=prompt_id,
            error=str(e),
            result=result
        )
        raise AIOutputError(f"AI output doesn't match schema for {prompt_id}")

    return result
```

### Error Handling (AI Service)
```python
from anthropic import APIError, RateLimitError, APITimeoutError

async def _call_anthropic(self, prompt: dict, variables: dict) -> Message:
    """Calls Anthropic with retry logic."""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await self.anthropic.messages.create(...)
            return response

        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning("anthropic_rate_limit",
                    attempt=attempt,
                    wait_time=wait_time
                )
                await asyncio.sleep(wait_time)
                continue
            raise

        except APITimeoutError as e:
            logger.error("anthropic_timeout", attempt=attempt)
            if attempt < max_retries - 1:
                continue
            raise

        except APIError as e:
            logger.error("anthropic_api_error",
                error=str(e),
                status_code=getattr(e, 'status_code', None)
            )
            raise
```

---

## 9. WhatsApp Integration

### 3-Second Webhook Rule (Meta Requirement)
```python
@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    """WhatsApp Cloud API webhook handler.

    CRITICAL: Meta requires response within 3 seconds or they will:
    - Retry the webhook (causing duplicates)
    - Eventually block the webhook endpoint

    Strategy: Enqueue immediately, process asynchronously.
    """
    payload = await request.json()

    # Validate webhook signature (security)
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_webhook_signature(signature, await request.body()):
        raise HTTPException(401, "Invalid signature")

    # Extract phone number for FIFO ordering
    phone = extract_phone_from_payload(payload)

    # Enqueue to SQS (should take <100ms)
    await sqs_service.send_message(
        queue_url=settings.SQS_QUEUE_URL,
        message_body=json.dumps({
            "type": "inbound_whatsapp",
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat()
        }),
        message_group_id=phone  # FIFO ordering per parent
    )

    # Return 200 immediately (typically <500ms total)
    return Response(status_code=200)
```

### Message Templates (Pre-Approval Required)
```python
# Templates must be pre-approved in Meta Business Manager
# Use template_library.json for tracking

TEMPLATES = {
    "gapsense_welcome": {
        "name": "gapsense_welcome",
        "language": "en",
        "status": "APPROVED",  # Track approval status
        "variables": ["school_name", "child_first_name"]
    },
    "gapsense_activity": {
        "name": "gapsense_activity",
        "language": "en",
        "status": "APPROVED",
        "variables": ["parent_name", "child_name", "strength", "activity_steps", "materials", "check_back_date"]
    }
}

async def send_template(
    self,
    phone: str,
    template_name: str,
    language: str,
    variables: list[str]
) -> str:
    """Sends pre-approved template message."""

    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Unknown template: {template_name}")

    if template['status'] != "APPROVED":
        raise ValueError(f"Template {template_name} not approved")

    response = await self.http_client.post(
        f"{self.base_url}/{self.phone_number_id}/messages",
        json={
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": var} for var in variables
                        ]
                    }
                ]
            }
        }
    )

    return response.json()['messages'][0]['id']
```

### Media Handling
```python
async def download_media(self, media_id: str) -> bytes:
    """Downloads media from WhatsApp (exercise book photo, voice note)."""

    # Get media URL
    media_info = await self.http_client.get(
        f"{self.base_url}/{media_id}",
        headers={"Authorization": f"Bearer {self.api_token}"}
    )
    media_url = media_info.json()['url']

    # Download media
    media_response = await self.http_client.get(
        media_url,
        headers={"Authorization": f"Bearer {self.api_token}"}
    )

    return media_response.content

async def upload_to_s3(self, media_bytes: bytes, media_type: str, student_id: UUID) -> str:
    """Uploads media to S3 with encryption."""

    key = f"{media_type}/{student_id}/{uuid4()}.jpg"

    await s3_client.put_object(
        Bucket=settings.S3_MEDIA_BUCKET,
        Key=key,
        Body=media_bytes,
        ServerSideEncryption='AES256',
        ContentType='image/jpeg'
    )

    return key
```

---

## 10. Error Handling & Logging

### Custom Exceptions
```python
# core/exceptions.py

class GapSenseError(Exception):
    """Base exception for all GapSense errors"""
    pass

class NotFoundError(GapSenseError):
    """Resource not found (404)"""
    pass

class ConflictError(GapSenseError):
    """Resource conflict (409)"""
    pass

class ComplianceError(GapSenseError):
    """Wolf/Aurino compliance violation (422)"""
    def __init__(self, message: str, issues: list[str] | None = None):
        super().__init__(message)
        self.issues = issues or []

class AIServiceError(GapSenseError):
    """AI service failure (502/503)"""
    pass

class GraphTraversalError(GapSenseError):
    """Prerequisite graph traversal error"""
    pass

class NodeNotFoundError(GraphTraversalError):
    """Node code not found in graph"""
    pass
```

### Exception Handlers (FastAPI)
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)}
    )

@app.exception_handler(ComplianceError)
async def compliance_handler(request: Request, exc: ComplianceError):
    logger.error("compliance_violation",
        path=request.url.path,
        issues=exc.issues
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "issues": exc.issues
        }
    )

@app.exception_handler(AIServiceError)
async def ai_service_handler(request: Request, exc: AIServiceError):
    logger.error("ai_service_error", error=str(exc))
    return JSONResponse(
        status_code=503,
        content={"detail": "AI service temporarily unavailable"}
    )
```

### Structured Logging (structlog)
```python
import structlog
from datetime import datetime, timezone

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# GOOD: Structured, queryable
logger.info("diagnostic_session_created",
    session_id=str(session.id),
    student_id=str(student.id),
    entry_grade=entry_grade,
    entry_nodes=entry_nodes,
    duration_ms=duration_ms
)

logger.warning("guard_rejection",
    parent_id=str(parent.id),
    prompt_id="PARENT-001",
    issues=guard_result['issues'],
    message_length=len(message)
)

logger.error("ai_api_failure",
    prompt_id="DIAG-001",
    error_type=type(e).__name__,
    error_message=str(e),
    session_id=str(session.id),
    retry_attempt=attempt
)

# BAD: Unstructured, hard to query
logger.info(f"Created session {session.id} for student {student.id}")
```

### Correlation IDs (Track Requests Across Services)
```python
from contextvars import ContextVar
from uuid import uuid4

# Correlation ID stored in context
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')

# Middleware to inject correlation ID
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    # Get from header or generate new
    correlation_id = request.headers.get('X-Correlation-ID', str(uuid4()))
    correlation_id_var.set(correlation_id)

    # Add to all logs in this request
    logger = structlog.get_logger().bind(correlation_id=correlation_id)

    response = await call_next(request)
    response.headers['X-Correlation-ID'] = correlation_id
    return response

# Now every log in request context has correlation_id
logger.info("webhook_received", payload_type="message")
# Output: {"event": "webhook_received", "correlation_id": "abc-123", ...}
```

### Graceful Degradation
```python
async def analyze_exercise_book(image_bytes: bytes, student_id: UUID) -> GapProfile:
    """Analyzes exercise book photo.

    If Claude API is down, queue for later processing instead of failing.
    """
    try:
        analysis = await ai_service.invoke_prompt('ANALYSIS-001', {
            'image': base64.b64encode(image_bytes),
            'student_id': str(student_id)
        })

        return await create_gap_profile_from_analysis(analysis)

    except AIServiceError as e:
        logger.error("ai_service_unavailable",
            student_id=str(student_id),
            error=str(e)
        )

        # Graceful degradation: Queue for retry
        await sqs_service.send_message(
            queue_url=settings.RETRY_QUEUE_URL,
            message_body=json.dumps({
                "type": "retry_exercise_book_analysis",
                "student_id": str(student_id),
                "image_s3_key": s3_key,
                "retry_count": 0,
                "retry_after": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
            })
        )

        # Return partial result
        return GapProfile(
            student_id=student_id,
            status="pending_analysis",
            analysis_queued_at=datetime.now(timezone.utc)
        )
```

---

## 11. Performance Standards

### Response Time Targets
```python
# Target response times (p95)
TARGETS = {
    "whatsapp_webhook": 3000,      # Meta requirement
    "diagnostic_question": 2000,   # Generate next question
    "gap_profile_generation": 5000,# Final profile
    "parent_message": 10000,       # Generate + GUARD-001 + send
    "database_query": 100,         # With proper indexes
    "health_check": 50             # Fast path
}

# Measure with middleware
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    logger.info("request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2)
    )

    # Alert if slow
    target = TARGETS.get(request.url.path.split('/')[-1])
    if target and duration_ms > target:
        logger.warning("slow_request",
            path=request.url.path,
            duration_ms=round(duration_ms, 2),
            target_ms=target
        )

    response.headers['X-Response-Time'] = str(round(duration_ms, 2))
    return response
```

### Database Indexes (From data_model.sql)
```sql
-- Critical indexes for performance
CREATE INDEX idx_curriculum_nodes_grade ON curriculum_nodes(grade);
CREATE INDEX idx_curriculum_nodes_severity ON curriculum_nodes(severity DESC);
CREATE INDEX idx_curriculum_nodes_code ON curriculum_nodes(code);  -- Used in every lookup

CREATE INDEX idx_prerequisites_source ON curriculum_prerequisites(source_node_id);
CREATE INDEX idx_prerequisites_target ON curriculum_prerequisites(target_node_id);

CREATE INDEX idx_students_school ON students(school_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_gap_profiles_student ON gap_profiles(student_id);
CREATE INDEX idx_gap_profiles_updated ON gap_profiles(updated_at DESC);  -- For recent gaps query

CREATE INDEX idx_diagnostic_sessions_student ON diagnostic_sessions(student_id);
CREATE INDEX idx_diagnostic_sessions_status ON diagnostic_sessions(session_status);

CREATE INDEX idx_parent_activities_parent ON parent_activities(parent_id);
CREATE INDEX idx_parent_activities_delivered ON parent_activities(delivered_at DESC);

-- Never query without WHERE on indexed columns
-- Good: SELECT * FROM students WHERE school_id = $1 AND deleted_at IS NULL
-- Bad: SELECT * FROM students WHERE first_name = 'Kwame'  -- No index, full scan
```

### Prompt Caching (Already Covered in AI Section)
90% cost reduction is also 90% latency reduction for cached tokens.

---

## 12. Documentation Requirements

### Module README Pattern
```markdown
# Diagnostic Engine Module

## Purpose
Orchestrates adaptive diagnostic sessions using the NaCCA prerequisite graph and Anthropic Claude AI.

## Key Components
- `engine.py`: Main diagnostic orchestration
- `analyzer.py`: Response analysis logic
- `profiler.py`: Gap profile generation

## API
### create_session
Creates a new diagnostic session for a student.

**Args:**
- `student_id`: UUID of the student
- `entry_grade`: Starting grade (B1-B9)
- `entry_nodes`: Optional list of priority nodes to test

**Returns:** DiagnosticSession

**Example:**
```python
session = await diagnostic_engine.create_session(
    student_id=uuid("..."),
    entry_grade="B5"
)
```

## Testing
```bash
pytest tests/unit/test_diagnostic_engine.py -v
```

## Related Modules
- `curriculum/`: Provides graph traversal
- `ai/`: Provides prompt invocation
- `engagement/`: Consumes gap profiles
```

### ADR Pattern (Continue from gapsense_adr.md)
```markdown
## ADR-013: Dual-AI Architecture (Cloud → On-Device)

**Decision:** Cloud-first (Anthropic Claude) in Phase 1, distill to on-device SLM in Phase 2.

**Context:**
- On-device inference desired for offline teacher experience
- But: Cannot fine-tune SLM without labeled training data
- Cloud Phase 1 generates that training data

**Decision:**
Phase 1: Cloud (Anthropic Claude Sonnet/Haiku)
Phase 2: Distill to Gemma 3n or Phi-4-mini using Phase 1 data

**Consequences:**
- ✅ Phase 1 validates AI reasoning with strong model
- ✅ Generates labeled dataset for Phase 2
- ✅ Lower risk (proven model first)
- ⚠️ Higher initial costs (cloud inference)
- ⚠️ Requires internet in Phase 1
```

### Inline Documentation (When to Use)
```python
# Docstrings: All public functions, classes
# Type hints: Every function signature
# Comments: Explain WHY (rationale, constraints, non-obvious behavior)
# ADRs: Major architectural decisions
# README: Module purpose, API, examples
# TODO: Mark technical debt with owner and context
```

---

## 13. Git Workflow (7-Day Sprint Adapted)

### Branch Strategy
```bash
main                    # Production-ready code
├── develop             # Integration branch (if team >1)
└── feature/xyz         # Feature branches

# For solo sprint:
main                    # Just use main + feature branches
└── feature/diagnostic-engine
└── feature/whatsapp-integration
```

### Semantic Commits
```bash
# Format: <type>(<scope>): <subject>

# Types:
feat:     New feature
fix:      Bug fix
refactor: Code restructuring (no behavior change)
test:     Adding tests
docs:     Documentation only
chore:    Build, deps, config

# Examples:
feat(diagnostic): implement backward tracing algorithm
fix(guard): handle empty parent name in GUARD-001
refactor(models): extract base model to reduce duplication
test(graph): add cascade detection test cases
docs(adr): add ADR-013 for dual-AI architecture
chore(deps): upgrade anthropic to 0.43.0
```

### Pre-Commit Checklist
```bash
# Before committing:
□ Code formatted (ruff format)
□ Linting passed (ruff check)
□ Type checking passed (mypy --strict)
□ Tests passed (pytest)
□ No sensitive files (pre-commit hook checks)
□ Commit message follows semantic format
```

### Code Review (Even Solo - Use Claude Code)
```markdown
## Pre-Merge Checklist

### Functionality
- [ ] Code works as intended
- [ ] Edge cases handled
- [ ] Error handling in place

### Tests
- [ ] Unit tests added for new functions
- [ ] Critical paths covered (GUARD-001, graph traversal)
- [ ] Tests pass locally

### Code Quality
- [ ] Follows SOLID principles
- [ ] No code duplication
- [ ] Clear naming
- [ ] Type hints present
- [ ] Docstrings on public APIs

### Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] No PII in logs
- [ ] Encryption used for sensitive data

### Performance
- [ ] No blocking I/O in async functions
- [ ] Database queries use indexes
- [ ] Prompt caching enabled

### Compliance
- [ ] GUARD-001 validation on parent messages
- [ ] Wolf/Aurino principles followed
- [ ] Minimal data collection
```

---

## 14. Linting & Formatting

### Ruff (Fast Python Linter/Formatter)
```toml
# pyproject.toml

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
]
ignore = [
    "E501",  # Line too long (handled by formatter)
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]  # Allow assert in tests

[tool.ruff.lint.isort]
known-first-party = ["gapsense"]
```

### MyPy (Type Checking)
```toml
# pyproject.toml

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = false  # Too strict for libraries
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false  # Relax for tests
```

### Pre-Commit Framework
```yaml
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-all]

  - repo: local
    hooks:
      - id: block-sensitive-files
        name: Block sensitive files
        entry: bash -c 'if git diff --cached --name-only | grep -qE "prerequisite_graph|prompt_library|\.env$"; then echo "ERROR: Sensitive file detected!"; exit 1; fi'
        language: system
        pass_filenames: false

# Install: pre-commit install
# Run manually: pre-commit run --all-files
```

---

## 15. Deployment Standards

### Health Checks
```python
# Required endpoints for AWS ALB

@app.get("/v1/health")
async def health_check():
    """Basic health check - is the service running?"""
    return {"status": "ok"}

@app.get("/v1/health/ready")
async def readiness_check():
    """Readiness check - is the service ready to accept traffic?"""
    checks = {
        "database": await check_database(),
        "sqs": await check_sqs(),
        "s3": await check_s3(),
        "prerequisite_graph": await check_graph_loaded()
    }

    all_ready = all(checks.values())

    return JSONResponse(
        status_code=200 if all_ready else 503,
        content={"status": "ready" if all_ready else "not_ready", "checks": checks}
    )

async def check_database() -> bool:
    """Check database connectivity"""
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False

async def check_graph_loaded() -> bool:
    """Check prerequisite graph is loaded"""
    try:
        node = await graph_service.get_node("B2.1.1.1")
        return node is not None
    except Exception:
        return False
```

### Zero-Downtime Deployment
```python
# AWS Fargate deployment strategy:
# 1. Deploy new task definition
# 2. ALB routes traffic to new tasks
# 3. Health checks pass
# 4. Drain old tasks (30s grace period)
# 5. Terminate old tasks

# Graceful shutdown (handle SIGTERM)
import signal

async def shutdown():
    """Graceful shutdown handler"""
    logger.info("shutdown_initiated", reason="SIGTERM received")

    # Stop accepting new requests
    await app.shutdown()

    # Drain in-flight requests (max 30s)
    await asyncio.sleep(5)

    # Close database connections
    await engine.dispose()

    logger.info("shutdown_complete")

signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown()))
```

### Rollback Plan
```bash
# In CDK deployment:
# 1. Keep previous task definition
# 2. If new deployment fails health checks:
#    - AWS ECS automatically rolls back
#    - ALB stops routing to new tasks
# 3. Manual rollback:
aws ecs update-service \
  --cluster gapsense-production \
  --service gapsense-web \
  --task-definition gapsense-web:PREVIOUS_REVISION

# Database migrations:
# - Never destructive in production
# - Always reversible (alembic downgrade)
# - Test rollback in staging first
```

---

## 16. Sprint-Specific Guidelines (7-Day Context)

### What to Optimize For
✅ **Speed of iteration**
✅ **Critical path testing** (GUARD-001, graph traversal)
✅ **Working end-to-end demo**
✅ **Clean module boundaries** (future maintainability)

### What to Defer
⚠️ **Perfect test coverage** (aim for >70% on critical modules, skip boilerplate)
⚠️ **Performance optimization** (beyond obvious bottlenecks)
⚠️ **Comprehensive error messages** (good enough is fine)
⚠️ **UI polish** (it's an API, UNICEF won't see frontend)

### Daily Quality Gates
**Day 1-2:** Models + DB
- ✅ Alembic migrations run
- ✅ Graph loads into DB
- ✅ Basic CRUD works

**Day 3-4:** Core Services
- ✅ backward_trace test passes
- ✅ GUARD-001 test suite passes (BLOCKING)
- ✅ Diagnostic engine creates session

**Day 5-6:** WhatsApp
- ✅ Webhook responds <3s
- ✅ End-to-end: photo → analysis → parent message

**Day 7:** Deploy
- ✅ Health checks pass in production
- ✅ 1 real WhatsApp message delivered
- ✅ Video demo recorded

---

## 17. Open Source vs Closed Source

### Open Source (Future - After Validation)
**Potentially open-source framework:**
- `gapsense-platform` code (FastAPI architecture, module structure)
- Generic diagnostic engine framework (without NaCCA specifics)
- WhatsApp integration helpers
- Benefit: Community contributions, credibility, hiring

**License:** MIT or Apache 2.0

### Closed Source (Always)
**Never open-source:**
- `gapsense-data` (prerequisite graph, prompts, business docs)
- Deployed configuration (credentials, API keys)
- Customer data
- Business strategy documents

**Protection:** Private repo, restrictive license, legal agreements

---

## Final Reminders

1. **Wolf/Aurino compliance protects children** - GUARD-001 is non-negotiable
2. **Proprietary IP is the business** - Guard the prerequisite graph and prompts
3. **7-day sprint, not 7-month project** - Focus on critical path
4. **Ghana Data Protection Act compliance** - Minimal data, encryption, right to deletion
5. **WhatsApp 3-second rule** - Enqueue, don't process synchronously
6. **Types everywhere** - MyPy strict mode catches bugs early
7. **Async all the way** - Never block the event loop
8. **Structured logging** - Queryable, correlation IDs
9. **Test critical paths** - GUARD-001, graph traversal, diagnostic engine
10. **Separate repos** - Code vs IP

**Every commit should ask: "Does this protect children and the business?"**

---

## Questions / Additions?

This document will evolve as we build. If you encounter patterns not covered here, add them.

Last updated: February 13, 2026
