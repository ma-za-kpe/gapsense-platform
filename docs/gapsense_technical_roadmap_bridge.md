# GapSense Technical Roadmap Bridge
**From Current State → MVP → Full Vision**

**Date:** February 16, 2026 (UPDATED after MVP Blueprint analysis)
**Context:** UNICEF StartUp Lab Cohort 6 — Final Pitch February 20, 2026
**Purpose:** Show the credible path from where we are to the full v2 vision

---

## 🚨 CRITICAL UPDATE: MVP Specification Realignment

**Previous Understanding:** We thought we were 82% complete on Phase 1a
**Reality After MVP Blueprint Analysis:** We are 15% complete on the actual MVP

**The Issue:** We built parent-initiated text-based onboarding. The MVP Blueprint specifies teacher-initiated exercise book scanner with parent voice notes.

**See:** [mvp_specification_audit_CRITICAL.md](mvp_specification_audit_CRITICAL.md) for full gap analysis.

---

## Where We Actually Are (February 16, 2026)

### ✅ What's Working (15% of MVP):

**Infrastructure (75%):**
- WhatsApp Cloud API integration
- Webhook handler (342 lines, 67% coverage)
- FlowExecutor pattern for conversation management
- PostgreSQL database schema (6 migrations)
- FastAPI backend (async everywhere)
- 268 tests passing (58% overall coverage)

**FLOW-ONBOARD (100%):**
- 7-step parent onboarding
- Student record creation
- Language selection (English + 4 others)
- Diagnostic consent tracking
- Type-safe conversation state

**FLOW-OPT-OUT (100%):**
- 11+ keywords in 5 languages
- Instant opt-out
- Re-engagement support

**AI Prompt Library (100%):**
- All 13 prompts exist in `gapsense-data/prompts/`
- DIAG-001/002/003 (diagnostic engine)
- PARENT-001/002/003 (parent engagement)
- TEACHER-001/002/003 (teacher reports + conversation)
- ACT-001 (activity generator)
- ANALYSIS-001/002 (exercise book + voice)
- GUARD-001 (Wolf/Aurino compliance)

**Database Models (90%):**
- Parent, Student, Teacher, School
- DiagnosticSession, GapProfile
- Conversation state management
- Ghana Data Protection Act compliance

### ❌ What's Missing (85% of MVP):

**CORE MVP FEATURES:**
1. **Exercise Book Scanner** (0%) — THE CORE FEATURE
   - No image upload via WhatsApp
   - No multimodal AI integration (Claude/Gemini vision)
   - No handwriting analysis
   - No error pattern detection

2. **Teacher Onboarding** (0%)
   - No class roster upload
   - No bulk student creation
   - No school registration flow

3. **Parent Voice Notes** (0%)
   - No scheduled messaging (6:30 PM daily)
   - No Twi text-to-speech
   - No activity generation from gap profiles

4. **Voice Micro-Coaching** (0%)
   - No parent voice note processing
   - No speech-to-text
   - No pedagogical coaching responses

5. **Teacher Conversation Partner** (0%)
   - No conversational AI for lesson planning
   - No class-wide gap reasoning

6. **Weekly Gap Map** (0%)
   - No teacher summary generation

---

## The Actual MVP (From MVP Blueprint)

### Specification:
- **Scale:** 10 teachers, 100 parents, 400-500 students
- **Duration:** 12-week pilot
- **Budget:** Under $700
- **Region:** Greater Accra ONLY
- **Subject:** JHS 1 Mathematics ONLY
- **Languages:** English + Twi ONLY (not 5 languages)

### The 4 Channels:

**SCHOOL CHANNEL 1: Exercise Book Scanner**
```
Teacher sends photo of student's exercise book
↓
Multimodal AI (Claude/Gemini vision) analyzes handwriting
↓
Identifies error patterns across problems
↓
Traces to foundational gaps (P1-P6 prerequisites)
↓
Returns diagnosis + micro-intervention
↓
Updates student gap profile in database
```

**SCHOOL CHANNEL 2: Teacher Conversation**
```
Teacher asks: "I'm teaching fractions tomorrow. What should I worry about?"
↓
AI reasons across all diagnosed students in class
↓
Suggests lesson adjustments, warm-up activities
↓
Maintains conversation context across sessions
```

**PARENT CHANNEL 1: Evening Ritual**
```
6:30 PM daily (scheduled)
↓
AI generates activity targeting child's specific gap
↓
Text-to-speech converts to Twi voice note
↓
WhatsApp delivery to parent
↓
Parent sends 👍 when complete
↓
Database tracks engagement
```

**PARENT CHANNEL 2: Voice Micro-Coaching**
```
Parent sends voice note: "He got it but took too long"
↓
Whisper API transcribes (speech-to-text)
↓
AI provides pedagogical coaching
↓
Response converted to Twi voice note
↓
WhatsApp delivery
```

### Success Criteria (12-Week Pilot):
1. **AI Works:** 75%+ concordance with expert teacher on root cause
2. **Humans Use It:** 7/10 teachers scan 2+/week, 60%+ parents respond
3. **Students Improve:** 0.15+ SD improvement on re-scan

---

## The Path Forward (8-10 Weeks to MVP)

### Week 1-2: Foundation + Technical Spike
**Goal:** Validate core assumptions before building infrastructure

**Tasks:**
- [ ] Build NaCCA JHS 1 Math prerequisite knowledge base (20-30 misconceptions)
- [ ] Engineer Exercise Book Analyzer prompt (ANALYSIS-001)
- [ ] Test with 20+ real JHS exercise book photos
- [ ] Validate AI accuracy (target: 75%+ concordance)
- [ ] Test Twi TTS quality (Google Cloud TTS vs ElevenLabs)
- [ ] Get feedback from 3 Twi-speaking parents

**Deliverables:**
- Exercise Book Analyzer prompt (validated)
- Twi TTS decision (which provider)
- NaCCA knowledge base (embedded in prompts)

### Week 3-4: Multimodal AI + Image Processing
**Goal:** Build exercise book scanner

**Tasks:**
- [ ] Integrate Claude Sonnet 4.5 with vision OR Gemini Pro Vision
- [ ] Handle image messages from WhatsApp
- [ ] Process exercise book photos (preprocessing, orientation)
- [ ] Implement ANALYSIS-001 prompt call
- [ ] Format diagnosis for WhatsApp response
- [ ] Update student gap profile in database
- [ ] Test with pilot teachers

**Deliverables:**
- Working exercise book scanner
- Teacher can send photo → receive diagnosis

### Week 5-6: Parent Voice Notes + Scheduling
**Goal:** Build evening ritual system

**Tasks:**
- [ ] Implement scheduled messaging (6:30 PM daily)
- [ ] Build activity generator (ACT-001 → PARENT-001)
- [ ] Integrate TTS (Google Cloud TTS or ElevenLabs)
- [ ] Link activity to student gap profile
- [ ] Test Twi voice notes with parents
- [ ] Implement engagement tracking

**Deliverables:**
- Daily 6:30 PM Twi voice notes working
- Parents receive targeted activities

### Week 7-8: Teacher Conversation + Integration
**Goal:** Complete MVP

**Tasks:**
- [ ] Build teacher onboarding flow (class roster upload)
- [ ] Implement teacher conversation partner (TEACHER-003)
- [ ] Build weekly Gap Map generator
- [ ] Integrate STT for parent voice responses (optional)
- [ ] End-to-end testing with 2-3 pilot teachers
- [ ] Prepare for 12-week measurement period

**Deliverables:**
- Full MVP operational
- Ready for 10-teacher pilot

### Week 9-20: 12-Week Pilot Measurement
**Goal:** Answer the 3 MVP questions

**Milestones:**
- Week 9: First re-scan (are gaps closing?)
- Week 12: Mid-pilot assessment
- Week 16: Second re-scan (longitudinal trend)
- Week 20: Final assessment + decision (proceed to Phase 2 or pivot)

---

## Cost Estimate (Actual MVP — 12 Weeks)

Based on MVP Blueprint specifications:

| Item | Calculation | Cost (USD) |
|------|-------------|------------|
| **WhatsApp API** | 250 conversations/week × 12 weeks | $150-360 |
| **Multimodal AI** | 100 scans/week × 12 weeks × $0.05 avg | $60-120 |
| **Text AI** | 500 turns/week × 12 weeks × $0.005 | $30-60 |
| **Twi TTS** | 200 voice notes/week × 12 weeks × $0.01 | $24-50 |
| **Whisper STT** | 50 replies/week × 12 weeks × 30sec × $0.006/min | $9-18 |
| **Hosting** | 12 weeks VPS or free-tier | $0-60 |
| **Domain + SSL** | One-time | $12 |
| **TOTAL** | | **$285-680** |

**Per student (400 students):** $0.71-1.70

This is **drastically cheaper** than any existing diagnostic tool (TaRL requires facilitators, Mindspark requires computer labs, Nyansapo requires tablets).

---

## Phase Map: MVP → Full Vision

### Phase 1a: MVP (Months 1-5) — **IN PROGRESS**
**Timeline:** 8 weeks build + 12 weeks pilot
**Budget:** Under $700
**Status:** 15% complete (infrastructure only)

**What's Built:**
- WhatsApp infrastructure ✅
- Parent onboarding ✅
- Database schema ✅
- AI prompts ✅

**What's Missing (Next 8 Weeks):**
- Exercise book scanner ❌
- Teacher onboarding ❌
- Twi voice notes ❌
- Teacher conversation ❌

### Phase 1b: Expand Coverage (Months 6-8)
**Timeline:** 3 months
**Budget:** $10K-15K (grant funding)
**Prerequisites:** MVP validation (Questions 1-3 answered)

**Build:**
- Expand to 50 teachers, 500 parents
- Add Ga and Ewe languages
- Add voice micro-coaching (STT + coaching)
- Build teacher web dashboard (minimal)
- Expand prerequisite graph (B5-B6, literacy)

### Phase 2: On-Device AI (Months 9-12)
**Timeline:** 4 months
**Budget:** $50K-100K (seed funding)
**Prerequisites:** Phase 1b pilot data

**Build:**
- Distill cloud model to on-device SLM (Gemma 3n / Phi-4-mini)
- Train on Phase 1 diagnostic data (Ghanaian exercise books)
- Deploy to 100 schools (offline-capable)
- Add peer diagnostic games
- Add predictive early warning
- Community champions program

### Phase 3: Full Vision (Months 13-18)
**Timeline:** 6 months
**Budget:** $500K-1M (Series A)
**Prerequisites:** Phase 2 at scale

**Build:**
- 5 school channels + 14 parent channels
- Cross-school intelligence
- Teacher-to-teacher network
- TVET + SHS expansion
- All 5 Ghanaian languages
- Offline-first across all features

---

## Key Architectural Decisions

### Why Cloud-First for MVP is Correct:
You cannot fine-tune an on-device model without labeled training data. The MVP's cloud architecture **generates** this data:
- Every exercise book scan = labeled example
- Every diagnostic session = question-answer pairs
- Every gap identified = prerequisite trace

Phase 2 uses this data to distill a 2-3B parameter on-device model that runs offline.

### Why Teacher-Initiated (Not Parent-Initiated):
Per MVP Blueprint:
1. Teachers pre-register classes (40 students at once)
2. Exercise book scanner builds gap profiles
3. Parents receive **targeted** prompts (not generic)
4. Teacher controls who's in the system (school authority)

Parent-initiated (what we built) doesn't allow targeted prompts because there's no diagnostic yet.

### Why Exercise Book Scanner is THE Core Feature:
From MVP Blueprint Section 0:
> "Can AI accurately diagnose foundational gaps from exercise book photos? If this doesn't work, nothing else matters."

It's the riskiest, most novel component. If AI can't analyze messy Ghanaian handwriting to find root causes, the whole thesis fails. Must test this FIRST.

---

## Success Metrics (Realistic)

### Week 8 (MVP Complete):
✅ 10 teachers onboarded
✅ Exercise book scanner working
✅ Twi voice notes sending daily
✅ 50+ parents enrolled

### Week 12 (Mid-Pilot):
Target: 7/10 teachers actively scanning
Target: 60%+ parent response rate
Measure: First re-scan (gaps closing?)

### Week 20 (End of Pilot):
Answer Question 1: AI diagnostic concordance ≥75%?
Answer Question 2: Teacher + parent engagement sustained?
Answer Question 3: Student improvement ≥0.15 SD?

**Go/No-Go Decision:** If YES on all 3 → Proceed to Phase 1b. If NO on any → Investigate and iterate.

---

## What We Learned

### Mistake #1: Built Without Checking Business Docs
We reviewed technical specs (gapsense_whatsapp_flows.json) but never read MVP_Blueprint.docx in gapsense-data/business/. That's where the actual MVP is defined.

### Mistake #2: Assumed Parent-Initiated
We built a sophisticated parent onboarding flow because it seemed logical. The MVP is teacher-initiated for good reasons (bulk setup, targeted prompts, school control).

### Mistake #3: Over-Engineered Scope
We supported B1-B9 and 5 languages. MVP is JHS 1 Math + English/Twi ONLY. Simpler = faster validation.

### What We Got Right:
Infrastructure choices (WhatsApp-native, FastAPI, PostgreSQL, async) are correct. Just need to build the right features on top.

---

## Conclusion

**Current State:** 15% complete
**MVP Target:** 8-10 weeks from now
**Path:** Clear and achievable
**Budget:** Under $700 for 12-week pilot
**Risk:** Multimodal AI accuracy on Ghanaian handwriting (must validate Week 2)

**Next Step:** Stakeholder decision on pivot, then begin Week 1-2 technical spike.

---

**Last Updated:** February 16, 2026 (Post-MVP Blueprint Analysis)
**Authors:** Maku Mazakpe, Claude Code
