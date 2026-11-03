"""Inventory model and endpoint literals a project pins against `pinned-models.json`."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKIP_PARTS: frozenset[str] = frozenset(
    {".venv", ".ipynb_checkpoints", "node_modules", "__pycache__"}
)
_PIN_SKIP: frozenset[str] = frozenset({"PLANS.md"})

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
    if value.startswith(("https://", "http://", "projects/")):
        return True
    if re.fullmatch(r"[A-Z0-9_]+", value):
        return True
    return bool(_PLACEHOLDER_TOKEN_RE.search(value))


def _strip_line_comments(text: str) -> str:
    """Strip `--` and `#` comments per line while preserving line breaks."""
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines(keepends=True):
        ending = "\n" if raw_line.endswith("\n") else ""
        body = raw_line[:-1] if ending else raw_line
        if body.lstrip().startswith(("--", "#")):
            cleaned_lines.append(ending)
            continue
        quote: str | None = None
        idx = 0
        length = len(body)
        cut = length
        while idx < length:
            ch = body[idx]
            if quote is not None:
                if ch == "\\" and idx + 1 < length:
                    idx += 2
                    continue
                if ch == quote:
                    if idx + 1 < length and body[idx + 1] == quote:
                        idx += 2
                        continue
                    quote = None
                idx += 1
                continue
            if body[idx : idx + 2] == "--" or ch == "#":
                cut = idx
                break
            if ch in ("'", '"'):
                quote = ch
            idx += 1
        cleaned_lines.append(body[:cut] + ending)
    return "".join(cleaned_lines)


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
    """Extract non-placeholder pins from `text` after stripping line comments."""
    uncommented = _strip_line_comments(text)
    pins: list[Pin] = []
    for match in _PIN_RE.finditer(uncommented):
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
    text = _strip_line_comments(path.read_text(encoding="utf-8"))
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
        if not path.is_file() or (SKIP_PARTS & set(path.parts)) or path.name in _PIN_SKIP:
            continue
        if path.suffix in {".ipynb", ".sql", ".md", ".py"}:
            yield path


def _is_legacy_violation(
    pin: Pin,
    legacy_models: dict[str, dict[str, Any]],
) -> bool:
    """Return True when `pin` violates the `legacy_models` stem allowlist."""
    rule = legacy_models.get(pin.value)
    if rule is None:
        return False
    allow_code = {str(s) for s in rule.get("allow_in_code_cells", [])}
    allow_sql = {str(s) for s in rule.get("allow_in_sql", [])}
    stem = pin.path.stem
    if pin.path.suffix == ".ipynb":
        return stem not in allow_code
    if pin.path.suffix == ".sql":
        return stem not in allow_sql
    return stem not in (allow_code | allow_sql)


def _default_allow_file(project_root: Path) -> Path | None:
    """Locate the default `pinned-models.json` relative to `project_root` or package."""
    found = find_allow_file(project_root)
    if found is not None:
        return found
    repo_candidate = Path(__file__).resolve().parents[3] / "skills" / "pinned-models.json"
    if repo_candidate.is_file():
        return repo_candidate
    return None


def check_pinned_models(
    project_root: Path,
    allowed: set[str],
    deprecated: dict[str, str] | None = None,
    legacy_models: dict[str, dict[str, Any]] | None = None,
) -> PinnedModelsResult:
    """Scan `project_root` for model/endpoint pins and compare against allowlists."""
    if deprecated is None or legacy_models is None:
        default_file = _default_allow_file(project_root)
        if default_file is not None:
            if deprecated is None:
                deprecated = load_deprecated_models(default_file)
            if legacy_models is None:
                legacy_models = load_legacy_models(default_file)

    active_deprecated = deprecated or {}
    active_legacy = legacy_models or {}

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
    if allowed or active_deprecated or active_legacy:
        result.unlisted = [
            pin
            for pin in result.pins
            if (allowed and pin.value not in allowed)
            or pin.value in active_deprecated
            or _is_legacy_violation(pin, active_legacy)
        ]
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
    if key == "skills" or key.startswith("skills/"):
        allowed |= set(data.get("bigquery-ai", []))
        allowed |= set(data.get("bigquery-ml", []))
    allowed |= set(data.get(key, []))
    return allowed


def load_preferred_defaults(allow_file: Path) -> dict[str, str]:
    """Load `preferred_defaults` tier mapping from `allow_file`."""
    data = json.loads(allow_file.read_text(encoding="utf-8"))
    raw = data.get("preferred_defaults", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def load_deprecated_models(allow_file: Path) -> dict[str, str]:
    """Load `deprecated` model-to-replacement mapping from `allow_file`."""
    data = json.loads(allow_file.read_text(encoding="utf-8"))
    raw = data.get("deprecated", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def load_legacy_models(allow_file: Path) -> dict[str, dict[str, Any]]:
    """Load `legacy_models` per-stem allowlists from `allow_file`."""
    data = json.loads(allow_file.read_text(encoding="utf-8"))
    raw = data.get("legacy_models", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)}


def find_allow_file(
    skills_root: Path,
    filename: str = "pinned-models.json",
) -> Path | None:
    """Locate `pinned-models.json` walking up from `skills_root` and child skills."""
    starts = [skills_root.resolve()]
    if skills_root.is_dir():
        starts += [child.resolve() for child in sorted(skills_root.iterdir()) if child.is_dir()]
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
