"""Slice domain `reference/*.md` files by H2 heading into `skills/<domain>/syntax/*.md`.

Each H2 section in `<repo_root>/<domain>/reference/*.md` becomes a standalone syntax card
`<skills_root>/<domain>/syntax/<slug>.md` strictly under 25,000 bytes (25 KB) with a
clickable GitHub provenance banner and rewritten links, plus an auto-generated
`<skills_root>/<domain>/syntax/INDEX.md` catalog.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from bigquery_data_science.tooling.markdown_anchors import anchors_of, slugify_heading

MAX_SYNTAX_BYTES = 25_000
MAX_SYNTAX_CARD_BYTES = MAX_SYNTAX_BYTES
GITHUB_BLOB_BASE = "https://github.com/statmike/bigquery-data-science/blob/main"
DOMAIN_SKILLS: tuple[str, ...] = ("bigquery-ml", "bigquery-ai")

_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_H3_RE = re.compile(r"^###\s+(.+?)\s*$")
_LINK_RE = re.compile(r"(!?\[[^\]\n]*\]\()([^)\n]+)(\))")


@dataclasses.dataclass(frozen=True)
class SyntaxCard:
    """Generated syntax card metadata and content."""

    slug: str
    filename: str
    title: str
    source_ref: str
    source_anchor: str
    content: str
    byte_length: int


def card_slug_from_heading(heading_title: str) -> str:
    """Return the normalized single-hyphen filename slug for an H2 heading."""
    raw_slug = slugify_heading(heading_title)
    return re.sub(r"-+", "-", raw_slug).strip("-")


syntax_slug = card_slug_from_heading


def _extract_h1_and_h2_sections(
    markdown_text: str,
) -> tuple[str, list[tuple[str, str]]]:
    """Return `(h1_title, [(h2_title, section_body), ...])` ignoring fenced code."""
    lines = markdown_text.splitlines()
    h1_title = ""
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in lines:
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_fence = False
        if not in_fence:
            if not h1_title:
                h1_match = _H1_RE.match(line)
                if h1_match:
                    h1_title = h1_match.group(1).strip()
                    continue
            h2_match = _H2_RE.match(line)
            if h2_match:
                if current_title is not None:
                    sections.append((current_title, current_lines))
                current_title = h2_match.group(1).strip()
                current_lines = []
                continue
        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections.append((current_title, current_lines))

    return (
        h1_title,
        [(title, "\n".join(body).strip()) for title, body in sections],
    )


def _rewrite_section_links(
    body: str,
    *,
    ref_file: Path,
    repo_root: Path,
    h2_anchor_to_card: dict[str, str],
    local_anchors: set[str],
) -> str:
    """Rewrite relative links inside an H2 section so syntax cards have zero broken links."""
    out_lines: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    def _replace_link(match: re.Match[str]) -> str:
        prefix, raw_target, suffix = (
            match.group(1),
            match.group(2).strip(),
            match.group(3),
        )
        target = raw_target.split()[0]
        if target.startswith(("http://", "https://", "mailto:", "data:")):
            return match.group(0)
        if target.startswith("#"):
            anchor = target[1:]
            if anchor in local_anchors:
                return match.group(0)
            if anchor in h2_anchor_to_card:
                return f"{prefix}{h2_anchor_to_card[anchor]}{suffix}"
            ref_rel = ref_file.relative_to(repo_root).as_posix()
            return f"{prefix}{GITHUB_BLOB_BASE}/{ref_rel}#{anchor}{suffix}"

        if "#" in target:
            path_part, anchor_part = target.split("#", 1)
            anchor_suffix = f"#{anchor_part}"
        else:
            path_part = target
            anchor_suffix = ""

        resolved = (ref_file.parent / path_part).resolve()
        try:
            repo_rel = resolved.relative_to(repo_root.resolve()).as_posix()
            return f"{prefix}{GITHUB_BLOB_BASE}/{repo_rel}{anchor_suffix}{suffix}"
        except ValueError:
            return match.group(0)

    for line in body.splitlines():
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_fence = False
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
        else:
            out_lines.append(_LINK_RE.sub(_replace_link, line))

    return "\n".join(out_lines)


def _local_headings_anchors(body: str, h2_title: str) -> set[str]:
    """Collect heading anchors defined inside a single H2 card."""
    temp_lines = [f"# {h2_title}", *body.splitlines()]
    in_fence = False
    fence_char = ""
    fence_len = 0
    found: set[str] = set()
    for line in temp_lines:
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_fence = False
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m:
            found.add(slugify_heading(m.group(2)))
    return found


def build_syntax_cards_for_domain(
    repo_root: Path,
    domain: str,
) -> tuple[list[tuple[str, str, list[SyntaxCard]]], dict[str, str]]:
    """Build all syntax cards and `INDEX.md` content for `domain` (`bigquery-ml` or `bigquery-ai`).

    Returns `(grouped_cards, file_map)` where `file_map` maps `filename -> content`
    including `INDEX.md`.
    """
    repo_root = repo_root.resolve()
    ref_dir = repo_root / domain / "reference"
    if not ref_dir.is_dir():
        return [], {}

    ref_files = sorted(ref_dir.glob("*.md"))
    h2_anchor_to_card: dict[str, str] = {}
    parsed_refs: list[tuple[Path, str, list[tuple[str, str]]]] = []

    for ref_file in ref_files:
        text = ref_file.read_text(encoding="utf-8")
        h1_title, sections = _extract_h1_and_h2_sections(text)
        parsed_refs.append((ref_file, h1_title or ref_file.stem, sections))
        for h2_title, _ in sections:
            anchor = slugify_heading(h2_title)
            card_filename = f"{card_slug_from_heading(h2_title)}.md"
            h2_anchor_to_card[anchor] = card_filename

    grouped_cards: list[tuple[str, str, list[SyntaxCard]]] = []
    file_map: dict[str, str] = {}

    for ref_file, h1_title, sections in parsed_refs:
        ref_rel = ref_file.relative_to(repo_root).as_posix()
        valid_ref_anchors = anchors_of(ref_file)
        cards_for_ref: list[SyntaxCard] = []

        for h2_title, raw_body in sections:
            anchor = slugify_heading(h2_title)
            if anchor not in valid_ref_anchors:
                # Fallback if duplicate heading received suffix
                anchor = next(
                    (a for a in valid_ref_anchors if a.startswith(anchor)),
                    anchor,
                )
            slug = card_slug_from_heading(h2_title)
            filename = f"{slug}.md"
            local_anchors = _local_headings_anchors(raw_body, h2_title)
            rewritten_body = _rewrite_section_links(
                raw_body,
                ref_file=ref_file,
                repo_root=repo_root,
                h2_anchor_to_card=h2_anchor_to_card,
                local_anchors=local_anchors,
            )
            provenance = (
                f"> **Source:** [`{ref_rel}#{anchor}`]"
                f"({GITHUB_BLOB_BASE}/{ref_rel}#{anchor})"
            )
            card_content = (
                f"# {h2_title}\n\n{provenance}\n\n{rewritten_body}\n"
                if rewritten_body
                else f"# {h2_title}\n\n{provenance}\n"
            )
            encoded = card_content.encode("utf-8")
            if len(encoded) >= MAX_SYNTAX_BYTES:
                raise ValueError(
                    f"Syntax card {domain}/syntax/{filename} is {len(encoded):,} bytes "
                    f"(>= {MAX_SYNTAX_BYTES:,} byte limit)."
                )
            card = SyntaxCard(
                slug=slug,
                filename=filename,
                title=h2_title,
                source_ref=ref_rel,
                source_anchor=anchor,
                content=card_content,
                byte_length=len(encoded),
            )
            cards_for_ref.append(card)
            file_map[filename] = card_content

        grouped_cards.append((ref_file.name, h1_title, cards_for_ref))

    # Build INDEX.md
    index_lines: list[str] = [
        f"# `{domain}` Syntax Cards Index (Lens 3)",
        "",
        (
            f"Focused, per-statement syntax and option cards sliced from "
            f"[`{domain}/reference/`]({GITHUB_BLOB_BASE}/{domain}/reference). "
            "Every card is strictly under 25 KB."
        ),
        "",
    ]
    for ref_filename, h1_title, cards in grouped_cards:
        index_lines.append(f"## {h1_title} (`{ref_filename}`)")
        index_lines.append("")
        for card in cards:
            index_lines.append(f"- [{card.title}]({card.filename})")
        index_lines.append("")

    index_content = "\n".join(index_lines).rstrip() + "\n"
    file_map["INDEX.md"] = index_content
    return grouped_cards, file_map


def sync_skill_syntax(
    skill_dir: Path,
    repo_root: Path,
    *,
    domain: str | None = None,
) -> list[Path]:
    """Generate and write `syntax/*.md` and `syntax/INDEX.md` inside `skill_dir`."""
    target_domain = domain or skill_dir.name
    if target_domain not in DOMAIN_SKILLS:
        return []
    _, file_map = build_syntax_cards_for_domain(repo_root, target_domain)
    if not file_map:
        return []

    syntax_dir = skill_dir / "syntax"
    syntax_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale .md files not in file_map
    for existing in syntax_dir.glob("*.md"):
        if existing.name not in file_map:
            existing.unlink()

    written: list[Path] = []
    for filename, content in sorted(file_map.items()):
        out_path = syntax_dir / filename
        out_path.write_text(content, encoding="utf-8")
        written.append(out_path)
    return written


def sync_all_syntax(
    skills_root: Path,
    repo_root: Path,
    *,
    skill_name: str | None = None,
) -> dict[str, list[Path]]:
    """Synchronize syntax cards across all domain skills in `skills_root`."""
    skills_root = skills_root.resolve()
    repo_root = repo_root.resolve()
    results: dict[str, list[Path]] = {}

    if (skills_root / "SKILL.md").is_file():
        skill_dirs = [skills_root]
    else:
        skill_dirs = [
            skills_root / name
            for name in DOMAIN_SKILLS
            if (skills_root / name).is_dir()
            and (skill_name is None or name == skill_name)
        ]

    for sdir in skill_dirs:
        written = sync_skill_syntax(sdir, repo_root)
        if written:
            results[sdir.name] = written
    return results


def check_syntax_sync(
    skills_root: Path,
    repo_root: Path,
    *,
    skill_name: str | None = None,
) -> list[str]:
    """Verify that on-disk `syntax/*.md` files match `<domain>/reference/*.md` with zero drift."""
    skills_root = skills_root.resolve()
    repo_root = repo_root.resolve()
    errors: list[str] = []

    if (skills_root / "SKILL.md").is_file():
        skill_dirs = [skills_root]
    else:
        skill_dirs = [
            skills_root / name
            for name in DOMAIN_SKILLS
            if (skills_root / name).is_dir()
            and (skill_name is None or name == skill_name)
        ]

    for sdir in skill_dirs:
        domain = sdir.name
        if domain not in DOMAIN_SKILLS:
            continue
        try:
            _, expected_map = build_syntax_cards_for_domain(repo_root, domain)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        syntax_dir = sdir / "syntax"
        if not syntax_dir.is_dir():
            errors.append(f"{domain}: missing syntax/ directory at {syntax_dir}")
            continue

        actual_files = {p.name: p for p in syntax_dir.glob("*.md")}
        for expected_name, expected_content in sorted(expected_map.items()):
            if expected_name not in actual_files:
                errors.append(f"{domain}/syntax/{expected_name}: missing syntax card")
                continue
            actual_content = actual_files[expected_name].read_text(encoding="utf-8")
            if actual_content != expected_content:
                errors.append(
                    f"{domain}/syntax/{expected_name}: content drifted from {domain}/reference/"
                )

        for actual_name in sorted(actual_files):
            if actual_name not in expected_map:
                errors.append(
                    f"{domain}/syntax/{actual_name}: orphan syntax file not in {domain}/reference/"
                )

    return errors
