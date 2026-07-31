# Adding a Country to GapSense Platform

Adding a country is a paired data and platform contract change. The private data repository owns
official curriculum identity and evidence; the platform validates and renders only a pinned,
sanitized release.

## 1. Complete the Data Contract First

Follow the sibling data repository's `docs/ADDING_A_COUNTRY.md`. The candidate must provide:

- every exact country/phase/level/subject catalogue cell;
- official authority names, URLs, scope notes, editions, and validity dates;
- source records and artifact/page counts;
- an explicit `extracted`, `located`, or missing boundary for every cell;
- page-complete projections and country-native graphs for extracted cells;
- immutable catalogue, source, node, and graph hashes.

Do not infer availability from directories or source-record counts.

## 2. Extend Backend Domain Validation

Update the curriculum catalogue, source inventory, release manifest, coverage, and detail
validators under TDD. Replace any Ghana/Uganda-only enum or authority allowlist only with the exact
new country/authority contract; do not loosen it to arbitrary strings.

The backend must:

- build one matrix entry for every exact catalogue cell;
- overlay only the release record with the same full identity;
- validate paths, hashes, bytes, page counts, hierarchy, source locators, dates, rights, and review
  states;
- preserve new country-native section kinds and titles without data loss;
- return an explicit authority-only detail boundary without invented nodes;
- fail closed on duplicates, detached nodes, unsafe paths, malformed payloads, and stale editions.

Add positive and negative tests and retain 100% line and branch coverage.

## 3. Extend the Frontend Contract

Update `frontend/src/services/coverage.ts`, `frontend/src/services/details.ts`, and the curriculum
components so the new code, name, authority, levels, subjects, statuses, extraction methods,
source records, and native section kinds are validated before rendering.

Current Ghana/Uganda slug selection in `CurriculumExplorer.tsx` is explicit. Before a third country,
move the API slug into the validated coverage contract or an exhaustive country registry; do not
add another implicit ternary.

The UI must:

- offer every release-qualified country/level/subject combination;
- keep every official catalogue cell and source record discoverable;
- render complete selected trees through progressive disclosure;
- make every control purposeful and deterministic;
- abort superseded requests and reject response-identity mismatches;
- state machine review, rights, prerequisite, and authority-only boundaries plainly;
- preserve keyboard, screen-reader, touch, forced-colour, reduced-motion, 320-pixel, and theme
  behavior.

## 4. Update the Public-Safe Fixture

Copy only approved, sanitized catalogue and source metadata into
`fixtures/public-data`. Pin exact hashes and retain an explicit empty projection manifest unless
rights and review permit public normalized evidence.

Never copy private PDFs, substantial curriculum text, internal paths exposed through the API,
learner data, or unreviewed assessment content into the fixture.

Test the local/private candidate and public fixture as distinct deployment profiles.

## 5. Extend Exhaustive Instrumentation

The E2E matrix must derive the expected country/level/subject set from the validated API and then
prove every exact cell in desktop and mobile Chromium. For each extracted cell, assert:

- exact release, country, phase, level, and subject identity;
- extraction status and method;
- non-empty structural and page records;
- rendered section and page counts equal the API;
- source provenance and extraction boundary are visible.

For each authority-only cell, assert zero sections/pages and a visible, non-invented publication
boundary.

Also exercise every supported assessment role and country, persistence/reset, invalid/stale state,
offline/retry behavior, learner and educator artifacts, accessibility, security headers,
responsive layout, themes, and reviewed screenshots.

## 6. Run the Paired Gate

Run the platform's strict Docker gate plus the sibling data gate. At minimum, retain:

- 100% backend line and branch coverage;
- 100% frontend statements, branches, functions, and lines;
- 100% data-script line, branch, and function coverage;
- exhaustive browser identity coverage;
- zero formatting, lint, typing, build, dependency-audit, policy, or whitespace failures.

Update both repositories' `TASKS.md` and `PROGRESS.md` only after the complete paired result is
known. Commit and promote through separate reviewed pull requests; production promotion remains a
separate explicit decision.
