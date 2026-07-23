#!/bin/sh
set -eu

mode=${1:-full}
repository_root=$(git rev-parse --show-toplevel)
cd "$repository_root"

export MSYS_NO_PATHCONV=1

case "$mode" in
  full)
    sh .githooks/pre-commit
    ;;
  docs)
    echo "GapSense CI: validating Docker Compose configuration"
    docker compose config --quiet

    echo "GapSense CI: validating workflow syntax"
    docker run --rm \
      -v "$repository_root:/repo:ro" \
      -w /repo \
      rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667

    echo "GapSense CI: building the locked policy toolchain"
    docker compose build web

    echo "GapSense CI: validating release and repository policy"
    docker compose run --rm --no-deps \
      -v "$repository_root:/workspace:ro" \
      -w /workspace \
      -e GAPSENSE_PR_TITLE \
      -e PYTHONPATH=/workspace/src \
      web python -m gapsense.release.policy

    echo "GapSense CI: scanning every commit candidate for secrets"
    docker compose run --rm --no-deps \
      -v "$repository_root:/workspace:ro" \
      -w /workspace \
      web sh scripts/scan_secrets.sh

    echo "GapSense CI: linting non-archived Markdown"
    docker run --rm \
      -v "$repository_root:/workspace:ro" \
      -w /workspace \
      node:22-alpine \
      npx --yes markdownlint-cli2@0.18.1 "README.md" "TASKS.md" "docs/**/*.md"

    echo "GapSense CI: checking patch whitespace"
    git diff --check
    ;;
  *)
    echo "Unsupported CI mode: $mode" >&2
    exit 2
    ;;
esac
