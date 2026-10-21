"""Audit high-precision numeric claims in notebook markdown cells against cell outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path

_HIGH_PRECISION_FLOAT_RE = re.compile(
    r"(?<![A-Za-z0-9_~≈.-])\d+\.\d{5,}(?![A-Za-z0-9_.-])"
)
_FORMULA_FRACTION_RE = re.compile(r"\b\d+\s*/\s*\d+|\b1\s*-\s*\(")
_RRF_DERIVATION_RE = re.compile(r"1/\(6[01]\s*\+")
_MIN_PREFIX_MATCH_LEN = 7


def _collect_notebook_code_and_outputs(notebook_data: dict[str, object]) -> str:
    """Return a concatenated string of all code cell sources and rendered outputs."""
    chunks: list[str] = []
    cells = notebook_data.get("cells", [])
    if not isinstance(cells, list):
        return ""
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            chunks.append("".join(str(s) for s in source))
        elif isinstance(source, str):
            chunks.append(source)

        outputs = cell.get("outputs", [])
        if not isinstance(outputs, list):
            continue
        for out in outputs:
            if not isinstance(out, dict):
                continue
            text = out.get("text")
            if isinstance(text, list):
                chunks.append("".join(str(t) for t in text))
            elif isinstance(text, str):
                chunks.append(text)
            data = out.get("data")
            if isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, list):
                        chunks.append("".join(str(v) for v in val))
                    elif isinstance(val, str):
                        chunks.append(val)
    return "\n".join(chunks)


def check_single_notebook_claims(
    notebook_path: Path,
    repo_root: Path | None = None,
) -> list[str]:
    """Return unbacked high-precision decimal claims found in `notebook_path` markdown cells."""
    try:
        data = json.loads(notebook_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{notebook_path}: failed to read JSON ({exc})"]

    if not isinstance(data, dict):
        return []

    corpus = _collect_notebook_code_and_outputs(data)
    cells = data.get("cells", [])
    if not isinstance(cells, list):
        return []

    label = (
        str(notebook_path.relative_to(repo_root))
        if repo_root is not None and notebook_path.is_relative_to(repo_root)
        else str(notebook_path)
    )
    unbacked: list[str] = []

    for cell_idx, cell in enumerate(cells):
        if not isinstance(cell, dict) or cell.get("cell_type") != "markdown":
            continue
        raw_source = cell.get("source", [])
        source = (
            "".join(str(s) for s in raw_source)
            if isinstance(raw_source, list)
            else str(raw_source)
        )
        if _RRF_DERIVATION_RE.search(source):
            continue
        for line in source.splitlines():
            if _FORMULA_FRACTION_RE.search(line):
                continue
            for match in _HIGH_PRECISION_FLOAT_RE.finditer(line):
                num_str = match.group(0)
                prefix = num_str[:_MIN_PREFIX_MATCH_LEN]
                if prefix not in corpus and num_str not in corpus:
                    unbacked.append(
                        f"{label}#cell-{cell_idx}: prose claim '{num_str}' "
                        "not found in code or cell outputs"
                    )
    return unbacked


def check_notebook_claims(
    target: Path,
    repo_root: Path | None = None,
) -> list[str]:
    """Check a single notebook or all `.ipynb` files under `target` for unbacked prose claims."""
    resolved_target = target.resolve()
    resolved_root = repo_root.resolve() if repo_root is not None else None
    if resolved_target.is_file():
        return check_single_notebook_claims(resolved_target, resolved_root)

    notebooks: list[Path] = []
    if (resolved_target / "bigquery-ml").is_dir() or (
        resolved_target / "bigquery-ai"
    ).is_dir():
        for domain in ("bigquery-ml", "bigquery-ai"):
            domain_dir = resolved_target / domain
            if domain_dir.is_dir():
                notebooks.extend(sorted(domain_dir.rglob("*.ipynb")))
    else:
        notebooks = [
            p
            for p in sorted(resolved_target.rglob("*.ipynb"))
            if ".venv" not in p.parts
        ]

    errors: list[str] = []
    for nb_path in notebooks:
        errors.extend(
            check_single_notebook_claims(
                nb_path,
                resolved_root or resolved_target,
            )
        )
    return errors
