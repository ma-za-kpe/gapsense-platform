# GapSense: Technical Roadmap Bridge
## Connecting the v2 Conceptual Design to the Technical Blueprint

**Author:** Maku Mazakpe | **Date:** February 16, 2026 (UPDATED) | **For:** UNICEF StartUp Lab Cohort 6 Application

---

## 🚨 CRITICAL UPDATE: Specification vs Implementation Status

**This Document Describes:** The v2 vision and the 10 technical deliverables that specify the full system
**Current Reality:** We are 15% complete on the actual MVP (see [mvp_specification_audit_CRITICAL.md](mvp_specification_audit_CRITICAL.md))

**What's Specified (100%):** All 10 deliverables exist - prompts, architecture, data models, flows
**What's Implemented (15%):** WhatsApp infrastructure, parent onboarding, database schema
**What's Missing (85%):** Exercise book scanner, teacher onboarding, Twi voice notes, multimodal AI

This document shows the *path* from MVP → Full Vision. For current implementation status, see [gapsense_technical_roadmap_bridge.md](gapsense_technical_roadmap_bridge.md).

---

## Purpose

The GapSense v2 Conceptual Design describes an 18-month vision: an on-device AI diagnostic reasoning partner with 5 school-side channels, 14 parent engagement channels, dual-AI architecture, and coverage across numeracy, literacy, and TVET.

The Technical Blueprint (10 deliverables, ~5,500 lines of specification) provides the engineering foundation to make that vision real. This document maps each deliverable to its role in v2's phased implementation, explains deliberate architectural choices, and shows the credible path from MVP to full vision.

**Note:** This document describes the *specifications and vision*. For what's actually built vs what's needed, see the MVP audit docs.

---

## Architecture Strategy: Cloud-First Is the Plan, Not a Limitation

The v2 document describes a dual-AI architecture: an on-device SLM (Gemma 3n or Phi-4-mini) handling real-time teacher interaction, and a cloud model handling complex reasoning and parent engagement.

The Technical Blueprint specifies cloud-only (Anthropic Claude on AWS). This is deliberate.

**Why cloud-first is the correct Phase 1 strategy:**

You cannot fine-tune an on-device SLM for Ghanaian exercise book analysis without a labeled dataset of Ghanaian exercise books analyzed by an expert model. Phase 1's cloud architecture generates exactly this dataset. Every exercise book the cloud model analyzes, every diagnostic session it runs, every error pattern it identifies becomes training data for the Phase 2 on-device model.

The sequence is: (1) Cloud model builds the reasoning baseline and generates labeled data → (2) Distill reasoning patterns into a 2-3B parameter on-device model → (3) On-device handles real-time teacher interaction, cloud handles complex tasks.

Skipping to on-device in Phase 1 means training on insufficient data, which means an inaccurate diagnostic model, which means teachers lose trust, which means GapSense dies. Cloud-first is the responsible path.

---

## Phase Mapping

### Phase 1a: Core Engine (Months 1-5) — 15% IMPLEMENTED

This is what the 10 deliverables specify. The diagnostic reasoning core, the data infrastructure, and the primary parent engagement channel.

**Status:** Specifications complete (100%), Implementation in progress (15%)

| Deliverable | v2 Section Served | What It Enables |
|---|---|---|
| **#1: NaCCA Prerequisite Graph v1.2** | §6.1 NaCCA Alignment, §2 Invisible Assessment | 35 nodes (27 numeracy + 8 literacy skeleton), 6 cascade paths, misconception database. The AI's "curriculum brain." Traces backward from JHS to find primary-level root causes. |
| **#2: Data Model** | §7.3 Privacy Architecture | 742-line PostgreSQL schema. Students, parents, teachers, diagnostic sessions, gap profiles, parent engagement cycles, prompt versioning, audit logs. Designed for Ghana Data Protection Act compliance. |
| **#3: Prompt Library (13 prompts)** | §2 Invisible Assessment, §3 Channels 1-2, §4 Channels 1-5 | The AI reasoning specifications. Includes DIAG-001/002/003 (diagnostic engine), PARENT-001/002/003 (WhatsApp engagement), TEACHER-001/002/003 (reports + conversation partner), ACT-001 (activity generator), ANALYSIS-001/002 (exercise book + voice), GUARD-001 (Wolf/Aurino compliance enforcer). |
| **#4: API Specification** | §7.2 WhatsApp Integration | 23 REST endpoints. Complete contract for diagnostic sessions, student management, parent engagement, teacher reporting, WhatsApp webhooks, analytics. |
| **#5: WhatsApp Flows** | §4.3-4.6, §4.16 | 6 conversation flows, 5 message templates. Onboarding, diagnostic, activity delivery cycle, exercise book intake, teacher onboarding, opt-out. |
| **#6: Architecture Decision Record** | §7.1-7.3 | 12 decisions documented: AWS Cape Town, FastAPI, PostgreSQL, WhatsApp Cloud API direct, Anthropic Claude, SQS queuing, modular monolith, defense-in-depth privacy. |
| **#7: Project Structure** | §7.1 | 8 application modules with strict dependency rules. No circular dependencies. Clean extraction path to microservices. |
| **#8: Infrastructure as Code** | §7.1 | AWS CDK stack (VPC, RDS, Fargate web+worker, SQS, S3, Cognito), Dockerfile, Docker Compose for local dev. Staging/production toggle. |
| **#9: Test Scenario Matrix** | §10 Success Metrics | 18 scenarios across 5 categories: diagnostic accuracy, parent engagement, conversation flows, API contracts, data integrity. |
| **#10: Claude Code System Prompt** | All sections | 458-line synthesis prompt that gives Claude Code full context to build the system. References all 9 preceding deliverables. |

**v2 coverage in Phase 1a (SPECIFICATION STATUS, not implementation):**

| v2 Feature | Specification Status | Implementation Status |
|---|---|---|
| Exercise Book Scanner (School Channel 1) | ✅ ANALYSIS-001 prompt specified | ❌ Not implemented (0%) |
| Teacher Conversation Partner (School Channel 2) | ✅ TEACHER-003 prompt specified | ❌ Not implemented (0%) |
| 3-Minute Evening Ritual (Parent Channel 1) | ✅ Full flow: ACT-001 → PARENT-001 → GUARD-001 → PARENT-002 | ❌ Not implemented (0%) |
| Dignity-First Framing (Parent Channel 3) | ✅ GUARD-001 at temperature 0.0 enforces Wolf/Aurino on EVERY outbound message | ❌ Not implemented (0%) |
| Market Math Activities (Parent Channel 4) | ✅ ACT-001 generates Ghanaian-context activities with household materials | ❌ Not implemented (0%) |
| Parent Diagnostic Sensor (Parent Channel 2) | ⚠️ ANALYSIS-002 handles voice notes; cognitive process analysis deferred | ❌ Not implemented (0%) |
| NaCCA Curriculum Alignment | ✅ 35-node graph with 6 cascade paths, numeracy fully populated B1-B4 | ⚠️ Partial (data files exist, not loaded) |
| L1 Language Support | ✅ Templates in Twi, Ewe, Ga, Dagbani, English. L1 math vocabulary guides. | ⚠️ Partial (opt-out keywords only) |
| Adaptive Engagement Recovery (Parent Channel 14) | ✅ Re-engagement template + opt-out flow | ✅ Opt-out flow implemented |

---

### Phase 1b: Expand Coverage (Months 2-4)

Building on the Phase 1a engine with broader diagnostic capability and teacher experience.

| Work Item | v2 Section | Approach |
|---|---|---|
| **Populate literacy graph** | §6.3 Language Architecture | Expand 8 skeleton nodes to full indicators using NaCCA English Language B1-B6 standards PDF. Add B4-B6 literacy nodes. |
| **Oral Reading Intelligence** | §3 Channel 3 | New prompt ANALYSIS-003: analyze audio recording of student reading. Detect hesitation patterns, self-corrections, prosody. On-device STT → cloud analysis initially. |
| **Voice Micro-Coaching** | §4.7 Parent Channel 5 | New prompt PARENT-004: generate 15-second coaching scripts. TTS integration via Google Cloud TTS or Africa's Talking voice API for Twi/Ewe/Ga/Dagbani. |
| **USSD/Voice Callback skeleton** | §4.10 Parent Channel 8 | Africa's Talking USSD gateway. *789# menu: weekly update, tonight's activity, record reading, speak to GapSense. Ensures non-smartphone parents are not excluded. |
| **Teacher web dashboard** | §3 Channel 2 | Minimal web interface for TEACHER-003 conversation. Chat-style UI. Exercise book photo upload. Class gap visualization. |
| **500+ diagnostic items** | §8 Phase 1 | Expand from current misconception/error pattern database to 500+ items across numeracy and literacy, sourced from NaCCA standards and Ghanaian teacher input. |
| **TTS models for L1** | §7.2, §4.7 | Evaluate Google Cloud TTS (Twi available), Africa's Talking voice, or open-source Coqui TTS fine-tuned on Ghanaian language samples. |

---

### Phase 2: Pilot + On-Device (Months 5-8)

Deploy to 25 schools. Begin distilling cloud model to on-device SLM.

| Work Item | v2 Section | Approach |
|---|---|---|
| **On-device SLM distillation** | §7.1 Dual-AI | Using Phase 1 cloud data (exercise book analyses, diagnostic sessions, teacher conversations) as training set. Fine-tune Gemma 3n or Phi-4-mini. Target: exercise book analysis + teacher conversation on-device. |
| **Peer Diagnostic Games** | §3 Channel 4 | Mobile-first games (Flutter). Secretly diagnostic. Market trader simulation (numeracy), story-building (literacy), measurement challenges (TVET). |
| **Predictive Early Warning** | §3 Channel 5 | Analyze 2-3 weeks of student work patterns to predict upcoming topic struggles. Requires longitudinal data from pilot schools. |
| **Community Champions** | §4.13 Parent Channel 11 | Recruit 1 champion per class. WhatsApp onboarding sequence. Champion serves as human bridge for low-confidence parents. |
| **Parent Peer Networks** | §4.9 Parent Channel 7 | AI-moderated WhatsApp groups for parents of students with shared gaps. Weekly activity + discussion prompt. Shame prevention via AI moderation. |
| **Family Learning Pact** | §4.8 Parent Channel 6 | Structured teacher-parent coordination protocol. AI generates complementary home/school activities. |
| **Grandmother Channel** | §4.11 Parent Channel 9 | Voice-only weekly call in L1. Story/game framing. Africa's Talking voice callback. |
| **Report Card Translator** | §4.15 Parent Channel 13 | Photo → OCR → cross-reference with gap profile → voice note in L1 with context and encouragement. |
| **Wolf/Aurino validation** | §4.1, §10 | Critical metric: engagement rate among parents with zero formal education must be ≥50% of overall rate. |

---

### Phase 3: Scale (Months 9-18)

300+ schools. Cross-school intelligence. National integration.

| Work Item | v2 Section |
|---|---|
| **Teaching Gap Detector** | §5.1 — Cross-classroom pattern analysis. "85% of Teacher X's students have the same misconception" |
| **Teacher-to-Teacher Network** | §5.2 — Connect teachers facing identical patterns across schools |
| **TVET Vocational Contextualization** | §6.2 — Embed diagnostic in trade practice (carpentry measurement, hospitality calculations) |
| **Sibling Tutor** | §4.12 — Guided peer tutoring via WhatsApp for older siblings |
| **Weekend Family Challenge** | §4.14 — Friday family activities for whole household |
| **Full on-device capability** | §7.1, §6.4 — Complete offline diagnostic. Graceful degradation at every infrastructure level. |
| **GES district integration** | §8 Phase 3 — Feed anonymized analytics into Ghana Education Service monitoring |
| **NaCCA partnership** | §8 Phase 3 — Formal curriculum integration |

---

## Cost Trajectory

| Phase | Monthly Cost | Scale |
|---|---|---|
| Phase 1a (cloud MVP) | ~$70-110/month | 500 diagnostic sessions, 1500 parent messages |
| Phase 1b (expanded) | ~$150-250/month | 2000 sessions, 5000 parent messages, TTS |
| Phase 2 (pilot, 25 schools) | ~$400-800/month | On-device reduces cloud costs. Pilot infrastructure. |
| Phase 3 (300+ schools) | ~$1500-3000/month | On-device handles majority. Cloud for cross-school intelligence. |

The on-device SLM in Phase 2 is the key cost inflection — it shifts the majority of inference from cloud ($$$) to phone (free), making 300+ school scale economically viable.

---

## What the Technical Blueprint Proves to UNICEF

1. **The diagnostic reasoning is real.** 35-node prerequisite graph with cascade paths, misconception databases, and error patterns. 13 AI prompts with specific input/output contracts and test cases. This is not hand-waving — it's a working diagnostic specification.

2. **Wolf/Aurino compliance is architectural, not aspirational.** GUARD-001 runs at temperature 0.0 on every outbound parent message. The banned word list, the strength-first requirement, the jargon filter, the privacy constraints — all enforced at the system level. This cannot be accidentally bypassed.

3. **The system is buildable by a small team on a real budget.** Modular monolith architecture. AWS Cape Town for low latency. $70-110/month MVP cost. One developer can ship Phase 1a with Claude Code using the system prompt that synthesizes all 10 deliverables.

4. **The path from cloud to on-device is deliberate and data-driven.** Cloud Phase 1 generates the labeled training data that makes on-device Phase 2 accurate. This is not a limitation — it's the responsible engineering sequence.

5. **Ghana-specific design is embedded at every layer.** Ghanaian names in diagnostic questions. GH₵ and pesewas in examples. Bottle caps and kenkey in activities. Twi/Ewe/Ga/Dagbani in parent messages. Rural Northern Region constraints in material lists. This is not a "localized" global product — it's built for Ghana from the ground up.

---

## Summary: 10 Deliverables → v2 Vision

The 10 deliverables are not a separate product from v2. They are v2's engine room — the diagnostic reasoning core, the data infrastructure, the parent engagement pipeline, and the compliance architecture that make everything else possible.

Every feature in v2 — from the Grandmother Channel to the Teaching Gap Detector to the Weekend Family Challenge — runs on this engine. The graph provides the diagnostic intelligence. The prompts provide the reasoning. The API provides the interface. The compliance guard provides the dignity.

Build the engine right, and the 14 channels, the 5 school channels, and the on-device experience are extensions — not rewrites.

The engine is specified. It's ready to build.
