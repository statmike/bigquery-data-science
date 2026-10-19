"""Detect and synchronize `narrative/*.md` files against source notebooks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from bigquery_data_science.tooling.convert_notebook import (
    convert_notebook,
    convert_notebook_to_file,
)
from bigquery_data_science.tooling.manifest import MANIFEST_FILENAME

NARRATIVE_DIRNAME = "narrative"
_SKIP_DIRS: frozenset[str] = frozenset(
    {".venv", ".ipynb_checkpoints", "__pycache__", ".git", "node_modules"}
)


@dataclass
class DriftResult:
    """Result of checking narrative files for a single skill."""

    skill_name: str
    stale: list[str] = field(default_factory=list)
    missing_source: list[str] = field(default_factory=list)
    checked: int = 0

    @property
    def ok(self) -> bool:
        """Return True when zero narratives are stale or missing sources."""
        return not self.stale and not self.missing_source


def _find_notebooks(project_root: Path, stem: str) -> list[Path]:
    """Find notebooks matching `stem.ipynb` under `project_root`."""
    return [
        candidate
        for candidate in sorted(project_root.rglob(f"{stem}.ipynb"))
        if not (_SKIP_DIRS & set(candidate.parts))
    ]


def check_skill_narratives(skill_dir: Path, repo_root: Path) -> DriftResult | None:
    """Check `narrative/*.md` files in `skill_dir` against source notebooks."""
    result = DriftResult(skill_name=skill_dir.name)
    manifest_path = skill_dir / MANIFEST_FILENAME
    narrative_dir = skill_dir / NARRATIVE_DIRNAME
    if not manifest_path.exists() or not narrative_dir.exists():
        return None

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_project = manifest.get("source_project")
    if not isinstance(source_project, str) or not source_project:
        return None
    project_root = (repo_root / source_project).resolve()
    declared = manifest.get("narrative_sources") or {}

    for narrative in sorted(narrative_dir.glob("*.md")):
        result.checked += 1
        if narrative.name in declared:
            notebook = project_root / str(declared[narrative.name])
            if not notebook.exists():
                result.missing_source.append(
                    f"{narrative.name} declares a source notebook that does "
                    f"not exist: {declared[narrative.name]}"
                )
                continue
        else:
            candidates = _find_notebooks(project_root, narrative.stem)
            if not candidates:
                result.missing_source.append(
                    f"{narrative.name} has no source notebook"
                )
                continue
            if len(candidates) > 1:
                relative = ", ".join(
                    str(candidate.relative_to(project_root))
                    for candidate in candidates
                )
                result.missing_source.append(
                    f"{narrative.name} is ambiguous ({relative}) — add a "
                    "narrative_sources entry to the manifest"
                )
                continue
            notebook = candidates[0]

        regenerated = (
            convert_notebook(notebook_path=notebook, subproject_root=project_root)
            + "\n"
        )
        if regenerated != narrative.read_text(encoding="utf-8"):
            result.stale.append(narrative.name)

    return result


def check_all_narratives(
    skills_root: Path,
    repo_root: Path,
) -> dict[str, DriftResult]:
    """Check narrative drift across all skills under `skills_root`."""
    results: dict[str, DriftResult] = {}
    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        result = check_skill_narratives(skill_dir, repo_root)
        if result is not None:
            results[skill_dir.name] = result
    return results


def sync_skill_narratives(skill_dir: Path, repo_root: Path) -> int:
    """Regenerate all `narrative/*.md` files for `skill_dir`."""
    manifest_path = skill_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_project = manifest.get("source_project")
    if not isinstance(source_project, str) or not source_project:
        return 0
    project_root = (repo_root / source_project).resolve()
    declared: dict[str, str] = dict(manifest.get("narrative_sources") or {})
    declared_sources = {
        (project_root / rel_nb).resolve(): md_name
        for md_name, rel_nb in declared.items()
    }
    narrative_dir = skill_dir / NARRATIVE_DIRNAME
    narrative_dir.mkdir(parents=True, exist_ok=True)

    # Discover all topic notebooks under models/, functions/, workflows/, pipelines/
    topic_notebooks: dict[str, Path] = {}
    for md_name, rel_nb in declared.items():
        nb_path = (project_root / rel_nb).resolve()
        if nb_path.is_file():
            topic_notebooks[md_name] = nb_path

    for category in ("models", "functions", "workflows", "pipelines"):
        cat_dir = project_root / category
        if not cat_dir.is_dir():
            continue
        for nb_path in sorted(cat_dir.rglob("*.ipynb")):
            if _SKIP_DIRS & set(nb_path.parts):
                continue
            resolved_nb = nb_path.resolve()
            if resolved_nb in declared_sources:
                continue
            md_name = f"{nb_path.stem}.md"
            topic_notebooks[md_name] = resolved_nb

    written = 0
    for filename, notebook in sorted(topic_notebooks.items()):
        output_path = narrative_dir / filename
        convert_notebook_to_file(notebook, project_root, output_path)
        written += 1
    return written


def sync_all_narratives(skills_root: Path, repo_root: Path) -> int:
    """Regenerate all `narrative/*.md` files across skills under `skills_root`."""
    total = 0
    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        total += sync_skill_narratives(skill_dir, repo_root)
    return total
