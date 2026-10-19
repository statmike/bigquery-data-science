"""Resolve markdown heading anchors the way GitHub does.

Shared by the anchor check in `link_policy`, the index check in
`reference_structure`, and the H2 slicer in `sync_syntax`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_INLINE_HTML_RE = re.compile(r"<[^>]*>")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]\n]*)\]\([^)\n]*\)")


def slugify(title: str) -> str:
    """Compute GitHub's heading-anchor slug for a heading title."""
    text = title.strip().lower()
    text = _INLINE_HTML_RE.sub("", text)
    text = text.replace("`", "")
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


slugify_heading = slugify


def headings(text: str) -> list[tuple[int, str]]:
    """Return `[(level, title)]` for every ATX heading outside a code fence."""
    found: list[tuple[int, str]] = []
    in_fence = False
    marker: str | None = None
    for line in text.split("\n"):
        fence = _FENCE_RE.match(line)
        if fence:
            token = fence.group(1)[0] * 3
            if not in_fence:
                in_fence, marker = True, token
            elif token == marker:
                in_fence, marker = False, None
            continue
        if in_fence:
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            found.append((len(heading.group(1)), heading.group(2)))
    return found


def markdown_sources(path: Path) -> list[str]:
    """Return markdown text segments of a file or notebook markdown cells."""
    if path.suffix != ".ipynb":
        return [path.read_text(encoding="utf-8", errors="replace")]
    try:
        notebook = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return []
    return [
        "".join(cell.get("source", []))
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "markdown"
    ]


def anchors_of(path: Path) -> set[str]:
    """Return every heading anchor a reader can link to in `path`.

    Repeated headings are suffixed in document order (`-1`, `-2`, `-3`),
    matching GitHub's renderer across `bigquery-ai/setup/README.md` and
    multi-cell notebooks.
    """
    seen: dict[str, int] = {}
    anchors: set[str] = set()
    for text in markdown_sources(path):
        for _, title in headings(text):
            base = slugify(title)
            count = seen.get(base, 0)
            anchors.add(base if count == 0 else f"{base}-{count}")
            seen[base] = count + 1
    return anchors
