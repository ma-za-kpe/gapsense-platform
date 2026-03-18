# MVP SPECIFICATION AUDIT — CRITICAL FINDINGS
**Date:** February 16, 2026
**Status:** 🚨 FUNDAMENTAL MISUNDERSTANDING IDENTIFIED
**Action Required:** Stop current implementation. Re-align to actual MVP specification.

---

## Executive Summary

After analyzing the three source specification documents in `gapsense-data/business/`, we have identified **fundamental mismatches** between what the MVP Blueprint specifies and what we have been building.

**The Core Issue:** We thought the MVP was about building questionnaire-based WhatsApp flows (FLOW-DIAGNOSTIC, FLOW-ACTIVITY-DELIVERY). The actual MVP is about **multimodal AI analyzing exercise book photos** and **conversational teacher/parent interfaces**.

**Impact:** Approximately 60% of our implementation effort has been focused on the wrong architecture.

**Severity:** HIGH — This changes the fundamental product direction.

---

## The Three Source Documents

### 1. **GapSense_MVP_Blueprint.docx** (THE SOURCE OF TRUTH)
- 8-week build timeline, under $2,000 budget
- WhatsApp-native, zero apps, cloud AI is correct
- **10 teachers, 100 parents, 400-500 students, 12-week pilot**
- JHS 1 Mathematics ONLY, English + Twi, Greater Accra only

### 2. **GapSense_Conceptual_Design.docx** (FULL VISION)
- Teacher-first diagnostic platform
- Adaptive testing (12-18 questions)
- Three diagnostic modes (Phone-to-Group, Shared Device, Voice Assessment)
- Offline-first, NaCCA-aligned

### 3. **GapSense_v2_AI_Native_Redesign.docx** (PHASE 2/3)
- On-device AI (NOT MVP)
- 5 school channels + 14 parent channels (NOT MVP)
- Predictive early warning (Phase 3)
- Teacher-to-Teacher network (Phase 3)

---

## WHAT THE MVP BLUEPRINT ACTUALLY SPECIFIES

### Teacher Flow: Exercise Book Scanner + Conversation

**NOT a questionnaire. NOT a structured assessment form.**

```
Teacher: [Photographs a page from Kwame's exercise book. Sends the image.]

GapSense: Kwame's Work — Long Division (6 problems)

Strength: Kwame understands the division algorithm and applies it consistently.

Gap Found: He errors when borrowing across place values (problems 3, 5, 7).
This is a place-value decomposition gap, not a division gap.
Approximately P4 level.

Suggested Micro-Intervention: 3-minute warm-up tomorrow —
"If I have GH₵4.35 and spend GH₵1.78, what's left?"
This targets the exact regrouping skill he's missing.

Shall I scan another student, or would you like to discuss Kwame's gap further?
```

**Key Technical Requirements:**
- **Multimodal AI** (Claude Sonnet with vision or Gemini Pro Vision)
- Analyzes **handwritten work as images**
- Identifies **error PATTERNS** across multiple problems
- Traces patterns to **foundational causes** using NaCCA prerequisite knowledge
- Generates **specific micro-interventions**
- Cost: ~$0.01-0.10 per image analysis

**Teacher Conversation:**
```
Teacher: I'm introducing fractions tomorrow. Based on what you've seen
from my class, what should I worry about?

GapSense: Based on the exercise books you've scanned this week:
• 8 students have multiplication gaps that will make fraction operations difficult
• 5 students have place-value gaps affecting denominator understanding
• 3 students seem strong across the board

I'd suggest starting with a concrete fraction introduction using folding paper...
Want me to generate the warm-up activity?
```

**Key Technical Requirements:**
- Maintains **running profile** of every student scanned
- Reasons **across aggregate** when advising on lesson planning
- **Conversation state persists** across WhatsApp sessions
- AI is a **diagnostic partner**, not a report generator

### Parent Flow: Evening Ritual + Voice Coaching

**NOT scheduled questionnaires. NOT structured activities.**

```
6:30 PM Daily:
GapSense: [Voice note in Twi] Good evening! Tonight, ask Kwame to help you
figure out how much 3 sachets of pure water cost at 50 pesewas each.
Let him work it out his way. Don't worry about right or wrong — just let him try!
Send me a 👍 when you've done it.

Parent: 👍

GapSense: [Voice note in Twi] Thank you! You're helping Kwame build his
multiplication skills. He's already showing good number sense at school.
See you tomorrow!
```

**Key Technical Requirements:**
- **3-minute activities** embedded in daily Ghanaian life
- **Voice notes** in Twi (Google Cloud TTS or ElevenLabs)
- **Dignity-first framing**: Lead with strength, frame as "next step", never deficit
- Targets child's **specific diagnosed gap** from exercise book scans
- **Adaptive**: Increases complexity if parent responds consistently

**Voice Micro-Coaching:**
```
Parent: [Voice note in Twi] He counted and got 56 but it took him a long time.
Is that okay?

GapSense: [Voice note in Twi] That's actually perfect! The fact that he got
the right answer by counting means he understands the concept. Speed comes
later — understanding comes first, and Kwame has that. Keep doing this with
different numbers.
```

**Key Technical Requirements:**
- **Speech-to-text** processing (Whisper API: ~$0.006/minute)
- Detects parent concerns and provides **pedagogical coaching**
- Always **asset-first**, never shaming

### Weekly Gap Map (NOT a web dashboard)

**Sent as a WhatsApp message or image:**
- Shows all scanned students
- Their identified gaps
- Progress over time
- Suggested next steps

**NOT a web application. NOT a separate portal.**

---

## WHAT WE ACTUALLY BUILT

### ✅ CORRECT: FLOW-ONBOARD (100% Working)
- 7-step parent onboarding via WhatsApp ✅
- Language selection (English/Twi) ✅
- Child information collection ✅
- Diagnostic consent ✅
- Dignity-first framing ✅
- Student creation in database ✅
- 25/25 tests passing ✅

**Status:** PERFECT. Matches specification exactly.

### ✅ CORRECT: FLOW-OPT-OUT (100% Working)
- Opt-out keywords detection ✅
- Confirmation step ✅
- Reactivation support ✅
- Tests passing ✅

**Status:** PERFECT. Matches specification exactly.

### ❌ WRONG: Diagnostic Implementation

**What We Built:**
- API endpoints for structured questionnaires (`POST /api/v1/diagnostics/sessions`)
- Question-by-question flow with multiple choice answers
- 6-12 question adaptive test
- Text-based Q&A format

**What MVP Specifies:**
- **Exercise book photo upload** → multimodal AI analysis
- **Teacher sends image** → AI analyzes handwriting, identifies error patterns
- **Conversational diagnostic** → teacher can ask questions about class
- **No structured questionnaire** for MVP

**Impact:** We built the wrong diagnostic architecture. The MVP diagnostic is **image-based multimodal AI**, not a questionnaire flow.

### ❌ WRONG: Activity Delivery

**What We Built:**
- Plans for scheduled message delivery
- Activity session tracking
- Completion tracking

**What MVP Specifies:**
- **Daily 6:30 PM voice notes in Twi**
- **3-minute embedded-in-daily-life activities** (market scenarios, not worksheets)
- **Adaptive based on parent engagement**
- Activities generated **from exercise book scan diagnostics**
- Voice micro-coaching when parent reports difficulties

**Impact:** We built tracking infrastructure but missed the core: voice notes, Twi TTS, dignity-first framing engine, and connection to exercise book diagnostics.

### ❌ MISSING: Exercise Book Scanner (THE CORE MVP FEATURE)

**Status:** 0% implemented

**What's Required:**
1. WhatsApp image message handling
2. Image upload to cloud multimodal AI (Claude Sonnet vision / Gemini Pro Vision)
3. Diagnostic reasoning prompt that:
   - Analyzes handwritten work
   - Identifies error patterns across multiple problems
   - Traces to foundational causes via NaCCA prerequisites
   - Distinguishes careless errors from systematic misconceptions
   - Suggests specific micro-interventions
4. Response formatting for WhatsApp
5. Update student gap profile in database
6. Maintain teacher conversation context

**Cost Per Scan:** $0.01-0.10 (MVP budget: ~$60-120 for 1,200 scans over 12 weeks)

### ❌ MISSING: Teacher Conversation Partner

**Status:** 0% implemented

**What's Required:**
1. Conversation state management (beyond simple flow steps)
2. Context of all diagnosed students in teacher's class
3. AI prompt that:
   - Reasons across student profiles
   - Advises on lesson planning
   - Suggests practical interventions
   - Adapts to teacher constraints (time, materials, inspectors)
4. Persistent conversation across multiple WhatsApp sessions

### ❌ MISSING: Parent Voice Notes (Twi)

**Status:** 0% implemented

**What's Required:**
1. Text-to-speech integration (Google Cloud TTS or ElevenLabs)
2. Twi voice synthesis (must test quality with native speakers)
3. Activity generation prompt:
   - Targets child's specific gap from exercise book scan
   - Embedded in daily Ghanaian life (market, kitchen, transport)
   - 3-minute maximum
   - Zero special materials
   - Parent as facilitator, child as problem-solver
4. Dignity-first framing engine (4 rules hard-coded)
5. 6:30 PM scheduled delivery

### ❌ MISSING: Parent Voice Micro-Coaching

**Status:** 0% implemented

**What's Required:**
1. Speech-to-text for parent voice replies (Whisper API)
2. AI prompt that:
   - Processes parent concerns
   - Provides specific pedagogical coaching
   - Never shames
   - Adjusts future prompts based on response
3. 15-second voice response generation

### ❌ MISSING: Weekly Gap Map

**Status:** 0% implemented

**What's Required:**
1. Summary generation from all scanned students
2. Visual formatting (text table or generated image)
3. WhatsApp delivery to teacher
4. Shows: students, identified gaps, progress, next steps

---

## WHAT WE GOT WRONG ABOUT MVP

### Misunderstanding #1: Diagnostic Format
**We thought:** Structured questionnaire with multiple choice answers, 6-12 questions, adaptive based on responses

**Reality:** Teacher photographs student's exercise book page. Multimodal AI analyzes handwritten work, identifies error patterns, traces to foundational gaps.

**Why This Matters:** The entire diagnostic architecture is different. Image processing + multimodal reasoning vs. structured question flow.

### Misunderstanding #2: Parent Engagement Format
**We thought:** Text messages with structured activities, possibly interactive buttons

**Reality:** Daily voice notes in Twi with 3-minute activities embedded in market/kitchen/transport scenarios. Voice micro-coaching when parent replies. Dignity-first framing as hard architectural constraint.

**Why This Matters:** Requires TTS/STT integration, Twi language support, and a completely different content generation approach.

### Misunderstanding #3: Teacher Interface
**We thought:** API endpoints returning structured data, possibly a web dashboard

**Reality:** Conversational partner via WhatsApp. Teacher sends images, asks questions, gets advice. Weekly Gap Map sent as WhatsApp message. No separate dashboard.

**Why This Matters:** The teacher never leaves WhatsApp. Everything is conversational. State management and context tracking are critical.

### Misunderstanding #4: MVP Scope
**We thought:** Multiple flows (FLOW-DIAGNOSTIC, FLOW-ACTIVITY-DELIVERY, FLOW-CHECK-IN) as separate structured processes

**Reality:** Two continuous channels:
- **School:** Exercise book scanning + teacher conversation (ongoing, teacher-initiated)
- **Home:** Daily evening voice notes + micro-coaching (scheduled, AI-initiated)

**Why This Matters:** Not discrete "flows" but persistent conversational interfaces.

### Misunderstanding #5: Technology Stack
**We thought:** Focus on API infrastructure, database schemas, flow orchestration

**Reality:** Focus on multimodal AI integration (vision models), TTS/STT (Twi), conversation state management, dignity-first content generation.

**Why This Matters:** Different technical skills and infrastructure requirements.

---

## THE ACTUAL MVP SUCCESS CRITERIA

From MVP Blueprint, page 18:

### Question 1: Does the AI diagnostic work?
**Metric:** Concordance between AI exercise book diagnosis and expert teacher assessment

**Threshold:** 75%+ agreement on identified foundational gap (not just that student is wrong, but correct root cause)

**Our Status:** Cannot measure — we haven't built exercise book scanner yet

### Question 2: Do humans actually use it?
**Teacher Metric:** 7 of 10 teachers complete at least 2 scan sessions per week for 8+ of 12 weeks

**Parent Metric:** 60%+ of enrolled parents respond to at least 3 of 5 weekly prompts after first month

**Wolf/Aurino Metric:** Engagement among parents with no formal education is at least 40% of overall rate

**Our Status:**
- Teacher: Cannot measure — no exercise book scanner
- Parent: Cannot measure — no voice notes or evening prompts
- Wolf/Aurino: Cannot measure — no parent engagement system

### Question 3: Do students actually improve?
**Metric:** Students whose teachers used GapSense show 0.15+ standard deviation improvement on re-scan of previously diagnosed skills after 12 weeks

**Our Status:** Cannot measure — no diagnostic to re-scan with

---

## CORRECTED MVP UNDERSTANDING

### What the MVP Actually Is

**A WhatsApp-native multimodal AI diagnostic assistant that:**

1. **For Teachers:**
   - Receives exercise book photos via WhatsApp
   - Analyzes handwritten work using multimodal AI (Claude Sonnet vision)
   - Identifies error patterns and traces to foundational gaps
   - Suggests specific micro-interventions
   - Maintains conversational context across sessions
   - Sends weekly Gap Map summary via WhatsApp

2. **For Parents:**
   - Sends daily 6:30 PM voice note in Twi
   - Provides one 3-minute activity embedded in daily life (market, kitchen, etc.)
   - Activity targets child's specific gap from exercise book scan
   - Always uses dignity-first framing (lead with strength, frame as next step)
   - Provides voice micro-coaching when parent reports difficulties
   - Adapts complexity based on parent engagement

3. **For System:**
   - Tracks student gap profiles in database
   - Links teacher diagnostics to parent evening prompts
   - Monitors engagement patterns
   - Generates weekly summaries
   - Runs entirely on WhatsApp + cloud backend

### What the MVP Is NOT

❌ NOT a structured questionnaire system
❌ NOT a web dashboard
❌ NOT discrete "flows" with defined completion points
❌ NOT text-only (must support voice notes)
❌ NOT English-only (must support Twi voice)
❌ NOT on-device AI (cloud is correct for MVP)
❌ NOT covering multiple subjects (JHS 1 Math only)

---

## ARCHITECTURAL IMPLICATIONS

### Core Technology Changes Required

1. **Multimodal AI Integration (NEW)**
   - Anthropic Claude Sonnet 4.5 with vision
   - OR Google Gemini Pro Vision
   - Image preprocessing for WhatsApp photos
   - Prompt engineering for exercise book analysis
   - Cost: $0.01-0.10 per analysis

2. **Text-to-Speech for Twi (NEW)**
   - Google Cloud TTS (Twi voice available?)
   - OR ElevenLabs (Twi voice quality?)
   - Must test with native speakers Week 2
   - Fallback: Human-recorded templates + AI personalization
   - Cost: ~$0.01 per voice note

3. **Speech-to-Text for Parent Replies (NEW)**
   - Whisper API for Twi transcription
   - Process parent voice notes for content
   - Detect concerns for micro-coaching
   - Cost: $0.006/minute

4. **Conversation State Management (UPGRADE)**
   - Beyond flow_executor's simple state machine
   - Persistent context across multiple sessions
   - Teacher's entire class profile accessible
   - Student gap profiles updated from each scan

5. **Dignity-First Framing Engine (NEW)**
   - Hard-coded rules in AI system prompt
   - Every parent message must:
     - Lead with genuine, specific strength
     - Frame gap as "next step", never deficit
     - Provide exactly one actionable thing
     - Close with specific, earned encouragement
   - Validation: Manual review of first 100 messages

6. **WhatsApp Media Handling (UPGRADE)**
   - Image message reception
   - Voice note generation
   - Voice note reception
   - Media storage (S3 or equivalent)

### Database Schema Changes Required

**Current:** Student, Parent, Teacher, DiagnosticSession, Question, Response

**Needed:**
- `exercise_book_scans` table:
  - scan_id, student_id, teacher_id, image_url
  - ai_analysis (JSONB: strengths, gaps, error_patterns, micro_interventions)
  - scanned_at, analyzed_at

- `student_gap_profiles` table:
  - student_id, nacca_strand, foundational_skill, gap_level (P1-P6)
  - identified_at, last_updated, status (open/improving/closed)

- `parent_prompts` table:
  - prompt_id, parent_id, student_id, sent_at
  - activity_text, voice_note_url, targets_gap
  - parent_response, responded_at

- `teacher_conversations` table:
  - conversation_id, teacher_id, message_history (JSONB)
  - context (student profiles, class summary)
  - last_message_at

### AI Prompts Required (NEW)

1. **EXERCISE-BOOK-ANALYZER**
   - Input: Image + student name + grade level
   - Output: Strengths, error patterns, foundational gaps, micro-interventions
   - References: NaCCA prerequisite knowledge base
   - Model: Claude Sonnet 4.5 with vision OR Gemini Pro Vision

2. **TEACHER-CONVERSATION-PARTNER**
   - Input: Teacher query + class student profiles + conversation history
   - Output: Conversational advice, specific strategies, follow-up questions
   - Context: All diagnosed students in teacher's class
   - Model: Claude Sonnet 4.5

3. **PARENT-ACTIVITY-GENERATOR**
   - Input: Child's gap profile + language + previous activities
   - Output: 3-minute activity + dignity-first framing
   - Constraints: Market/kitchen/transport contexts, zero materials
   - Model: Claude Sonnet 4.5

4. **PARENT-MICRO-COACH**
   - Input: Parent voice transcription + child's gap + activity context
   - Output: 15-second coaching voice note script
   - Rules: Specific technique, local materials, one breath
   - Model: Claude Sonnet 4.5

### NaCCA Prerequisite Knowledge Base (NEW)

**Must be built Weeks 1-2:**
- JHS 1 Math content standards mapped to P1-P6 prerequisites
- 20-30 most common misconception patterns (from expert teachers)
- Micro-intervention templates for each misconception
- Parent activity templates for each foundational skill

**Format:** Structured JSON or embedded in AI system prompts

**Validation:** 2-3 experienced JHS math teachers review

---

## WHAT WE BUILT THAT'S STILL USEFUL

### ✅ Keep As-Is

1. **FLOW-ONBOARD** — Perfect, matches spec exactly
2. **FLOW-OPT-OUT** — Perfect, matches spec exactly
3. **Parent/Student/Teacher models** — Core entities correct
4. **WhatsApp webhook handling** — Foundation is solid
5. **Flow state management** — Pattern is useful, needs expansion
6. **Test infrastructure** — Comprehensive, keep all tests
7. **Database setup** — Core schema good, needs additions
8. **API infrastructure** — FastAPI setup is solid
9. **Alembic migrations** — Continue using for schema changes

### 🔄 Adapt/Extend

1. **Diagnostic API endpoints** → Repurpose for exercise book scan storage
2. **Question bank** → Becomes NaCCA prerequisite knowledge base
3. **flow_executor.py** → Extend to handle image messages + conversation state
4. **AI integration** → Expand to multimodal, add TTS/STT

### ❌ Deprioritize/Remove

1. **Structured questionnaire flows** — Not in MVP scope
2. **Multiple choice response handling** — Not MVP architecture
3. **Activity scheduling system** — Replaced by simple 6:30 PM daily voice note
4. **Check-in flows** — Happens naturally through parent responses

---

## RECOMMENDED PATH FORWARD

### Option 1: Pivot to Actual MVP (Recommended)

**Pros:**
- Aligns with source specification
- Tests the hardest assumptions (multimodal AI diagnosis from photos)
- Matches the UNICEF pitch narrative
- $2,000 budget and 8-week timeline are realistic

**Cons:**
- Requires new technical components (multimodal AI, TTS/STT)
- Some existing diagnostic API work becomes less relevant
- Need to learn/test Twi TTS quality

**Timeline:**
- Week 1-2: Build NaCCA knowledge base, engineer AI prompts, test Twi TTS
- Week 3-4: Integrate multimodal AI, build exercise book scanner, test with real photos
- Week 5-6: Build parent voice note system (TTS + activity generator)
- Week 7-8: Build teacher conversation partner, integrate everything

**Effort:** 8-10 weeks (matches MVP Blueprint timeline)

### Option 2: Finish Current Architecture First, Then Pivot

**Pros:**
- Complete what we started
- Structured diagnostic API could be useful for Phase 2
- Less context switching

**Cons:**
- Delays testing the core MVP thesis
- Builds features not in MVP specification
- May waste time on architecture we'll replace

**Not Recommended:** Source documents are clear that exercise book scanner is THE core feature.

### Option 3: Hybrid — Minimal Viable Bridge

**Pros:**
- Keep FLOW-ONBOARD as entry point
- Add exercise book scanner as next step after onboarding
- Add parent voice notes triggered by scan results
- Defer teacher conversation partner to Phase 2

**Cons:**
- Still misses some MVP components
- May not fully validate the three MVP questions

**Possible:** If UNICEF pitch is Feb 20 and we need a demo

---

## IMMEDIATE ACTIONS REQUIRED

### 1. Stakeholder Alignment (TODAY)
- [ ] Review this document with team
- [ ] Decide: Pivot to actual MVP or continue current path?
- [ ] Update UNICEF pitch deck if needed (ensure it matches what we're building)

### 2. Technical Spike (Week 1)
- [ ] Test multimodal AI with real JHS exercise book photos
- [ ] Test Twi TTS quality (Google Cloud TTS vs ElevenLabs)
- [ ] Estimate costs for 1,200 scans + 8,400 voice notes over 12 weeks
- [ ] Verify WhatsApp media handling (images, voice notes)

### 3. Knowledge Base Development (Week 1-2)
- [ ] Map JHS 1 Math to P1-P6 prerequisites (NaCCA docs)
- [ ] Interview 2-3 JHS math teachers for common misconceptions
- [ ] Build structured knowledge base (JSON or prompt embedding)
- [ ] Validate with educators

### 4. AI Prompt Engineering (Week 2)
- [ ] EXERCISE-BOOK-ANALYZER prompt
- [ ] Test against 50+ real exercise book photos
- [ ] Measure concordance with expert teacher assessment (target: 75%+)
- [ ] PARENT-ACTIVITY-GENERATOR with dignity-first constraints
- [ ] Test with Twi-speaking parents for tone/clarity

### 5. Architecture Redesign (Week 2-3)
- [ ] Database schema additions (scans, gap_profiles, prompts, conversations)
- [ ] Conversation state management (beyond simple flow steps)
- [ ] Image storage (S3 or equivalent)
- [ ] TTS/STT integration

### 6. Implementation (Week 3-6)
- [ ] Exercise book scanner (image → AI → WhatsApp response)
- [ ] Parent voice note system (daily 6:30 PM Twi voice notes)
- [ ] Teacher conversation partner (maintain context across sessions)
- [ ] Weekly Gap Map generator

### 7. Testing & Iteration (Week 6-8)
- [ ] Test with 2-3 pilot teachers
- [ ] Collect real exercise book scans
- [ ] Test Twi voice notes with parents
- [ ] Iterate on AI accuracy and framing
- [ ] Prepare for 12-week measurement period

---

## COST REALITY CHECK (Actual MVP)

Based on MVP Blueprint specifications:

**12-Week Pilot:**
- WhatsApp Business API: 200 parent conversations/week + 50 teacher conversations/week × 12 weeks = **$150-360**
- Multimodal AI: 100 exercise book scans/week × 12 weeks = 1,200 scans × $0.05 avg = **$60-120**
- Text AI: 500 conversation turns/week × 12 weeks × $0.005 avg = **$30-60**
- TTS (Twi): 200 voice notes/week × 12 weeks × $0.01 = **$24-50**
- STT (Whisper): 50 parent voice replies/week × 12 weeks × 30 sec avg × $0.006/min = **$9-18**
- Hosting: 12 weeks basic VPS or free-tier = **$0-60**
- Domain + SSL: **$12**

**TOTAL: $285-680**

**Per student (400 students): $0.71-1.70**

This is drastically cheaper than any existing diagnostic tool. The MVP Blueprint's thesis is validated: WhatsApp-native + cloud AI makes this economically viable.

---

## CONCLUSION

**We have been building a different product than what the MVP Blueprint specifies.**

The MVP is not a structured questionnaire system delivered via WhatsApp. It is a **multimodal AI diagnostic assistant** that:
- Analyzes exercise book photos to identify foundational gaps
- Provides conversational guidance to teachers
- Sends daily Twi voice notes to parents with embedded-in-life activities
- Always uses dignity-first framing
- Runs entirely on WhatsApp

**The good news:**
- Our foundation (FLOW-ONBOARD, database, API infrastructure) is solid
- The pivot is achievable in 8-10 weeks (matches MVP Blueprint timeline)
- The actual MVP is cheaper and more focused than what we were building

**The decision:**
- Continue current path and build something not in the specification?
- OR pivot now to build what the MVP Blueprint actually describes?

**Recommendation:** Pivot to actual MVP. The source documents are unambiguous, and the exercise book scanner is explicitly called "the riskiest, most novel component — if this fails, everything fails."

We should test the hardest assumption first.

---

**Next Step:** Stakeholder decision on path forward, then begin Week 1 technical spike if pivoting.
