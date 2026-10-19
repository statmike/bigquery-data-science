"""Convert a project notebook into a lean, agent-readable narrative markdown file.

Strips only cells that are provably generic execution ceremony (the tracker/badge
header, the shared `install()` helper, the Colab-only auth shim) and the trailing
Cleanup section, and prepends a clickable GitHub provenance banner to the source
`.ipynb` and companion `.sql` script.
"""

from __future__ import annotations

import re
import types
from pathlib import Path
from typing import Any

GITHUB_BLOB_BASE = "https://github.com/statmike/bigquery-data-science/blob/main"

MAGIC_LANG_MAP: types.MappingProxyType[str, str] = types.MappingProxyType(
    {
        "%%bigquery": "sql",
        "%%bash": "bash",
        "%%sh": "bash",
        "%%writefile": "python",
    }
)

_HEADER_TABLE_MARKERS: tuple[str, ...] = ("tracker", "header table")
_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((?!https?://)([^)\n]+)\)")


def _is_header_table(cell: Any) -> bool:
    """Return True when `cell` is the repository tracker/badge header cell."""
    if getattr(cell, "cell_type", None) != "markdown":
        return False
    source_lower = str(getattr(cell, "source", "")).lower()
    return all(marker in source_lower for marker in _HEADER_TABLE_MARKERS)


def _is_generic_install_helper(cell: Any) -> bool:
    """Return True when `cell` defines the generic `def install(` shim."""
    return (
        getattr(cell, "cell_type", None) == "code"
        and "def install(" in str(getattr(cell, "source", ""))
    )


def _is_generic_colab_auth(cell: Any) -> bool:
    """Return True when `cell` is the Colab `auth.authenticate_user()` shim."""
    source = str(getattr(cell, "source", ""))
    return (
        getattr(cell, "cell_type", None) == "code"
        and "from google.colab import auth" in source
        and "authenticate_user" in source
    )


def _is_inline_cleanup_cell(cell: Any) -> bool:
    """Return True when `cell` is a standalone resource-cleanup code cell."""
    if getattr(cell, "cell_type", None) != "code":
        return False
    source = str(getattr(cell, "source", "")).lstrip()
    return bool(re.match(r"^#+\s*clean\s*up\b", source, re.IGNORECASE))


def _is_cleanup_start(cell: Any) -> bool:
    """Return True when `cell` opens the trailing Cleanup section."""
    if getattr(cell, "cell_type", None) != "markdown":
        return False
    source = str(getattr(cell, "source", "")).strip()
    return bool(re.search(r"^#+\s*clean\s*up\b", source, re.IGNORECASE | re.MULTILINE))


def _detect_lang(source: str) -> str:
    """Infer the code fence language from cell magics."""
    stripped = source.lstrip()
    for magic, language in MAGIC_LANG_MAP.items():
        if stripped.startswith(magic):
            return language
    return "python"


def _resolve_relative_path(notebook_dir: str, relative_path: str) -> str:
    """Resolve a link relative to the notebook's directory."""
    combined = f"{notebook_dir}/{relative_path}" if notebook_dir else relative_path
    parts: list[str] = []
    for part in combined.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    return "/".join(parts)


def _fix_links(markdown_text: str, notebook_dir: str) -> str:
    """Rewrite non-HTTP relative links as code-formatted repo references."""

    def replace_match(match: re.Match[str]) -> str:
        text, target = match.group(1), match.group(2)
        if target.startswith("#"):
            return match.group(0)
        resolved = _resolve_relative_path(notebook_dir, target)
        return f"`{resolved}` ({text})"

    return _LINK_RE.sub(replace_match, markdown_text)


def _build_provenance_banner(notebook_path: Path, subproject_root: Path) -> str:
    """Build the clickable GitHub provenance blockquote for a narrative file."""
    project_name = subproject_root.name
    relative_notebook = notebook_path.relative_to(subproject_root).as_posix()
    repo_notebook = (
        f"{project_name}/{relative_notebook}"
        if project_name
        else relative_notebook
    )
    parts = [
        f"**Notebook:** [`{repo_notebook}`]({GITHUB_BLOB_BASE}/{repo_notebook})"
    ]
    sql_path = notebook_path.with_suffix(".sql")
    if sql_path.exists():
        relative_sql = sql_path.relative_to(subproject_root).as_posix()
        repo_sql = (
            f"{project_name}/{relative_sql}" if project_name else relative_sql
        )
        parts.append(f"**SQL:** [`{repo_sql}`]({GITHUB_BLOB_BASE}/{repo_sql})")
    return "> **Source (`statmike/bigquery-data-science`):** " + " · ".join(parts)


def convert_notebook(notebook_path: Path, subproject_root: Path) -> str:
    """Return the extracted narrative markdown for one notebook."""
    import nbformat

    nb_module: Any = nbformat
    notebook_path = notebook_path.resolve()
    subproject_root = subproject_root.resolve()
    notebook_dir = str(notebook_path.parent.relative_to(subproject_root))
    if notebook_dir == ".":
        notebook_dir = ""

    notebook = nb_module.read(notebook_path, as_version=4)

    blocks: list[str] = [_build_provenance_banner(notebook_path, subproject_root)]
    for cell in notebook.cells:
        if (
            _is_header_table(cell)
            or _is_generic_install_helper(cell)
            or _is_generic_colab_auth(cell)
            or _is_inline_cleanup_cell(cell)
        ):
            continue
        if _is_cleanup_start(cell):
            break
        if cell.cell_type == "markdown":
            blocks.append(_fix_links(cell.source.rstrip(), notebook_dir))
        elif cell.cell_type == "code":
            source = cell.source.rstrip()
            if not source:
                continue
            language = _detect_lang(source)
            blocks.append(f"```{language}\n{source}\n```")

    return "\n\n".join(blocks)


def convert_notebook_to_file(
    notebook_path: Path,
    subproject_root: Path,
    output_path: Path,
) -> None:
    """Convert `notebook_path` and write the narrative markdown to `output_path`."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        convert_notebook(notebook_path, subproject_root) + "\n",
        encoding="utf-8",
    )
