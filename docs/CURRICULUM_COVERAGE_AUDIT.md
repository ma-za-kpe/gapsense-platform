# Ghana and Uganda Curriculum Coverage Audit

**Audit date:** 2026-07-22
**Answer:** No. Neither country's curriculum extraction is complete under the current goal
of covering all official subjects and education levels.

## What This Audit Means by Complete

A country is not complete because one subject has deep data or because a README says
“100%.” Completion requires:

1. an authoritative inventory of official levels, phases, subjects, and pathways;
2. source documents and version provenance;
3. normalized learning outcomes for every in-scope subject;
4. prerequisite and diagnostic enrichment where GapSense claims diagnostic coverage;
5. structural validation and internally consistent counts;
6. domain, cultural, and pilot validation;
7. a versioned release manifest consumable by the platform.

This audit inspected repository structure and machine-readable node containers. It did not
endorse the educational validity of the existing prerequisite judgments.

## Repository Coverage Found

### Ghana

| Repository folder | Claimed level | Machine-observed state | Audit conclusion |
| --- | --- | --- | --- |
| `primary/mathematics` | Primary B1-B6, with some JHS material | Six expected artifact families exist, but the populated-node container has 11 keys while README and metadata claims refer to several different totals | Extracted/enriched subset; reconciliation required |
| `primary/english` | Primary B1-B6 | Six artifact families; 58 machine-observed node keys versus metadata claiming 60 | Substantial, not reconciled or externally validated |
| `primary/science` | Primary B1-B6 | Six artifact families; 54 machine-observed node keys | Substantial, not externally validated |
| `secondary/mathematics` | JHS B7-B9 | Six artifact families; 59 machine-observed node keys; README also contains conflicting 47/59 claims | Substantial, reconciliation required |
| `secondary/english` | SHS 1-3 | Six artifact families; 41 machine-observed node keys; explicitly says JHS English is missing | SHS subset; JHS gap remains |
| `secondary/general-science` | SHS 1-3 | Six artifact families; 28 machine-observed node keys; README says 0 populated while data metadata says complete | Reconciliation required |

No structured coverage was found for Kindergarten or most official Primary, JHS, SHS,
SHTS, STEM, TVET, or tertiary subjects and pathways.

The official NaCCA curriculum overview defines five phases: Kindergarten, lower Primary,
upper Primary, JHS, and SHS. It lists Primary curricula beyond the current three folders,
including History, Creative Arts, Religious and Moral Education, Physical Education,
French, Ghanaian Language, and Computing. NaCCA also notes a 2024/25 integration change
for Our World Our People. See the [NaCCA curriculum overview](https://nacca.gov.gh/curriculum/).

NaCCA's current [secondary curriculum catalogue](https://nacca.gov.gh/secondary-education-curriculum/)
contains a much wider SHS/SHTS/STEM menu, including additional mathematics, agriculture,
languages, arts, sciences, computing, engineering, humanities, social studies, physical
education, robotics, and other pathways. The exact authoritative inventory and subject
combination rules must be captured before child extraction tasks are generated.

### Uganda

| Repository folder | Claimed level | Machine-observed state | Audit conclusion |
| --- | --- | --- | --- |
| `primary/mathematics` | P1-P3 thematic Mathematics | One prerequisite-style graph plus thematic mappings and extraction summaries; it does not have the six canonical artifact families or a populated-node release file | Extraction milestone in uncommitted work; validation and normalization pending |
| `secondary/mathematics` | Unspecified | Empty | Not started |

No structured coverage was found for Pre-primary, other P1-P3 learning areas, P4, P5-P7,
Lower Secondary subjects, A-Level subjects, TVET, or tertiary curricula.

The NCDC describes Primary as three phases: P1-P3 thematic, P4 transition, and P5-P7
subject-based. P4-P7 includes English, Mathematics, Social Studies, Integrated Science,
Local Language, Creative Arts and Physical Education learning areas, and Religious
Education. See the [NCDC directorates and curriculum structure](https://ncdc.go.ug/directorates/)
and [NCDC Primary FAQ](https://ncdc.go.ug/faq/).

NCDC describes 35 subjects in the Lower Secondary menu, with compulsory and elective
combinations varying between S1-S2 and S3-S4. The official
[Lower Secondary Curriculum Framework](https://ncdc.go.ug/wp-content/uploads/2024/03/Curriculum_Framework.pdf)
and [secondary catalogue](https://ncdc.go.ug/book-category/secondary/) are the starting
points. NCDC also published aligned A-Level curriculum materials in 2025, so S5-S6 must be
inventoried against the current catalogue rather than legacy assumptions.

## Important Status Distinctions

The Uganda P1-P3 Mathematics artifacts describe themselves as production-ready while also
listing teacher, NCDC, UWEZO, and learner validation as future work. Under the current Ways
of Working, that material can be described as extracted and partially structured, not
released.

The Ghana datasets have significant depth, but contradictory counts and stale status text
mean completion must be recomputed from data. Structural completion would still not prove
domain or pilot validity.

## Required Next Actions

The canonical tasks live in [`TASKS.md`](../TASKS.md). Immediate curriculum actions are:

1. Define the canonical curriculum schema and maturity states.
2. Build machine-generated inventories from current official authority catalogues.
3. Reconcile all existing Ghana counts and statuses.
4. Validate and normalize the uncommitted Uganda P1-P3 Mathematics work on its own branch.
5. Generate one child task per official country/phase/subject combination.
6. Acquire official sources and proceed depth-first through those child tasks.
7. Recruit country and subject reviewers before any release claim.

## Audit Limitations

- Official catalogues change; inventories must record access and curriculum version dates.
- “All subjects” can differ between compulsory, elective, language, vocational, and school
  pathway menus.
- Tertiary institutions may not share one national outcome-level curriculum; scope must be
  researched with the relevant authorities.
- This audit did not reproduce or validate copyrighted curriculum text.
