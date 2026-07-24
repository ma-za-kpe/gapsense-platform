# GapSense Documentation Index

## Active Governance

- [Project Charter](PROJECT_CHARTER.md) - current web-first product direction
- [Ways of Working](WAYS_OF_WORKING.md) - mandatory operating and quality model
- [Working List](../TASKS.md) - canonical, ever-growing execution list
- [Curriculum Coverage Audit](CURRICULUM_COVERAGE_AUDIT.md) - honest Ghana/Uganda baseline
- [Market and User Research](MARKET_AND_USER_RESEARCH.md) - dated facts and hypotheses
- [Free Assessment Generation Product Brief](ASSESSMENT_GENERATION_PRODUCT_BRIEF.md) - public
  generator goal, official assessment constraints, quality model, and commercial hypothesis
- [Security and Privacy Engineering Model](SECURITY_AND_PRIVACY_MODEL.md) - secure-by-design
  invariants, threat model, control baseline, and release evidence
- [Analytics and Search Model](ANALYTICS_AND_SEARCH_MODEL.md) - aggregate-only product evidence,
  fail-closed indexing, technical search contracts, and promotion gates
- [Brand and Interface Guidelines](BRAND_AND_INTERFACE_GUIDELINES.md) - identity, typography,
  colour, layout, motion, accessibility, resilience, and interface release gates
- [Frontend and Branch Reconciliation Audit](FRONTEND_RECONCILIATION_AUDIT.md) - all-branch
  evidence, historical UI runtime findings, and the no-duplication migration decision
- [Remote Main Reconciliation](REMOTE_MAIN_RECONCILIATION.md) - capability-by-capability
  disposition for safely migrating the divergent remote history without activating stale code
- [Delivery and Release Model](DELIVERY_AND_RELEASE_MODEL.md) - branch lifecycle, remote CI audit,
  optimized required-check graph, version management, and Release Please plan

## Architecture and Specifications

- [Architecture decision record](architecture/gapsense_adr.md)
- [ADR-001: Local Web Frontend Stack](decisions/ADR-001-web-frontend-stack.md)
- [ADR-002: Analytics and Search Publication](decisions/ADR-002-analytics-and-search-publication.md)
- [API specification](specs/gapsense_api_spec.json)
- [Database specification](specs/gapsense_data_model.sql)
- [Test scenarios](specs/gapsense_test_scenarios.json)
- [WhatsApp flows](specs/gapsense_whatsapp_flows.json) - historical/future reference; channel
  implementation is currently on hold

## Historical Planning Context

The following documents explain earlier product and funding directions. They do not override
the active charter or working list:

- [Roadmap bridge](gapsense_roadmap_bridge.md)
- [Alignment analysis](gapsense_alignment_analysis.md)
- [Project structure blueprint](gapsense_project_structure.md)
- Claude Code prompts (`gapsense_claude_code_prompt*.md`)

When a historical document conflicts with the active governance documents, retain it for context
and add a supersession notice rather than rewriting history silently.
