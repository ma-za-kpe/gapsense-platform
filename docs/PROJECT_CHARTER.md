# GapSense Product Charter

**Status:** Active direction
**Date:** 2026-07-22
**Supersedes:** the seven-day WhatsApp-first implementation plan for current execution

## Mission

Help educators in Ghana and Uganda identify the earliest learning prerequisite that is
blocking progress, understand why it matters, and choose a practical next action without
reducing a learner to a score or deficit label.

GapSense should make both national curricula come alive as connected maps of learning,
not merely digitize curriculum PDFs or generate generic tutoring content.

## Current Product Bet

Build a polished, local-first web application before implementing messaging channels or
production infrastructure.

The web product will let people generate free, curriculum-aligned assessments and let
validated users explore curricula, understand prerequisite relationships, run and review
diagnostic sessions, inspect evidence and confidence, and track interventions and
reassessment. It will be usable with deterministic local mocks and may optionally use the
locally installed Ollama runtime. The active local phase requires no external-model API key.

## Primary Users to Validate

The initial hypothesis is teacher-first, but research must test it.

- Classroom teachers and learning-support teachers
- Curriculum and subject reviewers
- School academic leaders
- Learners, with age-appropriate and safeguarded experiences
- Parents or caregivers, where research supports a web workflow
- Education partners and researchers using aggregated, privacy-safe evidence
- Any legitimate visitor who needs an age-appropriate practice activity, quiz, test,
  assessment, or exam aligned to an available Ghanaian or Ugandan curriculum

No persona is treated as validated until direct research supports its workflows.

## Geographic and Curriculum Scope

GapSense will support Ghana and Uganda using each country's official terminology,
curriculum authority, grade/phase structure, subjects, languages, and cultural contexts.

The completion programme covers all official education levels and subjects for which an
authoritative curriculum can be lawfully sourced. Pre-tertiary coverage is the first
execution priority. TVET and tertiary scope must be inventoried with the relevant national
authorities rather than assumed to have a single curriculum model.

Coverage and validity are separate:

- **Coverage:** the official learning outcomes are represented.
- **Diagnostic depth:** prerequisite, misconception, and assessment intelligence exists.
- **Validity:** the representation and diagnostic reasoning have passed structural,
  educator, cultural, and pilot review.

## Product Principles

1. **Root cause over another score.** Explain the prerequisite chain and next action.
2. **Evidence over confidence theatre.** Show source, uncertainty, and review status.
3. **Teacher agency over automation.** AI proposes; qualified people can inspect,
   correct, override, and improve.
4. **Dignity by default.** Never frame learners as broken, behind, or incapable.
5. **Country truth over generic localization.** Ghana and Uganda are distinct systems.
6. **Curriculum structure before generated content.** Deterministic knowledge comes first.
7. **Useful without AI.** The web application degrades gracefully when models are absent.
8. **Low-resource excellence.** Fast, accessible, resilient interfaces are premium UX.
9. **Privacy is correctness.** Minimize data and make local synthetic use the default.
10. **Research continuously.** Product and market beliefs remain dated hypotheses until
    evidence supports them.
11. **Create durable economic value.** Every major capability should improve a valuable
    user outcome, strengthen buyer value, reduce delivery cost, or deepen defensibility.
12. **Profit without extraction.** Revenue must come from trusted outcomes and workflow
    value, not from selling learner data, manipulative engagement, or unsafe automation.
13. **Assessment fit over exam theatre.** Generate the format appropriate to the official
    curriculum and learner phase; a written paper is not always the right assessment.
14. **Free means useful.** The public assessment generator must produce a complete usable
    artifact, not a crippled teaser designed to coerce payment.
15. **Secure by construction.** Minimize attack surface and data, distrust every boundary,
    deny access by default, and require evidence that controls work. Security and child
    safeguarding block release.

## Commercial Intent

GapSense is intended to become a profitable and durable company, not only a demonstration
or research archive. Product discovery must therefore identify both the daily user and the
economic buyer.

Business-model hypotheses to test include:

- subscriptions or licenses for individual schools and school groups;
- programme licenses for NGOs and foundations;
- government or district curriculum/diagnostic contracts;
- curriculum-intelligence, validation, or API licensing to education products;
- implementation, evaluation, and research services that lead to repeatable product revenue;
- a useful free teacher entry point that creates evidence and qualified institutional demand.
- a free public assessment generator that earns trust and creates demand for optional school
  moderation, collaboration, analytics, diagnostic, integration, support, and API workflows.

None is selected yet. User adoption, procurement reality, willingness to pay, cost-to-serve,
gross margin, support burden, and outcome evidence must be researched in Ghana and Uganda.

The architecture should preserve replaceable ports for entitlements, usage metering, feature
flags, and billing while using local deterministic fakes in the current phase. Diagnostic
correctness, data export, privacy, and basic learner dignity must never depend on payment.

Commercial defensibility should come from validated curriculum graphs, diagnostic evidence,
country-specific workflow knowledge, trusted UX, accumulated outcome data with proper consent,
and institutional relationships—not artificial lock-in.

## Web Experience Standard

The product must:

- work responsively from low-cost mobile screens to desktop;
- meet WCAG 2.2 AA at minimum;
- support keyboard and assistive-technology use;
- preserve work through interruptions and connectivity changes;
- communicate loading, missing data, uncertainty, errors, and recovery clearly;
- use official country, level, and subject terminology;
- avoid decorative complexity that impairs comprehension or performance;
- validate visual identity and language with Ghanaian and Ugandan users.

## Local Technical Direction

- FastAPI remains the current backend direction unless an ADR changes it.
- PostgreSQL remains the current structured-data direction.
- A web frontend will be selected through an ADR and prototype.
- Docker is the development and validation runtime.
- Authentication is mocked locally behind a replaceable interface.
- AI is abstracted; deterministic fakes power tests and offline behavior.
- Ollama is the active local provider. Model availability is discovered and evaluated, while
  application startup and deterministic core workflows remain independent of it.
- Data access is versioned through a country/level/subject curriculum contract.
- All application-owned executable code maintains 100% line and branch coverage.

## Explicit Non-Goals for the Current Phase

- WhatsApp or SMS delivery
- Production cloud deployment
- Firebase, AWS, or other hosting selection
- Remote Git pushes
- Real learner or parent data
- Live payment, billing, procurement, or school-system integration
- Autonomous diagnosis without educator visibility and override
- Claims that structurally extracted curricula are educationally validated

These are holds, not permanent rejections. Each requires an explicit decision and evidence
before it enters active work.

## Success Evidence for the Local Web Phase

The phase succeeds when:

- the local Docker environment starts reliably from a clean checkout;
- Ghana and Uganda curriculum coverage is machine-auditable and versioned;
- at least one end-to-end workflow per country is usable through the browser;
- a visitor can generate a complete, source-linked, age-appropriate assessment package for
  at least one reviewed curriculum slice per country without providing personal data;
- the same domain model supports country-specific terminology and curriculum structure;
- educators can inspect sources, prerequisites, diagnostic reasoning, uncertainty, and
  recommended actions;
- critical workflows pass usability and accessibility testing;
- line and branch coverage remain at 100%;
- all CI-equivalent checks pass locally;
- no real PII, remote deployment, remote push, or WhatsApp dependency is required.

## Decision Authority

[`TASKS.md`](../TASKS.md) controls execution. [`WAYS_OF_WORKING.md`](WAYS_OF_WORKING.md)
controls how evidence is produced. Architecture decisions are captured in ADRs. Current
facts and hypotheses are captured in dated research documents.

When documents disagree, the newest explicit decision does not silently rewrite history:
the older document is marked superseded and retained for context.
