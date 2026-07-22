# GapSense Working List

**Canonical project execution list.** Last reconciled: 2026-07-22.

This list is deliberately never finished. A completed task stays as evidence; every
research finding, validation failure, user observation, curriculum gap, design debt
item, and new opportunity is added before work begins.

## How to Use This List

- `[ ]` ready or pending
- `[~]` actively being worked; keep the number of active milestones small
- `[x]` complete, with evidence linked in the task or commit
- `[!]` blocked, with the blocking condition and next check recorded
- `[?]` needs research or a product decision before implementation

Rules:

1. Add scope here before starting a new slice.
2. Work on a focused local branch created from an up-to-date local `main`.
3. Do not mark a task complete because a document says it is complete.
4. Completion requires the applicable automated checks, artifacts, and review evidence.
5. Every discovered follow-up is appended to this file; the list itself never closes.
6. Commit completed milestones and merge them into local `main` only after the local
   CI-equivalent pipeline is green.
7. Do not push branches, tags, or `main` to a remote until deployment and remote
   collaboration are explicitly authorized.

## Current Product Direction

- [~] Build a local-first, web-first GapSense experience for Ghana and Uganda.
- [ ] Make free, curriculum-aligned assessment generation a public web entry product for
  learners, parents/caregivers, teachers, school leaders, and other legitimate users.
- [ ] Make the web experience excellent on mobile, tablet, and desktop, including
  low-bandwidth and intermittent-connectivity conditions.
- [ ] Support teachers first while researching the needs of learners, parents,
  curriculum specialists, school leaders, and education-system partners.
- [ ] Complete official curriculum coverage for all in-scope subjects and levels in
  Ghana and Uganda.
- [~] Maintain 100% line and branch coverage for application-owned executable code.
- [ ] Use local mock services and local authentication until deployment is approved.
- [~] Use local Ollama as the active AI runtime behind a provider abstraction; never make a local
  model a hidden requirement for deterministic tests.
- [~] Keep WhatsApp delivery and production deployment on hold.

## Milestone 0 - Governance and Honest Baseline

- [x] Add this canonical, ever-growing working list.
- [x] Add `docs/WAYS_OF_WORKING.md`.
- [x] Add `docs/PROJECT_CHARTER.md` for the web-first decision.
- [x] Add an evidence-based curriculum coverage audit.
- [x] Add an initial market and user research brief based on primary sources.
- [x] Add a documentation index.
- [ ] Link active governance documents from both repository entry points.
- [x] Mark the old seven-day WhatsApp implementation plan as historical and superseded.
- [ ] Normalize or archive the six explicitly ignored historical Markdown documents, then
  remove their narrow lint exclusions; active governance and product docs have no exclusions.
- [ ] Reconcile stale and contradictory completion statements throughout both repos.
- [ ] Define owners or accountable reviewers for curriculum, pedagogy, UX, safety,
  engineering, and country validation.
- [ ] Create a decision log for unresolved product questions.
- [x] Create an append-only discovery section at the bottom of this file and review it
  at the start and end of every milestone.

### Milestone evidence

- [x] Governance documents reviewed for internal consistency.
- [x] New governance Markdown passes containerized linting.
- [x] Internal governance-document links validated in Docker.
- [x] Branch committed and merged locally to `main` with no remote push.

## Milestone 1 - Reproducible Local Runtime

- [x] Repair Docker Compose so the web service starts successfully.
- [ ] Remove references to nonexistent `gapsense.main`, worker, data mount, and
  LocalStack paths, or implement the intended components.
- [x] Add and commit a deterministic dependency lockfile.
- [ ] Standardize supported Python and tool versions across Docker, Poetry,
  pre-commit, and documentation.
- [x] Make locked Docker dependency installation resilient to transient package-index
  failures with bounded official retries and BuildKit caches.
- [x] Remove the unused `aiobotocore`/`botocore` cloud runtime dependency while
  WhatsApp/AWS delivery is on hold; reintroduce an adapter dependency only for a tested use case.
- [x] Remove the unused vulnerable `python-jose`/`ecdsa` stack until a threat-modeled,
  tested authentication adapter selects a maintained cryptographic implementation.
- [x] Upgrade FastAPI/Starlette, multipart parsing, and the pytest stack to audited
  compatible releases; accept no vulnerability allowlists for this baseline.
- [x] Align Poetry and pre-commit on a compatible virtualenv release; the first strict gate
  correctly exposed the inherited Poetry 1.8.2 / virtualenv 21 conflict.
- [x] Add a single containerized `validate` command.
- [x] Add local health and readiness endpoints.
- [ ] Add deterministic seed/demo data that contains no real personal information.
- [ ] Add local mock authentication with teacher, curriculum-reviewer, and admin roles.
- [ ] Add local object/media storage abstraction only when a web use case needs it.
- [ ] Add Ollama discovery and health checks without coupling application startup to it.
- [x] Remove the active Anthropic SDK, API-key configuration, and infrastructure secret path;
  retain no external-model credential requirement in local web development.
- [ ] Add a deterministic fake AI provider for tests and demos.
- [x] Confirm Windows Docker Desktop is the supported development path.
- [x] Make every Docker-backed Git hook safe from Git Bash/MSYS container-path
  rewriting on Windows and verify it through the real hook entry point.
- [x] Enforce LF checkout for container-executed scripts and parsed configuration so
  Windows Git settings cannot corrupt the Linux runtime contract.

## Milestone 2 - CI-Equivalent Quality Gate

- [x] Replace the current permissive pre-commit configuration with a strict,
  container-backed configuration that matches the CI-equivalent pipeline.
- [x] Remove host-specific Python 3.9 and macOS Poetry paths from hooks.
- [x] Remove every `|| echo`, ignored failure, or best-effort critical check.
- [x] Remove documentation that presents `--no-verify` as an accepted workflow.
- [x] Install commit-msg, pre-commit, and pre-push hooks through a reproducible setup command.
- [x] Enforce conventional/semantic commit messages including the task or milestone.
- [ ] Block secrets, credentials, private keys, proprietary-data leaks, PII, oversized
  generated files, merge markers, invalid JSON/YAML/TOML, and debug statements.
- [x] Enforce 100% line coverage.
- [x] Enforce 100% branch coverage.
- [ ] Require explicit, reviewed justification for any excluded non-executable line.
- [x] Add Ruff formatting and lint checks.
- [x] Add strict MyPy checks.
- [x] Add unit tests.
- [x] Add integration tests against containerized PostgreSQL.
- [x] Isolate integration tests from developer data and one another with a
  dedicated disposable database plus rollback-safe outer transactions.
- [ ] Add curriculum schema and graph contract tests.
- [ ] Add API contract tests.
- [ ] Add browser end-to-end tests.
- [ ] Add accessibility tests targeting WCAG 2.2 AA.
- [ ] Add keyboard-only and screen-reader workflow checks.
- [ ] Add visual regression tests for supported viewport and theme combinations.
- [ ] Add responsive-layout tests for low-cost Android-sized screens through desktop.
- [ ] Add performance budgets and Lighthouse-style checks.
- [ ] Add security, dependency, secret, and PII scans.
- [x] Keep network-backed dependency audits strict while using bounded socket
  timeouts and only ephemeral writable cache paths in the read-only container.
- [x] Add migration upgrade/downgrade tests.
- [x] Reconcile inherited ORM/server-default and severity-index drift through a
  forward migration without rewriting migration history.
- [x] Break the Alembic table-sort cycle for the learner's latest gap-profile
  foreign key while preserving the database constraint.
- [x] Run every migration upgrade, downgrade, rebuild, and drift check against a
  fresh dedicated local database in the strict gate.
- [x] Repair the unreleased initial migration's unnamed foreign-key downgrade
  operations using names verified from PostgreSQL; never rewrite a deployed migration.
- [x] Scan every tracked and unignored commit candidate for secrets in Docker;
  review each false positive explicitly at the source.
- [ ] Add property-based tests for graph invariants and critical domain rules.
- [ ] Add mutation testing for diagnostic and safety-critical logic.
- [ ] Make every validator fail closed when inputs are absent or zero records are tested.
- [x] Pin the validation container's import path to the candidate workspace so
  tests and coverage cannot accidentally measure the image's installed source tree.
- [~] Run the complete gate in Docker before every milestone commit and local merge.
- [x] Add local CI scripts now; add hosted CI only when remote work is authorized.

## Clean Engineering and Mandatory TDD

- [ ] Adopt red-green-refactor as the required implementation loop for every behavior change.
- [ ] Require a failing test that expresses the intended behavior before production code.
- [ ] Require a regression test before every bug fix.
- [ ] Keep domain rules independent of FastAPI, SQLAlchemy, Ollama, browser frameworks,
  cloud services, and other adapters.
- [ ] Adopt clean/hexagonal architecture: domain core, application use cases, ports, and adapters.
- [ ] Use domain-driven boundaries for curriculum, diagnostics, learners, interventions,
  identity/access, and research/validation.
- [ ] Use SOLID principles and dependency inversion at external boundaries.
- [ ] Prefer small pure functions and immutable value objects for scoring and graph logic.
- [ ] Keep aggregate invariants inside domain behavior instead of route handlers or ORM events.
- [ ] Separate commands from queries when it materially improves clarity and testing.
- [ ] Use repository and provider interfaces only at real boundaries; avoid speculative abstractions.
- [ ] Apply YAGNI to infrastructure while preserving explicit extension ports for auth, AI,
  storage, and delivery channels.
- [ ] Refactor only while the complete test suite remains green.
- [ ] Ban untracked TODOs in code; every debt marker must link to an item in this file.
- [ ] Establish complexity, duplication, file-size, dependency-direction, and architecture tests.
- [ ] Require public API documentation and meaningful domain naming.
- [ ] Require peer-style self-review against the full diff before every milestone commit.

## Measured Optimization and Product Smoothness

- [ ] Define user-journey friction metrics for setup, curriculum discovery, diagnosis,
  review, intervention planning, and reassessment.
- [ ] Establish frontend responsiveness, API latency, database query, bundle-size,
  memory, and local-model performance budgets.
- [ ] Profile before optimizing and retain before/after evidence.
- [ ] Prefer removing work, improving algorithms, batching, caching, and data-shape fixes
  before adding dependencies or infrastructure.
- [ ] Verify output equivalence for every performance optimization.
- [ ] Test perceived performance: progressive disclosure, skeletons, optimistic behavior
  only where safe, resumability, and useful partial results.
- [ ] Track cold-start and low-end-device behavior.
- [ ] Track Docker build time and developer feedback-loop time.
- [ ] Track cost-per-diagnostic and cost-per-active-organization for commercial viability.
- [ ] Remove unused code, stale paths, redundant documents, and accidental complexity only
  after provenance and supersession are preserved.
- [ ] Re-run accessibility, correctness, and security suites after optimization; speed never
  overrides safety or evidence.

## Curriculum Programme - Shared Foundations

- [ ] Define one canonical versioned curriculum data schema.
- [ ] Define country, authority, level, phase, grade, subject, language, and version IDs.
- [ ] Define normalization rules for nodes, indicators, prerequisites, misconceptions,
  cascade paths, assessment items, citations, and cultural context.
- [ ] Define maturity states: `draft`, `extracted`, `structurally_validated`,
  `domain_reviewed`, `culturally_reviewed`, `pilot_validated`, and `released`.
- [ ] Ban the term `production-ready` before domain, cultural, and pilot validation.
- [ ] Build JSON Schema validation for every artifact family.
- [ ] Validate actual counts instead of trusting metadata counts.
- [ ] Add missing-node, duplicate-code, dangling-edge, and cycle detection.
- [ ] Add prerequisite direction and grade-progression checks.
- [ ] Add source provenance down to document, page/section, and extracted passage.
- [ ] Add a reviewer ledger and review timestamp to released datasets.
- [ ] Add cross-repository loader contract tests.
- [ ] Add a curriculum release manifest pinning compatible data and prompt versions.
- [ ] Research licensing and permitted use for every official source document.
- [ ] Define a process for curriculum amendments and superseded official versions.
- [ ] Define coverage metrics for breadth, diagnostic depth, source fidelity, and review.

## Ghana Curriculum Completion Programme

- [ ] Build the authoritative Ghana level/subject inventory from NaCCA and relevant
  TVET/tertiary authorities; do not infer the menu from the current folders.
- [ ] Map Key Phase 1: Kindergarten 1-2 learning areas.
- [ ] Map Key Phases 2-3: Primary B1-B6 subjects and integrated changes from 2024/25.
- [ ] Map Key Phase 4: JHS B7-B9 Common Core Programme subjects.
- [ ] Map Key Phase 5: SHS, SHTS, and STEM core/elective pathways and combinations.
- [ ] Research and scope Ghana TVET and tertiary curricula where national standards exist.
- [ ] Reconcile Primary Mathematics graph, populated-node file, README, and metadata;
  current counts conflict.
- [ ] Reconcile Primary English actual node count with its stated count.
- [ ] Reconcile JHS Mathematics README counts with the data files.
- [ ] Reconcile SHS General Science README with its populated dataset.
- [ ] Acquire and extract the currently missing JHS English curriculum from the current
  official NaCCA source.
- [ ] Separate JHS and SHS datasets currently grouped under `secondary`.
- [ ] Create one child task per official Ghana subject and phase after inventory review.
- [ ] Complete structure, evidence, diagnostics, cultural review, and pilot validation
  for every Ghana curriculum child task.
- [ ] Recruit Ghanaian teachers and curriculum specialists for domain review.
- [ ] Recruit language reviewers for Ghanaian-language experiences.

## Uganda Curriculum Completion Programme

- [ ] Build the authoritative Uganda level/subject inventory from NCDC, MoES, and
  relevant TVET/tertiary authorities.
- [ ] Map Pre-primary learning areas.
- [ ] Complete P1-P3 thematic learning areas, not only Mathematics.
- [ ] Validate the current uncommitted P1-P3 Mathematics extraction before merging it.
- [ ] Complete P4 transition-phase subjects and learning outcomes.
- [ ] Complete P5-P7 subject-based curriculum coverage.
- [ ] Complete Lower Secondary S1-S4 compulsory and elective curriculum coverage.
- [ ] Complete aligned A-Level S5-S6 curriculum coverage.
- [ ] Research and scope Uganda TVET and tertiary curricula where national standards exist.
- [ ] Create one child task per official Uganda subject and phase after inventory review.
- [ ] Complete structure, evidence, diagnostics, cultural review, and pilot validation
  for every Uganda curriculum child task.
- [ ] Recruit Ugandan teachers and NCDC-aligned curriculum specialists for domain review.
- [ ] Recruit language reviewers for Luganda and additional regional languages.
- [ ] Explicitly design for the P3 local-language to P4 English transition.

## Web Product Discovery and UX

- [ ] Research and prioritize user groups in Ghana and Uganda.
- [ ] Interview or observe teachers across urban, peri-urban, rural, public, and private
  contexts before freezing primary workflows.
- [ ] Research learner needs by age, literacy, language, ability, and device access.
- [ ] Research school-leader and curriculum-reviewer workflows.
- [ ] Define jobs-to-be-done and measurable outcomes for each supported role.
- [ ] Define the minimum lovable web product through user evidence.
- [ ] Create information architecture for country, level, subject, class, learner,
  diagnostic, intervention, and progress contexts.
- [ ] Create a reusable, accessible design system.
- [ ] Establish responsive typography, spacing, color, motion, iconography, and content rules.
- [ ] Meet WCAG 2.2 AA and test beyond automated accessibility tooling.
- [ ] Design low-bandwidth, offline-tolerant, and resumable workflows.
- [ ] Design clear empty, loading, partial-data, error, and recovery states.
- [ ] Avoid deficit language in every learner-facing and teacher-facing surface.
- [ ] Validate terminology with Ghanaian and Ugandan educators.
- [ ] Support localization without encoding country stereotypes.
- [ ] Conduct moderated usability tests at every major workflow milestone.
- [ ] Track UX findings and design debt in this file.

## Web Product Engineering

- [?] Select the web frontend stack through an ADR and a tested prototype.
- [ ] Define the browser/API boundary and typed API contract.
- [ ] Implement local mock authentication and role switching.
- [ ] Implement country, phase, subject, and curriculum-version selection.
- [ ] Implement a curriculum explorer with prerequisite visualization.
- [ ] Implement teacher class and learner setup using synthetic/local data.
- [ ] Implement web-based diagnostic-session creation and continuation.
- [ ] Implement response capture for text and structured answers first.
- [ ] Add image/audio evidence only after privacy and UX research.
- [ ] Implement explainable root-gap and confidence presentation.
- [ ] Implement intervention recommendations with source and rationale visibility.
- [ ] Implement progress tracking and reassessment.
- [ ] Implement curriculum-review and data-quality workflows.
- [ ] Implement local data export, import, and deletion.
- [ ] Implement audit history for diagnostic and curriculum decisions.
- [ ] Add offline/PWA support if validated by user research.
- [ ] Add Ollama-backed optional analysis behind the AI provider interface.
- [ ] Ensure the web product remains usable when AI is unavailable.

## Free Assessment Generation Programme

- [x] Capture the initial assessment-generation product brief and primary-source research.
- [ ] Validate the jobs-to-be-done separately with Ghanaian and Ugandan learners,
  parents/caregivers, teachers, tutors, school leaders, and curriculum specialists.
- [ ] Use the age- and curriculum-appropriate term (`activity`, `practice`, `quiz`, `test`,
  `assessment`, or `exam`) instead of presenting every generated artifact as an exam.
- [ ] Define the anonymous public flow: role or use case, country, curriculum version,
  education level, class/year, subject, scope, purpose, language, duration, total marks,
  question formats, cognitive/competency balance, and accessibility/print needs.
- [ ] Allow generation without collecting learner names, phone numbers, school identities,
  or other personal data.
- [ ] Generate an editable learner paper or activity, separate answer/marking guide,
  explanations, rubric where appropriate, and curriculum-alignment blueprint.
- [ ] Include official learning-outcome identifiers, source provenance, curriculum version,
  generation method, review state, and generation timestamp in every artifact.
- [ ] Model country- and level-specific assessment policies rather than using one universal
  exam template for Ghana and Uganda.
- [ ] Support observation checklists, oral prompts, practical activities, projects, and
  continuous assessment in phases where a written examination is inappropriate.
- [ ] Support formative, diagnostic, summative, revision, homework, and mock-exam purposes
  only where the selected curriculum and level permit them.
- [ ] Create a deterministic assessment blueprint engine before adding generative AI.
- [ ] Create a reviewed item/template bank with difficulty, cognitive demand, language,
  estimated time, marks, prerequisites, misconceptions, and accessibility metadata.
- [ ] Put Ollama and future external models behind an optional item-drafting port; the
  product must remain useful when no model is available.
- [ ] Treat every AI-authored item as a draft until deterministic checks and the required
  human review state pass.
- [ ] Validate answer correctness, solvability, ambiguity, distractor quality, duplicate
  items, leakage between paper and key, marks/timing totals, reading level, units, bias,
  cultural relevance, and curriculum coverage.
- [ ] Add subject-specific validators for mathematics notation, sciences, languages,
  humanities, practical/technical subjects, arts, and special educational needs.
- [ ] Add seeded/property tests proving identical inputs and seed produce reproducible
  blueprints and that constrained variants remain equivalent in coverage and difficulty.
- [ ] Add golden educator-reviewed assessment fixtures per country, phase, and subject.
- [ ] Add browser preview, edit, regenerate-one-item, print, accessible HTML, and PDF export.
- [ ] Design monochrome, low-ink, A4, and phone-friendly outputs for constrained settings.
- [ ] Add a clear `practice material — not an official national examination` notice and
  never imply endorsement by NaCCA, WAEC, NCDC, UNEB, or another authority.
- [ ] Research source, curriculum, assessment-item, past-paper, logo, and output licensing;
  generate original items and do not copy protected examination questions without rights.
- [ ] Add misuse controls for answer-key exposure, impersonation of official papers,
  high-stakes cheating, automated scraping, and abusive compute consumption.
- [ ] Keep the core assessment generator genuinely free; test paid organization value in
  shared libraries, moderation, analytics, bulk variants, workflow, integrations, support,
  audit history, and APIs rather than withholding basic learner dignity or correctness.
- [ ] Define privacy-safe product analytics for generation completion, time saved, edit rate,
  print/export rate, regeneration reasons, validation failures, and voluntary usefulness.
- [ ] Measure curriculum-alignment precision, educator acceptance without edits, answer-key
  correctness, accessibility, latency, cost per generation, and repeat use by role.
- [ ] Do not release a country/level/subject combination until its underlying curriculum
  slice and assessment policy are at the required review maturity.

## Diagnostic and AI Quality

- [ ] Implement deterministic graph traversal before AI orchestration.
- [ ] Define ground-truth diagnostic fixtures with educators.
- [ ] Version every prompt and output schema.
- [ ] Record model, prompt, curriculum, parameters, latency, and token/cost metadata.
- [ ] Never store or expose private chain-of-thought; store concise decision rationale.
- [ ] Add hallucination and unsupported-citation checks.
- [ ] Add prompt-injection and adversarial input tests.
- [ ] Compare supported Ollama models on quality, latency, memory, and licensing.
- [ ] Add deterministic mocked model responses for the full test suite.
- [ ] Add evaluation sets across countries, subjects, levels, languages, and error types.
- [ ] Require domain review before AI-generated diagnostic items are released.
- [ ] Define abstention and human-review paths for low-confidence cases.

## Brand and Country Experience

- [ ] Research brand perception with Ghanaian and Ugandan teachers and families.
- [ ] Define one GapSense master brand without flattening country differences.
- [ ] Define country, phase, and subject navigation labels from official terminology.
- [ ] Create an accessible color system that does not encode ability or deficit.
- [ ] Create illustration and photography principles with consent and dignity rules.
- [ ] Create voice-and-tone guidance for teachers, learners, reviewers, and parents.
- [ ] Validate names, symbols, colors, examples, and imagery locally before release.
- [ ] Design subject and level identities as navigation aids, not stereotypes.
- [ ] Create a complete web asset kit only after the brand direction is validated.

## Market, Evidence, and Partnership Research

- [x] Create an initial primary-source market and context brief.
- [ ] Map existing digital curriculum, diagnostic, assessment, and teacher-support products.
- [ ] Separate competitors from potential partners and public infrastructure.
- [ ] Research procurement and adoption paths for public, private, NGO, and household use.
- [ ] Research device, connectivity, power, data-cost, and teacher-readiness constraints.
- [ ] Validate willingness to adopt before modeling willingness to pay.
- [ ] Interview at least five educators per country before fixing the MVP scope.
- [ ] Establish relationships with curriculum authorities and teacher organizations.
- [ ] Define an evidence plan for construct, predictive, cultural, and usability validity.
- [ ] Define ethical research, consent, child-safeguarding, and data-governance protocols.
- [ ] Keep market claims sourced, dated, and clearly separated from hypotheses.

## Commercial Model and Profitable Growth

- [ ] Identify the economic buyer separately from the daily user in each segment.
- [ ] Test school subscription, school-group licensing, NGO/programme licensing,
  government contracts, curriculum-data/API licensing, and research/evaluation services.
- [ ] Test whether a free teacher entry product creates qualified institutional demand.
- [ ] Quantify the value of saved diagnostic time, better intervention targeting, improved
  progression visibility, and curriculum intelligence for each buyer.
- [ ] Research procurement cycles, budgets, decision makers, and proof requirements in both countries.
- [ ] Model willingness to pay only after willingness to adopt and value are observed.
- [ ] Build cost-to-serve models for local-only, hosted, AI-assisted, offline, and support-heavy use.
- [ ] Track gross-margin sensitivity to inference, storage, support, onboarding, and validation costs.
- [ ] Define ethical product analytics that measure activation, retained use, diagnostic completion,
  intervention follow-through, and outcome evidence without exploiting learner data.
- [ ] Define replaceable entitlement, feature-flag, usage-metering, and billing ports; use local fakes now.
- [ ] Keep core diagnostic correctness independent of payment status.
- [ ] Define packaging by demonstrated buyer value, not arbitrary feature withholding.
- [ ] Research data and curriculum licensing constraints before monetizing any derived dataset.
- [ ] Define IP strategy for schemas, graph methodology, enriched curriculum data, evaluations,
  prompts, brand, and accumulated validation evidence.
- [ ] Model country-by-country customer acquisition, onboarding, training, support, and retention.
- [ ] Define leading commercial metrics and explicit stop/pivot criteria for unprofitable segments.
- [ ] Create a dated business-model document after the first user and buyer interviews.
- [ ] Keep speculative revenue and TAM figures out of investor or partner materials until sourced.

## Privacy, Safety, and Local Data

- [x] Add the initial secure-by-design and privacy engineering model.
- [x] Prevent parent hard deletion from cascading into silent learner-record deletion and
  replace the skipped regression with enforced database-integrity evidence.
- [ ] Maintain a versioned asset inventory, data-flow diagram, trust-boundary map, threat
  register, abuse-case catalog, and control-to-evidence matrix for every major workflow.
- [ ] Use OWASP ASVS 5.0 Level 2 as the minimum web/API verification target before accepting
  real user data; select additional Level 3 controls through risk analysis.
- [ ] Map the secure development lifecycle to NIST SSDF 1.1 and track the 1.2 draft without
  representing draft guidance as final.
- [ ] Track OWASP Top 10:2025, API Security Top 10:2023, and GenAI/LLM Top 10:2025 risks in
  threat models, tests, and the security evidence matrix.
- [ ] Perform threat modeling at design time and whenever data flows, trust boundaries,
  dependencies, authorization rules, AI providers, or deployment assumptions change.
- [ ] Add explicit security acceptance criteria and abuse cases to every product slice.
- [ ] Make authorization server-side, deny-by-default, least-privilege, object-scoped, and
  independently tested for every role/action/resource combination.
- [ ] Keep local mock identity clearly separated from authorization policy and structurally
  impossible to enable in a production configuration.
- [ ] Test broken-object-level, broken-function-level, horizontal, vertical, confused-deputy,
  enumeration, replay, session fixation, and privilege-escalation attacks.
- [ ] Define secure session, re-authentication, recovery, logout, timeout, and device rules
  before implementing non-mock identity.
- [ ] Define strict request/response schemas, size/depth/count limits, canonicalization rules,
  safe error responses, and fail-closed exceptional-condition behavior.
- [ ] Add tests and controls for injection, XSS, CSRF, SSRF, unsafe redirects, path traversal,
  insecure deserialization, mass assignment, file upload, content sniffing, and cache leakage.
- [ ] Add restrictive CORS, CSP, framing, MIME, referrer, permissions, transport, and cache
  headers appropriate to each web surface before browser feature work is called complete.
- [ ] Add rate, concurrency, cost, export, and generation quotas at application boundaries;
  controls must resist abuse without silently excluding legitimate low-resource users.
- [ ] Bind local service ports to loopback by default and document every exposed port.
- [ ] Run containers as non-root where practical, minimize capabilities and writable mounts,
  separate networks, add resource ceilings, and scan both development and production images.
- [ ] Pin direct and transitive dependencies through a committed lockfile; verify hashes,
  provenance, licenses, known vulnerabilities, typosquatting risk, and malicious releases.
- [ ] Produce and retain an SBOM for release candidates; define signed build provenance and
  artifact verification before any deployment hold is lifted.
- [ ] Pin or deliberately update base images, scan OS packages, and test the production image
  separately from the development image.
- [x] Build and smoke-test the production image locally as a non-root, read-only container
  with no-new-privileges, read-only curriculum data, loopback binding, and no deployment.
- [ ] Run secret, credential, private-key, high-entropy-token, PII, proprietary-data, SAST,
  dependency, container, IaC, and DAST checks in the strict Docker gate.
- [ ] Block commits and milestone merges on unresolved critical/high vulnerabilities; require
  a named, dated, scoped, expiring risk decision for any lower-severity acceptance.
- [ ] Complete Ghana and Uganda data-protection requirements research.
- [ ] Obtain qualified Ghanaian and Ugandan legal/privacy review before collecting real data;
  engineering research is not legal advice.
- [ ] Perform child-safety and privacy threat modeling.
- [ ] Minimize learner data and use synthetic data by default locally.
- [ ] Encrypt sensitive local data where retained.
- [ ] Classify data by sensitivity and define purpose, lawful basis, fields, access, residency,
  retention, deletion, backup, export, and processor rules before collection.
- [ ] Add consent, retention, export, correction, and deletion workflows.
- [ ] Prevent PII and sensitive learner information from entering logs or model prompts.
- [ ] Add role-based access tests.
- [ ] Add secure defaults and visible privacy explanations to the web UX.
- [ ] Use structured allowlisted security logging with correlation IDs and tamper-evident audit
  events; never log secrets, answer keys for learner sessions, or sensitive free text.
- [ ] Separate operational metrics, product analytics, audit evidence, and research datasets.
- [ ] Add curriculum/artifact hashes and signature verification so poisoned or substituted
  source data cannot silently enter generation or diagnostic workflows.
- [ ] Treat curriculum text, user input, generated items, and retrieved documents as untrusted
  data at every AI boundary; isolate instructions and constrain tool/output capabilities.
- [ ] Test prompt injection, sensitive-information disclosure, poisoning, excessive agency,
  insecure output handling, unbounded consumption, and model/provider substitution.
- [ ] Never send child/learner PII, secrets, proprietary corpora, or private chain-of-thought
  to Ollama or an external model; make provider data policy visible and enforceable.
- [ ] Back up only intentionally retained data, encrypt backups, test restoration and deletion,
  and prevent test/demo data from contaminating real environments.
- [ ] Define incident response before any real user data is accepted.
- [ ] Define vulnerability intake, triage, remediation SLAs, disclosure, notification,
  containment, recovery, evidence preservation, and post-incident learning.
- [ ] Complete independent penetration testing and remediate findings before accepting real
  child data or lifting the production deployment hold.
- [ ] Review the security model and evidence at every milestone; security-critical follow-ups
  enter this never-finished list immediately.

## Explicit Holds

- [!] WhatsApp channel implementation is on hold. Resume only by an explicit product
  decision after the web experience is validated.
- [!] Production deployment is on hold. Do not deploy to Firebase, AWS, or another host.
- [!] Remote Git pushes are on hold. Work in local branches, commit milestones, and merge
  into local `main` only.
- [ ] Before lifting deployment hold, write an ADR comparing hosting, API, database,
  authentication, observability, privacy, cost, regional availability, and offline needs.
- [ ] Preserve channel-neutral domain boundaries so WhatsApp can be added later without
  rewriting diagnostic logic.

## Discovery Inbox - Append, Triage, Never Delete

Add new findings here immediately. During milestone reconciliation, move actionable items
to the appropriate section while retaining a short trace or link.

- [ ] Investigate why the tracked curriculum consistency script reports success after all
  input loads fail; replace it with a fail-closed validator.
- [ ] Decide whether Ghana and Uganda tertiary coverage belongs in the same product or a
  later product family after authoritative curriculum and user research.
- [ ] Determine which country/level/subject combination gives the fastest valid web pilot
  without weakening the all-curricula programme.
- [ ] Revisit every old count and completion claim using machine-derived coverage reports.
- [ ] Investigate intermittent Docker Desktop DNS failure resolving `auth.docker.io`; do not
  replace the Docker evidence path with host dependencies.
- [ ] Determine where Ghana and Uganda require activities, continuous assessment, projects,
  or competency tasks instead of written examinations, and encode that policy by phase.
- [ ] Request or obtain legal guidance on lawful use of official curricula, public sample
  items, past papers, authority names, and generated assessment artifacts.
- [ ] Test whether free assessment generation is the strongest acquisition loop into paid
  school moderation, analytics, diagnostic, and curriculum-intelligence workflows.
- [ ] Add a Docker-native browser, accessibility, and visual-regression harness so local web
  journeys remain verifiable when an interactive browser automation runtime is unavailable.
