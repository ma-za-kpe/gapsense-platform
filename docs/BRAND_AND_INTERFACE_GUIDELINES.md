# GapSense Brand and Interface Guidelines

Date: 2026-07-22
Status: Active, living standard

These guidelines govern every GapSense web surface. They are intentionally stricter than a
visual style guide: brand quality includes truth, dignity, accessibility, speed, security, and
graceful failure.

## Brand Foundation

### Purpose

GapSense helps a learner, caregiver, educator, or tutor find a useful next learning step from
curriculum evidence they can inspect.

### Promise

**Find the gap. See the reason. Take the next step.**

The interface must make three things clear:

1. what the user is choosing;
2. what GapSense knows and how it knows it; and
3. what remains incomplete, uncertain, or subject to review.

### Personality

GapSense is calm, capable, warm, precise, and quietly optimistic. It is never childish,
institutionally cold, culturally generic, or impressed with its own technology.

### Product principles

- **Truth before theatre:** do not imply that a curriculum, assessment, or diagnosis is ready
  before its evidence and review gates pass.
- **Dignity before deficit:** describe the next prerequisite to strengthen, never a deficient
  learner.
- **Clarity before density:** disclose complexity progressively and keep the next action obvious.
- **Local relevance without stereotypes:** use each country's official terminology and
  structures, not flags, costumes, landmarks, or generic "African" decoration as shortcuts.
- **Accessible by default:** keyboard, touch, zoom, reduced motion, assistive technology, low
  bandwidth, and print needs are design inputs.
- **Useful without AI:** a missing model or network connection must not turn the core workflow
  into a dead end.

## Identity

### Founder attribution and independence

Use **Built by Maku for Africa** as the canonical founder attribution. GapSense must not present
UNICEF, a funding cohort, a former application, or any other institution as part of its identity,
endorsement, partnership, or product status without a current written agreement and explicit
approval to publish that relationship.

Third-party research is evidence, not branding. Replace UNICEF-derived active product claims with
authoritative Ghanaian or Ugandan sources where possible and retain source provenance until a
verified replacement exists; never turn a citation into implied affiliation.

### Name and wordmark

Write the product name as **GapSense**, with no space. The code-native mark is a four-cell learning
map with one contrasting cell: the gap becomes visible within a coherent system.

- Preserve the mark's square proportions.
- Keep clear space of at least one cell around it.
- Do not recolour it with a country's flag palette.
- Do not animate it continuously or use it as a loading spinner.
- Do not place the mark over visually busy imagery.

### Country expression

Ghana and Uganda share the GapSense design system but retain their own curriculum language.
Country accents help orientation; they do not create separate quality tiers.

| Context | Accent | Current official-system label |
| --- | --- | --- |
| Ghana | warm gold | NaCCA; KG, Basic B1-B9, SHS |
| Uganda | warm coral | NCDC; pre-primary, Primary P1-P7, secondary |

Authority names, level structures, and readiness statements must come from versioned product
content, not decorative CSS. Country terminology remains provisional until educator validation.

## Typography

Use the committed system stack. The product does not make a page render or leak metadata through
a third-party font request.

```css
font-family: "Avenir Next", "Segoe UI Variable", "Segoe UI", Inter, system-ui, sans-serif;
```

- Body copy: 16 px minimum, normally 17-19 px for high-value explanations.
- Supporting copy: 14 px minimum; never use tiny text to hide consequential information.
- Line length: aim for 45-75 characters for prose.
- Line height: at least 1.45 for body copy.
- Headings: use fluid `clamp()` scales and compact but readable line height.
- Numerals and abbreviations: explain curriculum authority abbreviations on first use.
- User-controlled zoom to 200% must not lose content or operation.

Use weight and space before colour to establish hierarchy. Avoid all-caps prose. Eyebrows may use
uppercase styling only when letter spacing and contrast remain legible.

## Colour

The canonical source is the CSS custom-property block in `frontend/src/styles.css`. Every new
semantic colour needs light-background, dark-background, focus, disabled, and high-contrast
evidence before adoption.

| Token family | Role |
| --- | --- |
| `--ink-*` | text, strong structure, dark surfaces |
| `--paper*` | primary and muted backgrounds |
| `--green-*` | brand action, connected/ready state |
| `--gold-*` | Ghana orientation accent |
| `--coral-*` | Uganda orientation accent |
| `--line` | quiet boundaries |

- Meet WCAG 2.2 AA contrast at minimum: 4.5:1 for normal text and 3:1 for large text and graphical
  controls.
- Never communicate state, country, or correctness with colour alone.
- Red is reserved for destructive or failed states; it is not used to label a learner.
- Keep the main reading surface light until a complete, independently tested dark theme exists.

## Layout, Space, and Shape

- Use a 4 px base spacing rhythm and the committed `--space-*` tokens.
- Keep a readable centred content width; full-bleed colour may frame it but not stretch prose.
- Use generous negative space to separate decisions, not to force excessive scrolling.
- Use smaller radii for controls and moderate radii for grouped cards. Avoid a collection of
  unrelated floating pills.
- Elevation communicates layer or emphasis, never mere decoration.
- Grid changes are content-led at approximately 1088 px, 800 px, and 640 px. A screen is supported
  when the workflow works, not merely when it matches a named device.
- Prevent horizontal page scrolling down to 320 CSS pixels.

## Interaction and Motion

- Interactive targets are at least 44 by 44 CSS pixels on touch layouts.
- Keyboard focus uses a visible 3 px outline with sufficient contrast and offset.
- DOM order, focus order, and reading order remain aligned.
- Every form control has a programmatic label; descriptive card copy may be part of the accessible
  name when it helps distinguish the choice.
- Disabled actions explain completion through nearby context, not a tooltip.
- Motion lasts roughly 160-320 ms, uses the shared easing token, and clarifies hierarchy or state.
- No essential information exists only in animation.
- `prefers-reduced-motion: reduce` reduces animations and transitions to effectively immediate.
- Avoid autoplay, parallax, scroll-jacking, and decorative infinite motion.

## Components and States

Shared components must expose semantic purpose instead of only visual variants. At minimum, every
workflow considers:

- initial and incomplete;
- loading or checking;
- ready;
- partial or still under review;
- offline or unavailable;
- invalid input;
- empty result;
- success;
- recovery and safe restart.

Buttons use verbs. Status text states what happened and what remains possible. Skeletons are used
only when the eventual shape is known; otherwise use direct progress copy.

## Content and Trust

- Use British English unless a country- or curriculum-specific source requires another form.
- Prefer “practise” as a verb and “practice” as a noun.
- Say “parent or caregiver,” not only “parent.”
- Say “learning step,” “prerequisite to strengthen,” or “review needed,” not “weak child,”
  “failure,” or “slow learner.”
- Identify whether a statement is official source material, GapSense interpretation, generated
  draft, or human-reviewed guidance.
- Never imply endorsement by NaCCA, WAEC, NCDC, UNEB, a school, or a ministry.
- Do not use learner names, school identities, phone numbers, or account creation when the task can
  be completed anonymously.
- Error messages reveal no secrets, stack traces, private paths, or personal information.

## Performance and Resilience

- Prefer semantic HTML and CSS over image assets for core navigation and explanation.
- No external font, analytics, ad, or model dependency is allowed in the initial critical path.
- Keep the page usable when the API readiness check fails.
- Budget and measure JavaScript, CSS, image, request, render, and interaction costs before adding a
  new dependency.
- Design for intermittent connectivity, small screens, lower-memory devices, monochrome print, and
  constrained data plans.

## Search, Sharing, and Measurement

- Write a unique, accurate page title and plain-language description for every indexable public
  route; the visible heading, title, and description must promise the same task.
- Keep curriculum, country, subject, level, and provenance terms specific enough for people to
  recognise the right official context. Do not manufacture search phrases or claims that the
  interface cannot support.
- Use one reviewed canonical URL for each public page. Canonicals, sitemaps, structured data, and
  social-preview URLs must derive from the same configured HTTPS public origin.
- Treat social previews as compact product surfaces: preserve the calm visual system, provide
  useful alternative text, and never place learner data, assessment results, or fabricated
  endorsements in preview content.
- Keep search indexing fail closed while the product is local-only. A build may become indexable
  only after the release checklist records legal, content, curriculum-provenance, security,
  performance, accessibility, canonical-origin, and crawl verification.
- Measure only allowlisted product events that answer an explicit product or sustainability
  question. Event names may describe an action; event payloads must not reveal the selected
  country, role, goal, curriculum answer, learner identity, or free text.
- Analytics must be disabled by default, same-origin, aggregate-only, and non-blocking. Respect
  Global Privacy Control, Do Not Track, reduced-data signals, and any future visible opt-out before
  sending an event.
- Never trade comprehension, accessibility, privacy, performance, or evidence quality for a search
  ranking or conversion metric. Search traffic and analytics trends are observations, not proof of
  learning impact.

The binding implementation, threat model, event catalogue, and indexing-promotion contract live in
[`ANALYTICS_AND_SEARCH_MODEL.md`](ANALYTICS_AND_SEARCH_MODEL.md).

## Release Evidence

An interface milestone is not complete until Docker evidence includes:

- exact-lockfile installation, formatting, lint, and strict TypeScript;
- 100% statements, branches, functions, and lines across owned executable modules;
- focused unit and component behaviour assertions;
- browser journeys at desktop and mobile viewports;
- automated axe checks with WCAG 2.2 AA tags;
- keyboard and visible-focus checks;
- target-size, no-horizontal-overflow, and reduced-motion checks;
- visual regression baselines reviewed by a person;
- API-ready and API-unavailable behaviour;
- console and page-error monitoring;
- security-header and production-image smoke tests;
- manual zoom, screen-reader, low-bandwidth, print, content, and cultural review as each workflow
  matures.

Automated accessibility checks find only a subset of accessibility problems. They do not replace
manual assistive-technology and user testing.

## Research Basis

These standards adapt principles rather than copying another company's visual identity.

- [Apple Human Interface Guidelines: design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles)
- [Apple Human Interface Guidelines: accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility/)
- [Apple Human Interface Guidelines: typography](https://developer.apple.com/design/human-interface-guidelines/typography)
- [W3C Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/)
- [Playwright accessibility testing guidance](https://playwright.dev/docs/accessibility-testing)

## Change Control

This document evolves with research and tested product evidence. Record meaningful changes in
`TASKS.md`; use an ADR for changes that affect architecture, dependency surface, privacy, or the
cross-product design contract.
