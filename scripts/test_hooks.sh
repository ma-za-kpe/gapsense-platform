#!/bin/sh
set -eu

repository_root=$(git rev-parse --show-toplevel)
cd "$repository_root"

valid_message=$(mktemp)
invalid_message=$(mktemp)
cleanup() {
  rm -f "$valid_message" "$invalid_message"
}
trap cleanup EXIT INT TERM

printf '%s\n' 'test(hooks): verify strict local controls' >"$valid_message"
printf '%s\n' 'bypass the quality gate' >"$invalid_message"

echo "Verifying conventional commit-message enforcement."
sh .githooks/commit-msg "$valid_message"
if sh .githooks/commit-msg "$invalid_message"; then
  echo "Commit-message hook accepted an invalid subject." >&2
  exit 1
fi

echo "Running the exact strict pre-commit gate."
sh .githooks/pre-commit

echo "Verifying the current local-only pre-push hold."
if sh .githooks/pre-push; then
  echo "Pre-push unexpectedly allowed a remote push." >&2
  exit 1
fi

echo "Git hook behavior is correct."
