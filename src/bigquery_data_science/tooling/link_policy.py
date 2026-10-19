"""Enforce the outward-link policy on a source project (`bigquery-ml`, `bigquery-ai`)."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from bigquery_data_science.tooling.markdown_anchors import anchors_of

_LINK_RE = re.compile(r"\[([^\]\n]*)\]\(((?:[^()\s]|\([^()]*\))+)\)")
_MENTION_RE = re.compile(r"`([^`\n]+)`")
_SKIP_DIRS: frozenset[str] = frozenset(
    {".venv", ".ipynb_checkpoints", "__pycache__", ".git", "node_modules"}
)
_SCANNED_SUFFIXES: frozenset[str] = frozenset({".ipynb", ".md", ".sql", ".py"})
_EXTERNAL_SCHEMES: tuple[str, ...] = (
    "http://",
    "https://",
    "mailto:",
    "gs://",
    "bq://",
)
_PATH_SUFFIXES: frozenset[str] = frozenset(
    {".ipynb", ".md", ".sql", ".py", ".json", ".csv", ".yaml", ".yml", ".txt"}
)

EXEMPT_ANY_TARGET: frozenset[str] = frozenset({"PLANS.md"})
README_ALLOWED_PREFIX = "skills"


@dataclass
class Violation:
    """A single outward-link, missing-target, or broken-anchor violation."""

    file: Path
    cell: int | None
    line: int
    kind: str
    target: str
    reason: str

    def format(self, project_root: Path) -> str:
        """Format the violation relative to `project_root`."""
        where = str(self.file.relative_to(project_root))
        where += (
            f" cell {self.cell}:{self.line}"
            if self.cell is not None
            else f":{self.line}"
        )
        return f"{where}: {self.reason} [{self.kind}] {self.target}"


@dataclass
class PolicyResult:
    """Aggregated link-policy results for a single source project."""

    project_root: Path
    violations: list[Violation] = field(default_factory=list)
    scanned: int = 0

    @property
    def ok(self) -> bool:
        """Return True when zero violations were found."""
        return not self.violations


def _sources(path: Path) -> Iterator[tuple[int | None, str]]:
    """Yield `(cell_index_or_None, text)` for a scannable file."""
    if path.suffix == ".ipynb":
        try:
            notebook = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            return
        for index, cell in enumerate(notebook.get("cells", [])):
            yield index, "".join(cell.get("source", []))
    else:
        try:
            yield None, path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return


def _line_of(text: str, offset: int) -> int:
    """Return the 1-based line number of character `offset` in `text`."""
    return text.count("\n", 0, offset) + 1


def _looks_like_path(candidate: str) -> bool:
    """Return True when `candidate` looks like a file path in backticks."""
    if "/" not in candidate or candidate.startswith(_EXTERNAL_SCHEMES):
        return False
    if any(character in candidate for character in "{}$*<>|"):
        return False
    return Path(candidate).suffix in _PATH_SUFFIXES


def _resolve(target: str, base: Path) -> Path:
    """Resolve a markdown link target against `base`."""
    cleaned = (
        target.split("#")[0]
        .replace("%20", " ")
        .replace("%28", "(")
        .replace("%29", ")")
    )
    return (base / cleaned).resolve()


def _classify(
    resolved: Path,
    project_root: Path,
    sibling_roots: list[Path],
    repo_root: Path,
) -> str:
    """Return empty string when allowed, else a human-readable violation reason."""
    if resolved.is_relative_to(project_root):
        return ""
    for sibling in sibling_roots:
        if resolved.is_relative_to(sibling):
            return ""
    if not resolved.is_relative_to(repo_root):
        return "points outside the repository"
    return "points elsewhere in the repository"


def _is_readme_allowed(resolved: Path, repo_root: Path) -> bool:
    """Return True when a README link/mention points to `skills/` or root `README.md`."""
    return (
        resolved.is_relative_to(repo_root / README_ALLOWED_PREFIX)
        or resolved == (repo_root / "README.md")
    )


def check_project(
    project_root: Path,
    sibling_roots: list[Path],
    repo_root: Path,
) -> PolicyResult:
    """Enforce link, mention, and `#anchor` rules on `project_root`."""
    project_root = project_root.resolve()
    resolved_siblings = [sibling.resolve() for sibling in sibling_roots]
    repo_root = repo_root.resolve()
    result = PolicyResult(project_root=project_root)

    for path in sorted(project_root.rglob("*")):
        if not path.is_file() or path.suffix not in _SCANNED_SUFFIXES:
            continue
        if _SKIP_DIRS & set(path.parts):
            continue
        policy_exempt = path.name in EXEMPT_ANY_TARGET
        result.scanned += 1
        is_readme = path.name == "README.md"

        for cell, text in _sources(path):
            for match in _LINK_RE.finditer(text):
                target = match.group(2)
                if target.startswith(_EXTERNAL_SCHEMES):
                    continue
                if target.startswith("#"):
                    if target[1:] not in anchors_of(path):
                        line = _line_of(text, match.start())
                        result.violations.append(
                            Violation(
                                path,
                                cell,
                                line,
                                "anchor",
                                target,
                                "no heading matches this anchor",
                            )
                        )
                    continue
                resolved = _resolve(target, path.parent)
                skip_policy = policy_exempt or (
                    is_readme and _is_readme_allowed(resolved, repo_root)
                )
                reason = (
                    ""
                    if skip_policy
                    else _classify(
                        resolved, project_root, resolved_siblings, repo_root
                    )
                )
                if not reason and not resolved.exists():
                    reason = "" if policy_exempt else "link target does not exist"
                if reason:
                    line = _line_of(text, match.start())
                    result.violations.append(
                        Violation(path, cell, line, "link", target, reason)
                    )
                    continue

                anchor = target.partition("#")[2]
                if (
                    not anchor
                    or resolved.suffix not in {".md", ".ipynb"}
                    or not resolved.exists()
                ):
                    continue
                if anchor not in anchors_of(resolved):
                    line = _line_of(text, match.start())
                    result.violations.append(
                        Violation(
                            path,
                            cell,
                            line,
                            "anchor",
                            target,
                            "no heading matches this anchor",
                        )
                    )

            if policy_exempt:
                continue

            for match in _MENTION_RE.finditer(text):
                candidate = match.group(1).strip()
                if not _looks_like_path(candidate):
                    continue
                for base in (path.parent, repo_root):
                    resolved = _resolve(candidate, base)
                    if not resolved.exists():
                        continue
                    if is_readme and _is_readme_allowed(resolved, repo_root):
                        break
                    reason = _classify(
                        resolved, project_root, resolved_siblings, repo_root
                    )
                    if reason:
                        line = _line_of(text, match.start())
                        result.violations.append(
                            Violation(
                                path, cell, line, "mention", candidate, reason
                            )
                        )
                    break

    result.violations.sort(
        key=lambda violation: (
            str(violation.file),
            violation.cell if violation.cell is not None else -1,
            violation.line,
        )
    )
    return result
