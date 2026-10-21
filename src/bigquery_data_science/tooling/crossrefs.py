"""Verify bidirectional `Functions/Models used` <-> `Featured in` links across notebooks."""

from __future__ import annotations

import json
import re
from pathlib import Path

_REL_TOPIC_LINK_RE = re.compile(
    r"\(\.\./\.\./((?:functions|models|workflows)/[a-z0-9_]+)"
)
_BACKTICK_SYMBOL_RE = re.compile(r"`([A-Z][A-Z0-9_.*]*)`")
_WORKFLOW_USES_KEYS: tuple[str, ...] = (
    "**Functions used:**",
    "**Models used:**",
    "**Models / Functions used:**",
    "**Used in this workflow:**",
)


def _read_intro_markdown_lines(notebook_path: Path, max_cells: int = 3) -> list[str]:
    """Return all markdown lines from the first `max_cells` non-header markdown cells."""
    try:
        data = json.loads(notebook_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    lines: list[str] = []
    seen = 0
    for cell in data.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        source = "".join(cell.get("source", []))
        if "<!--- header table --->" in source:
            continue
        lines.extend(source.splitlines())
        seen += 1
        if seen >= max_cells:
            break
    return lines


def check_domain_crossrefs(domain_root: Path) -> list[str]:
    """Verify two-way cross-references between `workflows/*` and `{functions,models}/*`."""
    errors: list[str] = []
    workflows_dir = domain_root / "workflows"
    if not workflows_dir.is_dir():
        return errors

    workflow_links: dict[str, set[str]] = {}
    workflow_symbols: dict[str, set[str]] = {}

    for wf_nb in sorted(workflows_dir.glob("*/*.ipynb")):
        wf_key = f"workflows/{wf_nb.parent.name}"
        links: set[str] = set()
        symbols: set[str] = set()
        for line in _read_intro_markdown_lines(wf_nb):
            if any(marker in line for marker in _WORKFLOW_USES_KEYS):
                links.update(_REL_TOPIC_LINK_RE.findall(line))
                symbols.update(_BACKTICK_SYMBOL_RE.findall(line))
        workflow_links[wf_key] = links
        workflow_symbols[wf_key] = symbols

    featured_in_links: dict[str, set[str]] = {}
    topic_symbols: dict[str, set[str]] = {}

    for sub in ("functions", "models"):
        sub_dir = domain_root / sub
        if not sub_dir.is_dir():
            continue
        for topic_nb in sorted(sub_dir.glob("*/*.ipynb")):
            topic_key = f"{sub}/{topic_nb.parent.name}"
            intro_lines = _read_intro_markdown_lines(topic_nb)
            f_links: set[str] = set()
            t_syms: set[str] = set()
            for line in intro_lines:
                t_syms.update(_BACKTICK_SYMBOL_RE.findall(line))
                if "**Featured in:**" in line:
                    f_links.update(_REL_TOPIC_LINK_RE.findall(line))
            featured_in_links[topic_key] = f_links
            topic_symbols[topic_key] = t_syms

    # 1. Every explicit link from a workflow to a function/model must have a Featured-in back-link
    for wf_key, targets in sorted(workflow_links.items()):
        for target_key in sorted(targets):
            if not target_key.startswith(("functions/", "models/")):
                continue
            back_links = featured_in_links.get(target_key)
            if back_links is None:
                errors.append(
                    f"{domain_root.name}/{wf_key}: links to missing topic '{target_key}'"
                )
            elif wf_key not in back_links:
                errors.append(
                    f"{domain_root.name}/{wf_key} -> {target_key}: missing back-link "
                    f"to '{wf_key}' in {target_key} '**Featured in:**'"
                )

    # 2. Every Featured-in link from a function/model to a workflow or model must be valid
    for topic_key, wfs in sorted(featured_in_links.items()):
        for wf_key in sorted(wfs):
            if wf_key.startswith("models/"):
                if wf_key not in featured_in_links:
                    errors.append(
                        f"{domain_root.name}/{topic_key}: '**Featured in:**' references "
                        f"missing model '{wf_key}'"
                    )
                continue
            if wf_key not in workflow_links:
                errors.append(
                    f"{domain_root.name}/{topic_key}: '**Featured in:**' references "
                    f"missing workflow '{wf_key}'"
                )
                continue
            has_direct_link = topic_key in workflow_links[wf_key]
            has_symbol_match = bool(
                topic_symbols.get(topic_key, set())
                & workflow_symbols.get(wf_key, set())
            )
            if not (has_direct_link or has_symbol_match):
                errors.append(
                    f"{domain_root.name}/{topic_key} -> {wf_key}: workflow '{wf_key}' "
                    f"does not list '{topic_key}' in '**Functions/Models used:**'"
                )

    return errors


def check_crossrefs(repo_root: Path) -> list[str]:
    """Run `check_domain_crossrefs` across `bigquery-ai` and `bigquery-ml`."""
    errors: list[str] = []
    for domain in ("bigquery-ai", "bigquery-ml"):
        domain_root = repo_root / domain
        if domain_root.is_dir():
            errors.extend(check_domain_crossrefs(domain_root))
    return errors
