# GapSense Project Structure Blueprint
## Version 1.0.0 | 2026-02-13 | Maku Mazakpe | Proprietary IP

```
gapsense/
├── README.md
├── pyproject.toml                    # Poetry/pip project config
├── alembic.ini                       # Database migration config
├── Dockerfile                        # Production container
├── docker-compose.yml                # Local dev (app + postgres + localstack)
├── Makefile                          # Common commands (make dev, make test, make migrate)
├── .env.example                      # Environment variable template
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Lint + test on PR
│       ├── deploy-staging.yml        # Deploy to staging on merge to main
│       └── deploy-prod.yml           # Deploy to prod on release tag
│
├── infrastructure/                   # IaC (ADR-001: AWS)
│   ├── cdk/                          # AWS CDK (Python)
│   │   ├── app.py
│   │   ├── stacks/
│   │   │   ├── network_stack.py      # VPC, subnets, security groups
│   │   │   ├── database_stack.py     # RDS PostgreSQL
│   │   │   ├── compute_stack.py      # Fargate service + ALB
│   │   │   ├── queue_stack.py        # SQS queues + DLQ
│   │   │   ├── storage_stack.py      # S3 buckets
│   │   │   └── monitoring_stack.py   # CloudWatch dashboards + alarms
│   │   └── config.py                 # Environment-specific config
│   └── scripts/
│       ├── seed_curriculum.py        # Load prerequisite graph into DB
│       └── seed_regions.py           # Load Ghana regions/districts
│
├── migrations/                       # Alembic migrations
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
│
├── data/                             # Static data files (PROPRIETARY IP)
│   ├── prerequisite_graph.json       # NaCCA prerequisite graph v1.1
│   ├── prompt_library.json           # AI prompt templates
│   ├── cascade_paths.json            # Critical failure cascades
│   ├── l1_vocabulary/                # Language reference files
│   │   ├── twi.json
│   │   ├── ewe.json
│   │   ├── ga.json
│   │   └── dagbani.json
│   └── seed/
│       ├── regions.json              # Ghana's 16 regions
│       ├── districts.json            # Districts per region
│       └── strands.json              # 4 NaCCA math strands
│
├── src/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app factory + CORS + middleware
│   ├── config.py                     # Pydantic Settings (env vars, secrets)
│   ├── dependencies.py               # FastAPI dependency injection (db session, auth, etc.)
│   │
│   ├── core/                         # Shared foundation
│   │   ├── __init__.py
│   │   ├── database.py               # SQLAlchemy async engine + session factory
│   │   ├── models/                   # SQLAlchemy ORM models (from data_model.sql)
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Declarative base, common mixins (timestamps, UUID PK)
│   │   │   ├── curriculum.py         # CurriculumNode, Prerequisite, Misconception, CascadePath
│   │   │   ├── school.py             # Region, District, School
│   │   │   ├── user.py               # Teacher, Parent
│   │   │   ├── student.py            # Student, GapProfile
│   │   │   ├── diagnostic.py         # DiagnosticSession, DiagnosticQuestion
│   │   │   ├── engagement.py         # ParentInteraction, ParentActivity
│   │   │   ├── prompt.py             # PromptCategory, PromptVersion, PromptTestCase
│   │   │   └── analytics.py          # SchoolAnalytics, DistrictAnalytics
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── student.py
│   │   │   ├── diagnostic.py
│   │   │   ├── engagement.py
│   │   │   ├── curriculum.py
│   │   │   ├── teacher.py
│   │   │   └── analytics.py
│   │   ├── exceptions.py             # Custom exception classes
│   │   └── security.py               # JWT creation/validation, OTP generation
│   │
│   ├── curriculum/                   # NaCCA prerequisite graph module
│   │   ├── __init__.py
│   │   ├── router.py                 # GET /curriculum/nodes, /curriculum/cascade-paths
│   │   ├── service.py                # Graph traversal, prerequisite lookup, severity calculation
│   │   └── loader.py                 # Load prerequisite_graph.json into DB on startup/migration
│   │
│   ├── diagnostic/                   # Diagnostic engine (CORE MODULE)
│   │   ├── __init__.py
│   │   ├── router.py                 # POST /diagnostics/sessions, /sessions/{id}/respond
│   │   ├── service.py                # Session management, state machine
│   │   ├── engine.py                 # AI orchestration: calls DIAG-001/002/003 prompts
│   │   ├── analyzer.py               # Response analysis logic, error pattern matching
│   │   ├── profiler.py               # Gap profile generation, cascade path matching
│   │   └── image_analyzer.py         # Exercise book photo analysis (ANALYSIS-001)
│   │
│   ├── engagement/                   # Parent engagement module
│   │   ├── __init__.py
│   │   ├── router.py                 # GET /parents/{id}/activities, PATCH /parents/{id}/preferences
│   │   ├── service.py                # Activity selection, check-in scheduling
│   │   ├── message_generator.py      # AI message generation (PARENT-001/002/003)
│   │   ├── voice_processor.py        # Voice note handling (ANALYSIS-002)
│   │   └── scheduler.py              # Scheduled check-ins, reminders (runs as periodic task)
│   │
│   ├── teachers/                     # Teacher dashboard module
│   │   ├── __init__.py
│   │   ├── router.py                 # GET /teachers/{id}/class-report, /student-brief/{id}
│   │   └── service.py                # Report generation (TEACHER-001/002)
│   │
│   ├── webhooks/                     # WhatsApp Cloud API integration
│   │   ├── __init__.py
│   │   ├── router.py                 # GET+POST /webhooks/whatsapp (verification + message receipt)
│   │   ├── handler.py                # Message routing: text/image/voice/button → appropriate handler
│   │   ├── sender.py                 # Outbound message sending (text, template, interactive)
│   │   ├── templates.py              # WhatsApp message template definitions
│   │   └── media.py                  # Media download/upload (photos, voice notes → S3)
│   │
│   ├── analytics/                    # Reporting and aggregation
│   │   ├── __init__.py
│   │   ├── router.py                 # GET /analytics/school/{id}, /analytics/district/{id}
│   │   ├── service.py                # Aggregation logic
│   │   └── jobs.py                   # Periodic aggregation jobs (nightly school/district rollup)
│   │
│   ├── admin/                        # System administration
│   │   ├── __init__.py
│   │   ├── router.py                 # GET /admin/prompts, POST /admin/prompts/{id}/test
│   │   └── service.py                # Prompt management, test runner
│   │
│   └── ai/                           # AI integration layer
│       ├── __init__.py
│       ├── client.py                 # Anthropic API client (with retry, timeout, caching)
│       ├── prompt_loader.py          # Load prompts from prompt_library.json, render templates
│       ├── response_parser.py        # Parse AI JSON responses, validate against schemas
│       └── quality.py                # Anti-fabrication checks, confidence calibration
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Fixtures: test DB, test client, mock AI responses
│   ├── factories.py                  # Factory Boy factories for test data
│   ├── unit/
│   │   ├── test_curriculum_service.py    # Graph traversal, prerequisite lookup
│   │   ├── test_diagnostic_engine.py     # Session state machine
│   │   ├── test_response_parser.py       # AI response parsing
│   │   ├── test_message_generator.py     # Parent message formatting
│   │   └── test_webhook_handler.py       # WhatsApp payload routing
│   ├── integration/
│   │   ├── test_diagnostic_flow.py       # Full session: start → respond → conclude
│   │   ├── test_whatsapp_webhook.py      # Simulated WhatsApp payloads
│   │   └── test_parent_engagement.py     # Onboarding → activity → check-in flow
│   └── prompt_validation/
│       ├── test_diag_prompts.py          # DIAG-001/002/003 against test cases (live Claude)
│       ├── test_parent_prompts.py        # PARENT-001/002/003 against test cases
│       └── test_analysis_prompts.py      # ANALYSIS-001/002 against test cases
│
└── scripts/
    ├── run_dev.sh                    # Start local dev environment
    ├── run_tests.sh                  # Run test suite
    ├── run_prompt_validation.sh      # Run Tier 3 prompt tests (requires API key)
    └── generate_openapi.py           # Export OpenAPI spec from running app
```

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Python files | snake_case | `diagnostic_engine.py` |
| Classes | PascalCase | `DiagnosticSession` |
| Functions | snake_case | `analyze_response()` |
| Constants | UPPER_SNAKE | `MAX_TRACE_DEPTH = 4` |
| API routes | kebab-case | `/gap-profile`, `/class-report` |
| Database tables | snake_case | `diagnostic_sessions` |
| Environment vars | UPPER_SNAKE | `ANTHROPIC_API_KEY` |
| NaCCA codes | Dotted | `B2.1.1.1` |
| Misconception IDs | Hyphenated | `MC-B2.1.1.1-01` |
| Prompt IDs | UPPER-NNN | `DIAG-001`, `PARENT-002` |

## Module Dependency Rules

```
webhooks → diagnostic, engagement (receives messages, routes to handlers)
diagnostic → curriculum, ai (reads graph, calls Claude)
engagement → diagnostic, ai (reads profiles, generates messages)
teachers → diagnostic, curriculum (reads profiles, generates reports)
analytics → diagnostic, engagement (aggregates data)
admin → ai (prompt management)
ai → (external: Anthropic API only)
curriculum → (standalone: reads from data/)
core → (standalone: models, schemas, config)
```

**Rule:** No circular dependencies. `ai/` never imports from `diagnostic/` or `engagement/`. Module communication via service interfaces, not direct imports.
