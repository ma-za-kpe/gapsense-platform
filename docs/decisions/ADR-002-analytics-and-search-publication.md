# ADR-002: Aggregate-Only Analytics and Fail-Closed Search Publication

Date: 2026-07-23

Status: Accepted for the local web foundation

## Context

GapSense needs evidence about whether its free assessment and diagnostic entry products are useful,
and it needs a technically sound path to public discoverability. The product also serves education
communities, may be used by children, is not deployed, has no approved canonical host, and has not
completed Ghanaian or Ugandan legal/privacy review.

Adding a vendor script, identifier, cookie banner, public canonical URL, or crawlable local preview
now would create a larger data and dependency surface before it can be justified.

## Decision

1. Define a versioned, property-free analytics event allowlist.
2. Use a replaceable same-origin port and a process-local sink that retains event-name counters
   only.
3. Disable collection by default, restrict the temporary aggregate mode to the local environment,
   and honour explicit browser privacy/reduced-data signals.
4. Keep selected planner values, identity, URLs, referrers, free text, device data, and persistent
   identifiers outside the event contract.
5. Generate search metadata and crawler artifacts at build time from one typed source.
6. Default every build to `noindex` and require an approved HTTPS origin for public mode.
7. Bind public structured data to its exact CSP SHA-256 source instead of enabling unsafe inline
   script.
8. Keep production deployment, real analytics, webmaster registration, and release publication
   on hold.

## Consequences

Positive:

- current product actions remain private and work when analytics is absent or broken;
- no external analytics cost, cookie, tracking identifier, or runtime dependency enters the
  critical path;
- search artifacts cannot accidentally advertise localhost or an unapproved host;
- event and publication behaviour is deterministic and testable at 100% code coverage;
- later analytics or hosting adapters must cross explicit ports and reviews.

Trade-offs:

- process-local counters are intentionally ephemeral and have no dashboard;
- the first event set cannot segment by country, role, subject, level, or acquisition source;
- the deployment-hold build is intentionally not indexable;
- search outcomes and representative product insight cannot be measured until approved field use.

## Revisit When

- a production host and canonical domain are approved;
- qualified Ghana/Uganda privacy review is complete;
- representative user research identifies a decision that needs additional aggregate dimensions;
- authenticated operator analytics, retention, deletion, aggregation thresholds, or a processor
  become necessary;
- the product gains distinct, evidence-backed public routes beyond the entry page.
