# Delivery, Branching, Versioning, and Release Model

Date: 2026-07-22
Status: Proposed target model; remote mutation and deployment remain on hold

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
- `push` to `main`: a small post-merge integrity/release-input check, not a duplicate full suite;
- `workflow_dispatch`: an explicitly requested full diagnostic run;
- a bounded scheduled deep security/reproducibility run only when it adds evidence not already
  produced per change;
- no deployment event while the deployment hold remains active.

### Required validation graph

1. A cheap policy job validates workflow files, immutable action pins, conventional PR title,
   locks, Compose configuration, Markdown, links, secrets, conflict markers, and changed paths.
2. Documentation-only changes still run policy, Markdown/link, secrets, and documentation tests,
   then report the same required aggregate status without building unrelated images.
3. Application changes run the exact Docker migration and backend gate against disposable
   PostgreSQL, with 100% line and branch coverage.
4. Frontend changes run exact lockfile validation, 100% statement/branch/function/line coverage,
   dependency audit, build, and isolated development and immutable-production Playwright/axe,
   responsive, keyboard, visual, console, and security-header suites.
5. Curriculum-affecting changes fail closed on schema, source, hash, graph, coverage, and review
   evidence; CI must use a safe public synthetic fixture rather than depend on the private data
   repository or a secret checkout token.
6. One aggregate job reports success only when every selected required job succeeds or is
   explicitly and correctly not applicable.

Use a workflow-scoped concurrency key based on the pull request/head ref and cancel superseded
feature work. Do not cancel an in-progress release promotion. Keep artifacts only on failure or for
short-lived release evidence, with explicit small retention periods. A cache is an optimization,
never an input that correctness requires.

## Version and Release Management

Use Semantic Versioning and Conventional Commits. The first reconciliation release remains
`0.x` until GapSense has validated public API/product compatibility expectations.

Adopt Release Please's manifest configuration after choosing the canonical version source. The
preferred model is one GapSense platform version propagated to:

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
- avoid a broad personal access token; evaluate a least-privilege GitHub App token if the default
  `GITHUB_TOKEN` cannot trigger required release-PR checks;
- produce checksums, an SBOM, provenance, and reproducibility verification before a public tag is
  considered complete.

## Implementation Sequence

1. Finish and commit the current local web-entry milestone.
2. Reconcile remote `main` on a dedicated local branch so the existing workflow and application
   history are not silently replaced.
3. Add a public synthetic curriculum fixture for hosted validation.
4. Write workflow-policy tests, then replace the remote CI graph locally.
5. Run the exact CI-equivalent path locally in Docker and inspect generated workflow syntax.
6. Add Release Please configuration and version-consistency tests without creating a release.
7. Resolve the explicit remote-push hold before the first feature-branch push.
8. Push one feature branch, observe the single hosted run, fix it until green, then enable branch
   protection/rulesets and open a reviewed PR.
9. Keep production deployment disabled. WhatsApp remains the final product programme.
