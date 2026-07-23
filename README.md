# GapSense Platform

GapSense is a local-first, web-first education product for Ghana and Uganda. It
is being designed to help learners, caregivers, teachers, and schools find and
close curriculum-aligned learning gaps and to make high-quality assessment
generation freely accessible.

The current repository is an early engineering foundation, not a deployed or
curriculum-complete product. Neither Ghana nor Uganda has complete, reviewed
coverage across all subjects and levels yet. WhatsApp delivery and production
deployment are explicitly on hold while the web product, curriculum evidence,
safety controls, and user experience are built properly.

## Current Direction

- Web first, with excellent mobile, tablet, and desktop experiences.
- Ghana and Uganda, with honest versioned coverage and official-source provenance.
- Free assessment generation with separate answer keys, rubrics, blueprints,
  source references, and review status.
- Deterministic behavior for tests and core workflows; local Ollama is an
  optional AI capability, never a hidden startup or test requirement.
- Local mock authentication and services until deployment is authorized.
- Security, child safety, privacy, accessibility, and dignity by design.
- 100% line and branch coverage for application-owned executable code.

## Runtime Contract

Docker is the runtime. Do not install or run project Python or Node packages on
the host. The platform expects the private `gapsense-data` repository as a
sibling directory and mounts it read-only.

The public curriculum coverage response is an immutable snapshot built when the
web application starts. Restart the `web` service after changing the sibling
data repository so one coherent evidence release is served for the lifetime of
each application process.

Prerequisites:

- Docker Desktop with Docker Compose
- Git
- the sibling `gapsense-data` repository
- optional: Ollama on the host with `llama3.1:8b` or another configured local model

Start the local foundation:

```powershell
docker compose up -d --wait db
docker compose run --rm web alembic upgrade head
docker compose up -d --build web
```

Then use:

- API documentation: <http://localhost:8000/docs>
- liveness: <http://localhost:8000/v1/health/live>
- readiness: <http://localhost:8000/v1/health/ready>

Run the same strict gate used by the local Git hook:

```powershell
sh scripts/install_hooks.sh
sh .githooks/pre-commit
```

The installer configures this repository to use its versioned commit-message,
pre-commit, and pre-push hooks. The pre-push hook blocks direct integration-branch
and local tag pushes, rejects a dirty worktree, and repeats the exact strict
Docker gate before a feature branch can be contributed.

The gate builds and runs inside Docker and includes dependency consistency,
formatting, linting, strict typing, secret and static-security scans, fresh
migration round trips, model-to-schema drift detection, tests at 100% line and
branch coverage, package build, dependency audit, Markdown linting, and patch
whitespace checks.

## Local AI

GapSense uses Ollama at `http://host.docker.internal:11434` from Docker. The
default model is `llama3.1:8b`; override it with `OLLAMA_MODEL` in a local
`.env` file. No Anthropic key or other external-model credential is required.

The provider adapter, deterministic fake, health reporting, safety validation,
and graceful offline behavior remain tracked work. Core product workflows must
remain useful when Ollama is unavailable.

## Repositories and Data

- `gapsense-platform`: application, tests, local runtime, and active product docs
- `gapsense-data`: proprietary curriculum and research artifacts

Do not copy proprietary curriculum artifacts or real personal data into this
repository. Synthetic test data must be unmistakably fictional.

## Project Operating Documents

- [Working list](TASKS.md)
- [Ways of working](docs/WAYS_OF_WORKING.md)
- [Project charter](docs/PROJECT_CHARTER.md)
- [Curriculum coverage audit](docs/CURRICULUM_COVERAGE_AUDIT.md)
- [Assessment-generation product brief](docs/ASSESSMENT_GENERATION_PRODUCT_BRIEF.md)
- [Market and user research](docs/MARKET_AND_USER_RESEARCH.md)
- [Security and privacy model](docs/SECURITY_AND_PRIVACY_MODEL.md)
- [Documentation index](docs/README.md)

`TASKS.md` is deliberately never finished. Add discovered work before starting
it, keep the current slice marked active, and close it only with evidence.

## Change Policy

Work on focused local branches. Before every milestone commit and local merge,
run the full Docker gate and review the complete diff. Use conventional commit
messages. Do not bypass hooks. Batch each coherent milestone into one locally
green feature-branch push, require a reviewed pull request and green hosted
checks, never push directly to `main` or `develop`, and let Release Please own
release tags. Production deployment remains prohibited, and committed Vercel
configuration disables automatic preview and production deployments.

## License

Proprietary. Internal team use only.
