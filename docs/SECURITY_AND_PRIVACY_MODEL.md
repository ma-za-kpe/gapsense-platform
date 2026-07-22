# Security and Privacy Engineering Model

**Date:** 2026-07-22

**Status:** Active baseline; never complete
**Current exposure:** Local development only, synthetic data only, no authorized deployment

## Security Decision

Security, privacy, child safeguarding, and curriculum integrity are product invariants. They
are designed into domain rules, use cases, interfaces, data models, delivery workflows, tests,
and operating procedures. They are not delegated to a future hosting provider or postponed to
a penetration test.

No milestone is complete when it introduces an unmodeled trust boundary, an untested
authorization rule, an unexplained data field, a swallowed security failure, or an unresolved
critical/high vulnerability. Product deadlines, cost, convenience, and AI capability do not
override this rule.

## Standards Baseline

The programme uses current standards as structured inputs, not as unsupported certification
claims:

- [OWASP ASVS 5.0.0](https://owasp.org/www-project-application-security-verification-standard/)
  Level 2 is the minimum web/API verification target before real data. Risk-selected Level 3
  requirements apply where child data, sensitive educational inference, privileged review,
  or high-impact administration justify them.
- [OWASP Top 10:2025](https://owasp.org/Top10/) informs web risk awareness, including broken
  access control, insecure design, supply-chain failures, integrity failures, and mishandled
  exceptional conditions.
- [OWASP API Security Top 10:2023](https://owasp.org/API-Security/) informs object/function
  authorization, resource consumption, inventory, and unsafe third-party API use.
- [OWASP GenAI/LLM Top 10:2025](https://genai.owasp.org/llm-top-10/) informs prompt injection,
  disclosure, poisoning, supply-chain, output-handling, agency, and consumption controls.
- [NIST SSDF 1.1](https://csrc.nist.gov/projects/ssdf) structures preparation, software
  protection, production, and vulnerability response. Revision 1.2 is a draft as of this date
  and is tracked without being presented as final guidance.
- [OWASP SAMM](https://owasp.org/www-project-samm//) provides a measurable improvement model
  across governance, design, implementation, verification, and operations.

Compliance with Ghanaian and Ugandan law requires qualified local advice. Initial engineering
research includes Ghana's [Data Protection Act, 2012 (Act 843)](https://dataprotection.org.gh/documents/)
and Uganda PDPO guidance under the
[Data Protection and Privacy Act](https://pdpo.go.ug/media/2022/01/15122021123537-Guidance_note_on_lodging_complaints.pdf).
The Uganda guidance explicitly identifies concerns involving inadequate security, excessive
retention, uninformed consent, unauthorized disclosure, and children's data without required
parent/guardian authority. This document does not settle lawful basis, registration,
cross-border processing, or child-consent questions.

## Non-Negotiable Invariants

1. **No real personal data in the current phase.** Tests, demos, logs, screenshots, exports,
   prompts, analytics, and seed data use obviously synthetic identities.
2. **Collect nothing by default.** Every future field needs a documented purpose, sensitivity,
   lawful basis, access policy, retention period, deletion rule, and product owner.
3. **Deny by default.** Authentication proves an identity claim; server-side authorization
   separately proves that actor may perform this action on this exact resource.
4. **Least privilege everywhere.** Users, service identities, containers, database roles,
   files, networks, models, and build systems receive only required capability.
5. **Untrusted at every boundary.** Browser input, curriculum files, generated content,
   retrieved text, model output, imports, dependencies, environment values, and webhooks are
   validated and constrained.
6. **Secrets never enter code or artifacts.** They do not belong in Git, images, logs, browser
   bundles, fixtures, generated exams, model prompts, screenshots, or error responses.
7. **Security failures fail closed.** Missing policy, unavailable validation, ambiguous role,
   invalid signature, stale session, unknown artifact version, or failed audit is a denial or a
   stopped release, not a warning-only success.
8. **Evidence travels with decisions.** Curriculum releases, generated assessments,
   diagnostics, overrides, and exports carry provenance, version, actor, and integrity evidence.
9. **Children are never the security boundary.** Interfaces do not rely on a child noticing a
   privacy problem, protecting an answer key, understanding model risk, or managing consent.
10. **No security by obscurity.** Public identifiers may be unguessable, but authorization,
    validation, rate controls, and audit evidence remain mandatory.

## Assets and Highest-Concern Harms

Assets include curriculum source and enriched graph IP, assessment items and answer keys,
learner/parent/teacher identity and contact data, diagnostic responses and inferred gaps,
school membership, consent and safeguarding records, authorization policy, audit history,
model prompts/configuration, generated artifacts, signing keys, credentials, source code,
dependencies, build artifacts, and business evidence.

The threat model must consider at least:

- a learner seeing another learner's data or restricted answer key;
- a parent, teacher, school, reviewer, or administrator crossing an object/organization boundary;
- enumeration, scraping, bulk export, account takeover, insider misuse, or privilege escalation;
- malicious input causing injection, unsafe model behavior, data leakage, or resource exhaustion;
- poisoned curriculum, item bank, dependency, model, container, or build artifact;
- generated misinformation being mistaken for official curriculum or examination material;
- re-identification through logs, analytics, exports, free text, or small-group reporting;
- loss, corruption, unavailability, or unverifiable deletion of retained data;
- fraud, official-paper impersonation, answer-key leakage, or high-stakes cheating;
- suppressed security signals, incomplete audit trails, and failures that appear green.

## Threat Modeling as Normal Delivery Work

For each major workflow, record:

1. what is being built, including assets, actors, data flows, dependencies, and trust boundaries;
2. what can go wrong, including accidental harm and deliberate abuse;
3. prevention, detection, containment, recovery, ownership, and residual risk;
4. the tests and operating evidence that prove the response is adequate.

Use data-flow diagrams and STRIDE or another appropriate method. Revisit the model when a role,
field, export, provider, model, tool, dependency, integration, or deployment boundary changes.
Threat-model tasks and unresolved risks belong in [`TASKS.md`](../TASKS.md), not private notes.

## Identity and Authorization

Local mock authentication is a replaceable adapter for product development. It must never become
a production backdoor or teach routes to trust client-supplied roles.

- Production configuration must be unable to enable mock identity.
- Browser claims are untrusted; authorization uses server-side policy and resource context.
- Object and function permissions are explicit for learner, caregiver, teacher, school leader,
  curriculum reviewer, administrator, service, anonymous generation, and future support roles.
- Organization/household membership never implies unrestricted access to every child or artifact.
- Sensitive actions require purpose, audit evidence, and re-authentication where risk demands it.
- Sessions, recovery, invitations, impersonation/support access, revocation, and role changes get
  dedicated threat models and adversarial tests before real identity is implemented.

## Data Protection and Child Safeguarding

Before any real-data pilot, create and review a data inventory and record for every field:
purpose, data subject, sensitivity, source, lawful basis, consent/authority where relevant,
visibility, processors, residency/transfer, retention, correction, export, deletion, backup,
aggregation, and incident impact.

Privacy controls include minimization, field-level access, secure defaults, purpose limitation,
short retention, safe deletion, export/correction, aggregation thresholds, PII-safe logs,
non-identifying analytics, encryption in transit/at rest where data exists, protected backups,
restoration tests, and processor review. Consent is not used as a universal substitute for
necessity, fairness, safeguarding, or another required lawful basis.

Free assessment generation should require no personal data. Age-appropriate experiences must
avoid manipulative design, public profiles, unsafe messaging, location exposure, and unmoderated
sharing. Real learner response capture remains blocked until legal, safeguarding, security, and
field-research protocols are approved.

## Web and API Controls

The API uses strict schemas and rejects unknown or over-limit input. Resources use stable opaque
identifiers plus authorization, never identifiers alone. Queries and templates are parameterized;
rendering treats content as data. Uploads, when a validated use case exists, are isolated,
size/type/content validated, malware scanned, renamed, stored outside executable paths, and served
with safe headers.

The web boundary requires restrictive CORS and browser security headers, CSRF protection where
cookies are used, safe cookies/session storage, output encoding, content security policy,
anti-framing, safe MIME handling, non-sensitive caches, generic external errors, correlation IDs,
and detailed protected operator evidence. Rate/concurrency/cost limits apply per capability and
must not leak whether a private object exists.

## AI and Generated-Content Security

Local Ollama is the active optional AI runtime and receives the least context and capability
possible. No external-model API key is required in the current phase. Curriculum excerpts,
retrieved documents, user instructions, and model output remain untrusted data. Provider adapters
enforce allowlisted inputs/outputs, time and token budgets, schema validation, content boundaries,
and no tool access unless a separately threat-modeled use case requires it.

Never send secrets, real learner PII, private chain-of-thought, unrestricted proprietary corpora,
or answer keys outside their authorized context. Model output cannot directly construct SQL,
HTML, shell commands, authorization decisions, file paths, or official-looking artifacts. Prompt
injection, disclosure, poisoning, insecure output handling, excessive agency, denial of wallet,
and model/provider substitution require adversarial tests.

## Curriculum and Assessment Supply Chain

Official sources, extracted files, enriched graphs, item banks, prompts, review decisions, and
release manifests require provenance and integrity checks. Record hashes, source authority,
acquisition date, license/permission state, extractor/tool version, reviewer, maturity, and
compatible platform version. Unknown, modified, unsigned where signatures are required, stale, or
unreviewed artifacts fail closed.

Generated assessment papers must not copy protected questions without rights, imitate authority
branding, claim endorsement, or leak answer material. Artifact separation, access control,
watermark/notices, audit events, and misuse limits must be tested.

## Development and Software Supply Chain

Docker is the runtime and the security boundary must be intentional:

- deterministic lockfiles and reviewed dependency updates;
- minimal, scanned base/runtime images and non-root execution where practical;
- read-only and least-privilege mounts, loopback-bound local ports, separated services, resource
  ceilings, and no host secret inheritance unless explicitly required;
- secret, PII, proprietary-data, SAST, dependency, license, container, IaC, and DAST scans;
- an SBOM and verifiable build provenance for future release candidates;
- protected source and artifact history, reviewed changes, strict hooks, and no swallowed checks.

No critical/high known vulnerability enters a milestone merge. Any lower-severity acceptance must
name the owner, scope, compensating controls, evidence, expiry, and remediation task. A scanner
failure is a failed gate unless a recognized, bounded infrastructure retry succeeds.

## Verification Evidence

Security tests include unit policy tests, full role/action/resource matrices, integration tests,
API contract/adversarial tests, malformed and boundary inputs, property/fuzz tests, browser
security tests, dependency/container/IaC scans, DAST against the local service, backup/restore and
deletion tests, logging redaction tests, artifact-integrity tests, AI red-team fixtures, and
external penetration testing before real child data or deployment.

One hundred percent line and branch coverage remains mandatory but is insufficient: each control
needs a meaningful assertion, negative tests, and abuse cases. Skips, empty scans, missing inputs,
and zero-target validation fail the gate.

## Incident and Vulnerability Readiness

Before real data or deployment, define secure vulnerability reporting, triage and remediation
SLAs, contact and decision roles, detection and alerting, containment, credential/key rotation,
forensic evidence preservation, communication, regulator/data-subject notification review,
recovery, restoration validation, and blameless root-cause follow-up. Exercises must prove the
process rather than merely documenting it.

## Current-Phase Actions

The immediate local foundation should:

- expose only loopback-bound ports;
- mount proprietary curriculum data read-only and keep it out of image layers;
- remove unused secrets and external-service configuration from the default web profile;
- provide liveness and fail-closed readiness without sensitive detail;
- commit a deterministic lockfile;
- build and test both development and production stages;
- establish strict Docker-backed security/quality gates;
- use synthetic fixtures and local mock identity only;
- create the first data-flow/threat model before the first user workflow.

Every security discovery creates a task. This model is reviewed and expanded at each milestone.
