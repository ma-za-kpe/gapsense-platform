# Ways of Working

Date: 2026-07-22

GapSense is an education diagnostic and curriculum-intelligence project. Our operating
model is deliberately evidence-led because a false claim or false diagnosis can waste a
teacher's time, damage a learner's confidence, mislead a family, and undermine trust in
the entire product.

## Exercise Co-Founder Judgment

Everyone working on GapSense is responsible for the outcome, not merely the requested output.

- Verify claims against code, data, users, and current primary sources.
- Challenge stale plans, unsafe assumptions, contradictory counts, and premature certainty.
- Make reversible in-scope decisions when evidence is sufficient; record consequential
  decisions and alternatives in ADRs or product decision records.
- Surface product, pedagogy, UX, safety, privacy, technical, operational, and commercial
  risks early.
- Distinguish fact, inference, hypothesis, preference, and decision.
- Protect focus: ambitious possibilities enter `TASKS.md`; they do not silently expand the
  active milestone.
- Protect users over schedules and durable quality over theatrical progress.
- Do not defer an observed critical defect merely because it was outside an old plan.
- Do not conceal uncertainty. State what would resolve it and create the task.

Why: co-founder ownership means thinking across the whole system while preserving disciplined
execution.

## The Working List Is Never Finished

[`TASKS.md`](../TASKS.md) is the canonical execution list across the platform and data
repositories.

- Add scope before starting a work slice.
- Keep active work marked `[~]`.
- Mark work `[x]` only after its evidence exists.
- Record blockers as `[!]` with the condition that would unblock them.
- Add every newly discovered gap, test failure, research question, and opportunity.
- Never delete inconvenient work from the list; reconcile or supersede it explicitly.

Why: curriculum work and product development span long periods, many artifacts, and two
repositories. A living list prevents invisible work, stale claims, and abandoned partial
solutions.

## Focused Branches, Local Milestone Merges

Every milestone uses a focused local branch created from an up-to-date local `main`.

- Use descriptive branches such as `feat/web-curriculum-explorer`,
  `data/uganda-primary-english`, or `fix/curriculum-validator`.
- Keep one coherent purpose per branch.
- Commit only after the local CI-equivalent pipeline is green.
- Merge completed milestones into local `main`.
- Do not push any branch, tag, or `main` to a remote until explicitly authorized.
- Do not mix unrelated user-owned changes into a milestone commit.

Why: small branches make evidence review, rollback, and historical reasoning possible.
The current project contains very large commits and long-lived uncommitted work; this rule
reduces that risk.

## Docker Is the Runtime

Implementation, migrations, tests, validation, local services, and product smoke tests
run inside Docker.

- Do not treat host Python packages as evidence.
- Pin and commit dependency versions.
- Maintain one containerized command for the complete validation pipeline.
- Keep local services deterministic and seeded with synthetic data.
- Docker runtime failures are product work, not setup problems to work around silently.

Why: a result that depends on one co-founder's machine is not reproducible evidence.

## Web First, Local First

The current product channel is the web.

- Design for mobile, tablet, and desktop from the beginning.
- Treat low bandwidth, intermittent connectivity, low-cost devices, and shared devices as
  primary design conditions.
- Use local mock authentication and local synthetic data.
- Keep domain services independent of presentation channel.
- Keep WhatsApp implementation on hold.
- Keep production deployment on hold.

Why: the team needs to validate the diagnostic value and user experience before taking on
channel, infrastructure, compliance, and operational complexity.

## Official Sources Before Generated Content

Curriculum work begins with the current official authority and source document.

Each released curriculum claim must be traceable through:

```text
official source
  -> extracted passage
  -> normalized learning outcome
  -> prerequisite or diagnostic judgment
  -> reviewer and validation evidence
```

- Preserve source document identity, version, page or section, and extraction date.
- Separate verbatim source material from GapSense interpretation.
- Treat AI extraction as a proposal that must be verified.
- Record licensing and permitted-use findings.
- Do not fill a missing official curriculum with plausible generated material.

Why: fluency is not authority. A convincing but unsupported curriculum artifact is more
dangerous than an explicitly missing artifact.

## Depth First, Then Breadth

Retain the project's proven inside-out approach while making slices reviewable.

- Complete a coherent phase, grade band, subject strand, or product workflow deeply.
- Prefer foundational and high-cascade concepts first.
- Do not claim country or subject completion from a strategically selected subset.
- Create child tasks for the remaining breadth before moving on.
- Keep source extraction, normalization, enrichment, and validation distinguishable.

Why: depth creates useful diagnostic intelligence; explicit breadth accounting prevents
depth from being mistaken for complete national coverage.

## Maturity Is Explicit

Curriculum and prompt artifacts use these states:

```text
draft
-> extracted
-> structurally_validated
-> domain_reviewed
-> culturally_reviewed
-> pilot_validated
-> released
```

Automated structural success does not imply educational validity. “Complete” always names
the completed dimension. “Production-ready” is not used before domain, cultural, and pilot
validation.

Why: the existing repositories sometimes call work complete while simultaneously listing
expert and pilot validation as future work.

## Two Repositories, One Compatible Release

`gapsense-platform` contains application code and non-proprietary fixtures.
`gapsense-data` contains private curriculum, prompt, language, cultural, and business IP.

- Never copy proprietary data into the platform repository.
- Version the shared curriculum contract.
- Pin data, prompt, and schema versions in a release manifest.
- Run cross-repository contract tests before a milestone merge.
- Reconcile changes in one repository with compatibility implications in the other.

Why: separation protects the IP, but uncoordinated evolution currently leaves the platform
pointing at legacy Ghana-only files.

## AI Is Optional Infrastructure, Not Hidden Logic

Ollama is the active local AI runtime behind a provider abstraction. Do not add an external-model
SDK or API-key requirement without a new evidence-backed decision. Deterministic fakes remain the
test runtime, and core workflows remain usable when Ollama is unavailable.

- Deterministic domain logic comes before model orchestration.
- The complete automated test suite uses deterministic fake model responses.
- Record provider, model, version, prompt version, curriculum version, parameters, latency,
  and token or cost data for every evaluation run.
- Compare models with fixed evaluation sets before adoption.
- Provide abstention and human-review paths.
- Store concise decision rationales, not private chain-of-thought.
- The web product must degrade usefully when no model is available.

Why: model availability and persuasive output are not proof of diagnostic quality.

## User Research Is Product Work

Research is continuous, dated, and recorded in tasks and research artifacts.

- Prefer current primary sources for policy, curriculum, and market facts.
- Interview and observe target users rather than relying only on documents.
- Include Ghana and Uganda; urban, peri-urban, and rural contexts; public and private
  schools; different device, connectivity, language, gender, and ability contexts.
- Clearly label facts, inferences, hypotheses, and decisions.
- Add research findings and follow-ups to `TASKS.md`.
- Revalidate unstable facts before product or business decisions.

Why: building for a generalized “African classroom” would erase the differences that
GapSense is designed to respect.

## High UI/UX Standards Are Release Gates

High quality means understandable, accessible, fast, resilient, and contextually valid.

- Target WCAG 2.2 AA as a minimum.
- Test keyboard, screen-reader, zoom, reduced-motion, touch, and color-contrast behavior.
- Test real workflows across supported viewport sizes and network conditions.
- Maintain visual regression coverage for the design system and critical screens.
- Design loading, empty, partial-data, offline, error, and recovery states.
- Use official country and level terminology.
- Validate language, examples, imagery, symbols, and tone with target users.
- Never use visual or verbal deficit framing for learners.

Why: attractive screenshots are not evidence of a usable education product.

## One Hundred Percent Means Line and Branch Coverage

Application-owned executable code maintains 100% line and branch coverage.

The test strategy includes:

- unit tests for pure domain behavior;
- property-based tests for graph and scoring invariants;
- integration tests for database and service boundaries;
- data-schema and cross-repository contract tests;
- API contract tests;
- browser end-to-end tests;
- accessibility and visual regression tests;
- performance and low-bandwidth tests;
- security, privacy, authorization, and adversarial tests;
- prompt and diagnostic evaluation sets;
- mutation tests for diagnostic and safety-critical code.

An excluded line requires a documented technical reason and review. Coverage is a floor,
not a substitute for meaningful assertions.

Why: a line executed without a useful assertion can still conceal a harmful diagnostic
failure.

## TDD Is the Implementation Loop

Every behavior change follows red-green-refactor.

1. **Red:** write the smallest meaningful test and observe it fail for the expected reason.
2. **Green:** implement only enough behavior to pass the test.
3. **Refactor:** improve names, structure, duplication, and boundaries while all tests stay green.

- A bug fix starts with a failing regression test.
- Tests assert domain behavior, not incidental implementation details.
- Unit tests dominate; integration, contract, and browser tests prove boundaries and journeys.
- Mocks are used at external ports, not to imitate the internal domain.
- Snapshot tests supplement intentional assertions; they never replace them.
- Production code is not written first with tests added later to manufacture coverage.

Why: 100% coverage without test-first design can still produce shallow tests that merely execute
the implementation they were written to excuse.

## Clean and Hexagonal Boundaries

The domain core owns curriculum, prerequisite, diagnostic, confidence, intervention, and dignity
rules. Frameworks are replaceable details around it.

```text
web / CLI / future channels
        -> application use cases
                -> domain model
        <- ports and interfaces
database / auth / Ollama / files / future cloud adapters
```

- Domain code does not import FastAPI, SQLAlchemy, Ollama clients, or frontend frameworks.
- Application services coordinate use cases and transactions without owning domain rules.
- Adapters translate between domain types and external protocols.
- Dependency arrows point inward.
- Aggregate invariants are expressed as behavior, not scattered route or ORM callbacks.
- Use SOLID, dependency inversion, explicit value objects, and small pure functions where useful.
- Apply YAGNI: create an abstraction for a demonstrated boundary, not an imagined future class.
- Prefer clarity over pattern ceremony; architecture tests enforce the boundaries that matter.

Why: web-first today and possible WhatsApp or cloud adapters later should not duplicate or distort
the diagnostic core.

## Pre-Commit Is Strict and Cannot Be Bypassed

Pre-commit and pre-push run the same material checks as the local CI-equivalent pipeline.

- Hooks run through the reproducible Docker environment.
- Formatting, linting, typing, tests, coverage, schemas, migrations, docs, architecture,
  accessibility where applicable, security, secrets, PII, and dependency checks fail closed.
- Commit messages follow the project convention and identify the task or milestone.
- No critical hook may use `|| true`, `|| echo`, or another failure-swallowing pattern.
- `--no-verify` is not an accepted workflow.
- If tooling itself fails, fix the tooling or record a blocker; do not commit around it.
- A milestone merge repeats the full pipeline even if hooks already passed.

Why: a green commit must mean the same thing on every co-founder's machine and eventually in hosted
CI.

## Optimize What Is Measured

Smoothness includes user flow, perceived response, computational efficiency, delivery cost, and
developer feedback time.

- Start with an observed user problem, performance budget, profile, trace, or benchmark.
- Record the baseline, change, result, and output-equivalence evidence.
- Prefer removing unnecessary work and improving algorithms or data access before adding caches,
  concurrency, dependencies, or infrastructure.
- Treat perceived performance and recovery as seriously as raw latency.
- Profile low-end devices, cold starts, poor networks, Docker builds, database queries, and local
  model execution where applicable.
- Re-run correctness, accessibility, privacy, and security gates after every optimization.
- Remove accidental complexity continuously, while preserving decision and data provenance.
- Track cost-to-serve alongside latency so technical smoothness contributes to profitable growth.

Why: premature optimization creates complexity, while ignored friction destroys adoption and margin.

## Validation Fails Closed

A validator fails if it cannot prove that it performed meaningful work.

- Missing inputs fail.
- Invalid JSON or schema fails.
- Zero records tested fails unless zero is the explicit expected fixture.
- Metadata and actual-count disagreement fails.
- Duplicate codes, dangling references, cycles, and invalid progressions fail.
- Unrecognized infrastructure or dependency failures fail.
- A skipped critical test fails the milestone gate.

Why: the existing tracked curriculum consistency script reports a successful summary even
after every source load fails. Green output without inspected evidence is worse than red.

## Safety, Privacy, and Dignity Are Blocking

- Follow the active [Security and Privacy Engineering Model](SECURITY_AND_PRIVACY_MODEL.md).
- Add security acceptance criteria and abuse cases before implementing each major workflow.
- Update the threat model whenever a trust boundary, data flow, role, provider, or dependency changes.
- Deny access by default and prove authorization at the server/resource boundary.
- Use synthetic learner and family data until real-data protocols are approved.
- Minimize all collected data.
- Keep PII out of logs, fixtures, analytics, and model prompts.
- Research both Ghanaian and Ugandan data-protection obligations.
- Threat-model child safety, unauthorized access, inference, and misuse.
- Require explicit confidence, evidence, and human-review paths for diagnostics.
- Apply dignity-first language across the web, not only future parent messages.

Why: safeguarding and security are part of correctness. A feature that works only for honest
inputs and authorized users is not complete.

## Reconcile Every Major Slice

A passing implementation is not complete until every applicable status surface agrees.

Review and update:

- `TASKS.md`;
- relevant subject and module README files;
- curriculum metadata and country configuration;
- coverage and validation reports;
- API/schema and release manifests;
- ADRs and product decisions;
- research findings and hypotheses;
- user-visible documentation.

Run the full validation pipeline again after reconciliation, then commit and merge locally.

## Definition of a Completed Milestone

A milestone is complete only when:

1. Its task scope and acceptance evidence are explicit.
2. Implementation and documentation agree.
3. The Docker validation pipeline is green.
4. Line and branch coverage are both 100%.
5. Required research, accessibility, safety, and domain reviews are recorded.
6. Newly discovered work has been added to `TASKS.md`.
7. The branch is committed and merged into local `main`.
8. Nothing has been pushed remotely.
