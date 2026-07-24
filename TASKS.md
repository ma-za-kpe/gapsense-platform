# GapSense Working List

**Canonical project execution list.** Last reconciled: 2026-07-23.

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
2. Work on a focused branch created from the current reviewed integration target.
3. Do not mark a task complete because a document says it is complete.
4. Completion requires the applicable automated checks, artifacts, and review evidence.
5. Every discovered follow-up is appended to this file; the list itself never closes.
6. Commit completed milestones only after the local CI-equivalent pipeline is green; push once,
   review the resulting hosted evidence, and merge by pull request.
7. Remote contribution is authorized as of 2026-07-23. Batch coherent green milestones to
   minimize CI runs. Production deployment remains separately prohibited.

## Current Product Direction

- [~] Build a local-first, web-first GapSense experience for Ghana and Uganda.
- [ ] Make free, curriculum-aligned assessment generation a public web entry product for
  learners, parents/caregivers, teachers, school leaders, and other legitimate users.
- [x] Deliver a fully usable local web prototype: planner selection, evidence-linked starter
  activity generation, answer key, print/export affordance, and honest unsupported-coverage states.
  WhatsApp and deployment remain explicitly out of scope for this slice. Evidence: Docker
  frontend validation reached 100% coverage, the dedicated Playwright target passed 10/10
  desktop/mobile tests, and the local draft flow is covered by unit and accessibility tests.
- [ ] Replace the deterministic starter bank with versioned, educator-reviewed curriculum
  evidence records, beginning with Ghana primary Mathematics and Uganda Primary 1–3 Mathematics.
- [x] Add a teacher-facing curriculum evidence explorer so users can inspect country, authority,
  phase, source status, and question-organization concepts before trusting generated material.
  Keep raw proprietary documents out of the public UI. Evidence: the loaded country panels now
  expose expandable Ghana/Uganda organization maps, authority links, and generated-draft provenance.
- [x] Add a release-managed “latest version” link in the public footer, backed by the repository
  Releases page and kept compatible with Release Please; verify it in UI, accessibility, and SEO
  checks without hard-coding a stale version number. Evidence: footer contract test and Docker
  frontend validation.
- [ ] Add a manually triggered, environment-protected Vercel deployment workflow only after the
  deployment hold is explicitly lifted; keep `vercel.json` automatic deployments disabled and
  require hosted security, privacy, accessibility, and release checks before promotion.
- [!] Three-milestone deployment checkpoint reached after `v0.3.0`, but Docker `vercel --prod`
  failed closed because the available Vercel token is invalid. Obtain a fresh scoped token and
  project/org binding, then rerun the same command only after verifying the target and rollback.
- [ ] After every three reviewed milestones, run a deployment checkpoint: reconcile release
  version, CI evidence, privacy/security status, runtime logs, rollback target, and Vercel
  promotion approval before deploying.
- [ ] Rewrite `README.md` to professional-grade current-state documentation: accurately describe
  implemented workflows, known limitations, local commands, Docker services, validation evidence,
  release/deployment state, troubleshooting, logs, privacy boundaries, and links to the canonical
  operating documents. Keep it synchronized after each milestone.
- [ ] Raise CI/CD to open-source professional standard: split fast checks from expensive Docker
  gates, use dependency and Docker-layer caching safely, cancel superseded branch runs, pin every
  action by immutable SHA, publish test/coverage/security artifacts, surface flaky-test and runtime
  metrics, enforce least-privilege permissions, protect release/deployment environments, and keep
  required checks green without wasting hosted minutes.
- [ ] Establish professional contribution hygiene: pull-request and issue templates, reproducible
  checklists, security-report routing, conventional titles, release-note prompts, screenshots or
  evidence links for UX changes, curriculum provenance fields, and consistent labels/milestones.
- [ ] Add a real assessment document export contract (PDF/download) with print-layout and
  answer-key snapshots before calling generation production-ready.
- [x] Document the current local web workflow, Docker startup, validation commands, prototype
  boundaries, and next evidence-backed slice in `docs/LOCAL_WEB_PROTOTYPE_GUIDE.md`.
- [ ] Make the web experience excellent on mobile, tablet, and desktop, including
  low-bandwidth and intermittent-connectivity conditions.
- [ ] Support teachers first while researching the needs of learners, parents,
  curriculum specialists, school leaders, and education-system partners.
- [ ] Complete official curriculum coverage for all in-scope subjects and levels in
  Ghana and Uganda.
- [ ] Audit and model Uganda secondary as O’Level (lower secondary / UCE) and A’Level (advanced
  secondary / UACE), rather than generic “secondary”; inventory NCDC O-Level and A-Level sources,
  subjects, combinations, examination links, and curriculum-version dates. Research lead:
  NCDC’s official resources catalogue separates O Level Curriculum and A Level Curriculum:
  [NCDC resources catalogue](https://ncdc.go.ug/resource/).
- [~] Maintain 100% line and branch coverage for application-owned executable code.
- [ ] Use local mock services and local authentication until deployment is approved.
- [~] Use local Ollama as the active AI runtime behind a provider abstraction; never make a local
  model a hidden requirement for deterministic tests.
- [~] Keep WhatsApp delivery and production deployment on hold.

## Current Analytics and Search Slice

- [x] Establish the first privacy-safe product-analytics and technical-search foundation on
  `feat/privacy-safe-analytics-seo`; keep analytics collection disabled and search indexing
  blocked by default while production deployment and qualified privacy review remain on hold.
  Evidence: the complete Docker gate passed on 2026-07-23; the branch remains undeployed.
- [x] Document the analytics data flow, event taxonomy, minimization rules, abuse cases,
  retention boundary, search-publication contract, primary-source research basis, and the exact
  distinction between 100% automated contract coverage and outcomes that software cannot
  guarantee, such as search ranking, indexing, traffic, or representative product insight.
  Evidence: `docs/ANALYTICS_AND_SEARCH_MODEL.md` and ADR-002 define the disabled-by-default,
  local-aggregate-only architecture, research basis, publication gate, and deferred decisions.
- [x] Implement an allowlisted, versioned, first-party funnel event contract under TDD; accept no
  names, contact details, school or learner identifiers, free text, URLs, query strings,
  referrers, cookies, persistent IDs, advertising IDs, device fingerprints, or hidden external
  analytics dependency. Evidence: the versioned schema accepts exactly 11 property-free events,
  forbids unknown fields, and is covered through the browser client and API boundary.
- [x] Add a bounded same-origin analytics adapter and local aggregate-only API sink that fails
  silently from the user's perspective, never blocks a product action, never logs event bodies,
  rejects unknown fields/events and oversized batches, and remains replaceable behind a port.
  Evidence: disabled mode exposes no route; local mode uses in-memory thread-safe counters, a
  20-event/4 KiB ceiling, strict media-type checks, and an application-level streaming limit.
- [x] Instrument the complete current public funnel—entry view, primary navigation, planner role,
  country and goal selections, plan review/reset, readiness retry, and coverage retry—without
  collecting the selected values or creating a shadow learner profile. Evidence: all 11 current
  journey events are emitted without selection values, and React Strict Mode entry rendering is
  deduplicated.
- [x] Respect browser Global Privacy Control, Do Not Track, and reduced-data constraints; keep the
  immutable production-style frontend disabled while real collection is on hold.
- [ ] Design a visible analytics notice and explicit future opt-out only after Ghana/Uganda legal
  and user research establishes the lawful basis, notice, choice, retention, access, deletion, and
  processor requirements.
- [x] Generate complete static search metadata from one typed source of truth: unique title and
  description, application identity, robots directives, canonical and Open Graph URL only for an
  approved HTTPS origin, social metadata, `WebSite` JSON-LD, `robots.txt`, and a canonical-only
  XML sitemap. Evidence: 17 typed publication tests cover all statements, branches, functions,
  and lines, including unsafe origins and local/loopback variants.
- [x] Fail closed at build time if public indexing is requested without an approved absolute HTTPS
  origin; default local, test, preview, and deployment-hold artifacts to `noindex`, omit false
  canonicals and structured URLs, and return a real 404 for a sitemap that was not generated.
  Evidence: the hold artifact returns `noindex` and a text/plain sitemap 404; a synthetic,
  undeployed public artifact proved canonical, Open Graph URL, JSON-LD, sitemap, CSP digest,
  hidden-source removal, container health, and final runtime UID 101.
- [x] Prove analytics and search behaviour through red-green unit, API-contract, security,
  build-artifact, development-browser, immutable-production-browser, accessibility, console/log,
  CSP, and regression tests while maintaining 100% statements, branches, functions, and lines
  for all application-owned executable code. Evidence so far: 94 backend tests cover 953
  statements and 132 branches at 100%; 64 frontend tests retain 100% statements, branches,
  functions, and lines; and the focused development and production browser suites each pass
  10/10 desktop/mobile scenarios with zero unexpected server errors or analytics requests. The
  complete strict Docker gate, including migrations, security scans, dependency audits, package
  builds, Markdown policy, and patch checks, passed on 2026-07-23.
- [ ] Add deterministic size and Core Web Vitals budgets; measure LCP, INP, and CLS in field
  analytics only after privacy approval, using coarse classifications rather than fingerprinting
  precision and never loading a third-party script in the critical path.
- [ ] Create evidence-backed Ghana, Uganda, phase, level, subject, assessment, and diagnostic
  landing-page information architecture only as the underlying curriculum/product surfaces
  become real; never manufacture thin keyword pages or claim unsupported coverage.
- [!] Search Console/Bing registration, public sitemap submission, real analytics collection,
  crawl validation, ranking measurement, and production dashboards require an approved host and
  remain blocked by the production-deployment hold.

## Current Cross-Repository Delivery Sequence

- [x] Complete the `gapsense-platform` release/CI milestone on
  `chore/remote-main-reconciliation`: implement immutable-action CI, Release Please, one
  synchronized product version, synthetic public curriculum fixtures, and local policy tests.
  Evidence: 40 release-policy tests cover 162 statements and 70 branches at 100%; Actionlint and
  the complete strict gate passed on 2026-07-23.
- [x] Run the exact strict Docker gate for that platform milestone, commit once, and push the
  branch once so hosted CI is triggered only for a locally green candidate. Evidence: commit
  `28309d2` passed the commit and pre-push gates; GitHub Actions run `30037813589` completed the
  repository-owned `Required` Docker job successfully in 3 minutes 50 seconds.
- [x] Disable the inherited Vercel Git integration at the repository configuration boundary:
  automatic preview and production deployments must be false, historical AWS rewrites must not
  return, repository policy must fail closed if the hold is removed, and PR #10 must show no new
  Vercel deployment before merge. The first PR event exposed and failed the legacy preview path
  while the intended `Required` Docker job passed. Evidence: final PR SHA `1f39f03` and merge SHA
  `8da93e1` both returned empty GitHub deployment lists.
- [x] Remove the production-browser curriculum coverage race exposed by the corrective commit
  gate: delegate recursive evidence scans away from the async event loop, give the browser
  assertion time to observe the five-second fail-closed outcome, retain the failing regression
  test, and prove the complete production suite repeatedly before closing the task. Evidence:
  the focused route suite passed 3/3 after the regression test failed first; the immutable
  production suite passed 30/30 repeated desktop/mobile scenarios; and the corresponding API log
  recorded 13/13 coverage responses at HTTP 200 with zero 499 cancellations. The next exact gate
  correctly caught an unnarrowed heterogeneous FastAPI route type in the new regression test;
  the explicit `APIRoute` narrowing then passed both complete local gates and hosted CI.
- [x] Close the recurring production-browser coverage race found by the 2026-07-23 pre-push
  gate: page teardown cancelled repeated `/v1/curriculum/coverage` requests with HTTP 499 while
  their worker-thread filesystem scans continued, eventually exhausting the frontend's
  five-second fail-closed budget. Build one immutable coverage snapshot per application process,
  prove concurrent requests cannot duplicate the scan, repeat the production browser suite, and
  inspect proxy/API logs before attempting another remote push. Evidence: the regression failed
  with eight scans for eight concurrent requests before the fix, then passed 4/4 focused tests;
  the production stress suite passed 30/30 desktop/mobile scenarios with 60/60 coverage requests
  at HTTP 200, zero 499 responses, and zero API errors; the complete strict Docker gate passed
  with 82 backend tests and 37 frontend tests at 100% coverage plus both 10/10 browser suites.
- [x] Remove deprecated Node 20 action runtimes from hosted automation: pin the reviewed official
  Node 24 releases of Checkout `v7.0.1` and Release Please Action `v5.0.0`, update the fail-closed
  action allowlist under TDD, and require a warning-free hosted Required run before merge.
  Evidence: Required run `30041138985` passed in 4 minutes 5 seconds with zero annotations.
- [x] Open the platform reconciliation PR against remote `main`; review the large historical
  replacement diff, verify every required hosted check is green, merge through GitHub, and
  reconcile local `main` without deploying. Evidence: PR #10 merged as `8da93e1`, local `main`
  fast-forwarded to the same SHA, and the feature branch was pruned locally and remotely.
- [x] Repair the first post-merge Release Please run: keep default workflow token permissions
  read-only, enable the repository setting required for GitHub Actions to create the release PR,
  rerun failed workflow `30041492848`, require its bot PR and dispatched Required check to pass,
  and confirm no deployment occurs. Evidence: the rerun created PR #11 and dispatched Required;
  that gate then exposed a hard-coded `0.1.0` health-test expectation after the generated tree
  correctly advanced to `0.2.0`; commit `109d323` replaced it with the canonical package version.
  The updated bot SHA `02cef84` then passed Required run `30042715809` in 3 minutes 53 seconds with
  zero annotations and an empty deployment list.
- [~] Normalize the first-release changelog lifecycle under TDD: keep the pre-release changelog
  empty so Release Please creates the canonical heading exactly once, reject heading-only or
  repeated-heading states in repository policy, and prove the corrected bot branch through the
  Docker gate without merging or tagging it.
- [x] Make squash merging the only normal GitHub merge mode and delete reviewed head branches
  automatically so main stays linear, Release Please sees one Conventional Commit per PR, stale
  branches do not accumulate, and the duplicate merge-commit/child-commit notes seen in PR #11
  cannot recur. Evidence: the GitHub repository now reports merge commits and rebase merges false,
  squash merges true with `PR_TITLE`/`PR_BODY`, and automatic head-branch deletion true.
- [ ] Reconcile the one-time duplicate `fix(release)` entry on Release Please PR #11 after its
  final automated update and before any first tag; do not hand-edit an actively regenerated bot
  branch or allow the historical merge-policy defect into public release notes.
- [?] Review the first-release baseline before merging Release Please PR #11: confirm that
  `0.2.0` is the intended first public tag, decide how a missing `v0.1.0` comparison baseline
  should be represented, and do not publish a release merely to make the automation appear done.
- [x] Create a focused branch in the separate `gapsense-data` repository without mixing platform
  code or history into it. Evidence: `research/ghana-uganda-secondary-inventory` was developed in
  an isolated worktree while the original seven uncommitted curriculum files remained untouched.
- [x] Inventory every Ghana and Uganda secondary source already present, including misplaced,
  duplicate, partial, stale, and untracked artifacts; reconcile rather than overwrite useful
  extraction work. Evidence: merged data PR #2 records the honest baseline and unresolved gaps.
- [x] Build the official secondary source matrix by country, authority, phase, level, subject,
  syllabus edition, source URL, retrieval date, license/use status, checksum, extraction state,
  review state, and known gap. Evidence: 66 official-source records are machine validated.
- [x] Download the currently discoverable missing official secondary documents from NaCCA and
  NCDC first; use broader web
  discovery only to locate an authoritative copy or archive, and quarantine any source whose
  authenticity cannot be proven. Evidence: 57 visible Uganda PDFs and three useful Ghana SHS PDFs
  were acquired; Ghana SHS English and authority-index count discrepancies remain explicit gaps.
- [x] Hash, catalogue, and retain immutable provenance for every acquired source document before
  extraction; detect duplicates and source substitutions automatically. Evidence: 62 catalogued
  artifacts are byte verified and 60 acquisition receipts are cross-checked by policy.
- [ ] Extract and normalize the acquired secondary curricula with deterministic tooling, preserve
  raw originals, and validate output structure and source traceability.
- [ ] Measure Ghana and Uganda secondary coverage per phase, level, and subject; add every newly
  exposed gap to this working list and never infer completeness from file presence.
- [x] Run the data repository's complete Docker validation and quality gates, commit the coherent
  secondary acquisition/extraction milestone, push once, and open a separate data PR.
  Evidence: 29 tests and the eight-step Docker gate passed with 100% coverage before PR #2.
- [x] Review and merge the data acquisition/provenance PR only when hashes, catalogues, policy,
  security checks, and hosted CI are green; keep extraction/review incompleteness explicit.
  Evidence: data PR #2 and hosted Required run `30050380590` passed before merge `f742937`.
- [x] Repair the first `gapsense-data` Release Please candidate without weakening Markdown policy:
  scope the generated-changelog MD012 allowance to `CHANGELOG.md`, policy-lock the one-file,
  one-rule exception, normalize workflow-policy input across LF/CRLF Docker mounts, and retain the
  failing regressions. Evidence: data PR #4 passed 30 tests at 100% line, branch, and function
  coverage plus Required run `30051104472`, then squash-merged as `220eaf3`.
- [x] Prove the regenerated `gapsense-data` draft release candidate without publishing it.
  Evidence: Release Please generated candidate SHA `8be32d2`; dispatched Required run
  `30052774447` passed the exact Docker gate. Draft PR #3 remains open and unmerged.
- [x] Align the data repository with the platform's reviewed history policy after the one-time
  corrective merge: squash-only merging is enabled, merge commits and rebase merges are disabled,
  and merged head branches are deleted automatically.
- [!] Keep `gapsense-data` draft release PR #3 unmerged and untagged until the first-release
  baseline, version, changelog, curriculum completeness language, and release hold receive an
  explicit co-founder review.
- [ ] Update the platform coverage contract only after a separately reviewed deterministic
  secondary extraction milestone establishes phase/subject maturity; raw PDF presence is not
  curriculum completion.

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
- [x] Add bounded retry and freshness checks to Debian OS-package index/download layers; the
  2026-07-23 first lightweight-CI rehearsal failed closed when transient DNS/timeouts left `apt`
  without a usable package index for `curl`. Evidence: both OS-package layers now use bounded
  index/download retries, timeouts, and an index-presence check; a clean `web` image build
  completed successfully in 91.7 seconds.
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
- [~] Inspect and prune stopped one-off containers, unused networks, dangling images, and
  dangling build cache after each major validation or browser milestone; record reclaimed
  space, preserve named evidence containers that are still needed, and never auto-prune
  volumes because unattached data can still be irreplaceable. Evidence: the 2026-07-23
  release/CI milestone cleanup reclaimed 1.089 GB of dangling build cache and removed one unused
  network while preserving every volume and all five healthy GapSense containers.
- [x] Recover the Docker orchestration layer after the 2026-07-23 client stall and reclaim
  11.46 GB from 13 stopped containers, two unused networks, and dangling build cache while
  preserving all four local volumes.

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
- [x] Add browser end-to-end tests.
- [x] Add automated accessibility tests targeting WCAG 2.2 AA; retain manual assistive-
  technology validation as a separate release-readiness requirement.
- [ ] Add keyboard-only and screen-reader workflow checks.
- [x] Add visual regression tests for the initial supported desktop and mobile viewports;
  expand baselines as themes and product routes are added.
- [x] Add responsive-layout tests for low-cost Android-sized screens through desktop.
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
- [x] Make the complete application gate operate against a read-only candidate workspace by
  routing Ruff, MyPy, Pytest, Coverage, Poetry, pip, and build artifacts only to ephemeral `/tmp`
  paths; retain the read-only mount in the exact pre-commit entry point.
- [~] Run the complete gate in Docker before every milestone commit and local merge.
- [x] Add local CI scripts now; add hosted CI only when remote work is authorized.

## Delivery, Branching, Versioning, and Releases

- [x] Audit the workflow already present on remote platform `main`, current GitHub Actions runs,
  branch activity, cache use, permissions, event triggers, duplicated work, and billable-minute
  waste before adding or replacing any workflow. Evidence:
  [`docs/DELIVERY_AND_RELEASE_MODEL.md`](docs/DELIVERY_AND_RELEASE_MODEL.md).
- [x] Define and document the branch lifecycle: protected `main` as releasable history, `develop`
  as the integration branch only where it reduces risk, short-lived `feature/*` branches,
  time-bounded `release/*` stabilization branches, and urgent `hotfix/*` branches.
- [x] Prefer trunk-based feature integration over permanently divergent branches; define merge,
  rebase, deletion, stale-branch, backport, and release-cut rules with repository evidence.
- [~] Require conventional commits, pull-request titles, reviewed changes, green required checks,
  linear or explicitly justified merge history, and no direct writes to protected branches.
- [x] Design one reusable CI graph shared by pull requests, merge queues, and protected-branch
  pushes; avoid running the same full suite twice for the same commit.
- [x] Minimize CI credit use with event filters, path filters, concurrency groups with
  `cancel-in-progress`, dependency and Docker layer caches, change-aware job selection, bounded
  matrices, fail-fast ordering, artifact retention limits, and scheduled deep checks only where
  risk justifies them.
- [x] Keep security-critical, lockfile, migration, coverage, browser, and release checks fail
  closed even when optimizing runtime; cost reduction must never create an evidence gap.
- [x] Add a lightweight documentation-only path that still runs Markdown, links, secrets, policy,
  and workflow validation without rebuilding unrelated application images.
- [x] Pin every third-party GitHub Action to an immutable commit SHA, minimize `GITHUB_TOKEN`
  permissions per job, use no long-lived release secret, and review artifact/provenance trust.
- [x] Add workflow syntax, policy, action-pin, and local Docker-equivalent tests so CI changes are
  validated before they consume a hosted run.
- [x] Select one canonical product version source, adopt Semantic Versioning, and expose the
  version consistently in Python package metadata, frontend metadata, API responses, artifacts,
  and release notes without manual duplication.
- [x] Configure Release Please with manifest-based version management for the platform components,
  conventional-commit changelogs, release pull requests, signed/tagged releases where supported,
  and no automatic production deployment.
- [x] Prove the local release/CI candidate through the exact Docker gate on 2026-07-23: migration
  upgrade/downgrade/rebuild/drift passed; 76 backend tests and 37 frontend tests maintained 100%
  line and branch coverage; Bandit, pip-audit, and npm audit reported no findings; development and
  immutable-production Playwright suites each passed 10/10 desktop/mobile scenarios.
- [ ] Define pre-release identifiers and promotion rules for `develop`/`release/*`; do not publish
  a stable release from an unreviewed feature branch or a dirty worktree.
- [ ] Add software-bill-of-materials, build provenance, checksums, dependency review, and a
  reproducible release-artifact verification step before any public release.
- [ ] Measure CI wall time, runner minutes, cache hit rate, flaky reruns, queue time, and cost per
  accepted change; add optimization work when thresholds regress.
- [x] Lift the remote contribution hold only: the co-founder authorized branch pushes, pull
  requests, and reviewed merges on 2026-07-23, while requiring CI-credit-aware batching. Production
  deployment remains separately and explicitly on hold.

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
- [ ] Inventory, reconcile, and surface the Ghana secondary artifacts already present
  (JHS Mathematics, SHS English, and SHS General Science) by exact level, subject, source
  version, extraction state, and review state; file presence must not imply full coverage.
- [ ] Complete every official Ghana JHS and SHS/SHTS/STEM subject and pathway after the
  authoritative menu and combination rules are approved, with one traceable child task per
  level/subject combination.
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
- [~] Validate the current uncommitted P1-P3 Mathematics extraction before merging it. Initial
  Docker read-only audit confirms the P1–P3 mapping, prerequisite graph, and source manifest parse;
  educator review, schema normalization, and data-repository commit evidence remain outstanding.
- [ ] Complete P4 transition-phase subjects and learning outcomes.
- [ ] Complete P5-P7 subject-based curriculum coverage.
- [ ] Complete Lower Secondary S1-S4 compulsory and elective curriculum coverage.
- [ ] Complete aligned A-Level S5-S6 curriculum coverage.
- [ ] Verify whether any current Uganda secondary artifact exists outside the empty canonical
  `secondary/mathematics` folder found by the 2026-07-22 audit; migrate nothing by assumption
  and record source/version evidence for every located artifact.
- [ ] Complete every official Uganda Lower Secondary and A-Level subject and permitted
  combination after the current NCDC inventory is approved, with one traceable child task per
  level/subject combination.
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

### Completed slice - `localhost:3000` entry experience

- [x] Audit every local and GitHub branch in both GapSense repositories, run the substantial
  historical frontend from remote `main`/`develop`/`feature/mvp-core-services` in an isolated
  Docker worktree, and reconcile its strongest workflows and assets with the web-first Ghana and
  Uganda product direction without disturbing the co-founder review service on port 3000.
  Evidence: [`docs/FRONTEND_RECONCILIATION_AUDIT.md`](docs/FRONTEND_RECONCILIATION_AUDIT.md).
- [x] Record a page-by-page and capability-by-capability reconciliation decision before accepting
  the frontend ADR; preserve useful historical work, retire WhatsApp-first presentation from the
  active web journey, and add every discovered gap to this persistent list. Evidence:
  [`docs/FRONTEND_RECONCILIATION_AUDIT.md`](docs/FRONTEND_RECONCILIATION_AUDIT.md).
- [~] Reconcile remote platform `main` on the dedicated
  `chore/remote-main-reconciliation` branch without activating either line wholesale; preserve
  remote commit `b24ec44` as a merge parent and port every meaningful behaviour through the
  current TDD, security, Docker, and product gates. Evidence and disposition map:
  [`docs/REMOTE_MAIN_RECONCILIATION.md`](docs/REMOTE_MAIN_RECONCILIATION.md).
- [x] Classify the divergent remote UI, API, domain, migration, AI, WhatsApp, infrastructure,
  data, asset, test, and documentation families as rebuild, defer, or retire before completing
  the history merge; keep every rejected active file recoverable from the merge parent.
- [ ] Port the accepted remote backend, migration, governance, security, and frontend behaviours
  in small tested slices; do not import external-provider credentials, copied proprietary data,
  stale claims, or skipped checks to make historical tests pass.
- [ ] Complete the remote-main reconciliation only after every accepted backend, migration,
  governance, security, and frontend behaviour across the 138/4 divergence has current evidence;
  run the strict gate and merge the branch into local `main` without pushing.
- [ ] Migrate the historical curriculum explorer, teacher diagnostic workspace, class and learner
  reports, and concise architecture/trust story into the tested web shell; do not ship duplicate
  public frontends or unsupported production, latency, reach, cost, and coverage claims.
- [ ] Add and enforce route-level transfer budgets informed by the historical frontend's compact
  228 KB uncompressed build, including JavaScript, CSS, image, font, and total-page budgets.
- [ ] Resolve or retire the historical frontend's strict-type failures, missing lint dependencies,
  empty build chunks, backend-coupled HTTP 500 paths, and four high/three moderate dependency
  vulnerabilities before any of its executable code enters the active product.
- [x] Select and document the frontend stack through an ADR grounded in official framework,
  testing, accessibility, browser-support, operational, and deployment-neutral evidence.
- [x] Add a Docker-only frontend service on `http://localhost:3000` with a deterministic lockfile,
  health check, read-only runtime, loopback binding, and same-origin API proxy.
- [x] Build a polished responsive GapSense entry experience that represents Ghana and Uganda
  distinctly without stereotypes and never overstates curriculum readiness.
- [x] Build the accessible public assessment-planning entry flow for role, country, and intended
  outcome while clearly separating currently available and still-being-reviewed coverage.
- [x] Create the first reusable design tokens and components for typography, color, spacing,
  focus, motion, status, buttons, cards, and form controls.
- [x] Add explicit loading, API-ready, API-unavailable, incomplete-curriculum, and recovery states.
- [x] Add frontend format, lint, strict TypeScript, unit/component, DOM-accessibility, production
  build, dependency-audit, browser, axe, responsive-viewport, and security-header gates in Docker.
- [x] Enforce 100% frontend statement, branch, function, and line coverage across every owned
  executable TypeScript/TSX module, including files not imported by tests.
- [~] Periodically open the rendered page in a visible browser and inspect frontend and API logs
  throughout implementation; retain deterministic Docker browser tests as repeatable evidence.
- [x] Isolate immutable-production browser validation from the visible port 3000 development
  service so repeated quality gates do not unnecessarily interrupt a co-founder review session.
- [x] Add an internal development-browser target and make frontend validation plus development
  and immutable-production browser suites mandatory in the exact strict pre-commit entry point,
  without recreating the visible port 3000 review service.
- [x] Build and smoke-test a non-root production frontend image locally without deploying it.
- [x] Reconcile evidence, commit this slice on its feature branch, and merge it into local `main`
  only after the complete backend and frontend gates pass; do not push.

### Active slice - truthful curriculum coverage contract

- [x] Replace the legacy singular `curriculum/` readiness test with a fail-closed canonical
  `curricula/` contract for Ghana and Uganda; directory or file presence must never be reported as
  completed extraction or educator approval.
- [x] Add a tested country/authority/level catalog using current official NaCCA and NCDC
  terminology, while keeping tertiary scope and any unsupported level explicitly unresolved.
- [x] Build a deterministic read-only inventory that ignores hidden/transient files, refuses
  symlink traversal, reports source-file availability separately from review state, and exposes
  no private paths or file content.
- [x] Add a typed `/v1/curriculum/coverage` API with explicit incomplete/unknown states and tests
  for present, partial, missing, malformed, and unexpected repository structures.
- [ ] Evolve the country-level inventory into a machine-generated country/phase/level/subject
  coverage matrix so the UI distinguishes existing secondary artifacts from primary artifacts
  and shows `missing`, `located`, `extracted`, `structurally validated`, and human-review states
  without inferring any state from an aggregate file count.
- [x] Update service readiness to require the canonical Ghana and Uganda roots while remaining
  independent of optional Ollama, authentication, deployment, and WhatsApp services.
- [x] Consume the typed coverage contract in the port-3000 web shell without overstating
  readiness; cover loading, success, partial, unavailable, and recovery paths at 100%.
- [x] Run the complete Docker gate and inspect both browser viewports and logs. Evidence on
  2026-07-23: 36 backend tests and 37 frontend tests at 100% line/branch coverage, 10/10
  development and 10/10 immutable-production browser checks, zero known dependency
  vulnerabilities, clean security/secret/type/lint/migration/package/docs gates, and reviewed
  desktop/Pixel 7 baselines.
- [~] Commit the truthful coverage slice on the reconciliation branch, merge the completed
  milestone into local `main`, and retain the no-push/no-deploy hold.

- [x] Select the web frontend stack through an ADR and a tested prototype.
- [x] Define the first browser/API boundary and typed curriculum-coverage contract.
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
- [?] Research an opt-in **bring your own AI provider key** path for educators who choose
  AI-assisted assessment features in the free product; validate demand, provider terms,
  accessibility, support burden, and whether the trust and setup cost is justified.
- [ ] Define a provider-neutral credential port and local fake before any BYOK UI; keep
  deterministic generation and local Ollama available without an external credential and
  never make BYOK a hidden condition of a free or safety-critical workflow.
- [ ] Threat-model BYOK end to end before implementation: explicit informed consent,
  provider/data-policy disclosure, least privilege, secret redaction, memory and persistence
  boundaries, encryption where retention is unavoidable, rotation/revocation, expiry,
  account/session isolation, CSP/XSS and extension risk, SSRF/egress allowlists, quota abuse,
  incident response, and proof that keys never enter logs, analytics, exports, prompts,
  browser storage, source control, or support tooling.
- [ ] Prototype and test the safest viable BYOK flow locally with synthetic data only; compare
  server-side ephemeral use, an encrypted per-user vault, and provider-supported delegated
  authorization, and reject direct browser key handling unless a documented threat model proves
  it appropriate for that provider.
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

- [~] Remove UNICEF from GapSense product identity, active UI, demos, pitch language, metadata,
  and implied affiliation or endorsement across both repositories; replace required evidence with
  authoritative Ghanaian or Ugandan sources instead of deleting provenance silently.
- [x] Use the founder attribution **Built by Maku for Africa** consistently in the active product
  and brand standard, backed by unit and browser regression checks.
- [ ] During remote-branch reconciliation, remove the historical frontend's UNICEF cohort badges,
  application language, footer credit, metadata, and external calls to action before any migrated
  surface enters the active build.
- [~] Audit product copy across both repositories and replace Ghana-only, Math-only,
  WhatsApp-first, or unsupported continent-wide positioning with the honest hierarchy: GapSense is
  **built by Maku for Africa**, grounded first in Ghana and Uganda, and every coverage claim names
  its verified country, authority, level, subject, version, and review state.
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
- [ ] Model whether optional educator BYOK can preserve a genuinely useful free tier without
  shifting hidden provider cost, security liability, confusing setup, or unequal access onto
  educators; compare it with funded inference allowances and fully local Ollama operation.
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

- [!] WhatsApp channel implementation is the **very last product programme**. Resume only after
  the complete web product, Ghana and Uganda curriculum evidence, free assessment workflows,
  security/privacy, accessibility, performance, release engineering, local operations, and
  deployment-readiness gates are complete and reconciled; no earlier task may depend on it.
- [!] Production deployment is on hold. Do not deploy to Firebase, AWS, or another host.
- [~] Enforce the deployment hold in Vercel configuration as well as project policy; the inherited
  Git integration attempted preview deployment `5578453910` on PR #10 before this missing
  repository-level guardrail was discovered.
- [x] Remote contribution hold lifted by explicit co-founder direction on 2026-07-23. Push only
  locally green milestone branches, use reviewed PRs, batch changes to avoid duplicate CI, and do
  not interpret this as production-deployment authorization.
- [ ] Before lifting deployment hold, write an ADR comparing hosting, API, database,
  authentication, observability, privacy, cost, regional availability, and offline needs.
- [ ] Preserve channel-neutral domain boundaries so WhatsApp can be added later without
  rewriting diagnostic logic.

## Final Programme - WhatsApp Delivery

- [!] Do not begin this programme until every preceding applicable programme is complete and an
  explicit co-founder decision lifts the hold.
- [ ] Revalidate whether WhatsApp remains the best last-mile channel for target users in Ghana and
  Uganda after observing the mature web product in real user research.
- [ ] Reconcile and threat-model the historical WhatsApp code; migrate only channel-neutral,
  secure, tested behaviour and reject stale pitch-driven assumptions.
- [ ] Design consent, identity, child safeguarding, opt-in/out, retention, deletion, rate limits,
  abuse controls, message templates, media handling, delivery receipts, and human escalation.
- [ ] Implement the channel as an adapter over proven web/domain use cases, never as a second
  source of curriculum, assessment, diagnostic, learner, or authorization logic.
- [ ] Prove equivalent correctness, privacy, accessibility alternatives, observability, cost,
  provider-failure recovery, and end-to-end security before a production-channel decision.

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
- [x] Add a Docker-native browser, accessibility, and visual-regression harness so local web
  journeys remain verifiable when an interactive browser automation runtime is unavailable.
- [ ] Make the strict gate recover predictably from Docker Desktop BuildKit missing-parent
  snapshot cache faults without broad cache deletion, disabled checks, or a host-runtime fallback.
- [ ] Investigate the 2026-07-23 co-founder observation that curriculum coverage appeared
  primary-only; replace ambiguous aggregate presentation with verified per-level and per-subject
  evidence, explicitly including Ghana and Uganda secondary education.
- [x] Add an application-level streaming byte ceiling to the local analytics route so a direct
  loopback client cannot bypass the production proxy cap by lying about `Content-Length`.
  Evidence: the regression first returned 422 for a 4 KiB-plus body declared as one byte, then
  passed with HTTP 413; 11 focused analytics tests cover 80 statements and 12 branches at 100%.
- [x] Exercise the dormant public-search production artifact locally without deploying it; make
  the build-time root transition explicit for the pinned unprivileged Nginx image and return the
  runtime to UID 101. Evidence: the first image failed to remove its temporary CSP source, while
  the corrected image became healthy with matching canonical, Open Graph URL, `WebSite` JSON-LD,
  robots, sitemap, and exact JSON-LD CSP digest, and no retained hidden source file.
- [x] Narrow the browser analytics-request assertion to the exact API pathname after the broad
  substring check incorrectly classified Vite's source-module request as data collection.
  Evidence: the retained assertion watches only `/api/v1/analytics/events`, and both browser
  modes prove that the disabled default sends no analytics request.
- [x] Return the deployment-hold sitemap miss with an explicit `text/plain` media type rather than
  allowing Nginx's URI-extension inference to label the 404 as XML. Evidence: red-green immutable
  browser assertions verify HTTP 404, `text/plain`, and the exact non-indexable response body.
- [x] Preserve the strict credential scanner when a test-only unsafe-origin fixture resembles
  embedded credentials; use the scanner's exact-line test pragma instead of weakening or
  excluding the check. Evidence: the first complete gate stopped at the fixture, while the
  focused secret scan passed after the narrow annotation.
- [ ] Add a release-only, Docker-native public-search artifact verifier so the synthetic HTTPS
  canonical, sitemap, JSON-LD, CSP-digest, hidden-file-removal, and runtime-UID assertions remain
  reproducible without adding a duplicate full PR workflow.
- [ ] Define an evidence-based analytics abuse and rate policy before any host is approved; test
  burst, concurrency, proxy-bypass, slow-body, malformed-transfer, and multi-process behaviour
  without relying on IP tracking as the only control.
- [ ] Design authenticated, purpose-limited operator access to aggregate metrics with minimum
  reporting thresholds, audit evidence, retention, deletion, and no public summary endpoint.
- [ ] Produce and review a provenance-safe favicon, manifest, and responsive social-preview image
  after the identity system is approved; validate dimensions, crops, contrast, alternative text,
  cache behaviour, and absence of learner data or fabricated authority endorsements.
- [ ] After the deployment hold is explicitly lifted, verify crawl status, canonical selection,
  structured-data eligibility, field Core Web Vitals, and search-query quality with controlled
  organisation accounts; record these as monitored outcomes rather than guaranteed “100% SEO.”
