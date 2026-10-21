"""Generate and update a per-skill manifest with version and file inventory."""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

MANIFEST_FILENAME = "skill.manifest.json"


def _default_version() -> str:
    """Return the package `__version__` as the fallback manifest version."""
    import bigquery_data_science

    return bigquery_data_science.__version__


def _git_short_hash(cwd: Path) -> str | None:
    """Return the short git commit hash for `cwd`, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def build_manifest(
    skill_dir: Path,
    version: str | None = None,
    source_project: str | None = None,
) -> dict[str, object]:
    """Build a manifest dictionary for `skill_dir`.

    Passing `None` for `version` or `source_project` preserves the existing
    manifest's value, falling back to `bigquery_data_science.__version__` for a
    new skill.
    """
    reference_dir = skill_dir / "reference"
    syntax_dir = skill_dir / "syntax"
    narrative_dir = skill_dir / "narrative"

    reference_files = (
        sorted(path.name for path in reference_dir.glob("*.md"))
        if reference_dir.exists()
        else []
    )
    syntax_files = (
        sorted(
            path.name
            for path in syntax_dir.glob("*.md")
            if path.name != "INDEX.md"
        )
        if syntax_dir.exists()
        else []
    )
    narrative_files = (
        sorted(path.name for path in narrative_dir.glob("*.md"))
        if narrative_dir.exists()
        else []
    )

    existing: dict[str, object] = {}
    existing_manifest_path = skill_dir / MANIFEST_FILENAME
    if existing_manifest_path.exists():
        loaded = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            existing = loaded

    resolved_version = (
        version
        if version is not None
        else str(existing.get("version", _default_version()))
    )
    resolved_source_project = (
        source_project
        if source_project is not None
        else existing.get("source_project")
    )
    narrative_sources = existing.get("narrative_sources", {})
    if not isinstance(narrative_sources, dict):
        narrative_sources = {}

    return {
        "name": skill_dir.name,
        "version": resolved_version,
        "source_project": resolved_source_project,
        "narrative_sources": narrative_sources,
        "generated_date": date.today().isoformat(),
        "source_commit": _git_short_hash(skill_dir)
        or existing.get("source_commit"),
        "reference_files": reference_files,
        "syntax_files": syntax_files,
        "narrative_files": narrative_files,
    }


def write_manifest(
    skill_dir: Path,
    version: str | None = None,
    source_project: str | None = None,
) -> tuple[Path, str]:
    """Write `skill.manifest.json` in `skill_dir` and return `(path, version)`."""
    manifest = build_manifest(
        skill_dir,
        version=version,
        source_project=source_project,
    )
    manifest_path = skill_dir / MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path, str(manifest["version"])


def check_all_manifests(skills_root: Path) -> list[str]:
    """Verify that every skill under `skills_root` has an up-to-date `skill.manifest.json`."""
    errors: list[str] = []
    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        if not (skill_dir / "SKILL.md").is_file():
            continue
        manifest_path = skill_dir / MANIFEST_FILENAME
        if not manifest_path.is_file():
            errors.append(f"{skill_dir.name}: missing {MANIFEST_FILENAME}")
            continue
        actual = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = build_manifest(skill_dir)
        for key in ("name", "version", "reference_files", "syntax_files", "narrative_files"):
            if actual.get(key) != expected.get(key):
                errors.append(
                    f"{skill_dir.name}/{MANIFEST_FILENAME}: field '{key}' out of sync "
                    f"(expected {expected.get(key)!r}, got {actual.get(key)!r})"
                )
    return errors


def source_projects(skills_root: Path) -> list[str]:
    """Return sorted distinct `source_project` values declared under `skills_root`."""
    projects: set[str] = set()
    for manifest_path in sorted(skills_root.glob(f"*/{MANIFEST_FILENAME}")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        project = data.get("source_project")
        if isinstance(project, str) and project:
            projects.add(project)
    return sorted(projects)
