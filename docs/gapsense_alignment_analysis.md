# GapSense v2 ↔ Technical Blueprint: Strategic Alignment Analysis

**Date:** February 16, 2026 (Updated)
**Context:** UNICEF StartUp Lab Cohort 6 deadline — February 20, 2026
**Question:** Do the 10 technical deliverables support the v2 Conceptual Design?

---

## 🚨 Current Status Update (Feb 16, 2026)

**This analysis (from Feb 13) discusses specification gaps.**

**New Reality:** We're only 15% complete on implementing even the MVP Blueprint. The v2 vision is even further away.

**See:** [mvp_specification_audit_CRITICAL.md](mvp_specification_audit_CRITICAL.md) for current implementation status.

---

## Executive Summary

**The honest answer: our deliverables are a strong Phase 1 engine specification, but (1) the v2 document has evolved significantly beyond what we've specified, and (2) we've only implemented 15% of the specifications.**

The 10 deliverables nail the diagnostic reasoning core — the prerequisite graph, the adaptive engine, the prompt architecture, the Wolf/Aurino compliance layer. This is the hardest part to get right and the part UNICEF cares most about (can the AI actually reason about learning gaps?).

But v2 has made three major architectural moves that our blueprint doesn't yet reflect:

1. **On-device first** — v2 positions GapSense as an on-device SLM reasoning partner, not a cloud API. Our architecture is cloud-only.
2. **Teacher as primary user** — v2 makes the teacher the power user (conversational partner, not report recipient). Our deliverables center the parent WhatsApp loop.
3. **Invisible assessment paradigm** — v2's core thesis is "no more tests." Our diagnostic engine still runs explicit assessment sessions.

These aren't bugs — they're the difference between the MVP we specified (cloud + WhatsApp + explicit diagnostic) and the product vision v2 describes (on-device + conversational + invisible assessment).

---

## Section-by-Section Alignment

### Section 0: "If you removed the AI, GapSense would cease to function"

| v2 Principle | Our Blueprint | Alignment |
|---|---|---|
| AI is not a feature, AI IS GapSense | ✅ 12 AI prompts power every interaction | **Strong** |
| Everything else is scaffolding | ✅ Architecture serves the AI reasoning pipeline | **Strong** |

**Verdict:** Our blueprint passes this test. Remove the Anthropic prompts and every endpoint returns nothing. The prerequisite graph, the cascade paths, the diagnostic engine — all exist to feed AI reasoning.

---

### Section 2: The Invisible Assessment Paradigm

| v2 Claim | Our Blueprint | Gap |
|---|---|---|
| "Does not add another test" | DIAG-001/002 run explicit diagnostic sessions (6-18 questions) | **CRITICAL MISMATCH** |
| Intelligence extracted from artifacts that already exist | ANALYSIS-001 does this for exercise books | **Partial** |
| Exercise books, oral participation, homework conversations, market transactions | Only exercise books covered | **Significant gap** |

**This is the biggest conceptual gap.** v2 says GapSense should NEVER feel like a test. Our diagnostic engine IS a test — an adaptive one, but still an explicit "answer these questions" session. v2 wants the AI to observe naturally occurring artifacts (exercise books, voice notes, homework conversations) and silently build the gap profile.

**What this means for the blueprint:**
- The DIAG-001 → DIAG-002 → DIAG-003 chain is still valuable as a **teacher-initiated deep diagnostic** (Channel 2 in v2: Teacher Conversation Partner)
- But it should NOT be the primary diagnostic pathway
- The primary pathway should be ANALYSIS-001 (exercise book) feeding directly into the gap profile, with the teacher conversational interface layered on top
- The WhatsApp 3-question diagnostic (FLOW-DIAGNOSTIC-WHATSAPP) actually contradicts v2's core thesis

**Recommendation:** Reframe the diagnostic session as "Teacher Deep Dive" — available but not default. Default diagnostic pathway = exercise book scan → AI analysis → gap profile update → teacher conversation. No student-facing "test" at all.

---

### Section 3: Five School-Side Diagnostic Channels

| Channel | Our Coverage | Status |
|---|---|---|
| **1. Exercise Book Scanner** | ANALYSIS-001 + POST /diagnostics/analyze-image | ✅ Covered |
| **2. Teacher Conversation Partner** | TEACHER-001/002 generate reports, not conversations | ⚠️ Wrong modality |
| **3. Oral Reading Intelligence** | Not addressed at all | ❌ Missing |
| **4. Peer Diagnostic Games** | Not addressed at all | ❌ Missing (Phase 2+) |
| **5. Predictive Early Warning** | Not addressed at all | ❌ Missing (Phase 2+) |

**Channel 2 is the critical miss.** v2 says "reports don't change teacher behavior — conversations do." Our TEACHER-001 generates a JSON report. v2 wants an interactive conversation where the teacher says "I'm teaching fractions next week, which students should I watch?" and the AI responds with diagnostic intelligence.

**What this means:**
- We need a TEACHER-003 prompt: "Teacher Conversation Partner" — a conversational diagnostic interface, not a report generator
- This is the teacher-facing equivalent of the parent WhatsApp flow
- It's also where the on-device SLM comes in — the teacher conversation needs to work offline, which means on-device inference

**Oral Reading (Channel 3)** is a Phase 1 requirement per v2's own roadmap. We have zero literacy infrastructure — no reading fluency nodes in the prerequisite graph, no prompts for analyzing reading patterns. This is a significant gap for the UNICEF pitch because literacy is arguably more critical than numeracy for foundational learning.

**Channels 4 & 5** are Phase 2 — acceptable to omit from technical blueprint.

---

### Section 4: The Parent-Home Partnership (14 Channels)

| Parent Channel | Our Coverage | Status |
|---|---|---|
| **1. 3-Minute Evening Ritual** | PARENT-001, ACT-001, FLOW-ACTIVITY-DELIVERY | ✅ Strong |
| **2. Parent as Diagnostic Sensor** | ANALYSIS-002 (voice notes), but shallow | ⚠️ Partial |
| **3. Dignity-First Framing Engine** | GUARD-001, global Wolf/Aurino rules | ✅ Strong |
| **4. Market Math & Kitchen Literacy** | ACT-001 has Ghanaian materials/contexts | ✅ Covered |
| **5. Voice Micro-Coaching (15s TTS)** | Not addressed | ❌ Missing |
| **6. Family Learning Pact** | Not addressed | ❌ Missing |
| **7. Parent Peer Networks** | Not addressed | ❌ Missing |
| **8. USSD & Voice Callback** | Not addressed | ❌ Missing |
| **9. Grandmother Channel** | Not addressed | ❌ Missing |
| **10. Sibling Tutor** | Not addressed | ❌ Missing |
| **11. Community Champions** | Not addressed | ❌ Missing |
| **12. Weekend Family Challenge** | Not addressed | ❌ Missing |
| **13. Report Card Translator** | Not addressed | ❌ Missing |
| **14. Adaptive Engagement Recovery** | FLOW-OPT-OUT + re-engagement template | ⚠️ Basic |

**We cover 4 of 14 channels well.** But the 4 we cover are the CORE 4 — the ones v2's Phase 1 roadmap prioritizes. Channels 5-14 are enrichment layers that build on top.

**The critical addition for UNICEF credibility:**
- Channel 2 (Parent as Diagnostic Sensor) needs deepening — the "listen to HOW the child answers" cognitive analysis is v2's "radical innovation"
- Channel 5 (Voice Micro-Coaching) is Phase 1 in v2's roadmap and needs at least a prompt specification
- Channel 8 (USSD) matters for equity narrative — "we don't leave behind parents without smartphones"

---

### Section 4.1: Wolf/Aurino Evidence Base

| v2 Requirement | Our Blueprint | Alignment |
|---|---|---|
| Never remind parents of deficiencies | GUARD-001 rejects deficit language at temp=0.0 | ✅ **Strongest alignment** |
| Specific, not generic | ACT-001 generates from gap profile, not templates | ✅ Strong |
| L1 communication | Language templates in 5 languages | ✅ Strong |
| Community Champions as human bridge | Not addressed | ❌ Missing |

**This is where our blueprint shines.** The Wolf/Aurino compliance is not a feature we added — it's a structural constraint enforced at the architecture level (GUARD-001 validates every outbound message). This is exactly what UNICEF wants to see: evidence-based design built into the system, not bolted on.

---

### Section 6: Ghana-Specific Design

| v2 Feature | Our Coverage | Status |
|---|---|---|
| **6.1 NaCCA Deep Alignment** | Prerequisite graph v1.1, 25 nodes, cascade paths | ✅ Strong for numeracy |
| NaCCA JHS → Primary backward tracing | CASCADE paths trace B7→B4→B2→B1 | ✅ Covered |
| **6.2 TVET Vocational Contextualization** | Not addressed | ❌ Missing |
| **6.3 Language Architecture** | 5 languages, L1 vocab guides, direct generation | ✅ Strong |
| English vs L1 reading distinction | Not addressed (numeracy only) | ❌ Missing |
| **6.4 Infrastructure Graceful Degradation** | Not addressed (cloud-only) | ❌ Missing |

---

### Section 7: Technical Architecture

| v2 Architecture | Our Blueprint | Gap Severity |
|---|---|---|
| **Dual-AI: on-device SLM + cloud** | Cloud-only (Anthropic Claude) | **HIGH** |
| Gemma 3n / Phi-4-mini on-device | No on-device component at all | **HIGH** |
| On-device: exercise books, teacher conversation, peer games | All cloud-routed | Architecture mismatch |
| Cloud: cross-school analytics, parent content, WhatsApp | ✅ This matches our architecture | Aligned |
| **Privacy: local-first data** | Cloud-first (RDS PostgreSQL) | **MEDIUM** |
| Student data on teacher's device | Student data in cloud DB | Architecture mismatch |
| Identifiers stripped before sync | No sync model — cloud is primary | Gap |
| **WhatsApp Integration** | Full Cloud API integration, SQS queue, templates | ✅ **Strong** |
| TTS for Ghanaian languages | Not addressed | ❌ Missing |
| USSD via Africa's Talking | Not addressed | ❌ Missing |

**The dual-AI architecture is the biggest technical divergence.** v2 positions on-device inference as a core differentiator — the teacher can use GapSense without internet. Our blueprint requires internet for every AI interaction.

**However:** For the UNICEF pitch, this may be acceptable IF we frame it as: "Phase 1 validates the AI reasoning with cloud models. Phase 2 distills to on-device SLM after we have training data from Phase 1 pilot." You can't fine-tune Gemma 3n on Ghanaian exercise books until you have a labeled dataset — which the cloud diagnostic engine generates.

---

### Section 8: Implementation Roadmap Alignment

**v2 Phase 1 (Months 1-4) vs Our Blueprint:**

| Phase 1 Requirement | Our Status | Action Needed |
|---|---|---|
| On-device exercise book scanner | Cloud version specified (ANALYSIS-001) | Reframe as "cloud-first, on-device Phase 2" |
| Teacher conversation engine | ❌ Not specified | Need TEACHER-003 prompt |
| 500+ NaCCA-aligned diagnostic items | 25 nodes with diagnostic items | Need to acknowledge scale gap |
| Fine-tune SLM on Ghanaian handwriting | ❌ Not addressed | Phase 2 — needs cloud data first |
| Parent WhatsApp flow | ✅ Fully specified | Strong |
| Dignity-first framing engine | ✅ GUARD-001 + global rules | Strong |
| TTS for Twi, Ga, Ewe, Dagbani | ❌ Not addressed | Need at least ADR for TTS approach |
| Usability testing with 15 teachers, 30 parents | Test scenarios cover functional, not usability | Different scope — OK |

**Alignment score with v2 Phase 1: ~55-60%**

We've deeply specified the diagnostic engine, the parent WhatsApp loop, and the compliance layer. We're missing the teacher conversation engine, literacy, TTS, and the on-device framing.

---

## The Three Things That Matter Most for UNICEF (Feb 20)

### 1. Can the AI actually reason about learning gaps?

**YES — this is our strongest card.** The prerequisite graph with cascade paths, the 3-phase diagnostic chain (DIAG-001→002→003), the misconception database, the backward-tracing algorithm — this is the technical proof that the AI doesn't just quiz students, it reasons about WHY they're wrong and traces to root causes. No other applicant will have this level of diagnostic specification.

### 2. Is the parent engagement evidence-based?

**YES — arguably our second strongest card.** Wolf/Aurino principles aren't mentioned in a slide deck — they're enforced by GUARD-001 at temperature 0.0 on every outbound message. The dignity-first framing, the L1 language support, the "never say behind/struggling/failing" constraint, the 3-minute activity limit, the household materials requirement — all architecturally enforced.

### 3. Is this buildable in the timeline?

**This is where we need to be strategic.** v2 describes an 18-month vision. UNICEF wants to know Phase 1 is achievable. Our 10 deliverables prove the core engine is deeply thought through and technically sound. The gap is showing UNICEF we have a credible path from "cloud diagnostic engine" to "on-device teacher partner with 14 parent channels."

---

## Recommended Actions Before Feb 20

### MUST DO (Critical for UNICEF coherence)

**A. Create a Technical Roadmap Bridge Document**
A 2-3 page document that explicitly maps our 10 deliverables to v2 phases:
- Phase 1a (NOW — what we've built): Cloud diagnostic engine, WhatsApp parent loop, NaCCA numeracy graph
- Phase 1b (Months 2-4): Teacher conversation engine, literacy graph, exercise book scanner optimization
- Phase 2 (Months 5-8): On-device SLM distillation, USSD/voice channels, Community Champions, pilot
- Phase 3 (Months 9-18): Cross-school intelligence, TVET, full 14-channel parent system

This bridges the conceptual design (v2) to the technical reality (deliverables) without contradictions.

**B. Add a TEACHER-003 Prompt to the Prompt Library**
"Teacher Diagnostic Conversation Partner" — the conversational interface v2 describes as the primary teacher UX. This is v2's biggest insight and our biggest gap. Even a well-specified prompt with I/O contract shows UNICEF we understand that reports ≠ behavior change.

**C. Add a Literacy Section to the Prerequisite Graph**
Even 5-8 skeleton nodes for P1-P3 literacy (letter recognition → phonemic awareness → word decoding → fluency → comprehension) shows UNICEF that numeracy is Phase 1a and literacy is Phase 1b, not an afterthought.

### SHOULD DO (Strengthens the pitch)

**D. Add an ADR for Dual-AI Architecture**
ADR-013: "Cloud-first, on-device second." Rationale: We need labeled Ghanaian exercise book data to fine-tune SLM. Cloud Phase 1 generates this dataset. Phase 2 distills to Gemma 3n. This turns the architecture mismatch into a deliberate strategy.

**E. Add Voice Micro-Coaching Prompt Spec**
PARENT-004: "15-Second Voice Coaching." Even without TTS implementation, specifying the prompt shows UNICEF the channel is designed.

**F. Add USSD Flow Skeleton**
A lightweight specification showing the *789# menu structure and Africa's Talking integration. Even 30 lines proves you've thought about non-smartphone parents.

### NICE TO HAVE (If time permits)

- Report Card Translator prompt (ANALYSIS-003)
- Community Champions onboarding flow
- Grandmother Channel voice flow specification
- Sibling Tutor WhatsApp flow

---

## What Our Blueprint Gets RIGHT That v2 Needs

It's not all gaps. Our technical deliverables add precision that v2 lacks:

| What We Specify | What v2 Doesn't |
|---|---|
| Exact API contracts (23 endpoints) | v2 has no API specification |
| Database schema with constraints | v2 mentions "local storage" without schema |
| Prompt versioning and A/B testing | v2 doesn't address prompt management |
| SQS message queuing for reliability | v2 doesn't address message delivery guarantees |
| Three-tier testing strategy | v2 mentions "calibrate" without test methodology |
| Cost modeling ($20-30/mo AI, $50-80/mo infra) | v2 has no cost estimates |
| Anti-fabrication guardrails | v2 trusts the AI implicitly |
| WhatsApp template pre-approval workflow | v2 treats WhatsApp as simple messaging |

**The deliverables make v2 credible.** v2 is a visionary conceptual design. The deliverables prove someone has done the engineering to make it real.

---

## Final Assessment

**Are we on track for UNICEF Feb 20?**

The 10 deliverables are a solid technical foundation that proves:
- The AI diagnostic reasoning is deeply specified (not hand-waving)
- Wolf/Aurino compliance is architecturally enforced (not aspirational)
- The system is buildable by a small team on a realistic budget
- Ghana-specific design is embedded at every layer

**What's missing is the bridge between v2's VISION and our BLUEPRINT.**

The v2 document promises an on-device, invisible-assessment, teacher-conversational, 14-channel system. Our blueprint delivers a cloud-based, explicit-diagnostic, parent-WhatsApp-centered, 4-channel engine.

Both are true. Both are necessary. What UNICEF needs to see is that they're connected — that the engine we've built IS the foundation for the vision v2 describes, and there's a credible technical path from one to the other.

The must-do items (A, B, C) close this gap. They take the 10 deliverables from "strong Phase 1 engine" to "credible full-vision technical blueprint."
