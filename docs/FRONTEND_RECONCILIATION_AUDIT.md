# Frontend and Branch Reconciliation Audit

Date: 2026-07-22
Status: Active migration evidence; not a completeness declaration

## Why This Audit Exists

The local platform checkout was based on commit `938aedb`, while the GitHub default branch had
advanced substantially. The stale remote-tracking refs initially hid an existing frontend and a
large body of backend work. This audit records what was actually found, how it was exercised, and
which work must be preserved or replaced. It prevents either frontend from being treated as the
whole product by accident.

No remote branch was changed, pushed, or deployed during the audit. The current web-first service
on `http://localhost:3000` remained available while the historical UI ran in an isolated Docker
worktree on `http://localhost:3002`.

## Repository and Branch Evidence

### `gapsense-platform`

| Ref | Last commit at audit | Relationship to remote `main` | Interpretation |
| --- | --- | --- | --- |
| local `main` | `394ae97`, 2026-07-22 | 138 remote-only / 4 local-only commits | Current governance and secure local foundation have not yet absorbed the March remote work. |
| `feat/web-entry-experience` | `394ae97` plus the active worktree | same ancestry as local `main` | Active web-entry slice; do not merge until all gates pass. |
| remote `main` | `b24ec44`, 2026-03-19 | GitHub default | Contains the substantial historical UI and backend implementation. |
| remote `develop` | `1c12c6d`, 2026-03-19 | fully behind remote `main` | Its reviewed work is represented by remote `main`. |
| remote `feature/mvp-core-services` | `fd67199`, 2026-03-19 | 8 commits behind and 1 commit ahead | The one unique pricing change is in open PR 9 and needs a current commercial decision. |
| remote `feature/mvp-teacher-initiated` | `d68e475`, 2026-02-17 | 51 commits behind | Historical branch; no unique commit relative to remote `main`. |
| remote `feature/whatsapp-integration` | `4521c36`, 2026-02-16 | 85 commits behind | Historical channel work; WhatsApp remains on hold. |

GitHub PR 8 merged `develop` into `main`. PR 9, changing stated private-school pricing from USD 2
to USD 20 per learner per year, remains open. A stale price must not enter the product as fact
without willingness-to-pay and unit-economics evidence.

### `gapsense-data`

| Ref | Last commit at audit | Relationship to remote `main` | Interpretation |
| --- | --- | --- | --- |
| remote `main` | `346db33`, 2026-03-18 | GitHub default | Newest pushed data branch. |
| local `main` | `babcbff`, 2026-02-16 | 15 commits behind | Must not be treated as the current data baseline. |
| local/remote `feature/multi-country-abstraction` | `cbadba4`, 2026-03-16 | 6 commits behind and 4 commits ahead | Diverged curriculum branch with additional uncommitted Uganda extraction work. Preserve it exactly until reconciled on a dedicated branch. |

The data repository has no frontend paths. Its active working tree contains Uganda Primary 2 and
Primary 3 extraction artifacts that were not modified by this audit.

## Historical Frontend Runtime Audit

Remote platform `main` was checked out as a detached worktree, copied into a dedicated Docker
volume, and served by a non-root, capability-free container. Dockerized Playwright exercised the
pages at desktop and mobile sizes and captured console, page-error, request-failure, title,
heading, status, and screenshot evidence.

| Surface | Runtime result | Value to preserve | Gap to resolve |
| --- | --- | --- | --- |
| Landing page | HTTP 200; no browser-console error | Compact explanation and low-bandwidth static delivery | Ghana/Math/WhatsApp-only; unverified production, reach, latency, cost, and coverage claims; visually dated. |
| Demo | Document HTTP 200 | Teacher chat simulation, upload concept, report entry, presentation narrative | Backend request returns HTTP 500; unexpected empty JSON error; WhatsApp-first; duplicated long pitch content. |
| Curriculum explorer | Document HTTP 200 | Curriculum-code explanation, search, grade filters, browse concept | Curriculum request returns HTTP 500; Ghana/JHS/Math-only; visible `100%` claim is not supported by the current evidence audit. |
| Developer page | HTTP 200; no browser-console error | Architecture timeline and system explanation | Extremely long marketing page; stale Claude, deployment, performance, and production claims; not a target-user workflow. |
| Teacher and learner reports | Present as static/Jinja templates | Class overview, root-gap detail, remediation and learner report concepts | Not Vite entry points; tightly coupled to historical routes and template data; need privacy, authorization, responsive, and accessibility tests. |

The production frontend build succeeded and remained small at approximately 228 KB uncompressed.
That strength should become a measured JavaScript, CSS, image, and route budget in the current
frontend.

The historical frontend cannot pass the required gate:

- strict TypeScript checking reports extensive nullability, event, request-option, global, and
  component-contract errors;
- the declared lint command fails because ESLint and Stylelint are not installed;
- `npm audit --audit-level=low` reports four high and three moderate vulnerabilities;
- no unit, component, accessibility, browser, visual-regression, or coverage command is declared;
- the build emits empty manual chunks, showing that its intended modular code is not actually
  connected to the built HTML entry points.

## Reconciliation Decision

Use the current React and strict TypeScript frontend as the active public web shell. It is already
country-neutral at the domain boundary, explicitly distinguishes Ghana and Uganda, supports a
no-account free-assessment planning entry, stays useful when the API is unavailable, and has a
Docker-only 100% coverage and browser-quality foundation.

Do not discard the historical product work and do not expose two competing public frontends.
Migrate its useful capabilities into tested routes and components in this order:

1. curriculum explorer and curriculum-code explanation, backed by evidence-versioned Ghana and
   Uganda APIs and honest coverage states;
2. teacher diagnostic workspace, using a web-native interaction rather than a WhatsApp replica;
3. teacher class overview and learner gap/remediation reports with local mock authorization;
4. a concise, evidence-backed architecture and trust page for technical evaluators;
5. only then, archive the superseded static pages outside the active build while retaining Git
   history and a migration map.

Every migrated route requires test-first acceptance criteria, 100% owned-code coverage, axe and
keyboard checks, desktop/mobile browser journeys, API failure and recovery states, security
headers, privacy review, and visual review. Historical numerical or market claims are hypotheses
until a dated primary source or project measurement supports them.

## Integration Guardrails

- Finish and validate the current feature slice before committing it.
- Integrate remote `main` into a dedicated local reconciliation branch; never overwrite either
  side of the 138/4 commit divergence.
- Resolve backend, migration, dependency, and Compose conflicts with tests, not by selecting one
  side wholesale.
- Review PR 9's pricing change separately from code integration.
- Reconcile the data repository on its own branch and preserve its dirty Uganda extraction files.
- Keep WhatsApp, deployment, and remote pushes on hold.
- Add each newly exposed functional, curriculum, security, UX, commercial, or evidence gap to
  `TASKS.md` before implementation.
