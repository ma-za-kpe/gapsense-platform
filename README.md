# GapSense Platform

**AI-Powered Foundational Learning Diagnostic Platform for Ghana**

[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## 🎯 MVP Focus (Phase 1a — February 2026)

**The Core Problem We're Solving:**
JHS teachers inherit students with invisible primary-level gaps. A student struggling with fractions might actually have a P4 place-value gap. Teachers need to diagnose these gaps without adding another test.

**Our Solution:**
A WhatsApp-based AI that **analyzes photos of students' exercise books**, identifies error patterns, traces them to foundational gaps, and engages parents with targeted activities.

---

## 🚨 Current Status (February 16, 2026)

**MVP Specification:** Teacher-initiated exercise book scanner + parent evening voice notes
**Current Implementation:** 15% complete

### ✅ What's Working:
- WhatsApp webhook infrastructure
- Parent onboarding flow (FLOW-ONBOARD: 7 steps)
- Student record creation
- Database schema (PostgreSQL)
- AI prompt library (13 prompts in gapsense-data repo)
- Opt-out flow (11+ keywords in 5 languages)

### ❌ What's Missing (Core MVP Features):
- **Exercise Book Scanner** (multimodal AI analysis) — THE CORE FEATURE
- Teacher onboarding + class roster upload
- Multimodal AI integration (Claude/Gemini vision)
- Scheduled parent voice notes (6:30 PM daily in Twi)
- Text-to-speech (Twi)
- Speech-to-text (parent voice responses)
- Teacher conversation partner
- Weekly Gap Map

**See:** [docs/mvp_specification_audit_CRITICAL.md](docs/mvp_specification_audit_CRITICAL.md) for full gap analysis

---

## 📖 The Actual MVP (from MVP Blueprint)

### For Teachers:
```
1. Teacher sends "START" → Registers class → Creates 42 student profiles
2. Teacher sends photo of Kwame's exercise book
3. AI analyzes handwriting → Identifies error patterns
4. Returns: "Kwame errors on borrowing across place values (P4 gap).
   Suggested micro-intervention: 3-min warm-up with GH₵ subtraction."
5. Teacher asks: "I'm teaching fractions tomorrow. What should I worry about?"
6. AI reasons across all diagnosed students → Suggests lesson adjustments
```

### For Parents:
```
1. Teacher shares GapSense number at PTA meeting
2. Parent sends "START" → Links to existing student → Chooses language (Twi)
3. Daily 6:30 PM: Parent receives Twi voice note with 3-minute activity
   "Tonight: Ask Kwame to figure out 3 sachets of pure water at 50p each"
4. Parent sends 👍 when done
5. Parent sends voice note: "He got it but took too long, is that okay?"
6. AI provides pedagogical coaching: "Perfect! Speed comes later..."
```

### Success Criteria (12-Week Pilot):
1. **AI Diagnostic Works:** 75%+ concordance with expert teacher assessment
2. **Humans Use It:** 7/10 teachers scan 2+/week, 60%+ parents respond to 3/5 prompts
3. **Students Improve:** 0.15+ SD improvement on re-scan after 12 weeks

**Scale:** 10 teachers, 100 parents, 400-500 students
**Budget:** Under $700 for 12 weeks
**Region:** Greater Accra
**Subject:** JHS 1 Mathematics ONLY
**Languages:** English + Twi ONLY

---

## 🏗️ Architecture

**Current (Infrastructure Only):**
```
WhatsApp → Webhook → FlowExecutor → Database → WhatsApp
```

**Target MVP Architecture:**
```
WhatsApp → Image Upload → Claude Vision → Exercise Book Analysis
                                        ↓
                                   Gap Profile → Database
                                        ↓
                         6:30 PM → Activity Generator → Twi TTS → Parent Voice Note
                                        ↓
                         Parent Voice → Whisper STT → Micro-Coaching → Twi TTS
```

**Stack:**
- **Backend**: FastAPI (Python 3.12), async everywhere
- **Database**: PostgreSQL 16
- **AI (Planned)**:
  - Multimodal: Claude Sonnet 4.5 with vision OR Gemini Pro Vision
  - Text: Claude Sonnet/Haiku for conversation
  - TTS: Google Cloud TTS (Twi) or ElevenLabs
  - STT: Whisper API
- **Messaging**: WhatsApp Cloud API
- **Infrastructure**: AWS (Cape Town region)

---

## 📁 Project Structure

```
gapsense/
├── src/gapsense/
│   ├── core/                  # Models, config
│   ├── engagement/            # WhatsApp flows (ONBOARD, OPT-OUT)
│   ├── webhooks/              # WhatsApp webhook handlers
│   ├── diagnostic/            # Diagnostic engine (partial)
│   ├── ai/                    # AI client + prompt loader
│   └── api/                   # REST API endpoints
├── tests/                     # 268 tests (58% coverage)
├── alembic/                   # Database migrations (6 versions)
├── docs/                      # Documentation
│   ├── mvp_specification_audit_CRITICAL.md    # Gap analysis
│   └── mvp_user_flows_realistic_status.md     # Realistic flows
└── scripts/                   # Utility scripts
```

**Proprietary Data (Separate Repo):**
```
gapsense-data/
├── prompts/                   # 13 AI prompts (COMPLETE)
│   └── gapsense_prompt_library_v1.1.json
├── curriculum/                # NaCCA prerequisite graph
│   └── gapsense_prerequisite_graph_v1.2.json
└── business/                  # Strategy docs
    ├── GapSense_MVP_Blueprint.docx           # ← SOURCE OF TRUTH
    └── GapSense_v2_AI_Native_Redesign.docx
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 16
- Poetry
- Access to `gapsense-data` private repo

### Setup

```bash
# 1. Clone repos
git clone <gapsense-repo>
cd gapsense

# Clone data repo (sibling directory)
cd ..
git clone <gapsense-data-repo>  # Private
cd gapsense

# 2. Install dependencies
poetry install

# 3. Set up database
createdb gapsense_dev
poetry run alembic upgrade head

# 4. Set environment variables
cp .env.example .env
# Edit .env with your credentials:
# - DATABASE_URL
# - ANTHROPIC_API_KEY (for AI)
# - WHATSAPP_VERIFY_TOKEN
# - WHATSAPP_PHONE_NUMBER_ID
# - WHATSAPP_ACCESS_TOKEN

# 5. Load curriculum data
export GAPSENSE_DATA_PATH=../gapsense-data
poetry run python scripts/load_curriculum.py

# 6. Run tests
poetry run pytest

# 7. Start server
poetry run uvicorn gapsense.main:app --reload
```

---

## 📊 Development Status

### Phase 1a MVP (Target: 8-10 weeks from now)

| Component | Status | Notes |
|-----------|--------|-------|
| **Infrastructure** | ✅ 75% | WhatsApp, DB, API working |
| **Parent Onboarding** | ✅ 100% | FLOW-ONBOARD complete |
| **Teacher Onboarding** | ❌ 0% | Not started |
| **Exercise Book Scanner** | ❌ 0% | Core MVP feature missing |
| **Multimodal AI** | ❌ 0% | Not integrated |
| **Parent Voice Notes** | ❌ 0% | TTS not implemented |
| **Voice Micro-Coaching** | ❌ 0% | STT not implemented |
| **Teacher Conversation** | ❌ 0% | Not started |
| **Scheduled Messaging** | ❌ 0% | Not implemented |

**Overall: 15% complete toward MVP**

**Next 8 weeks (to MVP):**
- Week 1-2: NaCCA knowledge base + Exercise Book Analyzer prompt + test Twi TTS
- Week 3-4: Multimodal AI integration + image upload
- Week 5-6: Parent voice note system (TTS + activity generator)
- Week 7-8: Teacher conversation partner + integration
- Week 9-20: 12-week pilot measurement

---

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# With coverage
poetry run pytest --cov=src/gapsense --cov-report=html

# Run specific test
poetry run pytest tests/unit/test_flow_executor.py -v

# Integration tests only
poetry run pytest tests/integration/ -v
```

**Current Coverage:**
- Overall: 58%
- flow_executor.py: 72%
- whatsapp.py: 67%

---

## 📚 Key Documents

### Specifications (Source of Truth):
- **[GapSense_MVP_Blueprint.docx](../gapsense-data/business/GapSense_MVP_Blueprint.docx)** — The actual MVP (8 weeks, $700)
- **[gapsense_prompt_library_v1.1.json](../gapsense-data/prompts/)** — All 13 AI prompts
- **[gapsense_prerequisite_graph_v1.2.json](../gapsense-data/curriculum/)** — NaCCA curriculum

### Current Status:
- **[mvp_specification_audit_CRITICAL.md](docs/mvp_specification_audit_CRITICAL.md)** — Gap analysis
- **[mvp_user_flows_realistic_status.md](docs/mvp_user_flows_realistic_status.md)** — Real-world flows

### Architecture:
- **[ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)** — System design
- **[gapsense_adr.md](docs/architecture/gapsense_adr.md)** — Architecture decisions

---

## 🎯 MVP Success Metrics

From MVP Blueprint, Section 6:

**Question 1: Does the AI diagnostic work?**
- Metric: 75%+ concordance between AI and expert teacher on root cause identification
- Test: 100 exercise book scans validated by expert teachers

**Question 2: Do humans use it?**
- Teachers: 7/10 complete 2+ scans/week for 8+ of 12 weeks
- Parents: 60%+ respond to 3+ of 5 weekly prompts after month 1
- Wolf/Aurino: Parents with no formal education engage at 40%+ of overall rate

**Question 3: Do students improve?**
- Metric: 0.15+ standard deviation improvement on re-scan after 12 weeks
- Stronger signal: Students with active parent engagement improve more

---

## 📝 License

Proprietary. © 2026 GapSense. All rights reserved.

---

## 🤝 Contributing

This is a private project. Contact the team for access.

---

**Last Updated:** February 16, 2026
**MVP Target:** April 2026 (8-10 weeks from now)
