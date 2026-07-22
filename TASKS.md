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
- [ ] Make the web experience excellent on mobile, tablet, and desktop, including
  low-bandwidth and intermittent-connectivity conditions.
- [ ] Support teachers first while researching the needs of learners, parents,
  curriculum specialists, school leaders, and education-system partners.
- [ ] Complete official curriculum coverage for all in-scope subjects and levels in
  Ghana and Uganda.
- [ ] Maintain 100% line and branch coverage for application-owned executable code.
- [ ] Use local mock services and local authentication until deployment is approved.
- [ ] Support local Ollama models behind a provider abstraction; never make a local
  model a hidden requirement for deterministic tests.
- [ ] Keep WhatsApp delivery and production deployment on hold.

## Milestone 0 - Governance and Honest Baseline

- [x] Add this canonical, ever-growing working list.
- [x] Add `docs/WAYS_OF_WORKING.md`.
- [x] Add `docs/PROJECT_CHARTER.md` for the web-first decision.
- [x] Add an evidence-based curriculum coverage audit.
- [x] Add an initial market and user research brief based on primary sources.
- [x] Add a documentation index.
- [ ] Link active governance documents from both repository entry points.
- [ ] Mark the old seven-day WhatsApp implementation plan as historical and superseded.
- [ ] Reconcile stale and contradictory completion statements throughout both repos.
- [ ] Define owners or accountable reviewers for curriculum, pedagogy, UX, safety,
  engineering, and country validation.
- [ ] Create a decision log for unresolved product questions.
- [ ] Create an append-only discovery section at the bottom of this file and review it
  at the start and end of every milestone.

### Milestone evidence

- [x] Governance documents reviewed for internal consistency.
- [x] New governance Markdown passes containerized linting.
- [x] Internal governance-document links validated in Docker.
- [x] Branch committed and merged locally to `main` with no remote push.

## Milestone 1 - Reproducible Local Runtime

- [ ] Repair Docker Compose so the web service starts successfully.
- [ ] Remove references to nonexistent `gapsense.main`, worker, data mount, and
  LocalStack paths, or implement the intended components.
- [ ] Add and commit a deterministic dependency lockfile.
- [ ] Standardize supported Python and tool versions across Docker, Poetry,
  pre-commit, and documentation.
- [ ] Add a single containerized `validate` command.
- [ ] Add local health and readiness endpoints.
- [ ] Add deterministic seed/demo data that contains no real personal information.
- [ ] Add local mock authentication with teacher, curriculum-reviewer, and admin roles.
- [ ] Add local object/media storage abstraction only when a web use case needs it.
- [ ] Add Ollama discovery and health checks without coupling application startup to it.
- [ ] Add a deterministic fake AI provider for tests and demos.
- [ ] Confirm Windows Docker Desktop is the supported development path.

## Milestone 2 - CI-Equivalent Quality Gate

- [ ] Replace the current permissive pre-commit configuration with a strict,
  container-backed configuration that matches the CI-equivalent pipeline.
- [ ] Remove host-specific Python 3.9 and macOS Poetry paths from hooks.
- [ ] Remove every `|| echo`, ignored failure, or best-effort critical check.
- [ ] Remove documentation that presents `--no-verify` as an accepted workflow.
- [ ] Install commit-msg, pre-commit, and pre-push hooks through a reproducible setup command.
- [ ] Enforce conventional/semantic commit messages including the task or milestone.
- [ ] Block secrets, credentials, private keys, proprietary-data leaks, PII, oversized
  generated files, merge markers, invalid JSON/YAML/TOML, and debug statements.
- [ ] Enforce 100% line coverage.
- [ ] Enforce 100% branch coverage.
- [ ] Require explicit, reviewed justification for any excluded non-executable line.
- [ ] Add Ruff formatting and lint checks.
- [ ] Add strict MyPy checks.
- [ ] Add unit tests.
- [ ] Add integration tests against containerized PostgreSQL.
- [ ] Add curriculum schema and graph contract tests.
- [ ] Add API contract tests.
- [ ] Add browser end-to-end tests.
- [ ] Add accessibility tests targeting WCAG 2.2 AA.
- [ ] Add keyboard-only and screen-reader workflow checks.
- [ ] Add visual regression tests for supported viewport and theme combinations.
- [ ] Add responsive-layout tests for low-cost Android-sized screens through desktop.
- [ ] Add performance budgets and Lighthouse-style checks.
- [ ] Add security, dependency, secret, and PII scans.
- [ ] Add migration upgrade/downgrade tests.
- [ ] Add property-based tests for graph invariants and critical domain rules.
- [ ] Add mutation testing for diagnostic and safety-critical logic.
- [ ] Make every validator fail closed when inputs are absent or zero records are tested.
- [ ] Run the complete gate in Docker before every milestone commit and local merge.
- [ ] Add local CI scripts now; add hosted CI only when remote work is authorized.

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

- [ ] Complete Ghana and Uganda data-protection requirements research.
- [ ] Perform child-safety and privacy threat modeling.
- [ ] Minimize learner data and use synthetic data by default locally.
- [ ] Encrypt sensitive local data where retained.
- [ ] Add consent, retention, export, correction, and deletion workflows.
- [ ] Prevent PII and sensitive learner information from entering logs or model prompts.
- [ ] Add role-based access tests.
- [ ] Add secure defaults and visible privacy explanations to the web UX.
- [ ] Define incident response before any real user data is accepted.

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
