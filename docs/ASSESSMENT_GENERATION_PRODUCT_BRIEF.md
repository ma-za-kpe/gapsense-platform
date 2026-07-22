# Free Assessment Generation Product Brief

**Date:** 2026-07-22

**Status:** Active product hypothesis; implementation depends on reviewed curriculum slices
**Working promise:** Anyone can create a useful, curriculum-aligned assessment package for
an available Ghanaian or Ugandan curriculum without surrendering personal data or paying.

## Product Opportunity

GapSense can turn its curriculum graphs, learning outcomes, misconceptions, and diagnostic
logic into a public creation workflow. A learner preparing independently, a caregiver helping
at home, a teacher planning a class, a tutor, or a school leader should be able to select the
relevant context and receive an assessment that fits it.

The durable advantage cannot be generic AI question writing. It must be trustworthy alignment:
country-correct terminology, a visible assessment blueprint, official-source provenance,
appropriate cognitive and competency coverage, deterministic validation, educator review,
excellent editing and print UX, and a path from results to learning-gap action.

## Important Reframing

"Free exam generation" is the memorable entry idea. The product capability should be named
**assessment generation** internally because a written exam is inappropriate for some ages,
learning outcomes, and official policies.

For example, Uganda's P2 Thematic Curriculum says assessment is continuous, should occur in
normal teaching through observation, listening, and learner work, and should not generally be
a separate test or examination. Ghana's national assessment framework calls for techniques to
match performance indicators and for multiple methods, feedback, inclusion, and quality.

The interface should therefore use the learner-appropriate label and output:

- observation or conversation prompts;
- play, practical, oral, or performance activities;
- projects and portfolios;
- homework, revision sets, quizzes, and topical tests;
- formal practice or mock papers only where appropriate.

Sources:

- [Ghana National Pre-Tertiary Learning Assessment Framework](https://nacca.gov.gh/nplaf/)
- [Ghana National Pre-Tertiary Education Curriculum Framework](https://nacca.gov.gh/wp-content/uploads/2019/04/National-Pre-tertiary-Education-Curriculum-Framework-final.pdf)
- [Uganda P2 Thematic Curriculum](https://ncdc.go.ug/wp-content/uploads/2024/02/P2_Thematic_Curriculum_June_2011.pdf)
- [Uganda NCDC competency-based assessment module](https://ele.ncdc.go.ug/course/view.php?id=8)

## Primary User Journey

1. Choose the intended use or role without creating an account.
2. Choose country and official curriculum version.
3. Choose education sector/level, phase, class/year, and subject or learning area.
4. Choose full-term scope, topics, outcomes, prerequisite gaps, or a custom reviewed scope.
5. Choose purpose: formative, diagnostic, practice, homework, summative, or mock where valid.
6. Choose language, duration, marks, formats, difficulty/cognitive balance, and access needs.
7. Review the blueprint before generation: outcomes, weights, methods, marks, and timing.
8. Generate and edit the learner artifact and separate educator/answer artifact.
9. Regenerate a single item without destabilizing the rest of the blueprint.
10. Print or export accessible HTML and low-ink A4 output; PDF follows with visual QA.

No learner name, school, phone number, or account is required for the core journey. Local saved
work can be offered transparently; synchronized organization workflows belong behind local mock
authentication until deployment is authorized.

## Required Output Package

Every generation produces:

- the learner-facing paper, activity, or assessment;
- a separate answer key, marking guide, observation checklist, or rubric;
- concise answer rationales or performance evidence where appropriate;
- an assessment blueprint/table of specification;
- outcome codes and source references;
- curriculum version, generation method, seed, timestamp, and review state;
- marks and estimated time totals;
- an explicit notice that the artifact is practice material and not an official national paper.

## Country-Specific Constraints Found So Far

### Ghana

NaCCA's framework treats assessment as broader than final examinations and expects the method
to match the performance indicator, provide useful feedback, employ multiple methods, and be
inclusive. NaCCA also publishes preparatory Common Core assessment items initially covering
Mathematics, English, and Science. These are useful format evidence, but their availability does
not authorize GapSense to copy or repackage them.

WAEC describes BECE as combining continuous assessment and an external objective/written
examination. GapSense may offer clearly labelled practice formats aligned to public standards,
but must not imply that generated work is a WAEC paper, predict a live paper, or reproduce
protected questions without permission.

Sources:

- [NaCCA preparatory Common Core assessment items](https://nacca.gov.gh/assessment-items-for-the-common-core-programme/)
- [WAEC Ghana BECE overview](https://waecgh.org/athletics/bece-school/)

### Uganda

NCDC early-primary guidance makes assessment continuous and diagnostic. NCDC's competency-based
learning materials emphasize applying knowledge, skills, and values, including activities of
integration and evaluation grids. UNEB says its lower-secondary sample papers are guidance for
the new competency-based format and that final scenarios differ.

GapSense must encode phase policy: early-primary generation may yield observation/activity
tools, while later phases may support written papers, practical tasks, projects, and mock-style
formats appropriate to the syllabus.

Sources:

- [NCDC assessment and quality-assurance resources](https://ncdc.go.ug/book-category/q_a/)
- [UNEB lower-secondary sample-paper announcement](https://uneb.ac.ug/2024/03/26/nlsc_sample_papers/)

## Generation Architecture

Generation should be deterministic-first and AI-optional:

1. A policy resolver determines allowed purposes and formats from country, curriculum, and phase.
2. A blueprint engine allocates outcomes, methods, marks, cognitive demand, and time.
3. A vetted item/template repository satisfies the blueprint when coverage exists.
4. An optional model provider may draft missing items from bounded curriculum evidence.
5. Subject-specific validators reject unsupported, ambiguous, unsolvable, duplicated, biased,
   inaccessible, or answer-leaking items.
6. A renderer creates separate learner and educator artifacts.
7. Provenance and review state remain attached through edits, variants, print, and export.

The same input, curriculum release, item-bank release, and seed should reproduce the same
blueprint. Model-drafted wording may be explicitly non-deterministic, but it must remain marked
and independently validated. The web product must still generate useful assessments when the
local Ollama runtime is unavailable. External-model providers are not part of the active local
product direction.

## Quality and Safety Gates

Before a generated artifact is offered, validate:

- every selected outcome exists in the pinned curriculum release;
- weighting, marks, item count, and estimated time reconcile exactly;
- answer keys are correct and absent from learner-facing output;
- questions are solvable from the stated information and use appropriate units/notation;
- distractors are plausible without being deceptive or discriminatory;
- reading demand and language match the level unless language itself is being assessed;
- items are not duplicates or near-duplicates within the artifact;
- examples are culturally sensible and do not stereotype Ghanaian or Ugandan communities;
- accessibility and print constraints are met;
- output does not imitate authority branding or claim official endorsement;
- source and item licensing permit the intended use.

Generated high-stakes grading, live examination prediction, official-paper impersonation, and
unreviewed autonomous decisions about a learner are outside the current scope.

## Competitive Signal and Differentiation Hypothesis

Vendor sites already advertise adjacent capability:

- [EduMate Africa](https://www.edumategh.com/) claims curriculum-aligned exam generation for
  Ghana, Uganda, and other African systems.
- [Digital Schools Uganda](https://digitalschools.online/) advertises AI exam generation inside
  a Ugandan school-management product.
- [Ovacity](https://www.ovacity.com/) offers Ghana-focused exam preparation and analytics.
- [UNEB](https://uneb.ac.ug/) and NaCCA provide public official assessment guidance and samples
  that should be treated as infrastructure/evidence, not competitors to displace.

These are self-reported product claims and require hands-on evaluation. The proposed GapSense
differentiation is inspectable alignment and quality rather than the mere presence of a generate
button: all reviewed subjects and levels in both countries, country-specific assessment policy,
blueprint transparency, original-item safeguards, deterministic validation, accessible low-ink
output, and a direct bridge into prerequisite diagnosis and intervention.

## Free Core and Profitable Expansion

The core promise remains genuinely free: a user can generate, review, and print a complete
assessment package. Rate and compute controls may prevent abuse, but must not turn the result
into an unusable teaser.

Paid hypotheses should focus on organizational value:

- shared moderated item libraries and approval workflows;
- school/group templates, branding, and version governance;
- bulk equivalent variants and scheduled assessment programmes;
- class-level response capture, analytics, diagnostic linking, and intervention tracking;
- collaboration, audit history, imports/exports, LMS/SIS integrations, and APIs;
- implementation, curriculum validation, support, and evidence services.

This creates a plausible acquisition loop: a useful free tool earns trust and recurring usage;
organizations pay to coordinate, assure, analyze, and integrate work. Willingness to use and pay
must be validated rather than assumed.

## Validation Questions

- Who most needs generation: learners, caregivers, teachers, tutors, or school leaders?
- Which generated formats are actually used, edited, printed, or discarded?
- Does a visible blueprint increase trust or overwhelm users?
- Which country/phase fields can be inferred safely, and which must be explicit?
- How much editing is acceptable before the time-saving promise disappears?
- What error would cause an educator never to trust the product again?
- Which accessibility and language adaptations are required per subject and phase?
- Which free limits prevent abuse without excluding legitimate low-resource users?
- Which collaboration or assurance capability is valuable enough for an institution to pay?
- What permissions or approvals are required from curriculum and examination authorities?

All answers become dated research evidence and new items in [`TASKS.md`](../TASKS.md).
