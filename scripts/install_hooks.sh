#!/bin/sh
set -eu

repository_root=$(git rev-parse --show-toplevel)
cd "$repository_root"

git config --local core.hooksPath .githooks

configured_path=$(git config --local --get core.hooksPath)
if [ "$configured_path" != ".githooks" ]; then
  echo "Git hooks were not configured correctly." >&2
  exit 1
fi

chmod +x .githooks/commit-msg .githooks/pre-commit .githooks/pre-push

echo "Strict local Git hooks are installed from .githooks."
echo "Remote pushes remain blocked until the project hold is explicitly lifted."
