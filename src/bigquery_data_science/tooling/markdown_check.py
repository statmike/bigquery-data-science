"""Verify Markdown code fences, GFM table compilation, and vertical-first Mermaid layout."""

from __future__ import annotations

import json
import re
from pathlib import Path

MAX_MERMAID_HORIZONTAL_FANOUT = 3

_FENCE_OPEN_RE = re.compile(r"^(`{3,}|~{3,})(.*)$")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")
_MERMAID_EDGE_RE = re.compile(
    r"^\s*([A-Za-z0-9_]+)(?:\[[^\]]*\])?\s*(?:-->|---|-\.->|==>)\s*([A-Za-z0-9_]+)"
)
_UNQUOTED_PAREN_LABEL_RE = re.compile(r'\b[A-Za-z0-9_]+\[(?!")[^\]]*\([^\]]*\]')


def _check_mermaid_block(
    mermaid_lines: list[str],
    label: str,
    start_line: int,
) -> list[str]:
    """Validate a single `mermaid` fenced block for syntax and vertical-first layout."""
    issues: list[str] = []
    non_empty = [
        (offset, line.strip())
        for offset, line in enumerate(mermaid_lines)
        if line.strip() and not line.strip().startswith("%%")
    ]
    if not non_empty:
        issues.append(f"{label}:{start_line}: empty mermaid block")
        return issues

    first_offset, header = non_empty[0]
    if header.startswith(("flowchart LR", "graph LR")):
        issues.append(
            f"{label}:{start_line + first_offset}: top-level '{header}' shrinks font width; "
            "use vertical 'flowchart TD' instead"
        )

    subgraph_depth = 0
    fanout_targets: dict[str, set[str]] = {}

    for offset, raw_line in enumerate(mermaid_lines):
        stripped = raw_line.strip()
        line_no = start_line + offset
        if not stripped or stripped.startswith("%%"):
            continue
        if stripped.startswith("subgraph "):
            subgraph_depth += 1
        elif stripped == "end":
            subgraph_depth -= 1
            if subgraph_depth < 0:
                issues.append(
                    f"{label}:{line_no}: unmatched 'end' in mermaid block"
                )
        if _UNQUOTED_PAREN_LABEL_RE.search(stripped):
            issues.append(
                f"{label}:{line_no}: unquoted parentheses in Mermaid node label "
                "(wrap label in double quotes: id[\"Label (Detail)\"])"
            )
        edge_match = _MERMAID_EDGE_RE.match(stripped)
        if edge_match and "-->" in stripped and stripped.count("-->") == 1:
            src_node, dst_node = edge_match.group(1), edge_match.group(2)
            fanout_targets.setdefault(src_node, set()).add(dst_node)

    if subgraph_depth != 0:
        issues.append(
            f"{label}:{start_line}: unbalanced 'subgraph ... end' in mermaid block "
            f"(depth={subgraph_depth})"
        )

    for src_node, targets in sorted(fanout_targets.items()):
        if len(targets) > MAX_MERMAID_HORIZONTAL_FANOUT:
            issues.append(
                f"{label}:{start_line}: Mermaid node '{src_node}' fans out to "
                f"{len(targets)} parallel nodes ({sorted(targets)}), exceeding max "
                f"horizontal width of {MAX_MERMAID_HORIZONTAL_FANOUT}"
            )

    return issues


def check_markdown_text(text: str, label: str) -> list[str]:
    """Check `text` for unbalanced code fences, invalid GFM tables, and wide/broken Mermaid."""
    issues: list[str] = []
    lines = text.splitlines()
    in_fence = False
    fence_char = ""
    fence_len = 0
    fence_lang = ""
    fence_start_line = 0
    fence_lines: list[str] = []

    table_expected_cols: int | None = None
    table_start_line = 0

    for idx, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        fence_match = _FENCE_OPEN_RE.match(stripped)
        if fence_match:
            marker = fence_match.group(1)
            rest = fence_match.group(2).strip()
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
                fence_lang = rest.split()[0].lower() if rest else ""
                fence_start_line = idx
                fence_lines = []
                table_expected_cols = None
                continue
            if (
                marker[0] == fence_char
                and len(marker) >= fence_len
                and not rest
            ):
                if fence_lang == "mermaid":
                    issues.extend(
                        _check_mermaid_block(
                            fence_lines,
                            label,
                            fence_start_line + 1,
                        )
                    )
                in_fence = False
                fence_char = ""
                fence_len = 0
                fence_lang = ""
                fence_lines = []
                continue

        if in_fence:
            fence_lines.append(line)
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            for code_match in _INLINE_CODE_RE.finditer(stripped):
                code_span = code_match.group(1)
                if _UNESCAPED_PIPE_RE.search(code_span):
                    issues.append(
                        f"{label}:{idx}: unescaped '|' inside inline code `{code_span}` "
                        "in GFM table row"
                    )
            cleaned = _INLINE_CODE_RE.sub("CODE", stripped).replace(r"\|", "ESC")
            cols = len(cleaned.strip("|").split("|"))
            if table_expected_cols is None:
                table_expected_cols = cols
                table_start_line = idx
            elif cols != table_expected_cols:
                issues.append(
                    f"{label}:{idx}: GFM table row has {cols} columns, "
                    f"expected {table_expected_cols} (table started at line {table_start_line})"
                )
        else:
            table_expected_cols = None

    if in_fence:
        issues.append(
            f"{label}:{fence_start_line}: unclosed code fence "
            f"('{fence_char * fence_len}{fence_lang}')"
        )

    return issues


def check_markdown_files(repo_root: Path) -> list[str]:
    """Scan all tracked/domain `.md` files and `.ipynb` markdown cells under `repo_root`."""
    resolved_root = repo_root.resolve()
    issues: list[str] = []

    for md_path in sorted(resolved_root.rglob("*.md")):
        if any(
            part in md_path.parts
            for part in (".venv", ".git", ".agents", ".claude", "node_modules")
        ):
            continue
        rel = str(md_path.relative_to(resolved_root))
        issues.extend(
            check_markdown_text(md_path.read_text(encoding="utf-8"), rel)
        )

    for nb_path in sorted(resolved_root.rglob("*.ipynb")):
        if any(
            part in nb_path.parts
            for part in (".venv", ".git", "node_modules")
        ):
            continue
        rel_nb = str(nb_path.relative_to(resolved_root))
        try:
            nb_data = json.loads(nb_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(f"{rel_nb}: invalid notebook JSON ({exc})")
            continue
        if not isinstance(nb_data, dict):
            continue
        cells = nb_data.get("cells", [])
        if not isinstance(cells, list):
            continue
        for cell_idx, cell in enumerate(cells):
            if not isinstance(cell, dict) or cell.get("cell_type") != "markdown":
                continue
            raw_source = cell.get("source", [])
            source = (
                "".join(str(s) for s in raw_source)
                if isinstance(raw_source, list)
                else str(raw_source)
            )
            issues.extend(check_markdown_text(source, f"{rel_nb}#cell-{cell_idx}"))

    return issues
