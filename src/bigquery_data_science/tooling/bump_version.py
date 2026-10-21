"""Lockstep Semantic Version stamper and parity verifier across repository files."""

from __future__ import annotations

import json
import re
import tomllib
from datetime import date
from pathlib import Path

from bigquery_data_science.tooling.manifest import (
    MANIFEST_FILENAME,
    write_manifest,
)

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:rc\d+)?$")
_PYPROJECT_VERSION_RE = re.compile(
    r'^(version\s*=\s*)"([^"]+)"',
    re.MULTILINE,
)
_INIT_FALLBACK_RE = re.compile(
    r'(except\s+PackageNotFoundError:\s*\n\s*__version__\s*=\s*)"([^"]+)"'
)
_CITATION_VERSION_RE = re.compile(
    r'^(version:\s*)"?([^"\n]+)"?',
    re.MULTILINE,
)
_CITATION_DATE_RE = re.compile(
    r'^(date-released:\s*)"?([^"\n]+)"?',
    re.MULTILINE,
)
_SKILL_FRONTMATTER_VERSION_RE = re.compile(
    r"^(\s*version:\s*)\"?([^\"\n]+)\"?$",
    re.MULTILINE,
)
_TEST_EXPECTED_VERSION_RE = re.compile(
    r'^(EXPECTED_VERSION\s*=\s*)"([^"]+)"',
    re.MULTILINE,
)


def validate_semver(version_str: str) -> str:
    """Validate that `version_str` is a canonical `X.Y.Z` (or `X.Y.ZrcN`) string."""
    cleaned = version_str.strip()
    if not SEMVER_RE.fullmatch(cleaned):
        raise ValueError(
            f"Invalid semantic version {version_str!r}; expected 'X.Y.Z' or 'X.Y.ZrcN'."
        )
    return cleaned


def read_pyproject_version(repo_root: Path) -> str:
    """Read `project.version` from `<repo_root>/pyproject.toml`."""
    pyproject_path = repo_root / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    if not isinstance(project, dict) or not isinstance(project.get("version"), str):
        raise ValueError(f"Missing project.version in {pyproject_path}")
    return str(project["version"])


def _extract_skill_frontmatter_version(skill_md_path: Path) -> str | None:
    """Extract `metadata.version` from the YAML frontmatter of `SKILL.md`."""
    text = skill_md_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return None
    frontmatter = text[4:end_idx]
    match = _SKILL_FRONTMATTER_VERSION_RE.search(frontmatter)
    return match.group(2).strip() if match else None


def _update_skill_frontmatter_version(skill_md_path: Path, new_version: str) -> bool:
    """Update `version: "..."` inside the YAML frontmatter of `SKILL.md`."""
    text = skill_md_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return False
    frontmatter = text[4:end_idx]
    updated_frontmatter, count = _SKILL_FRONTMATTER_VERSION_RE.subn(
        rf'\g<1>"{new_version}"',
        frontmatter,
        count=1,
    )
    if count == 0:
        return False
    new_text = f"---\n{updated_frontmatter}{text[end_idx:]}"
    if new_text != text:
        skill_md_path.write_text(new_text, encoding="utf-8")
    return True


def check_version_lockstep(
    repo_root: Path,
    expected_version: str | None = None,
) -> list[str]:
    """Return a list of version mismatch errors across all lockstep files in `repo_root`."""
    errors: list[str] = []
    try:
        pyproject_version = read_pyproject_version(repo_root)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        return [f"pyproject.toml: {exc}"]

    target_version = (
        validate_semver(expected_version)
        if expected_version is not None
        else pyproject_version
    )
    if pyproject_version != target_version:
        errors.append(
            f"pyproject.toml: expected {target_version!r}, got {pyproject_version!r}"
        )

    init_path = repo_root / "src" / "bigquery_data_science" / "__init__.py"
    if init_path.is_file():
        init_match = _INIT_FALLBACK_RE.search(init_path.read_text(encoding="utf-8"))
        init_ver = init_match.group(2) if init_match else None
        if init_ver != target_version:
            errors.append(
                f"src/bigquery_data_science/__init__.py: expected {target_version!r}, "
                f"got {init_ver!r}"
            )
    else:
        errors.append("src/bigquery_data_science/__init__.py: file missing")

    citation_path = repo_root / "CITATION.cff"
    if citation_path.is_file():
        cit_match = _CITATION_VERSION_RE.search(
            citation_path.read_text(encoding="utf-8")
        )
        cit_ver = cit_match.group(2).strip() if cit_match else None
        if cit_ver != target_version:
            errors.append(
                f"CITATION.cff: expected {target_version!r}, got {cit_ver!r}"
            )
    else:
        errors.append("CITATION.cff: file missing")

    plugin_path = repo_root / "plugin.json"
    if plugin_path.is_file():
        plugin_data = json.loads(plugin_path.read_text(encoding="utf-8"))
        plugin_ver = plugin_data.get("version") if isinstance(plugin_data, dict) else None
        if plugin_ver != target_version:
            errors.append(
                f"plugin.json: expected {target_version!r}, got {plugin_ver!r}"
            )
    else:
        errors.append("plugin.json: file missing")

    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    if marketplace_path.is_file():
        mp_data = json.loads(marketplace_path.read_text(encoding="utf-8"))
        if isinstance(mp_data, dict):
            if mp_data.get("version") != target_version:
                errors.append(
                    f".claude-plugin/marketplace.json (root): expected "
                    f"{target_version!r}, got {mp_data.get('version')!r}"
                )
            metadata = mp_data.get("metadata")
            if isinstance(metadata, dict) and metadata.get("version") != target_version:
                errors.append(
                    f".claude-plugin/marketplace.json (metadata): expected "
                    f"{target_version!r}, got {metadata.get('version')!r}"
                )
            plugins = mp_data.get("plugins")
            if isinstance(plugins, list):
                for idx, entry in enumerate(plugins):
                    if isinstance(entry, dict) and entry.get("version") != target_version:
                        errors.append(
                            f".claude-plugin/marketplace.json (plugins[{idx}]): "
                            f"expected {target_version!r}, got {entry.get('version')!r}"
                        )
    else:
        errors.append(".claude-plugin/marketplace.json: file missing")

    skills_root = repo_root / "skills"
    if skills_root.is_dir():
        for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            fm_ver = _extract_skill_frontmatter_version(skill_md)
            if fm_ver != target_version:
                errors.append(
                    f"skills/{skill_dir.name}/SKILL.md: expected {target_version!r}, "
                    f"got {fm_ver!r}"
                )
            manifest_path = skill_dir / MANIFEST_FILENAME
            if manifest_path.is_file():
                mf_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                mf_ver = mf_data.get("version") if isinstance(mf_data, dict) else None
                if mf_ver != target_version:
                    errors.append(
                        f"skills/{skill_dir.name}/{MANIFEST_FILENAME}: expected "
                        f"{target_version!r}, got {mf_ver!r}"
                    )
            else:
                errors.append(
                    f"skills/{skill_dir.name}/{MANIFEST_FILENAME}: file missing"
                )

    test_pkg_path = repo_root / "tests" / "test_packaging.py"
    if test_pkg_path.is_file():
        tp_match = _TEST_EXPECTED_VERSION_RE.search(
            test_pkg_path.read_text(encoding="utf-8")
        )
        tp_ver = tp_match.group(2) if tp_match else None
        if tp_ver != target_version:
            errors.append(
                f"tests/test_packaging.py: expected {target_version!r}, got {tp_ver!r}"
            )

    return errors


def bump_version(
    repo_root: Path,
    new_version: str,
    release_date: str | None = None,
) -> list[Path]:
    """Stamp `new_version` across all lockstep files in `repo_root` and return updated paths."""
    validated = validate_semver(new_version)
    resolved_date = release_date or date.today().isoformat()
    updated: list[Path] = []

    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.is_file():
        text = pyproject_path.read_text(encoding="utf-8")
        new_text, count = _PYPROJECT_VERSION_RE.subn(
            rf'\g<1>"{validated}"',
            text,
            count=1,
        )
        if count:
            pyproject_path.write_text(new_text, encoding="utf-8")
            updated.append(pyproject_path)

    init_path = repo_root / "src" / "bigquery_data_science" / "__init__.py"
    if init_path.is_file():
        text = init_path.read_text(encoding="utf-8")
        new_text, count = _INIT_FALLBACK_RE.subn(
            rf'\g<1>"{validated}"',
            text,
            count=1,
        )
        if count:
            init_path.write_text(new_text, encoding="utf-8")
            updated.append(init_path)

    citation_path = repo_root / "CITATION.cff"
    if citation_path.is_file():
        text = citation_path.read_text(encoding="utf-8")
        new_text, count = _CITATION_VERSION_RE.subn(
            rf'\g<1>"{validated}"',
            text,
            count=1,
        )
        new_text, _ = _CITATION_DATE_RE.subn(
            rf'\g<1>"{resolved_date}"',
            new_text,
            count=1,
        )
        if count:
            citation_path.write_text(new_text, encoding="utf-8")
            updated.append(citation_path)

    plugin_path = repo_root / "plugin.json"
    if plugin_path.is_file():
        plugin_data = json.loads(plugin_path.read_text(encoding="utf-8"))
        if isinstance(plugin_data, dict):
            plugin_data["version"] = validated
            plugin_path.write_text(
                json.dumps(plugin_data, indent=2) + "\n",
                encoding="utf-8",
            )
            updated.append(plugin_path)

    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    if marketplace_path.is_file():
        mp_data = json.loads(marketplace_path.read_text(encoding="utf-8"))
        if isinstance(mp_data, dict):
            mp_data["version"] = validated
            metadata = mp_data.get("metadata")
            if isinstance(metadata, dict):
                metadata["version"] = validated
            plugins = mp_data.get("plugins")
            if isinstance(plugins, list):
                for entry in plugins:
                    if isinstance(entry, dict):
                        entry["version"] = validated
            marketplace_path.write_text(
                json.dumps(mp_data, indent=2) + "\n",
                encoding="utf-8",
            )
            updated.append(marketplace_path)

    skills_root = repo_root / "skills"
    if skills_root.is_dir():
        for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            if _update_skill_frontmatter_version(skill_md, validated):
                updated.append(skill_md)
            manifest_path, _ = write_manifest(skill_dir, version=validated)
            updated.append(manifest_path)

    test_pkg_path = repo_root / "tests" / "test_packaging.py"
    if test_pkg_path.is_file():
        text = test_pkg_path.read_text(encoding="utf-8")
        new_text, count = _TEST_EXPECTED_VERSION_RE.subn(
            rf'\g<1>"{validated}"',
            text,
            count=1,
        )
        if count:
            test_pkg_path.write_text(new_text, encoding="utf-8")
            updated.append(test_pkg_path)

    return updated
