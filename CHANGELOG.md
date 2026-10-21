# Changelog

All notable changes to `bigquery-data-science` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.2] - 2026-10-21

### Added
- **Maintainer Verification & Execution Gates (`P2.1`–`P2.5`):**
  - `bigquery-data-science check-status-labels`: Verifies `Preview` vs `GA` status label consistency across `bigquery-ai/README.md`, `bigquery-ml/README.md`, `<domain>/reference/*.md`, and `skills/bigquery-data-science/reference/namespace-matrix.md`.
  - `bigquery-data-science check-crossrefs`: Verifies bidirectional link symmetry between workflow notebooks (`**Functions/Models used:**`) and function/model notebooks (`**Featured in:**`).
  - `bigquery-data-science run-notebook`: Headless Jupyter notebook runner wrapping `jupyter_client` and `nbformat` with automatic working-directory resolution, mTLS certificate configuration, `bigquery-data-science` kernelspec stamping, and optional `--sync-narratives`.
  - `bigquery-data-science check-notebook-claims`: Audits high-precision decimal claims in notebook markdown prose against code cells and rendered cell outputs.
  - `bigquery-data-science check-markdown`: Verifies balanced code fences, GFM table column consistency (including zero unescaped `|` pipes inside inline code in table cells), and vertical-first `flowchart TD` Mermaid diagram layout ($\le 3$ parallel horizontal nodes per rank).
  - Integrated `check-status-labels`, `check-crossrefs`, `check-notebook-claims`, and `check-markdown` into `bigquery-data-science sweep` (Stage 7).

### Changed
- **Vertical-First Mermaid Diagram Refactor (`README.md` & `bigquery-ml/README.md`):**
  - Refactored `README.md` architecture diagram from `flowchart LR` to vertical `flowchart TD` and updated `pyproject.toml` `hatch-fancy-pypi-readme` pattern.
  - Refactored `bigquery-ml/README.md` lifecycle diagram to stack `SCORE` (`Evaluate & Score`) and `EXPLAIN` (`Explainability, Weights & Training Metadata`) vertically (`<= 3` nodes wide per rank) for maximum font legibility on GitHub.
- **Status Label & Table Alignment (`namespace-matrix.md`, `managed-functions.md`, `preprocessing-functions.md`):**
  - Synchronized `AI.AGG`, `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, `AI.EMBED`, `AI.SIMILARITY`, `AI.SEARCH`, and `ML.DECODE_IMAGE` family status labels in `skills/bigquery-data-science/reference/namespace-matrix.md`.
  - Replaced unescaped `||vector||_p` pipe syntax inside the `ML.NORMALIZER` GFM table row in `skills/bigquery-ml/reference/preprocessing-functions.md` with `ML.LP_NORM(vector, p)`.

## [0.8.1] - 2026-10-21

### Added
- **Lockstep Version Stamper (`bigquery-data-science bump-version`):**
  - Added `src/bigquery_data_science/tooling/bump_version.py` and the `bigquery-data-science bump-version [<version>] [--check]` CLI command to stamp or verify Semantic Version parity across `pyproject.toml`, `src/bigquery_data_science/__init__.py`, `CITATION.cff`, `plugin.json`, `.claude-plugin/marketplace.json`, `skills/*/SKILL.md`, `skills/*/skill.manifest.json`, and `tests/test_packaging.py` in a single step.
  - Integrated `check_version_lockstep` into `bigquery-data-science sweep`.
- **Authoring, Readability & Visual Standards (`CONTRIBUTING.md` & `skills/PLANS.md`):**
  - Codified the 100% additive/backward-compatible contract, simple Python/SQL and plain-English guidelines, vertical-first `flowchart TD` Mermaid diagram layout rules ($\le 3$ columns wide), and clean Markdown/table compilation standards.

### Changed
- **GitHub Actions Runner & Node 24 Modernization (`.github/workflows/ci.yml` & `release.yml`):**
  - Pinned `runs-on: ubuntu-24.04` and enabled `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"` across CI and Release workflows.
- **Pre-Commit Hook & Version Fallback Hygiene:**
  - Updated `.pre-commit-config.yaml` to use generic internal-domain regex detection.
  - Replaced hardcoded `"0.7.0"` fallback strings in `src/bigquery_data_science/installer.py` and `src/bigquery_data_science/tooling/manifest.py` with `bigquery_data_science.__version__`.

## [0.8.0] - 2026-10-20

### Added
- **`AI.AGG` Structured Output & Error Tolerance Support:**
  - Added coverage for GA `output_schema` parameter emitting typed `STRUCT` records directly from aggregation via SQL DDL schema strings.
  - Added coverage for GA `max_error_ratio` parameter for fault-tolerant aggregation.
  - Added Section 11 (`output_schema`) and Section 12 (`max_error_ratio`) to `bigquery-ai/functions/ai_agg/ai_agg.ipynb` and matching Examples 9 & 10 to `bigquery-ai/functions/ai_agg/ai_agg.sql`.
- **`gemini-4-argon` Foundation Model Support:**
  - Added `gemini-4-argon` to `skills/pinned-models.json`, `bigquery-ai/RESOURCES.md`, and `bigquery-ai/reference/general-purpose-functions.md`. Verified live via BigQuery.
- **GoogleSQL Reusable Column Aliases GA:**
  - Documented GoogleSQL GA support for referencing `SELECT` aliases inside expressions and `WHERE` clauses.

### Changed
- **`AI.AGG` Status Transition:**
  - Graduated `AI.AGG` from Preview to GA in `bigquery-ai/README.md`, `bigquery-ai/reference/managed-functions.md`, and `skills/bigquery-ai/reference/managed-functions.md`.
- **Skill Progressive Lenses Re-synchronized:**
  - Lens 3 (`skills/bigquery-ai/syntax/aiagg.md`): Regenerated surgical syntax card with `output_schema` and `max_error_ratio` signatures.
  - Lens 4 (`skills/bigquery-ai/narrative/ai_agg.md`): Regenerated textbook narrative from the executed `ai_agg.ipynb`.
  - Refreshed manifests across all 3 agent skills (`bigquery-data-science`, `bigquery-ml`, `bigquery-ai`).

## [0.7.0] - 2026-10-19

### Added
- **Standalone Repository & 1:1 Domain Normalization (`bigquery-ml/` and `bigquery-ai/`):**
  - Extracted and normalized all 61 BigQuery ML notebooks (`bigquery-ml/`) and 43 BigQuery AI notebooks (`bigquery-ai/`) with companion `.sql` scripts, exhaustive `reference/*.md` documentation, and unified `bigquery-data-science` Jupyter kernel metadata.
- **Hybrid 3-Skill Hierarchy & 4-Lens Progressive Disclosure (`skills/`):**
  - `skills/bigquery-data-science/`: Umbrella task router, 10 head-to-head empirical comparisons, cross-namespace composition guide, reviewer rubric, and `reference/namespace-matrix.md` prerequisite matrix.
  - `skills/bigquery-ml/` and `skills/bigquery-ai/`: 4-Lens architecture — Lens 1 (`SKILL.md` routing & cross-cutting gotchas), Lens 2 (`reference/*.md` use-case decision guides), Lens 3 (`syntax/*.md` surgical H2-sliced per-model/per-function syntax cards + `syntax/INDEX.md`), and Lens 4 (`narrative/*.md` 104 boilerplate-stripped textbook walkthroughs with GitHub provenance banners).
- **Zero-Dependency Python Package, CLI & Stdio MCP Server (`src/bigquery_data_science/`):**
  - Skill & kernel installer (`bigquery-data-science install`, `list`, `path`, `kernel`) and federated `statmike.agent_skills` entry point.
  - Instant offline catalog engine (`bigquery-data-science lookup`, `search`, `triage`).
  - Zero-dependency JSON-RPC stdio MCP server (`bigquery-data-science mcp`) exposing `triage_bigquery_task`, `lookup_bigquery_syntax`, `search_bigquery_gotchas`, and `get_bigquery_walkthrough`.
  - Maintainer verification suite (`sweep`, `validate`, `check-links`, `check-reference`, `check-syntax-sync`, `check-pinned-models`, `check-narratives`, `sync-syntax`, `convert-notebook`, `manifest`).
- **Unified Packaging & Layered `uv` Extras (`pyproject.toml` & `uv.lock`):**
  - Zero-dependency `< 1.5 MB` PyPI wheel bundling `skills/`, with optional extras `[notebooks]`, `[pipelines]`, `[workflows]`, and `[all]`.
