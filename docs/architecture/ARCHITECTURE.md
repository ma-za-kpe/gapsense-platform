# GapSense Platform Architecture
**Complete Technical Architecture & Stack Specification**

Version: 1.0.0 | Author: Maku Mazakpe | Date: 2026-02-14

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [AWS Infrastructure](#3-aws-infrastructure)
4. [Application Architecture](#4-application-architecture)
5. [Data Architecture](#5-data-architecture)
6. [AI Architecture](#6-ai-architecture)
7. [Security Architecture](#7-security-architecture)
8. [Cost Architecture](#8-cost-architecture)
9. [Deployment Architecture](#9-deployment-architecture)
10. [Monitoring & Observability](#10-monitoring--observability)

---

## 1. SYSTEM OVERVIEW

### 1.1 Mission

**Problem:** 84% of Ghanaian children aged 7-14 lack foundational numeracy (UNICEF MICS 2023).

**Solution:** AI-powered diagnostic platform that:
- Identifies root learning gaps using NaCCA prerequisite graph
- Engages parents via WhatsApp with dignity-first activities
- Provides teachers with actionable classroom insights
- Works on 2G networks in rural Ghana

### 1.2 Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Async-First** | FastAPI, SQLAlchemy async, aiobotocore |
| **Type-Safe** | Python 3.12, Pydantic v2, MyPy strict |
| **Cloud-Native** | AWS Fargate, RDS, SQS, S3 |
| **Cost-Optimized** | Serverless, prompt caching, Cape Town region |
| **Reliability** | Multi-AZ RDS, DLQ, circuit breakers |
| **Privacy-First** | Minimal PII, encryption at rest/transit, GDPR-ready |
| **Africa-Optimized** | 50ms latency, WhatsApp-first, offline-tolerant |

### 1.3 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER LAYER                               │
│  Parent (WhatsApp) │ Teacher (Web) │ Admin (Dashboard)          │
└──────────┬──────────┴───────────────┴────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EDGE LAYER (AWS)                            │
│         ALB (HTTPS) → Certificate Manager → Route 53            │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                             │
│                                                                 │
│  ┌──────────────────┐              ┌──────────────────┐        │
│  │  Fargate Web     │              │  Fargate Worker  │        │
│  │  (FastAPI)       │              │  (SQS Consumer)  │        │
│  │  - Webhooks      │◄─────SQS─────│  - AI Engine     │        │
│  │  - REST API      │    FIFO       │  - Messaging     │        │
│  │  - Health        │              │  - Analytics     │        │
│  └────────┬─────────┘              └────────┬─────────┘        │
│           │                                  │                  │
└───────────┼──────────────────────────────────┼──────────────────┘
            │                                  │
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                 │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  RDS PG 16   │    │     SQS      │    │      S3      │     │
│  │  Multi-AZ    │    │  FIFO + DLQ  │    │    Media     │     │
│  │  Encrypted   │    │  120s vis    │    │  365d expiry │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
            │                                  │
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                             │
│                                                                 │
│  ┌──────────────────┐              ┌──────────────────┐        │
│  │  Anthropic       │              │  WhatsApp Cloud  │        │
│  │  Claude API      │              │  API (Meta)      │        │
│  │  - Sonnet 4.5    │              │  - Templates     │        │
│  │  - Haiku 4.5     │              │  - Media CDN     │        │
│  └──────────────────┘              └──────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. TECHNOLOGY STACK

### 2.1 Core Stack

#### **Language & Runtime**
```toml
python = "^3.12"
poetry = "1.8.2"
```

#### **Backend Framework**
```toml
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.34"}
```
**Rationale (ADR-002):**
- Async-native (critical for 2-10s Claude API calls)
- Built-in OpenAPI generation
- Type hints for better code generation with Claude Code
- Lightweight for Fargate cold starts (<500ms)

#### **Database**
```toml
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
asyncpg = "^0.30"
alembic = "^1.14"
```
**Target:** PostgreSQL 16.4 on AWS RDS
**Rationale (ADR-003):**
- Relational data (students→parents, sessions→questions→nodes)
- JSONB for AI logs without sacrificing referential integrity
- Arrays for node lists (avoid junction tables)
- pg_trgm for fuzzy curriculum search

#### **AI Provider**
```toml
anthropic = "^0.43"
```
**Models (ADR-005):**
- **Sonnet 4.5**: Diagnostic reasoning (DIAG-001/002/003, ANALYSIS-001)
- **Haiku 4.5**: Parent messages (PARENT-001/002/003), compliance (GUARD-001)

**Cost:** ~$20-30/month at MVP scale (500 sessions + 1,500 messages)
**Optimization:** Prompt caching → 90% cost reduction on cached tokens

#### **Data Validation**
```toml
pydantic = "^2.10"
pydantic-settings = "^2.7"
```

#### **HTTP Client**
```toml
httpx = "^0.28"  # Async HTTP for external APIs
```

#### **AWS SDK**
```toml
aiobotocore = "^2.15"  # Async boto3 wrapper
```

#### **Authentication**
```toml
python-jose = {extras = ["cryptography"], version = "^3.3"}  # JWT
```

#### **Logging**
```toml
structlog = "^24.4"  # Structured JSON logging
```

#### **File Handling**
```toml
python-multipart = "^0.0.9"  # File uploads
aiofiles = "^24.1"            # Async file I/O
```

### 2.2 Development Tools

#### **Code Quality**
```toml
ruff = "^0.9"      # Linting + formatting
mypy = "^1.14"     # Type checking
pre-commit = "^4.0"
```

**Configuration:**
```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
strict = true
```

#### **Testing**
```toml
pytest = "^8.3"
pytest-asyncio = "^0.25"
pytest-cov = "^6.0"
factory-boy = "^3.3"  # Test data factories
```

### 2.3 Infrastructure Tools

#### **Containerization**
- **Docker**: Multi-stage build (dev + production)
- **Docker Compose**: Local dev environment (PostgreSQL + LocalStack)

#### **Infrastructure as Code**
- **AWS CDK**: Python (aws-cdk-lib, constructs)

#### **Local AWS Simulation**
- **LocalStack**: 3.0 (SQS FIFO + S3 buckets)

---

## 3. AWS INFRASTRUCTURE

### 3.1 Region & Availability

**Primary Region:** `af-south-1` (Cape Town)

**Rationale:**
- Lowest latency to Ghana (~50ms vs 150ms+ from Europe)
- UNICEF/World Bank projects commonly use AWS
- Multi-AZ support for production

### 3.2 Compute Layer

#### **AWS Fargate (ECS)**

**Web Service:**
```python
# Task Definition
cpu = 256 (staging), 512 (production)
memory = 512MB (staging), 1024MB (production)
desired_count = 1 (staging), 2 (production)
auto_scaling = {
    'max_capacity': 2 (staging), 4 (production),
    'metric': 'RequestCountPerTarget',
    'target_value': 500
}
```

**Worker Service:**
```python
# Task Definition
cpu = 256 (staging), 512 (production)
memory = 512MB (staging), 1024MB (production)
desired_count = 1 (both environments)
# No auto-scaling (fixed 1 task - see cost optimization doc for queue-based scaling)
```

**Container Image:**
- Multi-stage Dockerfile (base → dev → production)
- Non-root user for security
- Health check: `/v1/health/ready`

**Cost:**
- Staging: $10/month (2 tasks @ 256 CPU)
- Production: $40/month (4 tasks @ 512 CPU)

#### **Deployment Configuration**
- Circuit breaker: Enabled (automatic rollback on failure)
- Health check grace period: 60s
- Rolling update: 100% min healthy, 200% max

### 3.3 Database Layer

#### **RDS PostgreSQL 16.4**

**Staging:**
```python
instance_type = "db.t3.small"
allocated_storage = 20GB
max_allocated_storage = 50GB
multi_az = False
backup_retention = 1 day
deletion_protection = False
```

**Production:**
```python
instance_type = "db.t3.medium"
allocated_storage = 20GB
max_allocated_storage = 100GB
multi_az = True  # High availability
backup_retention = 7 days
deletion_protection = True
```

**Security:**
- Located in isolated private subnet (no internet access)
- Encryption at rest: AES-256
- TLS 1.3 in transit
- Automated backups to S3

**Extensions:**
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- Encryption
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- Fuzzy search
```

**Cost:**
- Staging: $13/month
- Production: $26/month

### 3.4 Messaging Layer

#### **SQS FIFO Queue**

**Configuration:**
```python
queue_name = "gapsense-messages-{env}.fifo"
fifo = True
content_based_deduplication = True
visibility_timeout = 120  # Seconds (AI processing takes up to 60s)
receive_wait_time = 20  # Long polling
message_retention = 4 days
```

**Dead Letter Queue:**
```python
dlq_name = "gapsense-messages-dlq-{env}.fifo"
max_receive_count = 3  # After 3 failures → DLQ
retention_period = 14 days
```

**Message Grouping:**
- `message_group_id = phone_number` → FIFO ordering per parent

**Cost:** ~$2/month (well within free tier)

### 3.5 Storage Layer

#### **S3 Bucket**

**Configuration:**
```python
bucket_name = "gapsense-media-{env}"
encryption = S3_MANAGED  # SSE-S3
block_public_access = BLOCK_ALL  # Never public
versioning = False  # Not needed for media
```

**Lifecycle Rules:**
```python
# Auto-delete old media
lifecycle_rules = [
    {
        'prefix': 'exercise-photos/',
        'expiration_days': 365
    },
    {
        'prefix': 'voice-notes/',
        'expiration_days': 365
    },
    {
        'prefix': 'temp/',
        'expiration_days': 1
    }
]
```

**Folder Structure:**
```
s3://gapsense-media-staging/
├── exercise-photos/
│   └── {student_id}/{timestamp}.jpg
├── voice-notes/
│   └── {student_id}/{timestamp}.ogg
└── temp/
    └── {upload_id}/
```

**Cost:** <$1/month (minimal storage, aggressive cleanup)

### 3.6 Authentication Layer

#### **Cognito User Pool**

**Configuration:**
```python
user_pool_name = "gapsense-{env}"
sign_in_aliases = ["phone", "email"]
self_sign_up = False  # Teachers added by admin only
password_policy = {
    'min_length': 8,
    'require_digits': True,
    'require_lowercase': True
}
```

**User Pool Client:**
```python
auth_flows = ["USER_SRP_AUTH", "USER_PASSWORD_AUTH"]
generate_secret = False  # Public client
token_validity = {
    'access_token': 1,  # Hour
    'id_token': 1,
    'refresh_token': 30  # Days
}
```

**Cost:** Free tier (< 50,000 MAUs)

### 3.7 Secrets Management

#### **AWS Secrets Manager**

**Secrets:**
```python
secrets = [
    "gapsense/{env}/anthropic-api-key",
    "gapsense/{env}/whatsapp",  # JSON: {api_token, phone_number_id, verify_token}
    # Database credentials auto-generated by RDS
]
```

**Access:**
- ECS tasks use IAM task roles (no hardcoded credentials)
- Secrets injected as environment variables
- Automatic rotation: Not enabled (manual for now)

**Cost:** $0.40/month per secret = $1.20/month

### 3.8 Networking Layer

#### **VPC Configuration**

```python
max_azs = 2
nat_gateways = 1 (staging), 2 (production)

subnet_configuration = [
    # Public subnets (CIDR /24)
    {
        'name': 'Public',
        'type': 'PUBLIC',
        'cidr_mask': 24,
        'resources': ['ALB']
    },
    # Private subnets with NAT (CIDR /24)
    {
        'name': 'Private',
        'type': 'PRIVATE_WITH_EGRESS',
        'cidr_mask': 24,
        'resources': ['Fargate tasks']
    },
    # Isolated subnets (CIDR /24)
    {
        'name': 'Isolated',
        'type': 'PRIVATE_ISOLATED',
        'cidr_mask': 24,
        'resources': ['RDS database']
    }
]
```

**Security Groups:**
- ALB: Inbound 80, 443 from 0.0.0.0/0
- Fargate: Inbound 8000 from ALB only
- RDS: Inbound 5432 from Fargate only

**Cost:**
- NAT Gateway: $32/month (staging), $64/month (production) ← **BIGGEST COST**

**Optimization (see Cost Optimization doc):**
- Use VPC Endpoints for S3, Secrets Manager, SQS → Save $10-15/month
- Consider NAT instance for staging → Save $28/month

#### **Application Load Balancer**

```python
public_load_balancer = True
listener_port = 443
redirect_http = True  # 80 → 443

health_check = {
    'path': '/v1/health/ready',
    'interval': 30,
    'healthy_threshold': 2,
    'unhealthy_threshold': 3,
    'timeout': 5
}
```

**⚠️ ISSUE:** No SSL certificate configured in CDK (deployment will fail)

**Fix Required:**
```python
from aws_cdk import aws_certificatemanager as acm

certificate = acm.Certificate(
    self, "Certificate",
    domain_name="api.gapsense.app",
    validation=acm.CertificateValidation.from_dns()
)
```

**Cost:** $16/month

### 3.9 Monitoring Layer

#### **CloudWatch**

**Log Groups:**
```python
log_retention = logs.RetentionDays.ONE_MONTH

log_groups = [
    '/ecs/gapsense-web',
    '/ecs/gapsense-worker',
    '/aws/rds/gapsense-db'
]
```

**Metrics (Specified in ADR-012, not implemented):**
- `diagnostic.session.duration`
- `diagnostic.confidence.mean`
- `engagement.activity.completion_rate`
- `ai.prompt.latency`
- `ai.prompt.error_rate`
- `whatsapp.delivery.rate`

**Alarms (Not implemented):**
- AI error rate > 5%
- SQS DLQ depth > 0
- RDS connection exhaustion
- Fargate CPU > 80%

**Cost:** ~$5/month

### 3.10 Cost Summary

| Service | Staging | Production |
|---------|---------|------------|
| **NAT Gateway** | $32 | $64 |
| **ALB** | $16 | $16 |
| **RDS** | $13 | $26 |
| **Fargate** | $10 | $40 |
| **SQS** | $2 | $2 |
| **S3** | $1 | $2 |
| **Secrets Manager** | $1 | $2 |
| **CloudWatch** | $1 | $4 |
| **TOTAL AWS** | **$76** | **$156** |
| **+ Anthropic AI** | +$20 | +$30 |
| **+ WhatsApp** | +$0 | +$5 |
| **GRAND TOTAL** | **$96** | **$191** |

**With Optimizations (see Cost Optimization doc):**
- Staging: $96 → **$50** (48% reduction)
- Production: $191 → **$120** (37% reduction)

---

## 4. APPLICATION ARCHITECTURE

### 4.1 Service Decomposition

**Modular Monolith** (ADR-010)

```
src/gapsense/
├── core/           # Shared foundation (models, schemas, config, DB)
├── curriculum/     # Prerequisite graph traversal
├── diagnostic/     # Adaptive diagnostic engine
├── engagement/     # Parent WhatsApp engagement
├── teachers/       # Teacher reports
├── webhooks/       # WhatsApp webhook handlers
├── analytics/      # Aggregation & reporting
├── admin/          # System administration
└── ai/             # Anthropic Claude integration
```

**Why monolith?**
- 1-2 developers
- Single database
- Single Fargate task = simpler everything
- FastAPI router groups = natural module boundaries

**When to extract microservices:**
- If any module needs independent scaling (e.g., webhooks at 10K msg/day)

### 4.2 Request Flow

#### **WhatsApp Message Processing**

```
1. WhatsApp Cloud API → POST /webhooks/whatsapp
   ↓
2. Validate signature (WHATSAPP_VERIFY_TOKEN)
   ↓
3. Extract: from, message_type, content
   ↓
4. Send to SQS FIFO (message_group_id = phone_number)
   ↓
5. Return HTTP 200 immediately (< 3 seconds, or Meta blocks)
   ↓
6. Worker polls SQS → receive message
   ↓
7. Route to handler based on message_type:
   - text → conversation_manager
   - image → exercise_book_analyzer
   - button_reply → activity_responder
   ↓
8. Process with AI (Claude Sonnet/Haiku)
   ↓
9. Generate response via PARENT-001 prompt
   ↓
10. Validate with GUARD-001 (dignity compliance)
   ↓
11. Send via WhatsApp Cloud API
   ↓
12. Log to database (parent_interactions table)
   ↓
13. Delete SQS message (success) OR let it retry (failure)
```

#### **Diagnostic Session Flow**

```
1. POST /diagnostics/sessions {student_id, channel}
   ↓
2. Load student record + gap profile (if exists)
   ↓
3. AI: DIAG-001 (Select Entry Node)
   Input: {current_grade, previous_gaps, curriculum_graph}
   Output: {entry_node, first_2_questions}
   ↓
4. Save diagnostic_session (status: in_progress)
   ↓
5. Return questions to client
   ↓
6. POST /diagnostics/sessions/{id}/respond {question_id, response}
   ↓
7. AI: DIAG-002 (Analyze Response)
   Input: {question, response, target_node, graph_context}
   Output: {is_correct, error_pattern, misconception, confidence, next_action}
   ↓
8. IF confidence ≥ 0.80 AND root found:
     AI: DIAG-003 (Generate Gap Profile)
     Update gap_profile table
     Send parent message (PARENT-001)
     Status: completed
   ELSE:
     Generate next question
     Status: in_progress
```

### 4.3 Module Dependency Graph

```
webhooks ───────────────────┐
  │                         │
  ├──> diagnostic           │
  │      │                  │
  │      └──> curriculum    │
  │      └──> ai ◄──────────┼─── (External: Anthropic)
  │                         │
  └──> engagement           │
         │                  │
         └──> ai            │
         └──> diagnostic    │
                            │
teachers ───> diagnostic    │
         └──> curriculum    │
                            │
analytics ──> diagnostic    │
         └──> engagement    │
                            │
admin ───────> ai           │
                            │
core ◄──────── (all modules depend on core)
```

**Rules:**
- No circular dependencies
- `ai/` never imports from `diagnostic/` or `engagement/`
- Module communication via service interfaces

### 4.4 Data Flow Patterns

#### **Command (Write)**
```python
# POST /students
1. Validate request (Pydantic schema)
2. Create SQLAlchemy model
3. Begin transaction
4. Insert to database
5. Commit
6. Return created resource
```

#### **Query (Read)**
```python
# GET /students/{id}/gap-profile
1. Load from database (async query)
2. Transform to Pydantic schema
3. Return JSON
```

#### **Event-Driven (Async)**
```python
# Diagnostic completed
1. Worker: diagnostic_engine.complete_session()
2. Generate gap_profile
3. Publish to SQS: {"type": "send_activity", "student_id": "..."}
4. Another worker: activity_sender.send()
```

---

## 5. DATA ARCHITECTURE

### 5.1 Database Schema

**Tables (25 total):**

**Curriculum (8 tables):**
- `curriculum_strands`
- `curriculum_sub_strands`
- `curriculum_nodes` ← Core: 35 nodes, prerequisite graph
- `curriculum_prerequisites` ← Edges in DAG
- `curriculum_indicators`
- `indicator_error_patterns`
- `curriculum_misconceptions`
- `cascade_paths` ← 6 critical failure cascades

**Users & Schools (6 tables):**
- `regions` (16 Ghana regions)
- `districts`
- `schools`
- `teachers`
- `parents`
- `students`

**Diagnostics (4 tables):**
- `diagnostic_sessions`
- `diagnostic_questions`
- `diagnostic_responses`
- `gap_profiles` ← The diagnostic output

**Engagement (2 tables):**
- `parent_interactions` ← WhatsApp conversation log
- `parent_activities` ← Assigned activities, completion tracking

**AI & Analytics (5 tables):**
- `prompt_categories`
- `prompt_versions` ← 13 prompts
- `prompt_test_cases`
- `school_analytics_daily`
- `district_analytics_monthly`

### 5.2 Key Design Patterns

#### **UUID Primary Keys**
```sql
CREATE TABLE students (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    -- ...
);
```
**Why:** Globally unique, no auto-increment conflicts, better for distributed systems

#### **Timestamps**
```sql
created_at TIMESTAMPTZ DEFAULT NOW(),
updated_at TIMESTAMPTZ DEFAULT NOW()
```
**SQLAlchemy:**
```python
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

#### **Soft Deletes**
```sql
deleted_at TIMESTAMPTZ DEFAULT NULL
```
**Why:** Preserve data for analytics, support "undo"

#### **JSONB for Flexible Data**
```sql
-- AI response logs
ai_response JSONB NOT NULL,
-- Example:
-- {
--   "reasoning": "Student shows place value confusion",
--   "confidence": 0.85,
--   "next_action": "test_prerequisite"
-- }
```

#### **Arrays for Lists**
```sql
mastered_nodes UUID[] DEFAULT ARRAY[]::UUID[],
gap_nodes UUID[] DEFAULT ARRAY[]::UUID[]
```
**Why:** Avoid junction tables for simple many-to-many

#### **Enums for Type Safety**
```sql
CREATE TYPE diagnostic_status AS ENUM ('pending', 'in_progress', 'completed', 'abandoned');
```

### 5.3 Indexing Strategy

**Critical Indexes:**
```sql
-- Students: Find by parent
CREATE INDEX idx_students_parent ON students(parent_id) WHERE deleted_at IS NULL;

-- Diagnostic sessions: Active sessions per student
CREATE INDEX idx_sessions_student_active
ON diagnostic_sessions(student_id, status)
WHERE status = 'in_progress';

-- Curriculum nodes: Find by grade/severity
CREATE INDEX idx_nodes_grade_severity
ON curriculum_nodes(grade, severity DESC);

-- Parent activities: Scheduled reminders
CREATE INDEX idx_activities_scheduled
ON parent_activities(scheduled_reminder)
WHERE scheduled_reminder IS NOT NULL AND completed_at IS NULL;

-- AI usage: Monthly cost analysis
CREATE INDEX idx_ai_usage_month
ON ai_usage_metrics(date_trunc('month', timestamp));
```

### 5.4 Data Retention

| Data Type | Retention | Reason |
|-----------|-----------|--------|
| **Diagnostic sessions** | 2 years | Student progress tracking |
| **Parent interactions** | 2 years | Engagement analysis |
| **AI logs** | 90 days | Cost analysis, debugging |
| **S3 media** | 365 days | Lifecycle policy auto-delete |
| **CloudWatch logs** | 30 days | Cost optimization |

---

## 6. AI ARCHITECTURE

### 6.1 Prompt Library Structure

**13 Prompts (see gapsense-data repo):**

| Prompt ID | Model | Purpose | Temp | Max Tokens |
|-----------|-------|---------|------|------------|
| **DIAG-001** | Sonnet 4.5 | Select diagnostic entry node | 0.3 | 500 |
| **DIAG-002** | Sonnet 4.5 | Analyze student response | 0.2 | 800 |
| **DIAG-003** | Sonnet 4.5 | Generate gap profile | 0.3 | 1500 |
| **PARENT-001** | Haiku 4.5 | Generate parent activity | 0.7 | 600 |
| **PARENT-002** | Haiku 4.5 | Check-in message | 0.8 | 300 |
| **PARENT-003** | Haiku 4.5 | Re-engagement message | 0.8 | 300 |
| **GUARD-001** | Haiku 4.5 | Compliance validation (blocking) | 0.0 | 100 |
| **ANALYSIS-001** | Sonnet 4.5 | Exercise book photo analysis | 0.3 | 1000 |
| **ANALYSIS-002** | Haiku 4.5 | Voice note transcription analysis | 0.5 | 400 |
| **TEACHER-001** | Sonnet 4.5 | Class-level gap report | 0.3 | 2000 |
| **TEACHER-002** | Sonnet 4.5 | Individual student brief | 0.2 | 1200 |
| **TEACHER-003** | Haiku 4.5 | Quick student question answer | 0.7 | 500 |

### 6.2 Prompt Caching Strategy

**Cache System Prompt + Graph Context:**
```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}  # Cache this!
            },
            {
                "type": "text",
                "text": json.dumps(prerequisite_graph),
                "cache_control": {"type": "ephemeral"}  # And this!
            },
            {
                "type": "text",
                "text": user_prompt  # Fresh each time
            }
        ]
    }
]
```

**Savings:**
- System prompt: ~2,000 tokens
- Graph context: ~2,000 tokens
- **Total cacheable: 4,000 tokens**
- Cache read cost: $0.30 per 1M tokens (vs $3.00 uncached)
- **90% cost reduction** on cached portion

**Cache TTL:** 5 minutes (Anthropic default)

### 6.3 Model Selection Logic

```python
async def select_model(prompt_id: str) -> str:
    """Select Claude model based on prompt requirements."""

    ACCURACY_CRITICAL = [
        'DIAG-001', 'DIAG-002', 'DIAG-003',  # Diagnostic must be accurate
        'ANALYSIS-001',  # Exercise book analysis
        'TEACHER-001', 'TEACHER-002'  # Teacher reports
    ]

    SPEED_CRITICAL = [
        'PARENT-001', 'PARENT-002', 'PARENT-003',  # Fast parent replies
        'GUARD-001',  # Compliance check (blocking)
        'ANALYSIS-002',  # Voice notes
        'TEACHER-003'  # Quick answers
    ]

    if prompt_id in ACCURACY_CRITICAL:
        return 'claude-sonnet-4.5'
    elif prompt_id in SPEED_CRITICAL:
        return 'claude-haiku-4.5'
    else:
        return 'claude-haiku-4.5'  # Default to cheaper
```

### 6.4 Error Handling & Retries

```python
from anthropic import Anthropic, APIError, RateLimitError
import backoff

@backoff.on_exception(
    backoff.expo,
    (APIError, RateLimitError),
    max_tries=3,
    max_time=30
)
async def call_anthropic(prompt_id: str, variables: dict) -> dict:
    """Call Anthropic API with automatic retries."""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = prompt_library.get(prompt_id)
    model = select_model(prompt_id)

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=prompt['max_tokens'],
            temperature=prompt['temperature'],
            messages=render_messages(prompt, variables)
        )

        # Track usage for cost monitoring
        await ai_cost_tracker.track_usage(prompt_id, model, response)

        return parse_response(response)

    except RateLimitError:
        logger.warning(f"Rate limited on {prompt_id}, retrying...")
        raise  # Let backoff handle it

    except APIError as e:
        logger.error(f"Anthropic API error: {e}")
        # Fallback: Queue for manual review
        await queue_for_manual_review(prompt_id, variables)
        raise
```

---

## 7. SECURITY ARCHITECTURE

### 7.1 Defense in Depth

```
Layer 1: Network (VPC, Security Groups, ALB WAF)
         ↓
Layer 2: Transport (TLS 1.3 everywhere)
         ↓
Layer 3: Application (JWT auth, rate limiting)
         ↓
Layer 4: Data (Encryption at rest, PII minimization)
         ↓
Layer 5: Audit (Logging, monitoring, alerts)
```

### 7.2 Data Protection (ADR-008)

**Ghana Data Protection Act 2012 Compliance:**

| Requirement | Implementation |
|-------------|----------------|
| **Minimal Collection** | Only first name, age, grade (no last name, no address) |
| **Consent** | Opt-in via WhatsApp (explicit "Yes, let's start!") |
| **Right to Deletion** | DELETE endpoint + WhatsApp "stop" → 24h data removal |
| **Encryption at Rest** | RDS AES-256, S3 SSE-S3 |
| **Encryption in Transit** | TLS 1.3 everywhere |
| **No PII in Logs** | Structured logging redacts phone numbers, names |
| **Retention Limit** | 2 years → auto-anonymize |

**PII Fields:**
```sql
-- NEVER COLLECTED:
-- ❌ Last name
-- ❌ Home address
-- ❌ Ghana Card number
-- ❌ Parent income
-- ❌ Literacy level (NEVER shared, only for internal AI context)

-- COLLECTED (Minimal):
-- ✅ Student first name only
-- ✅ Parent phone number (hashed in logs)
-- ✅ School name (not address)
```

### 7.3 Authentication Flow

**JWT Tokens (python-jose):**

```python
# Token structure
{
    "sub": "user_id",  # UUID
    "role": "parent",  # parent | teacher | admin
    "exp": 1234567890,  # Expiry (1 hour)
    "iat": 1234567890,  # Issued at
    "phone": "+233241234567"  # For audit logs only
}
```

**Token lifecycle:**
1. User sends phone number → `/auth/login`
2. System sends OTP via SMS (future) or WhatsApp
3. User submits OTP → `/auth/verify`
4. System returns: `{access_token, refresh_token}`
5. Client includes: `Authorization: Bearer {access_token}`
6. FastAPI validates via `Depends(get_current_user)`
7. After 1 hour: Client uses refresh_token → `/auth/refresh`

### 7.4 Secrets Management

**Never in Code:**
```python
# ❌ WRONG
ANTHROPIC_API_KEY = "sk-ant-xxxxx"

# ✅ CORRECT
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str

    class Config:
        env_file = ".env"
```

**In Production (AWS):**
- Secrets in AWS Secrets Manager
- ECS injects as environment variables
- No plaintext in CloudFormation/CDK

### 7.5 Input Validation

**Pydantic Schemas:**
```python
from pydantic import BaseModel, Field, field_validator

class StudentCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=5, le=18)
    current_grade: str = Field(pattern=r'^B[1-9]$')  # B1-B9 only

    @field_validator('first_name')
    def validate_name(cls, v):
        # No profanity, no numbers, etc.
        if any(char.isdigit() for char in v):
            raise ValueError('Name cannot contain numbers')
        return v.strip().title()
```

---

## 8. COST ARCHITECTURE

See **COST_OPTIMIZATION_STRATEGY.md** for full details.

**Summary:**
- **Current:** $96/month (staging), $191/month (production)
- **Optimized:** $50/month (staging), $120/month (production)
- **Savings:** 48% (staging), 37% (production)

**Biggest Cost Drivers:**
1. NAT Gateway: 40% of AWS bill
2. RDS: 17% of AWS bill
3. Fargate: 26% of AWS bill
4. ALB: 17% of AWS bill

**Optimization Strategies:**
- VPC Endpoints → Save $10/month
- NAT Instance (staging) → Save $28/month
- RDS off-hours scaling → Save $4/month
- Aggressive AI prompt caching → Save $10/month

---

## 9. DEPLOYMENT ARCHITECTURE

### 9.1 Environments

| Environment | Purpose | URL | Auto-Deploy |
|-------------|---------|-----|-------------|
| **Local** | Development | http://localhost:8000 | Manual |
| **Staging** | QA, testing | https://staging-api.gapsense.app | On `main` push |
| **Production** | Live users | https://api.gapsense.app | On release tag |

### 9.2 CI/CD Pipeline (GitHub Actions)

**On Pull Request:**
```yaml
# .github/workflows/ci.yml
- Ruff lint
- Ruff format check
- MyPy type check
- Pytest (unit + integration)
- Coverage report (must be ≥ 80%)
```

**On Merge to Main:**
```yaml
# .github/workflows/deploy-staging.yml
- Build Docker image
- Push to ECR
- Deploy to Staging via CDK
- Run smoke tests
```

**On Release Tag:**
```yaml
# .github/workflows/deploy-prod.yml
- Build Docker image
- Push to ECR
- Deploy to Production via CDK
- Run smoke tests
- Notify team
```

### 9.3 Deployment Process

**Manual Deployment:**
```bash
# 1. Bootstrap CDK (one-time)
cd infrastructure/cdk
cdk bootstrap aws://ACCOUNT_ID/af-south-1

# 2. Deploy to staging
cdk deploy GapSense-Staging --context env=staging

# 3. Populate secrets (manual - see Cost Optimization doc)
aws secretsmanager put-secret-value \
  --secret-id gapsense/staging/anthropic-api-key \
  --secret-string "sk-ant-xxxxx"

# 4. Run database migrations
./scripts/migrate.sh up

# 5. Load curriculum data
poetry run python scripts/load_curriculum.py

# 6. Verify deployment
curl https://staging-api.gapsense.app/v1/health
```

### 9.4 Rollback Strategy

**Automatic:** Circuit breaker enabled → failed health checks trigger rollback

**Manual:**
```bash
# Option 1: Rollback CDK stack
cdk deploy GapSense-Staging --context env=staging --previous-version

# Option 2: Database migration rollback
./scripts/migrate.sh down

# Option 3: Re-deploy previous Docker image
aws ecs update-service \
  --cluster gapsense-staging \
  --service web \
  --task-definition gapsense-web:PREVIOUS_VERSION
```

---

## 10. MONITORING & OBSERVABILITY

### 10.1 Logging Strategy

**Structured Logging (structlog):**
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "diagnostic_session_completed",
    session_id=session.id,
    student_id=student.id,
    duration_seconds=duration,
    root_gap_node=gap_profile.primary_gap_node,
    confidence=gap_profile.overall_confidence
)
```

**Output (JSON):**
```json
{
  "event": "diagnostic_session_completed",
  "session_id": "uuid-here",
  "student_id": "uuid-here",
  "duration_seconds": 145,
  "root_gap_node": "B2.1.1.1",
  "confidence": 0.87,
  "timestamp": "2026-02-14T10:30:45Z",
  "level": "info"
}
```

**CloudWatch Log Insights Queries:**
```sql
-- Average diagnostic session duration
fields @timestamp, duration_seconds
| filter event = "diagnostic_session_completed"
| stats avg(duration_seconds) as avg_duration

-- AI error rate
fields @timestamp
| filter event = "ai_call_failed"
| stats count() by bin(5m) as error_count
```

### 10.2 Metrics (Custom CloudWatch)

**Publish from Application:**
```python
import boto3

cloudwatch = boto3.client('cloudwatch', region_name='af-south-1')

async def publish_metric(name: str, value: float, unit: str = 'None'):
    """Publish custom metric to CloudWatch."""
    cloudwatch.put_metric_data(
        Namespace='GapSense',
        MetricData=[
            {
                'MetricName': name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.now()
            }
        ]
    )

# Usage:
await publish_metric('diagnostic.session.duration', duration, 'Seconds')
await publish_metric('diagnostic.confidence.mean', confidence, 'None')
await publish_metric('ai.prompt.latency', latency, 'Milliseconds')
```

### 10.3 Health Checks

**Endpoint:** `/v1/health/ready`

```python
@router.get("/health/ready")
async def health_check():
    """Comprehensive health check for ALB target group."""

    checks = {
        'database': await check_database(),
        'anthropic': await check_anthropic(),
        'sqs': await check_sqs(),
        's3': await check_s3()
    }

    all_healthy = all(checks.values())

    return {
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks,
        'version': settings.VERSION
    }

async def check_database():
    """Verify database connection."""
    try:
        await db.execute("SELECT 1")
        return True
    except:
        return False
```

### 10.4 Alerting (Not Implemented - See Cost Optimization)

**Recommended Alerts:**
1. **Budget Alert:** Monthly forecast > $100 (staging), $180 (production)
2. **AI Error Rate:** > 5% in 5-minute window
3. **SQS DLQ Depth:** > 0 (any message in DLQ = problem)
4. **RDS Connections:** > 80% of max
5. **Fargate CPU:** > 80% for 10 minutes
6. **WhatsApp Webhook Failures:** > 10 in 5 minutes

---

## APPENDICES

### A. Technology Decision Matrix

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| **Cloud** | AWS, GCP, Azure, DigitalOcean | AWS | Africa region, latency, UNICEF alignment |
| **Backend** | Django, FastAPI, Flask, Node | FastAPI | Async-native, OpenAPI, type hints |
| **Database** | PostgreSQL, MongoDB, DynamoDB | PostgreSQL | Relational data, JSONB flexibility |
| **AI** | OpenAI, Anthropic, Cohere | Anthropic | Multilingual, structured output, vision |
| **Queue** | SQS, Redis, RabbitMQ, Celery | SQS | AWS-native, durability, FIFO |
| **Auth** | Cognito, Auth0, Custom JWT | Cognito | AWS-native, phone auth, low cost |
| **Container** | ECS Fargate, EKS, EC2 | Fargate | Serverless, no cluster management |

### B. File & Folder Conventions

```
✅ CORRECT:
src/gapsense/diagnostic/engine.py
src/gapsense/core/models/student.py
tests/unit/test_diagnostic_engine.py

❌ WRONG:
src/gapsense/Diagnostic/Engine.py  # PascalCase folders
src/gapsense/core/models/Student.py  # PascalCase files
tests/Unit/test_diagnostic_engine.py  # PascalCase test folders
```

### C. Environment Variables

**Required (.env):**
```bash
# Application
ENVIRONMENT=staging
LOG_LEVEL=INFO
SECRET_KEY=xxx

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/gapsense

# AWS
AWS_REGION=af-south-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
SQS_QUEUE_URL=https://sqs.af-south-1.amazonaws.com/xxx/gapsense-messages.fifo
S3_MEDIA_BUCKET=gapsense-media-staging

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxx

# WhatsApp
WHATSAPP_API_TOKEN=xxx
WHATSAPP_PHONE_NUMBER_ID=xxx
WHATSAPP_VERIFY_TOKEN=xxx

# Cognito
COGNITO_USER_POOL_ID=af-south-1_xxx
COGNITO_CLIENT_ID=xxx

# Data repo
GAPSENSE_DATA_PATH=../gapsense-data
```

---

**Built for Ghana. Powered by AI. Grounded in dignity.**
