# Delivery, Branching, Versioning, and Release Model

Date: 2026-07-23
Status: Implemented release/CI candidate; remote contribution is authorized and production
deployment remains on hold

## Outcome

GapSense should make the safest path the fastest path: one locally proven Docker gate, one
change-aware hosted validation graph, protected promotion, and an explicit release pull request.
CI is evidence, not a substitute for the strict local gate, and a green badge must never be
manufactured by soft-failing a critical check.

The platform repository is public, so standard GitHub-hosted runner minutes are free. Optimization
still matters because failed and duplicate runs waste co-founder time, reviewer attention, queue
capacity, cache/artifact storage, energy, and signal. Larger runners and excess storage can still
cost money. See [GitHub Actions billing](https://docs.github.com/en/enterprise-cloud@latest/billing/concepts/product-billing/github-actions).

## Existing Remote Workflow Audit

The audit used GitHub CLI against `ma-za-kpe/gapsense-platform` and inspected remote `main` at
`b24ec44`.

| Finding | Evidence | Required response |
| --- | --- | --- |
| Persistent red CI | 27 of the latest 30 runs failed; the three successes were from February. | Do not enable required checks until the reconciled workflow is green, then protect branches immediately. |
| Slow feedback | The 30 runs represent 335.2 elapsed minutes, averaging 670.3 seconds each. | Fail fast on policy/format/type checks and share the Docker build graph. |
| Duplicate validation | 30 runs covered only 27 unique commit SHAs; `push` and `pull_request` tested several identical SHAs. | Separate pre-merge validation from post-merge integrity and use concurrency cancellation. |
| Repeated setup | Four jobs separately check out, set up Python/Poetry, restore a full virtualenv, and install dependencies. | Use the repository's exact Docker gate and BuildKit cache instead of four drifting host environments. |
| Critical soft failures | Migration uses `\|\| echo`; Safety and Codecov allow failures; tests require only 80% coverage. | Remove bypasses and enforce the local 100% line/branch, migration, security, and audit contract. |
| No frontend evidence | The workflow does not lint, type-check, audit, build, accessibility-test, or browser-test the existing UI. | Run the complete frontend and isolated development/production browser gates. |
| Mutable actions | Actions use moving major tags such as `@v4` and `@v5`. | Pin every action to a verified full commit SHA. GitHub states that this is the only immutable action reference. |
| No cancellation | No workflow concurrency group is defined. | Cancel superseded feature/PR runs while retaining protected release runs. |
| No active protection | The `main` ruleset exists but is disabled; branch protection API returns no active protection. | Enable reviewed, green, no-direct-write promotion after the first reconciled green run. |

GitHub's [secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use)
requires full-length commit SHAs for immutable third-party actions. Its
[concurrency guidance](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
supports canceling superseded work. Path filters require care: GitHub warns that a skipped required
workflow can remain pending, so GapSense should keep one always-created required workflow and make
job selection change-aware inside it rather than filtering the required workflow away. See
[workflow triggering](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

## Branch and Promotion Model

| Branch | Purpose | Entry | Exit |
| --- | --- | --- | --- |
| `main` | Protected, releasable product history | Reviewed PR or merge queue only | Release Please observes conventional commits; no direct feature work. |
| `develop` | Temporary integration branch for the current large remote/local reconciliation and future genuinely coupled programmes | Reviewed `feature/*` PR with green checks | Promote through a reviewed PR to `main`; retire if it becomes a permanent queue or duplicate-CI source. |
| `feature/<scope>` | One bounded product or engineering slice | Branch from the current integration target | Delete after reviewed merge; never release directly. |
| `release/<version>` | Exceptional, time-bounded stabilization when a multi-party release needs a freeze | Cut from `main` or approved `develop` state | Only fixes and release evidence; merge/backport and delete. Release Please remains the version authority. |
| `hotfix/<scope>` | Urgent correction to a released version | Branch from the affected `main` tag | Full gate, reviewed merge to `main`, then reconcile into active integration work. |

Prefer short-lived feature branches and a protected trunk. `develop` and `release/*` are tools for
coordination, not permanent parking places. A branch that has no owner, current purpose, or
time-bound exit becomes a task-list finding.

## Hosted CI Shape

### Events

- `pull_request` into `main` or `develop`: the required validation run;
- `merge_group`: the same validation for a merge queue;
- `workflow_dispatch`: an explicitly requested validation run, including the Release Please
  workflow's validation dispatch for a generated release pull request;
- `push` to `main`: Release Please only, without duplicating the full application suite;
- a bounded scheduled deep security/reproducibility run only when it adds evidence not already
  produced per change;
- no deployment event while the deployment hold remains active.

### Required validation graph

The initial implementation deliberately uses one repository-owned Docker entry point instead of a
premature multi-job graph:

1. A classifier selects either the documentation path or the complete path.
2. Documentation-only changes still validate Compose, workflows, immutable action pins, release
   policy, Markdown, secrets, and whitespace without running the application suites.
3. All other changes run `scripts/ci.sh full`, which delegates to the exact strict local Docker
   gate against disposable PostgreSQL and isolated frontend test services.
4. Backend and frontend executable code retain 100% line and branch coverage; browser evidence
   covers development and production builds, accessibility, keyboard use, responsive layouts,
   visual regressions, console errors, and security headers.
5. Hosted validation mounts a public two-country presence fixture. It proves the platform's
   fail-closed data contract without copying proprietary curriculum artifacts into this repository
   or depending on a private checkout token. It does not claim curriculum completeness.
6. The single required workflow fails if its selected path fails; no critical step is soft-failed.

Use a workflow-scoped concurrency key based on the pull request/head ref and cancel superseded
feature work. Do not cancel an in-progress release promotion. Keep artifacts only on failure or for
short-lived release evidence, with explicit small retention periods. A cache is an optimization,
never an input that correctness requires.

## Version and Release Management

Use Semantic Versioning and Conventional Commits. The first reconciliation release remains
`0.x` until GapSense has validated public API/product compatibility expectations.

Release Please uses a manifest configuration and one synchronized GapSense platform version
propagated to:

- root Python package metadata;
- `src/gapsense/__init__.py`;
- frontend `package.json`;
- API/service identity responses;
- container labels and built-artifact metadata;
- `CHANGELOG.md` and Git tag.

Release Please parses Conventional Commits, maintains a release PR, and creates the release when
that PR is merged. Its official documentation recommends manifest configuration for advanced and
multi-component use; see the
[Release Please action](https://github.com/googleapis/release-please-action) and
[manifest releaser](https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md).

The release workflow must:

- pin Release Please to a reviewed full commit SHA;
- use the minimum write permissions only in the release job;
- create version/changelog PRs but never deploy;
- ensure release PRs receive the normal required CI checks;
- avoid a broad personal access token; the release workflow uses its narrowly scoped
  `GITHUB_TOKEN` and dispatches the required CI workflow for the generated release-PR branch
  because events created with that token do not start another workflow automatically;
- produce checksums, an SBOM, provenance, and reproducibility verification before a public tag is
  considered complete.

The Release Please and checkout actions are pinned to reviewed full commit SHAs. Repository policy
tests enforce the action allowlist, workflow permissions, release configuration, bootstrap commit,
and synchronized `0.1.0` version in Python and frontend metadata. Release automation creates no
deployment and publishes no application artifact.

## Implementation Sequence

1. Reconcile remote `main` on the dedicated `chore/remote-main-reconciliation` branch so its
   history remains an ancestor and the replacement is reviewable.
2. Add the public synthetic curriculum fixture, workflow-policy tests, immutable workflows, and
   synchronized Release Please configuration.
3. Run the exact full gate locally in Docker, commit the coherent milestone, and let the pre-push
   hook repeat that evidence from a clean worktree.
4. Push the feature branch once, observe the single hosted run, open and review the reconciliation
   PR, and merge only when every required check is green.
5. Enable appropriate branch protection/rulesets after the reconciled workflow has proved green.
6. Let Release Please open a distinct release PR; review its version and changelog evidence rather
   than merging it automatically.
7. Keep production deployment disabled. WhatsApp remains the final product programme.
