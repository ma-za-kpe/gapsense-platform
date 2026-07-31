# GapSense Platform Progress

Last updated: 2026-07-30

## Current Milestone

**Branch:** `fix/curriculum-data-integrity`

**Paired data branch:** `fix/curriculum-data-integrity`

**Objective:** Consume the complete local Ghana/Uganda candidate deterministically and make
`/curriculum` represent every official country, level, subject, source record, evidence state, and
country-native tree without blank controls or invented data.

**Status:** The paired branches are pushed, both hosted CI gates are green, and the verified
public-safe platform commit is live on Vercel production. Draft PR #41 remains unmerged and no
release was created.

## Exact Local Runtime

| Country | Levels | Catalogue cells | Extracted cells | Authority-only cells | Source records | Artifacts | Official pages |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ghana | 5 | 67 | 67 | 0 | 63 | 61 | 9,052 |
| Uganda | 6 | 109 | 103 | 6 | 77 | 74 | 6,088 |
| **Total** | **11** | **176** | **170** | **6** | **140** | **135** | **15,140** |

The local Docker API consumes `curriculum-2026-07-30-candidate.4` from the sibling private data
repository. Its 170 extracted cells expose 25,999 complete page records and 16,192 page-traced
country-native structural sections. The six authority-only cells are selectable catalogue entries
with an explicit publication boundary and zero invented nodes.

## Implemented Consumption Boundary

- The backend loads and validates one immutable manifest snapshot at startup and rechecks pinned
  catalogue, source-ledger, node, graph, identity, hash, path, page, hierarchy, and extraction
  boundaries before serving detail.
- Coverage starts from all 176 exact official cells and overlays only the matching release record.
  No phase-wide inference or folder-presence heuristic can create availability.
- Detail responses preserve country-native section kinds and titles, complete page text, exact
  source IDs/pages, curriculum paths, extraction method, review state, and honest prerequisite
  status.
- Runtime frontend validators reject malformed, duplicated, detached, mismatched, or stale
  coverage/detail/source payloads.
- Every non-authority-only country/level/subject combination is selectable. Selector changes abort
  superseded requests, reject response-identity mismatches, and cannot display stale detail.
- `/curriculum` renders all 176 catalogue cells, all 140 source records, and the complete selected
  tree. Source pages and nested sections use progressive disclosure; every visible control has a
  purposeful outcome.
- The old `None recorded` and `no safe extracted detail` language is gone. Unstated prerequisites
  are described as not stated by the authority, and authority-only areas explain exactly why no
  tree is invented.
- The home coverage panels keep all 52 Ghana and 70 Uganda evidence-subject records available
  behind explicit disclosure controls, restoring compact mobile layout without hiding data.
- The public-safe fixture intentionally has the same 176-cell catalogue and sanitized 140-source
  ledger but zero projections or official text. Local Docker mounts the private sibling data
  repository and displays the full candidate.

## Validation Evidence

- Backend: 212 tests, 1,727 statements and 414 branches, 100% coverage.
- Frontend: 280 tests, 100% statements/branches/functions/lines; Prettier, ESLint, TypeScript,
  production build, and `npm audit` all green.
- Data: 64 tests, 100% line/branch/function coverage; 176 release records, 140 sources,
  135 artifacts, 15,140 official pages, and 342 pinned release artifacts verified.
- Browser: 32 desktop/mobile tests. Two exhaustive matrices traverse all 176 cells and compare
  exact live API identity/status/method/counts with rendered detail. Thirty additional tests cover
  every role/country sample path, persistence/reset, assessment entry, distinct learner and answer
  guide downloads, accessibility, keyboard/touch, forced colours, themes, 320-pixel reflow, all
  public routes, security headers, and reviewed screenshots.
- Visual audit: refreshed Ghana Kindergarten, Uganda P1-P3 Mathematics, Uganda Advanced German,
  and Uganda authority-only screenshots show purposeful country-native output with no promoted
  contents-page noise, bare `theme` branch, replacement character, or unsafe-detail message in the
  sampled visible UI.
- Final strict platform gate: backend 212/212, frontend 280/280, development browser 32/32, and
  production browser 32/32 all passed in one Docker pre-commit run with exact 100% executable
  coverage, migrations, typing, formatting, security, dependency, Markdown, and whitespace gates.
  The exhaustive E2E contract now distinguishes a purposeful public-fixture `404` for a catalogue
  cell without publishable detail from a private extracted or authority-located detail response.
- Task-debt audit: no platform source/configuration/test `TODO` or `FIXME` marker was found. The
  ordered task-list reconciliation, bounded project cleanup, commit/push, dual hosted-CI
  monitoring, and post-green `vercel --prod` verification sequence is pinned in `TASKS.md`.
- Added tested `/evidence`, `/privacy`, and `/terms` trust pages with dated policies, table-of-
  contents navigation, disclaimers, known blockers, acceptable-use and open-source/third-party
  rights boundaries, correction guidance, and footer/README links. Frontend validation remains
  280/280 at exact 100%; the new routes pass unit accessibility and Docker Playwright checks.
- Added exact Vercel rewrites and a repository contract test for all three trust routes so direct
  production requests cannot fall through to a platform 404.
- Pushed platform implementation commit `50188cd86309ecc9172a4b55477ed258c8081e5d` to
  `fix/curriculum-data-integrity`; draft PR #41 carries the implementation and this final evidence
  ledger.
- GitHub Actions run `30606212982` completed successfully. Its Required job passed the
  repository-owned Docker gate in 11 minutes 3 seconds.
- The restored local sibling-data runtime passed 26/26 non-visual Playwright journeys across
  desktop and mobile in 9 minutes. These include exhaustive all-176-cell selection, assessment
  creation and downloads, trust routes, accessibility, responsive behavior, and security. The six
  pixel-baseline assertions remain deliberately bound to the deterministic public fixture; the
  complete public-fixture suite passed 32/32 in the strict gate and hosted CI.
- Vercel CLI 58.4.4 deployed the verified platform commit as
  `dpl_8VC3Xo2VVGMdo1wXJGAoJkGKf4U4`. Vercel reports `Ready`; the immutable deployment is
  `https://gapsense-c0fg0duu6-popos-projects-fb891440.vercel.app`, the prior deployment remains the
  rollback target, and the custom domain is `https://gapsense.org`.
- Live verification returned HTTP 200 for `/`, `/curriculum`, `/assessment`, `/about`,
  `/evidence`, `/privacy`, `/terms`, `/robots.txt`, `/api/v1/health/ready`, and
  `/api/v1/curriculum/coverage`. Readiness is `ready`; all six configured security headers are
  present. The public boundary exposes the complete 176-cell authority catalogue and sanitized
  140-record source inventory with zero projections, raw PDFs, or source text.

## Honest Remaining Holds

- The 170 local trees are machine extracted, not educator reviewed. The UI states that boundary.
- Six NCDC catalogue areas have no complete downloadable official artifact on the current public
  indexes: four Primary 4 areas plus Advanced Physical Education and Principal ICT.
- Replacement-glyph and complex-table fidelity review remains for affected extracted source pages.
- Rights review prevents shipping raw PDFs or substantial curriculum text in the public fixture.
- Assessment generation still uses labelled illustrative banks; it does not yet generate from the
  unreviewed local curriculum trees.
- Production is refreshed and still uses the intentionally projection-empty public fixture.

## Next Paired Slice

1. Reconcile extraction-fidelity exceptions against page renders.
2. Complete Ghanaian and Ugandan educator/curriculum-specialist review.
3. Add a reviewed curriculum-to-assessment domain service with exhaustive failure and edge-case
   tests.
4. Resolve rights and publication policy before exposing any private projection publicly.
5. Acquire and pin the six authority-only syllabuses when NCDC supplies authoritative bytes.
6. Keep the paired draft PRs reviewable; merge only through the protected review workflow and
   rerun the release/deployment gate for any changed SHA.
