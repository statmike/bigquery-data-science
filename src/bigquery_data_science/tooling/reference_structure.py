"""Check that a project's `RESOURCES.md` index and its `reference/` pages agree."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from bigquery_data_science.tooling.markdown_anchors import headings, slugify

INDEX_FILENAME = "RESOURCES.md"
REFERENCE_DIRNAME = "reference"

_LINK_RE = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)\)")


@dataclass
class ReferenceResult:
    """Result of checking `RESOURCES.md` against `reference/*.md`."""

    project_root: Path
    errors: list[str] = field(default_factory=list)
    checked: int = 0

    @property
    def ok(self) -> bool:
        """Return True when zero reference structure errors were found."""
        return not self.errors


def _index_targets(index_path: Path) -> set[str]:
    """Return filenames under `reference/` that `index_path` links to."""
    targets: set[str] = set()
    for match in _LINK_RE.finditer(index_path.read_text(encoding="utf-8")):
        target = match.group(1).split("#")[0]
        if target.startswith(f"{REFERENCE_DIRNAME}/") and target.endswith(".md"):
            targets.add(Path(target).name)
    return targets


def check_reference(project_root: Path) -> ReferenceResult:
    """Verify `RESOURCES.md` and `reference/*.md` 1:1 coverage and H1 naming."""
    project_root = project_root.resolve()
    result = ReferenceResult(project_root=project_root)

    index_path = project_root / INDEX_FILENAME
    reference_dir = project_root / REFERENCE_DIRNAME
    if not index_path.exists():
        result.errors.append(f"{INDEX_FILENAME} not found")
        return result
    if not reference_dir.exists():
        return result

    pages = {path.name for path in reference_dir.glob("*.md")}
    linked = _index_targets(index_path)
    result.checked = len(pages)

    for orphan in sorted(pages - linked):
        result.errors.append(
            f"{REFERENCE_DIRNAME}/{orphan} exists but {INDEX_FILENAME} "
            "does not link to it"
        )
    for missing in sorted(linked - pages):
        result.errors.append(
            f"{INDEX_FILENAME} links to {REFERENCE_DIRNAME}/{missing}, "
            "which does not exist"
        )

    for page in sorted(pages & linked):
        page_headings = headings((reference_dir / page).read_text(encoding="utf-8"))
        titles = [title for level, title in page_headings if level == 1]
        if len(titles) != 1:
            result.errors.append(
                f"{REFERENCE_DIRNAME}/{page} has {len(titles)} top-level "
                "headings, expected exactly 1"
            )
            continue
        expected = re.sub(r"-{2,}", "-", slugify(titles[0])).strip("-") + ".md"
        if page != expected:
            result.errors.append(
                f"{REFERENCE_DIRNAME}/{page} is titled '{titles[0]}', "
                f"so it should be named {expected}"
            )

    return result
