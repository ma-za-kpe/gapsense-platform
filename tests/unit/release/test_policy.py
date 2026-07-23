from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from gapsense.release.policy import (
    RepositoryPolicyError,
    main,
    validate_pull_request_title,
    validate_repository,
)

if TYPE_CHECKING:
    from pathlib import Path

# pragma: allowlist nextline secret -- reviewed immutable GitHub Action commit fixture
CHECKOUT_SHA = "11d5960a326750d5838078e36cf38b85af677262"
# pragma: allowlist nextline secret -- reviewed immutable GitHub Action commit fixture
RELEASE_PLEASE_SHA = "5c625bfb5d1ff62eadeeb3772007f7f66fdcf071"
# pragma: allowlist nextline secret -- reviewed local reconciliation boundary fixture
RELEASE_BOOTSTRAP_SHA = "e3f3849914cea911d4d7c7e641cb18d4793804ca"


@pytest.mark.parametrize(
    "title",
    [
        "feat(web): add curriculum explorer",
        "fix!: reject untraceable curriculum",
        "chore(release/ci): establish guarded automation",
    ],
)
def test_pull_request_policy_accepts_conventional_titles(title: str) -> None:
    validate_pull_request_title(title)


@pytest.mark.parametrize(
    "title",
    [
        "Add curriculum explorer",
        "feat(Web): use invalid uppercase scope",
        "feat(web): ",
        f"feat(web): {'x' * 73}",
        f"feat({'x' * 100}): x",
    ],
)
def test_pull_request_policy_rejects_nonconventional_titles(title: str) -> None:
    with pytest.raises(RepositoryPolicyError, match="Pull request title"):
        validate_pull_request_title(title)


def _write(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _valid_repository(root: Path) -> None:
    _write(
        root,
        "pyproject.toml",
        '[project]\nname = "gapsense"\nversion = "0.1.0"\n',
    )
    _write(root, "src/gapsense/__init__.py", '__version__ = "0.1.0"\n')
    _write(
        root,
        "frontend/package.json",
        json.dumps({"name": "@gapsense/web", "version": "0.1.0"}),
    )
    _write(
        root,
        "frontend/package-lock.json",
        json.dumps(
            {
                "name": "@gapsense/web",
                "version": "0.1.0",
                "packages": {"": {"name": "@gapsense/web", "version": "0.1.0"}},
            }
        ),
    )
    _write(root, ".release-please-manifest.json", json.dumps({".": "0.1.0"}))
    _write(
        root,
        "vercel.json",
        json.dumps(
            {
                "$schema": "https://openapi.vercel.sh/vercel.json",
                "git": {"deploymentEnabled": False},
            }
        ),
    )
    _write(
        root,
        "release-please-config.json",
        json.dumps(
            {
                "bootstrap-sha": RELEASE_BOOTSTRAP_SHA,
                "include-component-in-tag": False,
                "include-v-in-tag": True,
                "packages": {
                    ".": {
                        "release-type": "python",
                        "package-name": "gapsense",
                        "extra-files": [
                            {
                                "type": "json",
                                "path": "frontend/package.json",
                                "jsonpath": "$.version",
                            },
                            {
                                "type": "json",
                                "path": "frontend/package-lock.json",
                                "jsonpath": "$.version",
                            },
                            {
                                "type": "json",
                                "path": "frontend/package-lock.json",
                                "jsonpath": '$.packages[""].version',
                            },
                        ],
                    }
                },
            }
        ),
    )
    _write(
        root,
        ".github/workflows/ci.yml",
        f"""name: CI
permissions:
  contents: read
env:
  GAPSENSE_PR_TITLE: ${{{{ github.event.pull_request.title || '' }}}}
jobs:
  validation:
    steps:
      - uses: actions/checkout@{CHECKOUT_SHA}
""",
    )
    _write(
        root,
        ".github/workflows/release-please.yml",
        f"""name: Release Please
jobs:
  release-please:
    permissions:
      contents: write
      issues: write
      pull-requests: write
    steps:
      - uses: googleapis/release-please-action@{RELEASE_PLEASE_SHA}
  dispatch-release-ci:
    permissions:
      actions: write
      contents: read
""",
    )


def test_repository_policy_accepts_pinned_single_version_contract(tmp_path: Path) -> None:
    _valid_repository(tmp_path)

    validate_repository(tmp_path)


@pytest.mark.parametrize(
    ("relative_path", "content", "message"),
    [
        ("src/gapsense/__init__.py", '__version__ = "0.1.1"\n', "versions differ"),
        (".release-please-manifest.json", '{".": "latest"}', "valid SemVer"),
        ("frontend/package.json", "{", "valid JSON"),
        ("frontend/package.json", "[]", "JSON object"),
        ("pyproject.toml", "[project", "valid TOML"),
        ("pyproject.toml", '[other]\nversion = "0.1.0"\n', "project must be an object"),
        ("src/gapsense/__init__.py", '"""No version."""\n', "must expose __version__"),
    ],
)
def test_repository_policy_rejects_invalid_version_sources(
    tmp_path: Path,
    relative_path: str,
    content: str,
    message: str,
) -> None:
    _valid_repository(tmp_path)
    _write(tmp_path, relative_path, content)

    with pytest.raises(RepositoryPolicyError, match=message):
        validate_repository(tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"bootstrap-sha": "0" * 40}, "reviewed bootstrap commit"),
        ({"include-component-in-tag": True}, "component-free"),
        ({"include-v-in-tag": False}, "v-prefixed"),
        ({"packages": {}}, "root package"),
        ({"packages": {".": {"release-type": "node"}}}, "Python release strategy"),
    ],
)
def test_repository_policy_rejects_unsafe_release_configuration(
    tmp_path: Path,
    mutation: dict[str, object],
    message: str,
) -> None:
    _valid_repository(tmp_path)
    config_path = tmp_path / "release-please-config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.update(mutation)
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(RepositoryPolicyError, match=message):
        validate_repository(tmp_path)


def test_repository_policy_requires_every_frontend_version_target(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    config_path = tmp_path / "release-please-config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["packages"]["."]["extra-files"].pop()
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(RepositoryPolicyError, match="frontend version targets"):
        validate_repository(tmp_path)


def test_repository_policy_requires_readable_python_version_file(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    (tmp_path / "src/gapsense/__init__.py").unlink()

    with pytest.raises(RepositoryPolicyError, match="must be readable"):
        validate_repository(tmp_path)


def test_repository_policy_requires_extra_file_list(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    config_path = tmp_path / "release-please-config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["packages"]["."]["extra-files"] = {}
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(RepositoryPolicyError, match="must be a list"):
        validate_repository(tmp_path)


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        ("actions/checkout@v4", "immutable commit SHA"),
        (f"unknown/action@{'a' * 40}", "allowlisted"),
        (f"actions/checkout@{'a' * 40}", "reviewed SHA"),
    ],
)
def test_repository_policy_rejects_untrusted_action_references(
    tmp_path: Path,
    reference: str,
    message: str,
) -> None:
    _valid_repository(tmp_path)
    _write(
        tmp_path,
        ".github/workflows/ci.yml",
        f"name: CI\npermissions:\n  contents: read\njobs:\n  validation:\n    steps:\n      - uses: {reference}\n",
    )

    with pytest.raises(RepositoryPolicyError, match=message):
        validate_repository(tmp_path)


def test_repository_policy_allows_local_actions(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    ci_path = tmp_path / ".github/workflows/ci.yml"
    ci_path.write_text(
        ci_path.read_text(encoding="utf-8") + "      - uses: ./actions/example\n",
        encoding="utf-8",
    )

    validate_repository(tmp_path)


@pytest.mark.parametrize(
    ("relative_path", "content", "message"),
    [
        (".github/workflows/ci.yml", "name: CI\njobs: {}\n", "read-only contents"),
        (
            ".github/workflows/release-please.yml",
            "name: Release Please\njobs: {}\n",
            "release permissions",
        ),
    ],
)
def test_repository_policy_rejects_missing_workflow_permissions(
    tmp_path: Path,
    relative_path: str,
    content: str,
    message: str,
) -> None:
    _valid_repository(tmp_path)
    _write(tmp_path, relative_path, content)

    with pytest.raises(RepositoryPolicyError, match=message):
        validate_repository(tmp_path)


def test_repository_policy_requires_pull_request_title_wiring(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    ci_path = tmp_path / ".github/workflows/ci.yml"
    ci_path.write_text(
        ci_path.read_text(encoding="utf-8").replace(
            "  GAPSENSE_PR_TITLE: ${{ github.event.pull_request.title || '' }}\n", ""
        ),
        encoding="utf-8",
    )

    with pytest.raises(RepositoryPolicyError, match="pull request title"):
        validate_repository(tmp_path)


def test_repository_policy_rejects_broken_internal_markdown_links(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    _write(
        tmp_path,
        "docs/OPERATING_MODEL.md",
        "[Missing evidence](evidence/does-not-exist.md)\n",
    )

    with pytest.raises(RepositoryPolicyError, match="broken internal Markdown link"):
        validate_repository(tmp_path)


def test_repository_policy_rejects_markdown_links_outside_repository(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    _write(tmp_path, "docs/OPERATING_MODEL.md", "[Outside](../../outside.md)\n")

    with pytest.raises(RepositoryPolicyError, match="broken internal Markdown link"):
        validate_repository(tmp_path)


@pytest.mark.parametrize(
    "content",
    [
        json.dumps({"git": {"deploymentEnabled": True}}),
        json.dumps({"git": {}}),
    ],
)
def test_repository_policy_rejects_enabled_or_implicit_vercel_deployment(
    tmp_path: Path, content: str
) -> None:
    _valid_repository(tmp_path)
    _write(tmp_path, "vercel.json", content)

    with pytest.raises(RepositoryPolicyError, match="automatic Vercel deployments"):
        validate_repository(tmp_path)


def test_repository_policy_requires_vercel_deployment_hold(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    (tmp_path / "vercel.json").unlink()

    with pytest.raises(RepositoryPolicyError, match="valid JSON"):
        validate_repository(tmp_path)


def test_repository_policy_accepts_resolvable_and_non_file_markdown_links(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    _write(tmp_path, "README.md", '[Operating model](docs/OPERATING_MODEL.md "Evidence")\n')
    _write(tmp_path, "TASKS.md", "# Tasks\n")
    _write(
        tmp_path,
        "docs/OPERATING_MODEL.md",
        "\n".join(
            (
                "# Operating model",
                "[Tasks](../TASKS.md?view=active#current)",
                "[Section](#operating-model)",
                "[Release Please](https://github.com/googleapis/release-please)",
            )
        ),
    )

    validate_repository(tmp_path)


def test_repository_policy_requires_workflows(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    (tmp_path / ".github/workflows/ci.yml").unlink()

    with pytest.raises(RepositoryPolicyError, match="Missing required workflow"):
        validate_repository(tmp_path)


def test_policy_cli_reports_success_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _valid_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main() == 0
    assert "passed" in capsys.readouterr().out

    (tmp_path / "frontend/package.json").write_text("{}", encoding="utf-8")
    assert main() == 1
    assert "failed" in capsys.readouterr().err


def test_policy_cli_validates_pull_request_title_from_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _valid_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GAPSENSE_PR_TITLE", "fix(ci): preserve release evidence")
    assert main() == 0
    assert "passed" in capsys.readouterr().out

    monkeypatch.setenv("GAPSENSE_PR_TITLE", "Bypass release policy")
    assert main() == 1
    assert "pull request title" in capsys.readouterr().err.lower()
