"""Packaging, version-parity, README link, and notebook hygiene tests."""

from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.8.2"
SKILL_NAMES: tuple[str, ...] = (
    "bigquery-data-science",
    "bigquery-ml",
    "bigquery-ai",
)
GOVERNANCE_FILES: tuple[str, ...] = (
    "LICENSE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CITATION.cff",
    "CHANGELOG.md",
)
RELATIVE_LINK_RE = re.compile(
    r"\[([^\]\n]+)\]\((?!https?://|mailto:|#|data:)([^)\s#]+)(?:#[^)\s]*)?\)"
)


def _extract_init_fallback_version(init_path: Path) -> str:
    """Extract the `ExceptHandler` fallback `__version__` string from `__init__.py`."""
    tree = ast.parse(init_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            for statement in node.body:
                if isinstance(statement, ast.Assign):
                    for target in statement.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id == "__version__"
                            and isinstance(statement.value, ast.Constant)
                            and isinstance(statement.value.value, str)
                        ):
                            return statement.value.value
    raise AssertionError("No fallback __version__ assignment found in __init__.py")


def test_pyproject_metadata_and_zero_runtime_dependencies() -> None:
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    project = pyproject["project"]
    assert project["name"] == "bigquery-data-science"
    assert project["version"] == EXPECTED_VERSION
    assert project["dependencies"] == []
    assert (
        project["scripts"]["bigquery-data-science"]
        == "bigquery_data_science.cli:main"
    )
    assert (
        project["entry-points"]["statmike.agent_skills"][
            "bigquery_data_science"
        ]
        == "bigquery_data_science:get_skills_dir"
    )


def test_version_parity_across_code_manifests_and_docs() -> None:
    import bigquery_data_science

    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    pyproject_version = pyproject["project"]["version"]
    assert pyproject_version == EXPECTED_VERSION
    assert bigquery_data_science.__version__ == pyproject_version

    fallback_version = _extract_init_fallback_version(
        REPO_ROOT / "src" / "bigquery_data_science" / "__init__.py"
    )
    assert fallback_version == pyproject_version

    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{pyproject_version}]" in changelog

    citation = (REPO_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f'version: "{pyproject_version}"' in citation or (
        f"version: {pyproject_version}" in citation
    )

    plugin_json = json.loads(
        (REPO_ROOT / "plugin.json").read_text(encoding="utf-8")
    )
    assert plugin_json["version"] == pyproject_version

    marketplace = json.loads(
        (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    assert marketplace["plugins"][0]["version"] == pyproject_version

    for skill_name in SKILL_NAMES:
        manifest = json.loads(
            (
                REPO_ROOT / "skills" / skill_name / "skill.manifest.json"
            ).read_text(encoding="utf-8")
        )
        assert manifest["version"] == pyproject_version
        skill_md = (REPO_ROOT / "skills" / skill_name / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert (
            f'version: "{pyproject_version}"' in skill_md[:600]
            or f"version: {pyproject_version}" in skill_md[:600]
        )


def test_wheel_and_sdist_hatch_configuration() -> None:
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    wheel_cfg = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel_cfg["packages"] == ["src/bigquery_data_science"]
    force_include = wheel_cfg["force-include"]
    assert any(
        str(val).startswith("bigquery_data_science/_skills")
        for val in force_include.values()
    )
    sdist_excludes = pyproject["tool"]["hatch"]["build"]["targets"]["sdist"][
        "exclude"
    ]
    for required_exclude in ("/.github", "/.agents", "/.claude", "/uv.lock"):
        assert required_exclude in sdist_excludes


def test_readme_relative_links_resolve_on_disk() -> None:
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    matches = list(RELATIVE_LINK_RE.finditer(readme_text))
    assert matches, "Expected relative links in README.md"
    for match in matches:
        target = match.group(2).strip()
        resolved = (REPO_ROOT / target).resolve()
        assert resolved.exists(), (
            f"Broken relative link in README.md: {target} -> {resolved}"
        )


def test_hatch_fancy_pypi_readme_substitutions_leave_zero_relative_links() -> None:
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    hook = pyproject["tool"]["hatch"]["metadata"]["hooks"]["fancy-pypi-readme"]
    rendered = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for sub in hook["substitutions"]:
        rendered = re.sub(sub["pattern"], sub["replacement"], rendered)
    remaining = list(RELATIVE_LINK_RE.finditer(rendered))
    assert not remaining, (
        f"Un-rewritten relative links after fancy-pypi-readme: {remaining}"
    )
    assert "https://github.com/statmike/bigquery-data-science/blob/main/" in rendered
    assert "```mermaid" not in rendered
    assert (
        "https://raw.githubusercontent.com/statmike/bigquery-data-science/main/docs/assets/readme_architecture.png"
        in rendered
    )
    assert (REPO_ROOT / "docs" / "assets" / "social_card.png").is_file()
    assert (REPO_ROOT / "docs" / "assets" / "readme_architecture.png").is_file()


def test_governance_and_ci_workflow_files_exist() -> None:
    for filename in GOVERNANCE_FILES:
        path = REPO_ROOT / filename
        assert path.is_file() and path.stat().st_size > 100, (
            f"Missing or empty governance file: {filename}"
        )
    assert (REPO_ROOT / ".github" / "workflows" / "ci.yml").is_file()
    assert (REPO_ROOT / ".github" / "workflows" / "release.yml").is_file()
    assert (REPO_ROOT / "scripts" / "check_install.sh").is_file()


def test_all_107_notebooks_have_unified_kernelspec_and_clean_links() -> None:
    notebooks = sorted((REPO_ROOT / "bigquery-ml").rglob("*.ipynb")) + sorted(
        (REPO_ROOT / "bigquery-ai").rglob("*.ipynb")
    )
    assert len(notebooks) == 107
    for nb_path in notebooks:
        data = json.loads(nb_path.read_text(encoding="utf-8"))
        for cell in data.get("cells", []):
            cell_source = "".join(cell.get("source", []))
            assert "vertex-ai-mlops/blob/main/data+ai" not in cell_source
            assert "bq-ai-functions" not in cell_source
        kernelspec = data.get("metadata", {}).get("kernelspec", {})
        assert kernelspec.get("name") == "bigquery-data-science"
        assert kernelspec.get("display_name") == "BigQuery Data Science"


def test_uv_lock_contains_only_public_pypi_urls() -> None:
    lock_text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    registries = set(re.findall(r'registry\s*=\s*"([^"]+)"', lock_text))
    assert registries == {"https://pypi.org/simple"}
    assert "devpi" not in lock_text
