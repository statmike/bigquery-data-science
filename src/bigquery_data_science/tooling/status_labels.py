"""Verify Preview vs GA status label consistency across READMEs, reference docs, and skills."""

from __future__ import annotations

import re
from pathlib import Path

_BACKTICK_SYMBOL_RE = re.compile(r"`([A-Z][A-Z0-9_.]*)`")
_H2_SINGLE_SYMBOL_RE = re.compile(r"^##\s+`([A-Z][A-Z0-9_.]*)`\s*$")
_REF_STATUS_LINE_RE = re.compile(
    r"^\s*-\s+\*\*(?:[^*]*Status[^*]*|Type:?)\*\*[:\s]*(.*)$"
)
_HISTORICAL_PREVIEW_RE = re.compile(r"preview\s+since\s+\d{4}", re.IGNORECASE)


def normalize_status(raw_status: str) -> str:
    """Normalize a status string into `'GA'`, `'Preview'`, `'GA / Preview'`, or `'Retired'`."""
    cleaned = _HISTORICAL_PREVIEW_RE.sub("", raw_status)
    lowered = cleaned.lower()
    if "retired" in lowered or "offline" in lowered:
        return "Retired"
    has_ga = bool(re.search(r"\bga\b", lowered))
    has_preview = "preview" in lowered
    if has_ga and has_preview:
        return "GA / Preview"
    if has_preview:
        return "Preview"
    if has_ga:
        return "GA"
    return raw_status.strip()


def parse_namespace_matrix_statuses(matrix_path: Path) -> dict[str, str]:
    """Return `{symbol: normalized_status}` from `namespace-matrix.md`."""
    statuses: dict[str, str] = {}
    if not matrix_path.is_file():
        return statuses
    for line in matrix_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 6:
            continue
        raw_status = cells[5]
        normalized = normalize_status(raw_status)
        for symbol in _BACKTICK_SYMBOL_RE.findall(cells[0]):
            statuses[symbol] = normalized
    return statuses


def parse_domain_readme_statuses(readme_path: Path) -> dict[str, str]:
    """Extract `{symbol: normalized_status}` from a domain `README.md` file."""
    statuses: dict[str, str] = {}
    if not readme_path.is_file():
        return statuses
    lines = readme_path.read_text(encoding="utf-8").splitlines()
    status_col_idx: int | None = None
    symbol_col_idx: int = 0

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            status_col_idx = None
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(set(c) <= {"-", ":"} and c for c in cells):
            continue
        lower_cells = [c.lower() for c in cells]
        if "status" in lower_cells:
            status_col_idx = lower_cells.index("status")
            if "category" in lower_cells:
                symbol_col_idx = lower_cells.index("category")
            elif "model_type" in lower_cells or "`model_type`" in lower_cells:
                symbol_col_idx = (
                    lower_cells.index("`model_type`")
                    if "`model_type`" in lower_cells
                    else lower_cells.index("model_type")
                )
            else:
                symbol_col_idx = 0
            continue
        if status_col_idx is not None and status_col_idx < len(cells):
            if symbol_col_idx >= len(cells):
                continue
            symbols = _BACKTICK_SYMBOL_RE.findall(cells[symbol_col_idx])
            if not symbols:
                continue
            norm = normalize_status(cells[status_col_idx])
            for sym in symbols:
                if sym == "EXPORT":
                    continue
                statuses[sym] = norm
    return statuses


def parse_reference_h2_statuses(reference_dir: Path) -> dict[str, tuple[str, str]]:
    """Extract `{symbol: (normalized_status, source_label)}` from `reference/*.md`."""
    statuses: dict[str, tuple[str, str]] = {}
    if not reference_dir.is_dir():
        return statuses
    for ref_path in sorted(reference_dir.glob("*.md")):
        current_symbol: str | None = None
        for idx, line in enumerate(
            ref_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            h2_match = _H2_SINGLE_SYMBOL_RE.match(line.strip())
            if h2_match:
                current_symbol = h2_match.group(1)
                continue
            if line.startswith("## "):
                current_symbol = None
                continue
            if current_symbol is None:
                continue
            status_match = _REF_STATUS_LINE_RE.match(line)
            if status_match:
                norm = normalize_status(line)
                if norm in ("GA", "Preview", "GA / Preview", "Retired"):
                    if (
                        current_symbol in statuses
                        and statuses[current_symbol][0] == "Retired"
                    ):
                        continue
                    statuses[current_symbol] = (
                        norm,
                        f"{ref_path.parent.parent.name}/reference/{ref_path.name}:{idx}",
                    )
    return statuses


def check_status_labels(
    repo_root: Path,
    skills_root: Path | None = None,
) -> list[str]:
    """Return status-label inconsistencies across READMEs, `reference/*.md`, and matrix."""
    resolved_skills = (
        skills_root if skills_root is not None else (repo_root / "skills")
    )
    matrix_path = (
        resolved_skills
        / "bigquery-data-science"
        / "reference"
        / "namespace-matrix.md"
    )
    if not matrix_path.is_file():
        return [f"Missing namespace matrix: {matrix_path}"]

    matrix_statuses = parse_namespace_matrix_statuses(matrix_path)
    errors: list[str] = []

    for domain in ("bigquery-ai", "bigquery-ml"):
        readme_path = repo_root / domain / "README.md"
        readme_statuses = parse_domain_readme_statuses(readme_path)
        for symbol, readme_status in sorted(readme_statuses.items()):
            matrix_status = matrix_statuses.get(symbol)
            if matrix_status is None:
                errors.append(
                    f"{domain}/README.md: symbol `{symbol}` missing from "
                    "skills/bigquery-data-science/reference/namespace-matrix.md"
                )
            elif matrix_status != readme_status:
                errors.append(
                    f"`{symbol}` status mismatch: {domain}/README.md has "
                    f"{readme_status!r} vs namespace-matrix.md {matrix_status!r}"
                )

        ref_statuses = parse_reference_h2_statuses(repo_root / domain / "reference")
        for symbol, (ref_status, ref_loc) in sorted(ref_statuses.items()):
            matrix_status = matrix_statuses.get(symbol)
            if matrix_status is not None and matrix_status != ref_status:
                # Allow 'GA / Preview' in matrix when reference notes feature Preview
                if matrix_status == "GA / Preview" and ref_status in ("GA", "Preview"):
                    continue
                errors.append(
                    f"`{symbol}` status mismatch: {ref_loc} has {ref_status!r} "
                    f"vs namespace-matrix.md {matrix_status!r}"
                )

    return errors
