# Remote Main Reconciliation

Date: 2026-07-22

## Purpose

This record governs the local reconciliation of platform commit `b24ec44` with the tested
web-first line at local merge commit `bbd7705`.

The remote commit is retained as a merge parent. Every historical file therefore remains
recoverable from Git, while the active tree accepts executable code only after it meets the
current product, security, Docker, and 100% coverage contract. This is an evidence quarantine,
not a claim that the historical work has no value.

The reconciliation branch is `chore/remote-main-reconciliation`. It must not be pushed while the
explicit remote-push hold remains active.

## Decision Rules

1. Preserve `b24ec44` as a merge parent so source material cannot be lost.
2. Do not activate code that depends on external model keys, production infrastructure,
   WhatsApp, writable source mounts, copied proprietary data, or unsupported claims.
3. Port valuable behaviour in small TDD slices into the current architecture.
4. Create forward migrations from the proven schema; do not restore unsafe or divergent
   historical migration state merely to make old code importable.
5. Keep the React/Vite web shell as the only public frontend. Historical pages are design and
   workflow references, not a second product.
6. Keep curriculum evidence in the private sibling data repository and mount it read-only.
7. Treat images, school lists, and learner examples as unavailable until provenance, consent,
   privacy, and licensing are verified.
8. Keep deployment on hold and WhatsApp as the final product programme.

## Capability Disposition

| Historical capability | Source area in `b24ec44` | Disposition |
| --- | --- | --- |
| Curriculum explorer | `public/curriculum.html`, curriculum API and templates | Rebuild in the tested web shell against a typed, versioned, country-aware API and verified sibling-repository data. |
| Teacher diagnostic workspace | demo pages, diagnostic routes and services | Rebuild web-first after the diagnostic domain contract, confidence model, abstention rules, and evaluation set exist. |
| Class and learner reports | teacher and student report pages/services | Rebuild as accessible responsive routes with synthetic local data, export tests, and no unsupported impact claims. |
| Architecture and trust story | developer page and architecture copy | Retain the concise explanatory pattern, but rewrite it around the actual local-first architecture and current evidence. |
| Country and grade normalization | country/grade utilities and multi-country schema | Reimplement from authoritative Ghana and Uganda terminology with property tests and forward migrations. Do not retain speculative Kenya/Nigeria support. |
| Curriculum and diagnostic APIs | `src/gapsense/api/v1` | Port endpoint-by-endpoint behind typed contracts, authorization boundaries, fail-closed validation, and 100% tests. |
| Diagnostic algorithms | adaptive, gap-analysis, question and response modules | Port only with curriculum fixtures, invariant/property tests, explainability, error-cost analysis, and educator review. |
| AI prompt and provider layer | AI clients, prompt services, embedding services | Replace external-key providers with a local Ollama abstraction and deterministic fake. Measure quality, latency, memory, licensing, and numerical equivalence. |
| Media and exercise-book analysis | media, image orchestration and scanner modules | Defer until child-data privacy, consent, retention, abuse, accessibility, and evidence-capture research is complete. |
| School, teacher, parent and learner flows | API, schema, service and engagement modules | Redesign for local mock authentication and web roles first. Port only the domain behaviour that survives user and security research. |
| Workers, processing ledger and vector retrieval | worker/jobs, ledger and pgvector migrations | Reconsider after measured workload evidence. Prefer simple deterministic processing before adding operational or numerical surface. |
| WhatsApp adapters and flows | engagement WhatsApp modules, webhook and channel tests | Preserve in the merge parent only. Revalidate and rebuild as the final programme after the web and deployment-readiness gates. |
| Historical migrations | revisions after the current proven schema | Do not activate as a chain. Review intent per accepted feature and create new reversible forward migrations with rebuild and drift proof. |
| Historical public UI | `public/`, Vite root files and Jinja demo templates | Retire from the active tree after the visual/capability audit. Do not ship two frontends. |
| Copied curriculum and prompt files | platform `data/` | Do not accept. The private sibling repository is the canonical evidence boundary. |
| AWS, Vercel and deployment material | CDK, deployment scripts and Vercel files | Keep on hold. Reassess hosting from measured web requirements; never expose provider secrets or imply deployment readiness. |
| Historical CI workflow | `.github/workflows/ci.yml` | Replace before any push with the optimized, change-aware, immutable-action design in the delivery model. |
| Historical images and school CSVs | pitch images and root CSV/image files | Do not accept without provenance, consent, licensing, data-minimization, and repository-placement review. |
| Historical plans and generated specs | root reports, `.kiro`, legacy improvement docs | Keep available through the merge parent; promote only independently verified requirements into active governance and `TASKS.md`. |

## Explicitly Retired Assumptions

- Ghana-only, Mathematics-only, or WhatsApp-first product positioning
- UNICEF identity, cohort labeling, implied affiliation, endorsement, or calls to action
- Anthropic, Grok, or OpenAI credentials as local runtime requirements
- production URLs, readiness statements, cost claims, impact claims, and completion percentages
  that have not been re-verified
- proprietary-only repository language for the platform while an open-source contribution model
  is being designed
- host Python/Node runtimes, writable source mounts, 80% coverage, skipped critical checks, and
  `--no-verify` guidance
- duplicated curriculum source documents or prompts in the platform repository

## Retrieval Pattern

Historical material can be inspected without restoring it to the active tree:

```powershell
git show b24ec44:path/to/file
git diff b24ec44..HEAD -- path/to/file
```

Any migration from that parent must begin with a scoped `TASKS.md` item and failing tests, then
pass the complete Docker gate before a milestone commit.

## Completion Evidence

This reconciliation is complete only when:

- every capability row is linked to completed evidence or an explicit product retirement
  decision;
- no active product copy or metadata implies Ghana-only or UNICEF positioning;
- all accepted behaviour has 100% line and branch coverage plus applicable integration,
  accessibility, browser, security, migration, and performance evidence;
- the active tree contains one public frontend and one canonical curriculum-data boundary;
- the exact strict Docker gate passes on the final merge tree;
- the branch is merged into local `main`; and
- no remote push, hosted workflow, release, deployment, or WhatsApp activation has occurred.
