# Ghana and Uganda Curriculum Coverage Audit

Audit date: 2026-07-30

Conclusion: the local `/curriculum` page represents all 176 official catalogue cells, all
140 source records, and complete country-native trees for all 170 cells with available official
source bytes. Six NCDC catalogue areas remain authority-only because the current public indexes do
not expose complete syllabus artifacts. Nothing is educator reviewed or approved for public
curriculum-text distribution.

## Exact Local Scope

| Country | Levels | Catalogue cells | Extracted cells | Authority-only cells | Source records | Artifacts | Official pages |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ghana | 5 | 67 | 67 | 0 | 63 | 61 | 9,052 |
| Uganda | 6 | 109 | 103 | 6 | 77 | 74 | 6,088 |
| **Total** | **11** | **176** | **170** | **6** | **140** | **135** | **15,140** |

Candidate `curriculum-2026-07-30-candidate.4` retains 25,999 projected page records and
16,192 page-traced sections across the 170 extracted cells.

## Consumption Path

```text
gapsense-data release manifest
  -> exact catalogue + source ledger + page projections + native graphs
    -> backend startup validation and immutable snapshot
      -> exact 176-cell coverage matrix and detail API
        -> frontend runtime validation
          -> deterministic selectors, complete selected tree, catalogue, and source inventory
```

1. Local Docker mounts the sibling private data repository read-only.
2. The backend validates hashes, exact case, paths, page counts, identities, dates, source
   locators, hierarchy, extraction methods, rights, and review states.
3. Coverage begins with all 176 catalogue cells and overlays only the exact matching release
   record. No folder or phase-wide inference creates availability.
4. Detail responses retain country-native section kinds, titles, paths, complete page evidence,
   source IDs/pages, extraction method, review state, and honest prerequisite status.
5. The frontend rejects malformed, duplicate, detached, mismatched, or stale payloads before
   rendering.
6. Selector changes abort superseded requests. Every selectable extracted combination renders
   exact API section/page counts; authority-only cells render a publication boundary and zero
   invented nodes.

The API snapshot is immutable for one process lifetime. Restart `web` after data changes; rebuild
and recreate the frontend after UI changes.

## Local and Public Behavior

The local candidate exposes 170 private machine-extracted trees. The bundled public fixture carries
the same 176-cell official catalogue and sanitized 140-source ledger but an explicit zero-record
projection manifest. It contains no raw PDFs or official curriculum text.

This distinction explains why local Docker can display complete candidate trees while a hosted
public-fixture build remains a truthful catalogue/source boundary.

## User-Facing Behavior

- Country, level, and subject controls expose every release-qualified local combination.
- The selected tree displays native hierarchy and complete source pages through progressive
  disclosure.
- `None recorded` is not used for unstated prerequisites; the UI says the authority does not state
  a relationship.
- `no safe extracted detail` is not shown for an extracted combination.
- Authority-only areas remain catalogue-visible and explain why no tree is invented.
- All 176 catalogue cells and 140 source records have deterministic DOM identities.
- The home page keeps all 52 Ghana and 70 Uganda evidence-subject records available behind explicit
  controls while staying compact on mobile.

## Validation

- Backend: 212 tests, 100% line and branch coverage.
- Frontend: 280 tests, 100% statements/branches/functions/lines; formatting, lint, typing, build,
  and dependency audit pass.
- Data: 64 tests, 100% line/branch/function coverage; 176 release records, 140 sources,
  135 artifacts, and 342 pinned artifacts validated.
- Browser: 32 tests across desktop and mobile. Two traverse all 176 cells and compare live API
  identity/status/method/counts with rendered output. Thirty cover role/country sample paths,
  persistence/reset, real learner and educator downloads, accessibility, keyboard/touch, forced
  colours, themes, 320-pixel reflow, routes, security headers, and reviewed screenshots.

## Remaining Holds

- The 170 trees are machine extracted and not educator reviewed.
- Replacement glyphs and complex multi-column reading order require source-render reconciliation
  on affected pages.
- Rights review blocks public redistribution of raw PDFs and substantial extracted text.
- Assessment generation remains illustrative and does not yet consume unreviewed trees.
- Six NCDC areas have no complete public artifact: four Primary 4 areas, Advanced Physical
  Education, and Advanced Principal ICT.

## Official Scope References

- [NaCCA standards-based curriculum](https://nacca.gov.gh/learning-areas-subjects/new-standards-based-curriculum-2019/)
- [NaCCA Common Core Programme](https://nacca.gov.gh/common-core-programme-ccp/)
- [NaCCA secondary curriculum](https://nacca.gov.gh/secondary-education-curriculum/)
- [NCDC directorates](https://ncdc.go.ug/directorates/)
- [NCDC resources](https://ncdc.go.ug/resource/)
- [NCDC document library](https://ncdc.go.ug/document-library/)
