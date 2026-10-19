"""Inventory model and endpoint literals a project pins against `pinned-models.json`."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

SKIP_PARTS: frozenset[str] = frozenset(
    {".venv", ".ipynb_checkpoints", "node_modules", "__pycache__"}
)

_PIN_RE = re.compile(
    r"""\b(?P<kind>endpoint|model)\s*(?:=>|=)\s*(?P<quote>['"])(?P<value>[^'"\n]*)(?P=quote)""",
    re.IGNORECASE,
)
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_PLACEHOLDER_TOKEN_RE = re.compile(
    r"\b(?:PROJECT_ID|PROJECT_NUM|PROJECT_NUMBER|LOCATION|REGION|ENDPOINT_ID|"
    r"PROCESSOR_ID|MODEL_ID|CONNECTION_ID|DATASET_ID|ENDPOINT|MODEL)\b"
)


def is_placeholder(value: str) -> bool:
    """Return True for syntax-table placeholders rather than real model pins."""
    if not value or "{" in value:
        return True
    if value.lower() in {"endpoint", "model"}:
        return True
    if re.fullmatch(r"[A-Z0-9_]+", value):
        return True
    return bool(_PLACEHOLDER_TOKEN_RE.search(value))


@dataclass
class Pin:
    """A single pinned `endpoint` or `model` literal discovered in source."""

    path: Path
    location: str
    kind: str
    value: str

    def format(self, project_root: Path) -> str:
        """Format the pin location relative to `project_root`."""
        return (
            f"{self.path.relative_to(project_root)} ({self.location}): "
            f"{self.kind} => '{self.value}'"
        )


@dataclass
class PinnedModelsResult:
    """Result of scanning a project for pinned model and endpoint literals."""

    project_root: Path
    scanned: int = 0
    pins: list[Pin] = field(default_factory=list)
    unlisted: list[Pin] = field(default_factory=list)

    @property
    def counts(self) -> Counter[str]:
        """Return frequency counts of each pinned model or endpoint value."""
        return Counter(pin.value for pin in self.pins)

    @property
    def ok(self) -> bool:
        """Return True when zero unlisted pins were found."""
        return not self.unlisted

    @property
    def checked(self) -> list[Pin]:
        """Alias for `pins`."""
        return self.pins

    @property
    def unpinned(self) -> list[Pin]:
        """Alias for `unlisted`."""
        return self.unlisted


def _pins_in_text(text: str, path: Path, location: str) -> list[Pin]:
    """Extract non-placeholder pins from `text`."""
    pins: list[Pin] = []
    for match in _PIN_RE.finditer(text):
        value = match.group("value").strip()
        if is_placeholder(value):
            continue
        pins.append(
            Pin(
                path=path,
                location=location,
                kind=match.group("kind").lower(),
                value=value,
            )
        )
    return pins


def _pins_in_notebook(path: Path) -> list[Pin]:
    """Extract pins from code cells in `path`."""
    notebook = json.loads(path.read_text(encoding="utf-8"))
    pins: list[Pin] = []
    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        pins.extend(_pins_in_text(source, path, f"cell {index}"))
    return pins


def _pins_in_markdown(path: Path) -> list[Pin]:
    """Extract pins from fenced code blocks in markdown `path`."""
    text = path.read_text(encoding="utf-8")
    pins: list[Pin] = []
    for match in _FENCE_RE.finditer(text):
        line_number = text.count("\n", 0, match.start()) + 1
        pins.extend(_pins_in_text(match.group(1), path, f"line {line_number}"))
    return pins


def _pins_in_plain(path: Path) -> list[Pin]:
    """Extract pins from plain `.sql` or `.py` files."""
    text = path.read_text(encoding="utf-8")
    pins: list[Pin] = []
    for match in _PIN_RE.finditer(text):
        value = match.group("value").strip()
        if is_placeholder(value):
            continue
        line_number = text.count("\n", 0, match.start()) + 1
        pins.append(
            Pin(
                path=path,
                location=f"line {line_number}",
                kind=match.group("kind").lower(),
                value=value,
            )
        )
    return pins


def iter_project_files(project_root: Path) -> Iterator[Path]:
    """Yield scannable `.ipynb`, `.sql`, `.md`, and `.py` files under `project_root`."""
    for path in sorted(project_root.rglob("*")):
        if not path.is_file() or (SKIP_PARTS & set(path.parts)):
            continue
        if path.suffix in {".ipynb", ".sql", ".md", ".py"}:
            yield path


def check_pinned_models(
    project_root: Path,
    allowed: set[str],
) -> PinnedModelsResult:
    """Scan `project_root` for model/endpoint pins and compare against `allowed`."""
    result = PinnedModelsResult(project_root=project_root)
    for path in iter_project_files(project_root):
        result.scanned += 1
        if path.suffix == ".ipynb":
            pins = _pins_in_notebook(path)
        elif path.suffix == ".md":
            pins = _pins_in_markdown(path)
        else:
            pins = _pins_in_plain(path)
        result.pins.extend(pins)
    if allowed:
        result.unlisted = [pin for pin in result.pins if pin.value not in allowed]
    return result


def load_allow_list(
    allow_file: Path,
    project_root: Path | str,
    repo_root: Path | None = None,
) -> set[str]:
    """Load allowed model/endpoint literals for `project_root` from `allow_file`."""
    data = json.loads(allow_file.read_text(encoding="utf-8"))
    if isinstance(project_root, str):
        key = project_root
    elif repo_root is not None:
        try:
            key = str(project_root.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            key = project_root.name
    else:
        key = project_root.name
    allowed: set[str] = set(data.get("*", []))
    allowed |= set(data.get(key, []))
    return allowed


def find_allow_file(
    skills_root: Path,
    filename: str = "pinned-models.json",
) -> Path | None:
    """Locate `pinned-models.json` walking up from `skills_root` and child skills."""
    starts = [skills_root.resolve()]
    if skills_root.is_dir():
        starts += [
            child.resolve()
            for child in sorted(skills_root.iterdir())
            if child.is_dir()
        ]
    seen: set[Path] = set()
    for start in starts:
        for candidate_dir in [start, *start.parents]:
            if candidate_dir in seen:
                continue
            seen.add(candidate_dir)
            candidate = candidate_dir / filename
            if candidate.is_file():
                return candidate
    return None
