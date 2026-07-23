"""Fail-closed repository policy checks for versioning and hosted automation."""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import cast
from urllib.parse import unquote

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
VERSION_ASSIGNMENT = re.compile(r'^__version__\s*=\s*"([^"]+)"$', re.MULTILINE)
ACTION_REFERENCE = re.compile(r"^\s*-\s+uses:\s*([^\s#]+)", re.MULTILINE)
PULL_REQUEST_TITLE = re.compile(
    r"^(feat|fix|docs|test|refactor|perf|build|ci|chore|revert)"
    r"(\([a-z0-9._/-]+\))?!?: .{1,72}$"
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
REVIEWED_ACTIONS = {
    # pragma: allowlist nextline secret -- reviewed immutable GitHub Action commit
    "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
    # pragma: allowlist nextline secret -- reviewed immutable GitHub Action commit
    "googleapis/release-please-action": "5c625bfb5d1ff62eadeeb3772007f7f66fdcf071",
}
# pragma: allowlist nextline secret -- reviewed local reconciliation boundary commit
RELEASE_BOOTSTRAP_SHA = "e3f3849914cea911d4d7c7e641cb18d4793804ca"
FRONTEND_VERSION_TARGETS = {
    ("json", "frontend/package.json", "$.version"),
    ("json", "frontend/package-lock.json", "$.version"),
    ("json", "frontend/package-lock.json", '$.packages[""].version'),
}


class RepositoryPolicyError(ValueError):
    """Raised when repository automation or version metadata fails closed."""


def validate_pull_request_title(title: str) -> None:
    """Require a bounded Conventional Commit title for squash-safe pull requests."""
    if len(title) > 100:
        raise RepositoryPolicyError("Pull request title must not exceed 100 characters")
    if PULL_REQUEST_TITLE.fullmatch(title) is None:
        raise RepositoryPolicyError(
            "Pull request title must use Conventional Commits with a 1-72 character description"
        )


def _json_object(path: Path) -> dict[str, object]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RepositoryPolicyError(f"{path.name} must contain valid JSON") from error
    if not isinstance(value, dict):
        raise RepositoryPolicyError(f"{path.name} must contain a JSON object")
    return cast(dict[str, object], value)


def _toml_object(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as stream:
            value: object = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RepositoryPolicyError(f"{path.name} must contain valid TOML") from error
    return cast(dict[str, object], value)


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RepositoryPolicyError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _version_sources(root: Path) -> dict[str, str]:
    pyproject = _toml_object(root / "pyproject.toml")
    project = _mapping(pyproject.get("project"), "pyproject project")
    frontend = _json_object(root / "frontend/package.json")
    frontend_lock = _json_object(root / "frontend/package-lock.json")
    locked_packages = _mapping(frontend_lock.get("packages"), "frontend lock packages")
    locked_root = _mapping(locked_packages.get(""), "frontend lock root package")
    manifest = _json_object(root / ".release-please-manifest.json")
    try:
        init_text = (root / "src/gapsense/__init__.py").read_text(encoding="utf-8")
    except OSError as error:
        raise RepositoryPolicyError("Python package version file must be readable") from error
    init_match = VERSION_ASSIGNMENT.search(init_text)
    if init_match is None:
        raise RepositoryPolicyError("Python package must expose __version__")

    raw_versions = {
        "pyproject": project.get("version"),
        "python_package": init_match.group(1),
        "frontend": frontend.get("version"),
        "frontend_lock": frontend_lock.get("version"),
        "frontend_lock_root": locked_root.get("version"),
        "release_manifest": manifest.get("."),
    }
    if not all(isinstance(version, str) for version in raw_versions.values()):
        raise RepositoryPolicyError("Every canonical version source must contain a string")
    return cast(dict[str, str], raw_versions)


def _validate_versions(root: Path) -> None:
    versions = _version_sources(root)
    invalid_versions = {
        source: version for source, version in versions.items() if SEMVER.fullmatch(version) is None
    }
    if invalid_versions:
        raise RepositoryPolicyError(
            f"Canonical product versions must be valid SemVer: {invalid_versions}"
        )
    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        raise RepositoryPolicyError(f"Canonical product versions differ: {versions}")


def _validate_release_configuration(root: Path) -> None:
    config = _json_object(root / "release-please-config.json")
    if config.get("bootstrap-sha") != RELEASE_BOOTSTRAP_SHA:
        raise RepositoryPolicyError("Release Please must use the reviewed bootstrap commit")
    if config.get("include-component-in-tag") is not False:
        raise RepositoryPolicyError("GapSense releases require component-free product tags")
    if config.get("include-v-in-tag") is not True:
        raise RepositoryPolicyError("GapSense releases require v-prefixed product tags")

    packages = _mapping(config.get("packages"), "Release Please packages")
    if set(packages) != {"."}:
        raise RepositoryPolicyError("Release Please must define exactly one root package")
    root_package = _mapping(packages["."], "Release Please root package")
    if root_package.get("release-type") != "python":
        raise RepositoryPolicyError("GapSense requires the Python release strategy")

    extra_files = root_package.get("extra-files")
    if not isinstance(extra_files, list):
        raise RepositoryPolicyError("Release Please frontend version targets must be a list")
    targets: set[tuple[object, object, object]] = set()
    for value in extra_files:
        item = _mapping(value, "Release Please extra-file entry")
        targets.add((item.get("type"), item.get("path"), item.get("jsonpath")))
    if targets != FRONTEND_VERSION_TARGETS:
        raise RepositoryPolicyError("Release Please must update all frontend version targets")


def _validate_deployment_hold(root: Path) -> None:
    config = _json_object(root / "vercel.json")
    git_configuration = _mapping(config.get("git"), "Vercel git configuration")
    if git_configuration.get("deploymentEnabled") is not False:
        raise RepositoryPolicyError(
            "Repository policy requires automatic Vercel deployments to remain disabled"
        )


def _validate_workflows(root: Path) -> None:
    workflow_root = root / ".github/workflows"
    required = {
        "ci.yml": workflow_root / "ci.yml",
        "release-please.yml": workflow_root / "release-please.yml",
    }
    for name, path in required.items():
        if not path.is_file():
            raise RepositoryPolicyError(f"Missing required workflow: {name}")

    workflow_text = {
        path: path.read_text(encoding="utf-8") for path in sorted(workflow_root.glob("*.y*ml"))
    }
    for path, text in workflow_text.items():
        for reference in ACTION_REFERENCE.findall(text):
            if reference.startswith("./"):
                continue
            action, separator, revision = reference.rpartition("@")
            if separator == "" or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
                raise RepositoryPolicyError(
                    f"{path.name}: {reference} must use an immutable commit SHA"
                )
            expected_revision = REVIEWED_ACTIONS.get(action)
            if expected_revision is None:
                raise RepositoryPolicyError(f"{path.name}: {action} is not allowlisted")
            if revision != expected_revision:
                raise RepositoryPolicyError(f"{path.name}: {action} does not use its reviewed SHA")

    ci_text = required["ci.yml"].read_text(encoding="utf-8")
    if "permissions:\n  contents: read" not in ci_text:
        raise RepositoryPolicyError("CI must default to read-only contents permission")
    if "GAPSENSE_PR_TITLE: ${{ github.event.pull_request.title || '' }}" not in ci_text:
        raise RepositoryPolicyError("CI must validate the pull request title")
    release_text = required["release-please.yml"].read_text(encoding="utf-8")
    required_release_permissions = (
        "contents: write",
        "issues: write",
        "pull-requests: write",
        "actions: write",
        "contents: read",
    )
    if not all(permission in release_text for permission in required_release_permissions):
        raise RepositoryPolicyError(
            "Release Please workflow is missing least-privilege release permissions"
        )


def _validate_markdown_links(root: Path) -> None:
    repository_root = root.resolve()
    candidates = (root / "README.md", root / "TASKS.md")
    markdown_paths = [path for path in candidates if path.is_file()]
    docs_root = root / "docs"
    if docs_root.is_dir():
        markdown_paths.extend(sorted(docs_root.rglob("*.md")))

    for markdown_path in markdown_paths:
        text = markdown_path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip("<>")
            if target.startswith("#") or URI_SCHEME.match(target):
                continue
            relative_target = unquote(re.split(r"[?#]", target, maxsplit=1)[0])
            resolved_target = (markdown_path.parent / relative_target).resolve()
            if not resolved_target.is_relative_to(repository_root):
                raise RepositoryPolicyError(
                    f"{markdown_path.relative_to(root)} contains a broken internal Markdown link: "
                    f"{target}"
                )
            if not resolved_target.exists():
                raise RepositoryPolicyError(
                    f"{markdown_path.relative_to(root)} contains a broken internal Markdown link: "
                    f"{target}"
                )


def validate_repository(root: Path) -> None:
    """Validate the release, version, action-pin, and permission contract."""
    _validate_versions(root)
    _validate_release_configuration(root)
    _validate_deployment_hold(root)
    _validate_workflows(root)
    _validate_markdown_links(root)


def main() -> int:
    """Run policy validation against the current repository."""
    try:
        validate_repository(Path.cwd())
        pull_request_title = os.environ.get("GAPSENSE_PR_TITLE", "")
        if pull_request_title:
            validate_pull_request_title(pull_request_title)
    except RepositoryPolicyError as error:
        print(f"GapSense repository policy failed: {error}", file=sys.stderr)
        return 1
    print("GapSense repository policy passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
