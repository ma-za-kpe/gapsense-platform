# Analytics and Search Model

Date: 2026-07-23

## Decision

GapSense uses a first-party, same-origin, aggregate-only analytics boundary and a build-time
search-publication boundary.

Both boundaries fail closed:

- analytics collection is `disabled` unless a local operator explicitly selects
  `local_aggregate`;
- search publication is `hold` unless a release build explicitly selects `public` and supplies
  an approved absolute HTTPS origin;
- production deployment, real-user collection, search-engine registration, sitemap submission,
  and release publication remain on hold.

This foundation adds no analytics vendor, advertising technology, cookie, persistent user
identifier, external font, or third-party script. It does not make analytics or search a hidden
requirement for the assessment-planning experience.

## What 100% Means

The following are deterministic contracts and must maintain 100% statements, branches, functions,
and lines coverage in application-owned executable code:

- every accepted event name;
- every analytics enable/disable and privacy-signal path;
- request shape, media type, declared-size, batch-count, and unknown-field rejection;
- aggregate counter behaviour under concurrent requests;
- every currently instrumented funnel action;
- search mode and public-origin validation;
- generated head metadata, canonical URL, `WebSite` structured data, `robots.txt`, sitemap, and
  CSP source hash;
- local/deployment-hold browser behaviour.

The following are outcomes, not code-coverage claims:

- whether a search engine crawls, indexes, ranks, or displays a result;
- whether structured data produces a search feature;
- traffic, conversion, retention, willingness to pay, or product-market fit;
- whether collected events represent the target population;
- legal compliance in a real operating context.

GapSense will never describe those outcomes as “100% SEO” or “100% analytics”. They require an
approved host, representative users, field evidence, webmaster tools, qualified legal/privacy
review, and ongoing measurement. Google explicitly describes sitemaps as hints and does not
guarantee structured-data display.

## Analytics Data Flow

```text
allowlisted UI action
        |
        | event name + schema version only
        v
same-origin /api/v1/analytics/events
        |
        | strict JSON, <= 4096 declared and streamed bytes, 1-20 events
        v
process-local event-name counters
```

The current sink retains no event rows. It only increments counters by event name. A process
restart clears the counters. There is no public summary endpoint, user-level profile, session
stitching, cohort join, export, processor, or cross-device identity.

The browser sends events with:

- `credentials: omit`;
- `Referrer-Policy: no-referrer`;
- no URL, path, query, hash, referrer, campaign, locale, device, IP, or timing property;
- no role, country, goal, answer, curriculum choice, school, learner, or educator value;
- no retry that can interrupt the underlying product action.

The web server and reverse proxy may still observe ordinary connection metadata needed to serve
an HTTP request. Before any real collection, operations must prove that access logs, error
tracking, infrastructure metrics, backups, and support tools do not convert the aggregate design
into identifying telemetry.

## Event Catalogue 1.0.0

| Event | Meaning | Property payload |
| --- | --- | --- |
| `entry_viewed` | Current public entry experience mounted once | None |
| `navigation_countries_selected` | A country-coverage navigation link was selected | None |
| `navigation_principles_selected` | The product-principles navigation link was selected | None |
| `navigation_planner_selected` | An assessment-planner call to action was selected | None |
| `planner_role_selected` | A role option was selected | Selected role is not sent |
| `planner_country_selected` | A country option was selected | Selected country is not sent |
| `planner_goal_selected` | A planning goal was selected | Selected goal is not sent |
| `planner_reviewed` | A complete anonymous plan was reviewed | Plan values are not sent |
| `planner_reset` | The reviewed planner was reset | None |
| `readiness_retry_selected` | The local evidence readiness retry was selected | None |
| `coverage_retry_selected` | The coverage-details retry was selected | None |

Adding or changing an event requires:

1. a named product question and decision owner;
2. proof that the question cannot be answered with less data;
3. data classification, lawful-basis, notice/choice, retention, access, deletion, and abuse review;
4. a versioned server and browser contract;
5. red-green tests at the domain, adapter, component, and applicable browser boundaries;
6. this catalogue and `TASKS.md` updated in the same reviewed slice.

Free text and arbitrary event properties are prohibited.

## Enablement and Privacy Signals

The interactive local Docker runtime maps `GAPSENSE_ANALYTICS_MODE` to both server and frontend
configuration. The default is `disabled`. The only other accepted value is `local_aggregate`, and
configuration rejects that value when the environment is staging or production. Immutable
production-style frontend artifacts also remain disabled while real collection is on hold.

Even in local aggregate mode, the browser sends nothing when any of these signals is active:

- Global Privacy Control;
- Do Not Track value `1`;
- the browser's reduced-data preference.

These are conservative product controls, not a claim that any one signal resolves every legal
obligation. A visible privacy choice, notice, retention policy, data-subject workflow, qualified
Ghana/Uganda review, and an operator-access design remain required before real collection.

## Analytics Threats and Controls

| Threat | Current control | Remaining gate |
| --- | --- | --- |
| PII or child data enters analytics | Fixed event enum; unknown fields rejected; no arbitrary properties | Inspect every future event and every infrastructure log |
| Small cohorts become identifiable | No dimensions or event rows; counters by name only | Define minimum aggregation thresholds before dimensions |
| Tracking becomes mandatory | Disabled default; transport failure is isolated from product action | Browser tests continue proving the product works with zero analytics |
| Cross-site tracking or vendor leakage | Same-origin endpoint; omitted credentials; no third-party dependency | Processor review before any adapter replacement |
| Endpoint abuse or memory pressure | 20-event model limit; application streaming byte ceiling; declared-size check; production Nginx 4 KiB limit | Add an evidence-based rate policy before hosting |
| Event-name probing exposes business data | No public counter endpoint | Design authenticated, purpose-limited operator access before dashboards |
| Access logs recreate identity | Event body is never logged by application code | Validate hosting/proxy log fields, retention, access, deletion, and IP handling |
| Analytics becomes dark-pattern optimisation | No advertising or selected-value profile | Ethics review and dignity metrics before experiments |

## Search Publication Contract

The Vite build has two modes.

### `hold` (default)

- emits a unique title, description, application name, Open Graph text, Twitter summary text, and
  theme information;
- emits `noindex, nofollow, noarchive`;
- emits `robots.txt` with `Disallow: /`;
- omits canonical URL, `og:url`, URL-bearing JSON-LD, and sitemap;
- returns a real `404 text/plain` for `/sitemap.xml`;
- makes no network request and loads no third-party search script.

This is the only permitted mode while deployment is on hold.

### `public` (future approved release)

The build fails unless `GAPSENSE_PUBLIC_ORIGIN` is:

- an absolute HTTPS origin;
- free of credentials, path, query, and fragment;
- not localhost or a loopback host.

An accepted public build emits:

- one root canonical URL;
- matching `og:url`;
- one `WebSite` JSON-LD object with the GapSense name, description, language, and canonical URL;
- an index-allowing robots directive;
- `robots.txt` with the canonical sitemap URL;
- a root-only XML sitemap;
- an exact SHA-256 CSP source for the generated JSON-LD block.

The current site has one real public information route, so the future sitemap contains one URL.
Country, phase, level, subject, assessment, and diagnostic URLs enter it only after those pages
contain unique, useful, evidence-backed content. GapSense will not generate thin keyword pages,
duplicate country variants, false curriculum-completeness claims, or structured data that is not
supported by visible page content.

## Search Promotion Checklist

Do not switch a build to `public` until all items are complete:

- production deployment hold explicitly lifted;
- canonical domain ownership and HTTPS verified;
- hosting choice, redirects, trailing slash, error pages, cache policy, and environment separation
  approved;
- privacy and child-safety reviews complete for any real analytics or logs;
- robots, sitemap, canonical, metadata, JSON-LD, CSP, and HTTP status contracts pass in the built
  production image;
- social preview image, favicon, and web-app asset provenance approved;
- Google Rich Results Test and URL Inspection completed where applicable;
- Search Console and Bing Webmaster ownership assigned to controlled organisation accounts;
- Ghana/Uganda mobile, low-bandwidth, accessibility, content, and cultural review complete;
- Core Web Vitals and bundle budgets pass on representative devices and networks;
- release notes state that indexing and ranking are monitored outcomes, never guarantees.

## Commercial Use

Analytics should answer product and commercial questions without profiling learners:

- Do visitors reach the anonymous planner?
- Where does the current three-step funnel lose momentum?
- Do users complete and restart a plan?
- Do readiness or coverage failures prevent progress?
- Which evidence-backed landing pages create qualified assessment or school-workflow demand?

Selected role, country, subject, level, school, and learner dimensions are deliberately absent from
this first boundary. Add a dimension only when a validated decision requires it and the privacy
review proves that aggregate thresholds, notice, access control, and retention make it acceptable.
Basic assessment correctness, learner dignity, privacy, export, and accessibility will never be
paywalled.

## Primary Research Basis

- [Google Search crawling and indexing overview](https://developers.google.com/search/docs/crawling-indexing)
- [Google guidance on canonical URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Google sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Google site-name and `WebSite` structured-data guidance](https://developers.google.com/search/docs/appearance/site-names)
- [Google structured-data guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)
- [MDN `sendBeacon` analytics transport reference](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/sendBeacon)
- [Global Privacy Control](https://globalprivacycontrol.org/)
- [Ghana Data Protection Act 2012 (Act 843)](https://dataprotection.org.gh/wp-content/uploads/2025/05/data-protection-act-2012-act-843.pdf)
- [Uganda Data Protection and Privacy Act 2019](https://pdpo.go.ug/media/2022/03/Data_Protection_and_Privacy_Act_No._9_of_2019.pdf)
- [Uganda Data Protection and Privacy Regulations 2021](https://pdpo.go.ug/media/2022/03/Data_Protection_and_Privacy_Regulations-2021.pdf)
- [Core Web Vitals](https://web.dev/articles/vitals)

This engineering model is not legal advice. Current law, regulator guidance, operating entities,
hosting locations, data flows, and user research must be reviewed by qualified Ghanaian and
Ugandan advisers before real collection.
