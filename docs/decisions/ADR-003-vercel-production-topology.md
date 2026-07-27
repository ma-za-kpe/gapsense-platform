# ADR-003: Vercel Production Topology

Date: 2026-07-25
Status: Accepted for explicit production promotion

## Context

`gapsense.org` was attached to the original Vercel project named `gapsense`, but that project still
served a 128-day-old Ghana/WhatsApp-first site. The reconciled repository had subsequently been
linked to two other Vercel projects, `gapsense-platform` and `frontend`. Neither project owned the
custom domain, and neither represented a complete production topology:

- the backend project retained a stale FastAPI preset and failed because it could not locate the
  application entry point;
- the frontend project served the Vite shell but returned 404 for every same-origin `/api` request;
- the public browser contract requires the Vite application, `/curriculum` deep link, readiness
  endpoint, and curriculum coverage endpoint to move together.

The current public slice is deliberately read-only. It uses the reviewed synthetic
`fixtures/public-data` boundary, collects no analytics in production, requires no account or
learner data, and does not need PostgreSQL, Ollama, AWS, authentication, or WhatsApp.

## Decision

Keep the existing `gapsense` Vercel project and `gapsense.org` as the single production surface.
Deploy the current repository root with:

- Vite as the primary Vercel framework and `public` as the generated CDN output;
- `api/index.py` as one Python function that imports the existing FastAPI application;
- an explicit `/api/*` rewrite that preserves the original backend path for ASGI dispatch;
- an explicit `/curriculum` rewrite to the SPA document;
- the reviewed public curriculum fixture included in the Python function bundle;
- production security headers defined in version-controlled `vercel.json`;
- `git.deploymentEnabled: false`, so neither a push nor a pull request can publish implicitly.

Production promotion is a manual release action after the focused branch passes the strict local
Docker gate, required GitHub pull-request CI, review, and a protected Vercel preview smoke test.
The deployment operator must verify the exact project ID before promotion and verify the custom
domain afterward.

## Alternatives considered

### Separate frontend and backend projects

This would require a stable backend domain, cross-project environment mapping, coordinated
promotion, CORS or proxy configuration, and two rollback operations. It adds failure modes without
current scale or ownership benefits.

### Vercel Services

Services express this topology directly, but the capability is in private beta. Production should
not depend on unconfirmed account access or experimental routing when the supported Vite plus
Python-function model satisfies the current contract.

### FastAPI as the primary framework with generated static assets

The preview proved that a build-generated `public` directory was not selected as the primary CDN
output under the forced FastAPI preset: `/`, `/curriculum`, and assets reached the Python function.
Serving all frontend assets from the function would be slower and would discard Vercel's static
delivery strengths.

### Add a hosted database now

No current public route persists user or curriculum state. Adding PostgreSQL would expand privacy,
security, migration, backup, regional, and cost scope without enabling the reviewed experience.
A database decision remains deferred until a use case requires durable server-side state.

## Security, privacy, and data boundary

- Only the unmistakably synthetic public fixture is bundled.
- `ANALYTICS_MODE` remains disabled and no event route is exposed.
- No secrets are required by the public runtime.
- API responses remain bounded projections and never expose raw proprietary curriculum content.
- Search indexing remains fail-closed until its separate publication gates are approved.
- WhatsApp, authentication, learner response capture, hosted AI, and database writes remain out of
  scope.

## Verification and rollback

Before production:

1. inspect the linked Vercel project and confirm it is `gapsense`;
2. deploy a protected preview;
3. verify `/`, `/curriculum`, the generated JS asset, `/robots.txt`,
   `/api/v1/health/ready`, and `/api/v1/curriculum/coverage`;
4. inspect build and runtime error evidence;
5. merge only through the protected GitHub workflow and confirm post-merge automation is green.

After promotion, repeat the checks against `https://gapsense.org`, verify the deployed content
title and curriculum UI, and retain the prior production deployment URL. Rollback is an explicit
Vercel promotion of that known-good deployment; source rollback is a reviewed revert pull request.

## Consequences

The frontend and read-only API now share one origin, deployment, domain, and rollback unit. The
repository contains the production topology instead of relying on stale dashboard inference.
Manual promotion remains an operational step until a protected, manually triggered deployment
workflow is designed and reviewed. Future durable data, private evidence, or write APIs require a
new decision rather than silently expanding this one.
