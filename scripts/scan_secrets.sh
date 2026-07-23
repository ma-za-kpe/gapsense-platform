#!/bin/sh
set -eu

# JSON cannot carry an inline detect-secrets allowlist comment. Repository policy independently
# pins this exact Release Please bootstrap field to the reviewed reconciliation boundary commit.
bootstrap_sha_field_pattern='"bootstrap-sha": "[0-9a-f]{40}"'

git -c safe.directory="$(pwd)" ls-files --cached --others --exclude-standard -z \
  | xargs -0 -r detect-secrets-hook \
      --exclude-lines "$bootstrap_sha_field_pattern"
