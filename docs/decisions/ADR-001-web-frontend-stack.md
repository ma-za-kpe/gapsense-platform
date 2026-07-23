# ADR-001: Local Web Frontend Stack

Date: 2026-07-22
Status: Accepted for the web foundation; historical capability migration required

## Context

GapSense needs a polished, mobile-responsive web product that runs locally on port 3000, remains
useful when Ollama or the API is unavailable, and can later be hosted without selecting a cloud
vendor now. The repository already has a FastAPI service and a Docker-only operating model. A
later all-branch audit also found a substantial Ghana/Math/WhatsApp-first static frontend on remote
`main`; see the [frontend reconciliation audit](../FRONTEND_RECONCILIATION_AUDIT.md). That
frontend provides useful curriculum, teacher-demo, reporting, and architecture concepts, but its
central pages fail without historical backend routes and it does not pass the current type, lint,
dependency, or test gates.

The foundation must support strict typing, test-first components, 100% owned-code coverage,
browser and accessibility testing, a same-origin API boundary, reproducible builds, and a small
security surface. WhatsApp and deployment remain on hold.

## Decision

Use this exact, locked foundation:

- React 19.2.8 for accessible component composition;
- TypeScript 6.0.3 with strict and additional correctness flags;
- Vite 8.1.5 for the development server and static production build;
- npm with a committed `package-lock.json` and `npm ci` in Docker;
- Vitest 4.1.10 with V8 coverage and 100% thresholds for statements, branches, functions, and
  lines, including owned modules not imported by tests;
- Testing Library and axe-core for behaviour- and semantics-led component tests;
- Playwright 1.61.1 and `@axe-core/playwright` for Chromium desktop/mobile journeys, visible focus,
  responsive layout, reduced motion, security headers, console errors, and visual regression;
- an unprivileged Nginx static image for local production smoke evidence;
- `/api/*` as the browser's same-origin boundary, proxied to FastAPI inside Docker;
- no third-party font, analytics, authentication, model, or cloud runtime in the critical path.

Application development and builds use the exact Node 22 image pinned in the frontend Dockerfile.
The exact official Playwright image supplies Node 24 for browser tests; the package engine range
therefore admits only supported Node 22 through 24 releases, while Docker pins the actual runtime.

The development service binds only to `127.0.0.1:3000` on the host, runs with a read-only root
filesystem and `no-new-privileges`, and waits for API readiness. The UI still exposes a useful
local planning flow if a later readiness request fails.

## Why a Client-Rendered Static Build

React's current documentation recommends a framework for many new applications, but explicitly
allows a from-scratch setup when framework constraints do not fit. GapSense does not yet need
server rendering, public search indexing, server components, or a JavaScript application server.
A static build:

- preserves the existing FastAPI boundary;
- keeps local and eventual static hosting options open;
- avoids adding a second server runtime and framework-specific data layer;
- is simple to run as an unprivileged, immutable container; and
- can be revisited when measured product needs justify more infrastructure.

This is not a decision that the full product must remain a single-page application forever.

## Alternatives Considered

### Next.js or another React framework

Deferred. It offers routing, data loading, and rendering conventions that may become valuable, but
the current single-entry workflow would pay an unnecessary server and deployment complexity cost.

### Server-rendered FastAPI templates with progressive enhancement

Viable for smaller forms, but rejected for this foundation because the planned interactive
curriculum explorer, diagnostic sessions, resumable state, and component-level visual testing
benefit from a typed component model. Existing Jinja report templates remain migration input, not
an alternative public frontend.

### Continue the historical static HTML and JavaScript frontend

Rejected as the active shell after a Docker runtime and quality audit. Its small static build is a
valuable performance reference, and its strongest workflows must be migrated, but the current
surface is Ghana/Math/WhatsApp-first, contains unsupported completion and production claims, has
backend-coupled failures, cannot run its declared lint gate, fails strict checking, reports high
dependency vulnerabilities, and has no automated frontend coverage evidence.

### A second frontend framework

Not selected. There is no project evidence that another runtime would improve target-user
outcomes enough to justify a broader skills and dependency surface.

## Consequences

Positive consequences:

- deterministic Docker builds and an exact dependency audit;
- a deployment-neutral static artifact;
- strong component, browser, accessibility, and visual tooling;
- clear separation between the web adapter and domain/API services;
- no production cloud or external AI dependency.

Costs and risks:

- client-side JavaScript must stay within explicit performance budgets;
- browser routing and search needs will require a future evidence-backed decision;
- automatic accessibility checks require manual testing to close their known gaps;
- dependency updates require deliberate lockfile, browser-image, audit, and regression work.
- migrating historical capabilities costs deliberate product and engineering effort, but avoids
  maintaining two public interfaces or silently losing prior work.

## Validation and Revisit Triggers

The decision is valid only while the Docker validation pipeline stays green and target-user
research supports the interaction model. Revisit it if measured evidence shows a need for search
indexing, server rendering, multi-page routing complexity, materially better offline support, or a
different rendering model.

Primary technical sources:

- [React: creating a React app](https://react.dev/learn/creating-a-react-app)
- [React 19 release](https://react.dev/blog/2024/12/05/react-19)
- [Vite guide](https://vite.dev/guide/)
- [Vite releases](https://vite.dev/releases.html)
- [Vitest coverage guidance](https://vitest.dev/guide/coverage.html)
- [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing)
