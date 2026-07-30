#!/bin/sh
set -eu

# JSON cannot carry an inline detect-secrets allowlist comment. Repository and curriculum policy
# independently validate these exact integrity fields as immutable Git or document digests.
reviewed_json_integrity_field_pattern='"bootstrap-sha": "[0-9a-f]{40}"|"(checksum_)?sha256": "[0-9a-f]{64}"'

git -c safe.directory="$(pwd)" ls-files --cached --others --exclude-standard -z \
  | xargs -0 -r detect-secrets-hook \
      --exclude-lines "$reviewed_json_integrity_field_pattern"
