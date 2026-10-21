"""Notebook-led `.ipynb` -> `.sql` companion parity and static SQL review gate."""

from __future__ import annotations

import json
from pathlib import Path

from bigquery_data_science.catalog import (
    _MODEL_TYPE_SQL_RE,
    _SQL_FN_TOKEN_RE,
    _SYMBOL_ALIASES,
    review_sql,
    strip_sql_comments,
)
from bigquery_data_science.installer import get_skills_dir

_REQUIRED_PAIR_DIRS: tuple[tuple[str, str], ...] = (
    ("bigquery-ml", "functions"),
    ("bigquery-ml", "models"),
    ("bigquery-ai", "functions"),
)

_DELEGATED_PIPELINE_STEMS: frozenset[str] = frozenset(
    {
        "airflow_with_kfp",
        "cloud_workflows",
        "composer_airflow",
        "dataform",
        "dbt",
        "scheduled_queries",
        "vertex_kfp",
    }
)


def extract_sql_symbols(text: str) -> set[str]:
    """Extract canonical `AI.*`, `ML.*`, `OBJ.*`, and `MODEL_TYPE` symbols from `text`."""
    uncommented = strip_sql_comments(text)
    symbols: set[str] = set()
    for match in _SQL_FN_TOKEN_RE.finditer(uncommented):
        symbols.add(match.group(1).upper())
    for match in _MODEL_TYPE_SQL_RE.finditer(uncommented):
        mtype = match.group(1).upper()
        symbols.add(_SYMBOL_ALIASES.get(mtype, mtype))
    return symbols


def _primary_symbol_for_stem(stem: str, nb_syms: set[str]) -> str | None:
    """Return the primary SQL symbol matching folder `stem` if present in `nb_syms`."""
    upper_stem = stem.upper()
    candidates = (
        upper_stem,
        upper_stem.replace("AI_", "AI.", 1) if upper_stem.startswith("AI_") else "",
        upper_stem.replace("ML_", "ML.", 1) if upper_stem.startswith("ML_") else "",
        f"AI.{upper_stem}",
        f"ML.{upper_stem}",
        _SYMBOL_ALIASES.get(upper_stem, ""),
    )
    for cand in candidates:
        if cand and cand in nb_syms:
            return cand
    return None


def _notebook_code_text(nb_path: Path) -> str:
    """Concatenate all code cells in `nb_path`."""
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    chunks: list[str] = []
    for cell in data.get("cells", []):
        if cell.get("cell_type") == "code":
            chunks.append("".join(cell.get("source", [])))
    return "\n".join(chunks)


def check_sql_companions(
    repo_root: Path,
    skills_root: Path | None = None,
) -> list[str]:
    """Verify `.ipynb` -> `.sql` companion parity and run `review_sql` across all `.sql` files."""
    resolved_repo = repo_root.resolve()
    resolved_skills = (
        skills_root.resolve()
        if skills_root is not None
        else (
            resolved_repo / "skills"
            if (resolved_repo / "skills").is_dir()
            else get_skills_dir()
        )
    )
    errors: list[str] = []

    # 1. Verify required .ipynb -> .sql pairs in functions/ and models/
    for project_name, category in _REQUIRED_PAIR_DIRS:
        cat_dir = resolved_repo / project_name / category
        if not cat_dir.is_dir():
            continue
        for nb_path in sorted(cat_dir.rglob("*.ipynb")):
            if ".ipynb_checkpoints" in nb_path.parts:
                continue
            sql_path = nb_path.with_suffix(".sql")
            rel_nb = nb_path.relative_to(resolved_repo).as_posix()
            if not sql_path.is_file():
                errors.append(
                    f"{rel_nb}: missing paired SQL companion '{sql_path.name}'"
                )

    # 2. Verify symbol parity and static SQL review across all .sql files
    for project_name in ("bigquery-ml", "bigquery-ai"):
        proj_dir = resolved_repo / project_name
        if not proj_dir.is_dir():
            continue
        for sql_path in sorted(proj_dir.rglob("*.sql")):
            if ".venv" in sql_path.parts or ".ipynb_checkpoints" in sql_path.parts:
                continue
            rel_sql = sql_path.relative_to(resolved_repo).as_posix()
            sql_text = sql_path.read_text(encoding="utf-8")
            if not sql_text.strip():
                errors.append(f"{rel_sql}: SQL companion file is empty")
                continue

            # Run static review_sql gate (P4.3)
            rev = review_sql(sql_text, skills_dir=resolved_skills)
            for finding in rev.findings:
                if finding.severity != "ERROR":
                    continue
                if (
                    finding.rule == "RETIRED_FUNCTION"
                    and sql_path.stem == "ai_parse_document"
                ):
                    continue
                errors.append(
                    f"{rel_sql}: [{finding.rule}] {finding.message}"
                )

            # Compare against paired .ipynb if present (P4.2)
            nb_path = sql_path.with_suffix(".ipynb")
            if not nb_path.is_file():
                continue
            if (
                "pipelines" in sql_path.parts
                and sql_path.stem in _DELEGATED_PIPELINE_STEMS
            ):
                if (
                    "sql_scripting" not in sql_text
                    and "ga4_churn_prediction" not in sql_text
                ):
                    errors.append(
                        f"{rel_sql}: delegated pipeline SQL companion must reference "
                        "'pipelines/sql_scripting' or 'workflows/ga4_churn_prediction'"
                    )
                continue

            nb_syms = extract_sql_symbols(_notebook_code_text(nb_path))
            sql_syms = extract_sql_symbols(sql_text)
            if nb_syms and not sql_syms:
                errors.append(
                    f"{rel_sql}: contains no BigQuery ML/AI SQL symbols "
                    f"(paired notebook demonstrates {sorted(nb_syms)})"
                )
                continue

            primary = _primary_symbol_for_stem(sql_path.stem, nb_syms)
            if primary and primary not in sql_syms:
                errors.append(
                    f"{rel_sql}: missing primary symbol '{primary}' demonstrated in "
                    f"paired notebook '{nb_path.name}'"
                )

    return errors
