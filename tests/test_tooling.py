"""Offline unit and failure-case tests for maintainer verification tooling."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from bigquery_data_science.cli import main
from bigquery_data_science.tooling.bump_version import (
    bump_version,
    check_version_lockstep,
    validate_semver,
)
from bigquery_data_science.tooling.convert_notebook import convert_notebook
from bigquery_data_science.tooling.link_policy import check_project
from bigquery_data_science.tooling.manifest import (
    build_manifest,
    check_all_manifests,
    source_projects,
    write_manifest,
)
from bigquery_data_science.tooling.markdown_anchors import (
    anchors_of,
    headings,
    slugify,
)
from bigquery_data_science.tooling.narrative_drift import (
    check_all_narratives,
    check_skill_narratives,
)
from bigquery_data_science.tooling.pinned_models import (
    check_pinned_models,
    find_allow_file,
    is_placeholder,
    load_allow_list,
)
from bigquery_data_science.tooling.reference_structure import check_reference
from bigquery_data_science.tooling.sync_syntax import (
    MAX_SYNTAX_CARD_BYTES,
    check_syntax_sync,
)
from bigquery_data_science.tooling.validate import validate_all, validate_skill

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"


def test_markdown_anchors_slugify_and_fenced_headings(tmp_path: Path) -> None:
    assert slugify("ML.EVALUATE") == "mlevaluate"
    assert (
        slugify("1. `model_type` Catalog")
        == "1-model_type-catalog"
    )
    sample = tmp_path / "sample.md"
    sample.write_text(
        "# Title\n\n```sql\n# Not a heading\n```\n\n## Section\n\n## Section\n",
        encoding="utf-8",
    )
    assert headings(sample.read_text(encoding="utf-8")) == [
        (1, "Title"),
        (2, "Section"),
        (2, "Section"),
    ]
    assert anchors_of(sample) == {"title", "section", "section-1"}


def test_validate_all_passes_on_repository_skills() -> None:
    results = validate_all(SKILLS_ROOT)
    assert set(results) == {
        "bigquery-data-science",
        "bigquery-ml",
        "bigquery-ai",
    }
    for name, res in results.items():
        assert res.ok, f"Skill {name} failed validation: {res.errors}"
        assert not res.warnings, (
            f"Skill {name} emitted warnings: {res.warnings}"
        )


def test_validate_skill_rejects_missing_frontmatter_and_broken_link(
    tmp_path: Path,
) -> None:
    bad_skill = tmp_path / "broken-skill"
    bad_skill.mkdir()
    (bad_skill / "SKILL.md").write_text(
        "# No Frontmatter\n\nBroken [link](missing.md).\n",
        encoding="utf-8",
    )
    res = validate_skill(bad_skill)
    assert not res.ok
    assert any("frontmatter" in err for err in res.errors)
    assert any("broken link" in err for err in res.errors)


def test_validate_skill_anchor_link_and_frontmatter_and_budget_rules(
    tmp_path: Path,
) -> None:
    skill_dir = tmp_path / "Invalid_Claude_Skill"
    (skill_dir / "reference").mkdir(parents=True)
    long_name = "Invalid_Claude_" + ("a" * 60)
    body_lines = "\n".join(f"Line {i}" for i in range(510))
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {long_name}\ndescription: >-\n  Multiline description text.\n---\n"
        f"# Title\n\nBroken [anchored link](missing-doc.md#section-1).\n{body_lines}\n",
        encoding="utf-8",
    )
    ref_lines = "\n".join(f"Ref line {i}" for i in range(110))
    (skill_dir / "reference" / "guide.md").write_text(
        f"# Guide Without TOC\n\n{ref_lines}\n",
        encoding="utf-8",
    )
    res = validate_skill(skill_dir)
    assert not res.ok
    assert any("exceeds 64 chars" in err for err in res.errors)
    assert any("lowercase letters/digits/hyphens" in err for err in res.errors)
    assert any("claude" in err for err in res.errors)
    assert any("missing-doc.md#section-1" in err for err in res.errors)
    assert len(res.warnings) == 2


def test_validate_skill_rejects_oversized_syntax_card(tmp_path: Path) -> None:
    skill_dir = tmp_path / "oversized-skill"
    (skill_dir / "syntax").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: oversized-skill\ndescription: Valid description.\n---\n# Title\n",
        encoding="utf-8",
    )
    (skill_dir / "syntax" / "huge.md").write_text(
        "# Huge\n\n" + ("x" * (MAX_SYNTAX_CARD_BYTES + 500)),
        encoding="utf-8",
    )
    res = validate_skill(skill_dir)
    assert not res.ok
    assert any("exceeds" in err for err in res.errors)


def test_check_syntax_sync_passes_and_detects_drift_and_orphans(
    tmp_path: Path,
) -> None:
    from bigquery_data_science.tooling.sync_syntax import (
        build_syntax_cards_for_domain,
        sync_skill_syntax,
    )

    assert check_syntax_sync(SKILLS_ROOT, REPO_ROOT) == []

    tmp_skills = tmp_path / "skills"
    shutil.copytree(SKILLS_ROOT, tmp_skills)
    target = tmp_skills / "bigquery-ai" / "syntax" / "aigenerate.md"
    target.write_text("# Drifted\n\nModified content.\n", encoding="utf-8")
    orphan = tmp_skills / "bigquery-ai" / "syntax" / "orphan-card.md"
    orphan.write_text("# Orphan\n", encoding="utf-8")
    errors = check_syntax_sync(tmp_skills, REPO_ROOT)
    assert any("aigenerate.md" in err for err in errors)
    assert any("orphan-card.md" in err for err in errors)

    # Resyncing removes the orphan card and restores aigenerate.md
    sync_skill_syntax(tmp_skills / "bigquery-ai", REPO_ROOT)
    assert not orphan.exists()
    assert check_syntax_sync(tmp_skills, REPO_ROOT) == []

    # Oversized H2 section raises ValueError during card slicing
    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "bigquery-ai" / "reference").mkdir(parents=True)
    (fake_repo / "bigquery-ai" / "reference" / "big.md").write_text(
        "# Big Ref\n\n## Huge Section\n\n" + ("y" * (MAX_SYNTAX_CARD_BYTES + 500)),
        encoding="utf-8",
    )
    try:
        build_syntax_cards_for_domain(fake_repo, "bigquery-ai")
        raise AssertionError("Expected ValueError on >= 25 KB H2 section")
    except ValueError as exc:
        assert "byte limit" in str(exc)


def test_convert_notebook_and_narrative_drift_detection(tmp_path: Path) -> None:
    results = check_all_narratives(SKILLS_ROOT, REPO_ROOT)
    assert results["bigquery-ml"].ok and results["bigquery-ml"].checked == 61
    assert results["bigquery-ai"].ok and results["bigquery-ai"].checked == 43

    converted = convert_notebook(
        REPO_ROOT / "bigquery-ml" / "models" / "arima_plus" / "arima_plus.ipynb",
        REPO_ROOT / "bigquery-ml",
    )
    assert converted.startswith("> **Source (`statmike/bigquery-data-science`):**")
    assert "<!--- header table --->" not in converted

    # Negative drift test + missing and ambiguous source notebook tests
    tmp_skill = tmp_path / "bigquery-ml"
    shutil.copytree(SKILLS_ROOT / "bigquery-ml", tmp_skill)
    nar_file = tmp_skill / "narrative" / "arima_plus.md"
    nar_file.write_text(
        nar_file.read_text(encoding="utf-8") + "\nDrifted line.\n",
        encoding="utf-8",
    )
    (tmp_skill / "narrative" / "nonexistent_topic_xyz.md").write_text(
        "# Missing Source\n",
        encoding="utf-8",
    )
    # Remove narrative_sources mapping so feature_store.md becomes ambiguous
    mf_path = tmp_skill / "skill.manifest.json"
    mf_data = json.loads(mf_path.read_text(encoding="utf-8"))
    mf_data["narrative_sources"] = {}
    mf_path.write_text(json.dumps(mf_data), encoding="utf-8")

    drift = check_skill_narratives(tmp_skill, REPO_ROOT)
    assert drift is not None and not drift.ok
    assert "arima_plus.md" in drift.stale
    assert any(
        "nonexistent_topic_xyz.md" in msg for msg in drift.missing_source
    )
    assert any("ambiguous" in msg for msg in drift.missing_source)


def test_link_policy_passes_on_domains_and_rejects_broken_anchor_or_escape(
    tmp_path: Path,
) -> None:
    ml_res = check_project(
        REPO_ROOT / "bigquery-ml",
        [REPO_ROOT / "bigquery-ai"],
        REPO_ROOT,
    )
    ai_res = check_project(
        REPO_ROOT / "bigquery-ai",
        [REPO_ROOT / "bigquery-ml"],
        REPO_ROOT,
    )
    assert ml_res.ok, [v.format(REPO_ROOT / "bigquery-ml") for v in ml_res.violations]
    assert ai_res.ok, [v.format(REPO_ROOT / "bigquery-ai") for v in ai_res.violations]

    # Negative test: broken anchor + escaping link
    proj = tmp_path / "subproj"
    proj.mkdir()
    (tmp_path / "outside.md").write_text("# Outside\n", encoding="utf-8")
    (proj / "page.md").write_text(
        "# Real Heading\n\nSee [bad anchor](#missing-anchor) and [escape](../outside.md).\n",
        encoding="utf-8",
    )
    bad_res = check_project(proj, [], tmp_path)
    assert not bad_res.ok
    kinds = {v.kind for v in bad_res.violations}
    assert "anchor" in kinds and "link" in kinds


def test_reference_structure_passes_and_rejects_orphan_page(
    tmp_path: Path,
) -> None:
    assert check_reference(REPO_ROOT / "bigquery-ml").ok
    assert check_reference(REPO_ROOT / "bigquery-ai").ok

    proj = tmp_path / "proj"
    (proj / "reference").mkdir(parents=True)
    (proj / "RESOURCES.md").write_text("# Resources\n", encoding="utf-8")
    (proj / "reference" / "orphan-page.md").write_text(
        "# Orphan Page\n", encoding="utf-8"
    )
    bad_ref = check_reference(proj)
    assert not bad_ref.ok
    assert any("orphan-page.md" in err for err in bad_ref.errors)


def test_pinned_models_passes_and_rejects_unpinned_model(
    tmp_path: Path,
) -> None:
    assert is_placeholder("PROJECT_ID")
    assert not is_placeholder("gemini-2.5-flash")

    allow_file = find_allow_file(REPO_ROOT / ".agents" / "skills")
    assert allow_file is not None
    allowed = load_allow_list(
        allow_file, REPO_ROOT / "bigquery-ai", REPO_ROOT
    )
    assert check_pinned_models(REPO_ROOT / "bigquery-ai", allowed).ok

    bad_proj = tmp_path / "bigquery-ai"
    bad_proj.mkdir()
    (bad_proj / "query.sql").write_text(
        "SELECT AI.GENERATE('hi', endpoint => 'gemini-1.5-pro-999');\n",
        encoding="utf-8",
    )
    bad_pin = check_pinned_models(bad_proj, allowed)
    assert not bad_pin.ok
    assert bad_pin.unlisted[0].value == "gemini-1.5-pro-999"


def test_manifest_generation_and_verification(tmp_path: Path) -> None:
    assert check_all_manifests(SKILLS_ROOT) == []
    assert source_projects(SKILLS_ROOT) == ["bigquery-ai", "bigquery-ml"]

    tmp_skill = tmp_path / "bigquery-ml"
    shutil.copytree(SKILLS_ROOT / "bigquery-ml", tmp_skill)
    manifest_path, version = write_manifest(tmp_skill, version="0.7.0")
    assert version == "0.7.0"
    committed = json.loads(
        (SKILLS_ROOT / "bigquery-ml" / "skill.manifest.json").read_text(
            encoding="utf-8"
        )
    )
    generated = build_manifest(tmp_skill, version="0.7.0")
    assert generated["syntax_files"] == committed["syntax_files"]
    assert generated["narrative_files"] == committed["narrative_files"]


def test_bump_version_and_lockstep_parity_check(tmp_path: Path) -> None:
    assert check_version_lockstep(REPO_ROOT) == []
    assert validate_semver("0.8.1") == "0.8.1"
    assert validate_semver("0.8.1rc1") == "0.8.1rc1"

    try:
        validate_semver("not-a-semver")
        raise AssertionError("Expected ValueError on invalid SemVer string")
    except ValueError as exc:
        assert "Invalid semantic version" in str(exc)

    # Copy lockstep files into an isolated tmp_path repo fixture
    for rel_file in (
        "pyproject.toml",
        "CITATION.cff",
        "plugin.json",
        ".claude-plugin/marketplace.json",
        "src/bigquery_data_science/__init__.py",
        "tests/test_packaging.py",
    ):
        dest = tmp_path / rel_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel_file, dest)

    for skill_name in ("bigquery-data-science", "bigquery-ml", "bigquery-ai"):
        skill_dest = tmp_path / "skills" / skill_name
        skill_dest.mkdir(parents=True, exist_ok=True)
        for fname in ("SKILL.md", "skill.manifest.json"):
            shutil.copy2(
                REPO_ROOT / "skills" / skill_name / fname,
                skill_dest / fname,
            )

    assert check_version_lockstep(tmp_path) == []

    updated = bump_version(tmp_path, "1.2.3", release_date="2026-10-21")
    assert len(updated) == 12
    assert check_version_lockstep(tmp_path, expected_version="1.2.3") == []
    assert (
        'date-released: "2026-10-21"'
        in (tmp_path / "CITATION.cff").read_text(encoding="utf-8")
    )

    # Introduce drift in plugin.json and verify CLI --check fails
    (tmp_path / "plugin.json").write_text(
        json.dumps({"name": "bigquery-data-science", "version": "0.0.1"}),
        encoding="utf-8",
    )
    drift_errors = check_version_lockstep(tmp_path)
    assert any("plugin.json" in err for err in drift_errors)
    assert main(["bump-version", "--check", "--repo-root", str(tmp_path)]) == 1

    # Re-stamp via CLI and verify --check passes
    assert main(["bump-version", "1.2.4", "--repo-root", str(tmp_path)]) == 0
    assert main(["bump-version", "--check", "--repo-root", str(tmp_path)]) == 0


