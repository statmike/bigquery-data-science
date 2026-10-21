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
from bigquery_data_science.tooling.crossrefs import check_crossrefs
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
from bigquery_data_science.tooling.markdown_check import (
    check_markdown_files,
    check_markdown_text,
)
from bigquery_data_science.tooling.narrative_drift import (
    check_all_narratives,
    check_skill_narratives,
)
from bigquery_data_science.tooling.notebook_claims import check_notebook_claims
from bigquery_data_science.tooling.pinned_models import (
    check_pinned_models,
    find_allow_file,
    is_placeholder,
    load_allow_list,
)
from bigquery_data_science.tooling.reference_structure import check_reference
from bigquery_data_science.tooling.run_notebook import (
    execute_notebook,
    sanitize_notebook_outputs,
)
from bigquery_data_science.tooling.sql_companions import (
    check_sql_companions,
    extract_sql_symbols,
)
from bigquery_data_science.tooling.status_labels import (
    check_status_labels,
    normalize_status,
)
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


def test_status_labels_passes_on_repo_and_detects_drift(tmp_path: Path) -> None:
    assert normalize_status("GA (GA announced 2025-05-12; Preview since 2024-09)") == "GA"
    assert normalize_status("GA (`mode` Preview)") == "GA / Preview"
    assert normalize_status("Preview (⚠️ offline)") == "Retired"
    assert check_status_labels(REPO_ROOT, SKILLS_ROOT) == []
    assert main(["check-status-labels", "--repo-root", str(REPO_ROOT)]) == 0

    # Negative fixture with Preview vs GA mismatch
    matrix_dir = tmp_path / "skills" / "bigquery-data-science" / "reference"
    matrix_dir.mkdir(parents=True)
    (matrix_dir / "namespace-matrix.md").write_text(
        "| Symbol | Skill | Category | Connection | Reservation | Status | Walkthrough |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| `AI.AGG` | `bigquery-ai` | Managed | None | OK | Preview | `ai_agg.md` |\n",
        encoding="utf-8",
    )
    ai_dir = tmp_path / "bigquery-ai"
    ai_dir.mkdir(parents=True)
    (ai_dir / "README.md").write_text(
        "| Function | Examples | Type | Status | What It Does |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `AI.AGG` | [nb](a) | Aggregate | GA | Aggregate |\n",
        encoding="utf-8",
    )
    errs = check_status_labels(tmp_path)
    assert any("AI.AGG" in err for err in errs)
    assert (
        main(
            [
                "check-status-labels",
                str(tmp_path / "skills"),
                "--repo-root",
                str(tmp_path),
            ]
        )
        == 1
    )


def test_crossrefs_passes_on_repo_and_detects_missing_backlink(tmp_path: Path) -> None:
    assert check_crossrefs(REPO_ROOT) == []
    assert main(["check-crossrefs", "--repo-root", str(REPO_ROOT)]) == 0

    wf_dir = tmp_path / "bigquery-ai" / "workflows" / "demo_wf"
    fn_dir = tmp_path / "bigquery-ai" / "functions" / "ai_generate"
    wf_dir.mkdir(parents=True)
    fn_dir.mkdir(parents=True)
    (wf_dir / "demo_wf.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": [
                            "**Functions used:** "
                            "[`AI.GENERATE`](../../functions/ai_generate/ai_generate.ipynb)\n"
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (fn_dir / "ai_generate.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": ["# `AI.GENERATE`\n"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    errs = check_crossrefs(tmp_path)
    assert any("missing back-link" in err for err in errs)
    assert main(["check-crossrefs", "--repo-root", str(tmp_path)]) == 1


def test_notebook_claims_passes_on_repo_and_detects_unbacked_float(
    tmp_path: Path,
) -> None:
    assert check_notebook_claims(REPO_ROOT, REPO_ROOT) == []
    assert main(["check-notebook-claims", str(REPO_ROOT), "--repo-root", str(REPO_ROOT)]) == 0

    bad_nb = tmp_path / "unbacked.ipynb"
    bad_nb.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": ["Measured accuracy was 0.9182736 on the test set.\n"],
                    },
                    {
                        "cell_type": "code",
                        "source": ["print(0.5000000)\n"],
                        "outputs": [{"output_type": "stream", "text": ["0.5000000\n"]}],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    errs = check_notebook_claims(bad_nb, tmp_path)
    assert any("0.9182736" in err for err in errs)
    assert main(["check-notebook-claims", str(bad_nb), "--repo-root", str(tmp_path)]) == 1


def test_markdown_check_passes_on_repo_and_rejects_bad_table_fence_and_mermaid(
    tmp_path: Path,
) -> None:
    assert check_markdown_files(REPO_ROOT) == []
    assert main(["check-markdown", "--repo-root", str(REPO_ROOT)]) == 0

    bad_md = (
        "# Sample\n\n"
        "| Col A | Col B |\n"
        "| --- | --- |\n"
        "| `a | b` | extra | third |\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "    A[Unquoted (Label)] --> B1\n"
        "    A --> B2\n"
        "    A --> B3\n"
        "    A --> B4\n"
        "    subgraph S1\n"
        "```\n\n"
        "```python\n"
        "x = 1\n"
    )
    issues = check_markdown_text(bad_md, "bad.md")
    assert any("unescaped '|'" in iss for iss in issues)
    assert any("GFM table row has 3 columns, expected 2" in iss for iss in issues)
    assert any("flowchart LR" in iss for iss in issues)
    assert any("unquoted parentheses" in iss for iss in issues)
    assert any("exceeding max horizontal width" in iss for iss in issues)
    assert any("unbalanced 'subgraph ... end'" in iss for iss in issues)
    assert any("unclosed code fence" in iss for iss in issues)

    (tmp_path / "bad.md").write_text(bad_md, encoding="utf-8")
    assert main(["check-markdown", "--repo-root", str(tmp_path)]) == 1


def test_run_notebook_executes_headlessly_and_catches_errors(
    tmp_path: Path,
) -> None:
    import nbformat

    nb_mod = nbformat
    nb = nb_mod.v4.new_notebook()
    nb.cells = [
        nb_mod.v4.new_markdown_cell("# Test Notebook"),
        nb_mod.v4.new_code_cell("import os\nprint('cwd:', os.getcwd())\n2 + 2"),
    ]
    nb_path = tmp_path / "sample.ipynb"
    nb_mod.write(nb, nb_path)

    res = execute_notebook(nb_path, kernel_name="python3", timeout_seconds=60)
    assert res.ok and res.executed_cells == 1
    assert main(["run-notebook", str(nb_path), "--kernel", "python3"]) == 0

    executed = nb_mod.read(nb_path, as_version=4)
    assert executed.metadata["kernelspec"]["name"] == "bigquery-data-science"
    assert executed.cells[1].outputs

    # Error notebook test
    err_nb = nb_mod.v4.new_notebook()
    err_nb.cells = [nb_mod.v4.new_code_cell("raise RuntimeError('boom')")]
    err_path = tmp_path / "failing.ipynb"
    nb_mod.write(err_nb, err_path)
    assert main(["run-notebook", str(err_path), "--kernel", "python3"]) == 1


def test_run_notebook_loads_dotenv_and_sanitizes_project_id_outputs(
    tmp_path: Path,
) -> None:
    import nbformat

    nb_mod = nbformat
    (tmp_path / ".env").write_text(
        "GOOGLE_CLOUD_PROJECT=my-secret-test-proj-999\n",
        encoding="utf-8",
    )
    nb = nb_mod.v4.new_notebook()
    nb.cells = [
        nb_mod.v4.new_code_cell(
            "import os\n"
            "proj = os.environ.get('GOOGLE_CLOUD_PROJECT', 'unset')\n"
            "print(f'Active project: {proj}.bq_ml')\n"
            "f'table: {proj}.bq_ml.sample'"
        )
    ]
    nb_path = tmp_path / "dotenv_sanitize.ipynb"
    nb_mod.write(nb, nb_path)

    res = execute_notebook(nb_path, kernel_name="python3", timeout_seconds=60)
    assert res.ok
    assert res.sanitized_outputs >= 1

    saved_text = nb_path.read_text(encoding="utf-8")
    assert "my-secret-test-proj-999" not in saved_text
    assert "your-gcp-project-id.bq_ml" in saved_text

    # Direct unit test of sanitize_notebook_outputs on error + display_data
    err_nb = nb_mod.v4.new_notebook()
    cell = nb_mod.v4.new_code_cell("pass")
    cell.outputs = [
        nb_mod.v4.new_output(
            "display_data",
            data={"text/html": "<div>proj-123-abc.bq_ml</div>"},
        ),
        nb_mod.v4.new_output(
            "error",
            ename="NotFound",
            evalue="Project proj-123-abc not found",
            traceback=["File 'x.py': proj-123-abc failed"],
        ),
    ]
    err_nb.cells = [cell]
    count = sanitize_notebook_outputs(err_nb, ["proj-123-abc"])
    assert count == 2
    dumped = nb_mod.writes(err_nb)
    assert "proj-123-abc" not in dumped
    assert "your-gcp-project-id" in dumped


def test_sql_companions_and_single_source_pinned_models(
    tmp_path: Path,
) -> None:
    from bigquery_data_science import catalog

    # P4.4: Single-source pinned-models.json (no duplicate _DEFAULT_ALLOWED_MODELS)
    assert not hasattr(catalog, "_DEFAULT_ALLOWED_MODELS")

    # P4.3: SQL comment stripping and placeholder filtering in review_sql
    commented_sql = (
        "-- Note: there is no standalone HYBRID_SEARCH TVF\n"
        "/* Also ignore AI.PARSE_DOCUMENT inside block comments */\n"
        "SELECT * FROM AI.FORECAST(\n"
        "  TABLE `bq_ai_functions.sales`,\n"
        "  data_col => 'sales',\n"
        "  timestamp_col => 'dt',\n"
        "  model => 'TimesFM 2.5'\n"
        ")\n"
    )
    rev = catalog.review_sql(commented_sql, skills_dir=SKILLS_ROOT)
    assert rev.ok
    assert "HYBRID_SEARCH" not in rev.detected_symbols

    # P4.2 & P4.3: Repo-wide check-sql-companions passes across all 87 .sql files
    assert check_sql_companions(REPO_ROOT, SKILLS_ROOT) == []
    assert (
        main(
            [
                "check-sql-companions",
                str(SKILLS_ROOT),
                "--repo-root",
                str(REPO_ROOT),
            ]
        )
        == 0
    )

    # Synthetic failure cases: missing .sql companion, missing primary symbol, retired SQL
    fn_dir = tmp_path / "bigquery-ai" / "functions" / "ai_forecast"
    fn_dir.mkdir(parents=True)
    nb_payload = {
        "cells": [
            {
                "cell_type": "code",
                "source": [
                    "SELECT * FROM AI.FORECAST(TABLE `t`, data_col => 'y', "
                    "timestamp_col => 'ts', model => 'TimesFM 2.5')"
                ],
                "outputs": [],
            }
        ]
    }
    nb_file = fn_dir / "ai_forecast.ipynb"
    nb_file.write_text(json.dumps(nb_payload), encoding="utf-8")

    # 1. Missing .sql companion
    errs_missing = check_sql_companions(tmp_path, SKILLS_ROOT)
    assert any("missing paired SQL companion" in e for e in errs_missing)

    # 2. Present .sql companion but missing primary symbol AI.FORECAST and using retired function
    sql_file = fn_dir / "ai_forecast.sql"
    sql_file.write_text(
        "SELECT * FROM AI.PARSE_DOCUMENT(TABLE `docs`);\n",
        encoding="utf-8",
    )
    errs_bad_sql = check_sql_companions(tmp_path, SKILLS_ROOT)
    assert any("RETIRED_FUNCTION" in e for e in errs_bad_sql)
    assert any("missing primary symbol 'AI.FORECAST'" in e for e in errs_bad_sql)
    assert (
        main(
            [
                "check-sql-companions",
                str(SKILLS_ROOT),
                "--repo-root",
                str(tmp_path),
            ]
        )
        == 1
    )
    assert "AI.FORECAST" in extract_sql_symbols(
        "SELECT * FROM AI.FORECAST(TABLE `t`)"
    )




