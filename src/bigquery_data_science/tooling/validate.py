"""Lint a skill directory against the 4-Lens Agent Skill specification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from bigquery_data_science.tooling.sync_syntax import MAX_SYNTAX_CARD_BYTES

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
_DESCRIPTION_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
_VALID_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((?!https?://|mailto:)([^)\n]+)\)")

SKILL_MD_LINE_BUDGET = 500
REFERENCE_FILE_LINE_BUDGET = 100


@dataclass
class ValidationResult:
    """Validation errors and warnings for a single skill directory."""

    skill_dir: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True when zero validation errors were recorded."""
        return not self.errors


def _extract_description(frontmatter: str) -> str | None:
    """Extract `description` from YAML frontmatter (single-line or block)."""
    match = _DESCRIPTION_RE.search(frontmatter)
    if not match:
        return None
    first_line = match.group(1).strip()
    if first_line in {">-", ">", "|-", "|"}:
        lines: list[str] = []
        after = frontmatter[match.end() :].splitlines()
        for line in after:
            if line.startswith(("  ", "\t")):
                lines.append(line.strip())
            elif not line.strip():
                continue
            else:
                break
        return " ".join(lines).strip()
    return first_line.strip("'\"")


def _check_frontmatter(skill_md_text: str, result: ValidationResult) -> None:
    """Validate `SKILL.md` YAML frontmatter fields and constraints."""
    match = _FRONTMATTER_RE.match(skill_md_text)
    if not match:
        result.errors.append("SKILL.md is missing YAML frontmatter (--- ... ---)")
        return
    frontmatter = match.group(1)

    name_match = _NAME_RE.search(frontmatter)
    if not name_match:
        result.errors.append("frontmatter missing 'name'")
    else:
        name = name_match.group(1).strip().strip("'\"")
        if len(name) > 64:
            result.errors.append(f"name '{name}' exceeds 64 chars")
        if not _VALID_NAME_RE.match(name):
            result.errors.append(
                f"name '{name}' must be lowercase letters/digits/hyphens only"
            )
        if "claude" in name.lower() or "anthropic" in name.lower():
            result.errors.append(
                f"name '{name}' must not contain 'claude' or 'anthropic'"
            )

    description = _extract_description(frontmatter)
    if description is None:
        result.errors.append("frontmatter missing 'description'")
    else:
        if not description:
            result.errors.append("description is empty")
        if len(description) > 1024:
            result.errors.append(
                f"description exceeds 1024 chars ({len(description)})"
            )


def _has_toc(text: str) -> bool:
    """Return True when the first 10 lines contain a table of contents."""
    head = "\n".join(text.splitlines()[:10])
    return "contents:" in head.lower() or bool(re.search(r"\]\(#", head))


def _check_line_budget(
    path: Path,
    budget: int,
    result: ValidationResult,
) -> None:
    """Check line count budget on `SKILL.md` or `reference/*.md`."""
    text = path.read_text(encoding="utf-8")
    line_count = len(text.splitlines())
    if line_count <= budget:
        return
    if budget == REFERENCE_FILE_LINE_BUDGET:
        if not _has_toc(text):
            result.warnings.append(
                f"{path.name} is {line_count} lines (budget {budget}) — "
                "should carry a table of contents"
            )
    else:
        result.warnings.append(
            f"{path.name} is {line_count} lines (budget {budget}) — "
            "should stay under budget"
        )


_FENCE_LINE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def _strip_fences_and_code(text: str) -> str:
    """Remove fenced code blocks and inline code spans before link extraction."""
    out_lines: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in text.splitlines():
        m = _FENCE_LINE_RE.match(line)
        if m:
            marker = m.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker[0] * len(marker)
            elif line.lstrip().startswith(fence_marker):
                in_fence = False
                fence_marker = ""
            continue
        if not in_fence:
            out_lines.append(_INLINE_CODE_RE.sub("", line))
    return "\n".join(out_lines)


def _check_links(
    path: Path,
    skill_dir: Path,
    result: ValidationResult,
) -> None:
    """Check that all non-HTTP markdown links in `path` resolve on disk."""
    cleaned = _strip_fences_and_code(path.read_text(encoding="utf-8"))
    for match in _LINK_RE.finditer(cleaned):
        link_text, raw_target = match.group(1), match.group(2).strip()
        rel_path = raw_target.split("#", 1)[0].strip()
        if not rel_path:
            continue
        resolved = (path.parent / rel_path).resolve()
        if not resolved.exists():
            result.errors.append(
                f"{path.relative_to(skill_dir)}: broken link "
                f"[{link_text}]({raw_target})"
            )


def validate_skill(skill_dir: Path) -> ValidationResult:
    """Validate `SKILL.md`, `reference/*.md`, `syntax/*.md`, and `narrative/*.md`."""
    result = ValidationResult(skill_dir=skill_dir)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result.errors.append("SKILL.md not found")
        return result

    _check_frontmatter(skill_md.read_text(encoding="utf-8"), result)
    _check_line_budget(skill_md, SKILL_MD_LINE_BUDGET, result)
    _check_links(skill_md, skill_dir, result)

    reference_dir = skill_dir / "reference"
    if reference_dir.exists():
        for md_file in sorted(reference_dir.glob("*.md")):
            _check_line_budget(md_file, REFERENCE_FILE_LINE_BUDGET, result)
            _check_links(md_file, skill_dir, result)

    syntax_dir = skill_dir / "syntax"
    if syntax_dir.exists():
        for md_file in sorted(syntax_dir.glob("*.md")):
            _check_links(md_file, skill_dir, result)
            if md_file.name != "INDEX.md":
                size_bytes = len(md_file.read_bytes())
                if size_bytes > MAX_SYNTAX_CARD_BYTES:
                    result.errors.append(
                        f"syntax/{md_file.name} exceeds {MAX_SYNTAX_CARD_BYTES:,} "
                        f"bytes ({size_bytes:,} B)"
                    )

    narrative_dir = skill_dir / "narrative"
    if narrative_dir.exists():
        for md_file in sorted(narrative_dir.glob("*.md")):
            _check_links(md_file, skill_dir, result)

    return result


def validate_all(skills_root: Path) -> dict[str, ValidationResult]:
    """Validate all skill subdirectories under `skills_root`."""
    results: dict[str, ValidationResult] = {}
    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        results[skill_dir.name] = validate_skill(skill_dir)
    return results
