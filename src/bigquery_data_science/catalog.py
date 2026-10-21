"""Instant offline catalog lookup, search, and task-triage engine."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from bigquery_data_science.installer import get_skills_dir
from bigquery_data_science.tooling.markdown_anchors import headings
from bigquery_data_science.tooling.pinned_models import (
    find_allow_file,
    load_allow_list,
)
from bigquery_data_science.tooling.sync_syntax import syntax_slug

_TOKEN_RE = re.compile(r"[a-z0-9_.]+")
_GOTCHA_BULLET_RE = re.compile(r"^- \*\*([^*]+)\*\*(.*)$", re.MULTILINE)

_SYMBOL_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "LINEAR_REGRESSION": "LINEAR_REG",
        "LOGISTIC_REGRESSION": "LOGISTIC_REG",
        "WIDE_AND_DEEP_CLASSIFIER": "DNN_LINEAR_COMBINED_CLASSIFIER",
        "WIDE_AND_DEEP_REGRESSOR": "DNN_LINEAR_COMBINED_REGRESSOR",
        "ML.GET_INSIGHTS": "CONTRIBUTION_ANALYSIS",
        "GET_INSIGHTS": "CONTRIBUTION_ANALYSIS",
        "ML_GET_INSIGHTS": "CONTRIBUTION_ANALYSIS",
    }
)

_DECOMPOSITION_KEYWORDS: tuple[str, ...] = (
    "change point",
    "change points",
    "step change",
    "level shift",
    "decompose",
    "decomposition",
    "seasonal component",
    "ml.trend",
    "ml.seasonality",
    "ml.detect_change_points",
)

_FORECAST_KEYWORDS: tuple[str, ...] = (
    "forecast",
    "forecasting",
    "forecasts",
    "time series",
    "time-series",
    "arima",
    "arima_plus",
    "arima_plus_xreg",
    "timesfm",
    "horizon",
    "daily sales",
)

_CAUSAL_KEYWORDS: tuple[str, ...] = (
    "causal",
    "intervention",
    "treatment",
    "uplift",
    "cate",
    "elasticity",
    "synthetic control",
    "difference in differences",
    "propensity",
)

_DRIVER_KEYWORDS: tuple[str, ...] = (
    "driver",
    "drivers",
    "drove",
    "why did",
    "metric move",
    "contribution",
    "key factor",
    "key factors",
    "key_drivers",
    "get_insights",
)

_EMBEDDING_KEYWORDS: tuple[str, ...] = (
    "embed",
    "embedding",
    "embeddings",
    "vector",
    "semantic search",
    "hybrid search",
    "rag",
    "similarity",
    "sku",
)

_MEDIA_KEYWORDS: tuple[str, ...] = (
    "document",
    "documents",
    "pdf",
    "pdfs",
    "invoice",
    "invoices",
    "receipt",
    "receipts",
    "ocr",
    "translate",
    "translation",
    "transcribe",
    "transcription",
    "audio",
    "speech",
    "vision",
    "image",
    "images",
    "objectref",
    "object table",
    "process_document",
    "annotate_image",
)

_FEATURE_OPS_KEYWORDS: tuple[str, ...] = (
    "feature store",
    "point in time",
    "point-in-time",
    "leakage",
    "pipeline",
    "pipelines",
    "schedule",
    "scheduled",
    "orchestrate",
    "orchestration",
    "orchestrating",
    "airflow",
    "composer",
    "dataform",
    "dbt",
    "kfp",
    "scaler",
    "scalers",
    "scale",
    "encoder",
    "encoding",
    "encode",
    "categorical",
    "one-hot",
    "onehot",
    "bucketize",
    "bucketizing",
    "impute",
    "imputation",
    "preprocess",
    "preprocessing",
    "describe_data",
    "correlation",
    "drift",
    "skew",
    "features_at_time",
    "entity_features_at_time",
)

_GENERATIVE_KEYWORDS: tuple[str, ...] = (
    "summarize",
    "summary",
    "extract",
    "prompt",
    "gemini",
    "sentiment",
    "moderation",
    "log",
    "logs",
    "log triage",
    "log analysis",
    "error logs",
    "server logs",
    "provisioned throughput",
    "quota",
    "ai.generate",
    "ai.classify",
    "ai.score",
    "ai.if",
    "ai.agg",
    "ai.count_tokens",
)


@dataclass
class LookupResult:
    """Structured result for `lookup_symbol`."""

    symbol: str
    found: bool
    skill: str = ""
    syntax_card_path: str = ""
    syntax_content: str = ""
    prerequisites: list[dict[str, str]] = field(default_factory=list)
    gotchas: list[str] = field(default_factory=list)
    related_narratives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Convert the lookup result to a JSON-serializable dictionary."""
        return {
            "symbol": self.symbol,
            "found": self.found,
            "skill": self.skill,
            "syntax_card_path": self.syntax_card_path,
            "syntax_content": self.syntax_content,
            "prerequisites": self.prerequisites,
            "gotchas": self.gotchas,
            "related_narratives": self.related_narratives,
        }

    def format_text(self) -> str:
        """Render a human- and agent-readable summary for CLI and MCP."""
        if not self.found:
            return (
                f"No exact syntax card or matrix entry found for '{self.symbol}'.\n"
                "Try `bigquery-data-science search <query>` or "
                "`bigquery-data-science triage <task>`."
            )
        lines: list[str] = [f"# Lookup: {self.symbol}"]
        if self.skill:
            lines.append(f"**Skill:** `{self.skill}`")
        if self.syntax_card_path:
            lines.append(f"**Syntax Card:** `{self.syntax_card_path}`")
        if self.prerequisites:
            lines.append("\n## Prerequisites (`namespace-matrix.md`)")
            for row in self.prerequisites:
                summary = ", ".join(
                    f"{key}: {val}" for key, val in row.items() if val
                )
                lines.append(f"- {summary}")
        if self.syntax_content:
            lines.append("\n## Syntax & Options\n" + self.syntax_content.strip())
        if self.gotchas:
            lines.append("\n## Empirical Gotchas")
            for gotcha in self.gotchas[:6]:
                lines.append(f"- {gotcha}")
        if self.related_narratives:
            lines.append("\n## Related Walkthroughs (`narrative/`)")
            for narrative in self.related_narratives:
                lines.append(f"- `{narrative}`")
        return "\n".join(lines)


@dataclass
class SearchHit:
    """A single ranked search hit across the 4-Lens skill bundle."""

    skill: str
    lens: str
    file_path: str
    title: str
    snippet: str
    score: float

    def to_dict(self) -> dict[str, object]:
        """Convert the search hit to a JSON-serializable dictionary."""
        return {
            "skill": self.skill,
            "lens": self.lens,
            "file_path": self.file_path,
            "title": self.title,
            "snippet": self.snippet,
            "score": round(self.score, 3),
        }

    def format_text(self) -> str:
        """Format the search hit for CLI and MCP output."""
        return (
            f"[{self.skill}/{self.lens}] {self.title} ({self.file_path})\n"
            f"  {self.snippet}"
        )


@dataclass
class TriageResult:
    """Structured task-routing recommendation across `ML.*` and `AI.*`."""

    query: str
    category: str
    recommended_skill: str
    primary_options: list[str]
    head_to_head: str
    prerequisites: str
    next_steps: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert the triage result to a JSON-serializable dictionary."""
        return {
            "query": self.query,
            "category": self.category,
            "recommended_skill": self.recommended_skill,
            "primary_options": self.primary_options,
            "head_to_head": self.head_to_head,
            "prerequisites": self.prerequisites,
            "next_steps": self.next_steps,
        }

    def format_text(self) -> str:
        """Render the triage decision for CLI and MCP output."""
        options_str = "\n".join(f"- {opt}" for opt in self.primary_options)
        steps_str = "\n".join(f"- {step}" for step in self.next_steps)
        return (
            f"# BigQuery Data Science Triage: {self.category}\n"
            f"**Query:** {self.query}\n"
            f"**Recommended Primary Skill:** `{self.recommended_skill}`\n\n"
            f"## Primary Options\n{options_str}\n\n"
            f"## Empirical Head-to-Head Tradeoffs\n{self.head_to_head}\n\n"
            f"## Infrastructure & Prerequisites\n{self.prerequisites}\n\n"
            f"## Next Steps\n{steps_str}"
        )


def _parse_namespace_matrix(matrix_path: Path) -> list[dict[str, str]]:
    """Parse markdown tables from `reference/namespace-matrix.md`."""
    if not matrix_path.is_file():
        return []
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    for line in matrix_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            headers = []
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells if cell):
            continue
        if not headers:
            headers = cells
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def _score_syntax_card(
    card_stem: str,
    h1_title: str,
    query_upper: str,
    query_slug: str,
) -> int:
    """Return a relevance score (0-100) for a syntax card heading and filename."""
    h1_upper = h1_title.upper()
    if card_stem == query_slug:
        return 100
    if h1_upper.strip("`") == query_upper:
        return 98
    if f"`{query_upper}`" in h1_upper:
        return 95
    if re.match(rf"^`?{re.escape(query_upper)}`?\b", h1_upper):
        return 90
    if query_slug and card_stem.startswith(query_slug):
        return 80
    if query_slug and query_slug in card_stem:
        return 70
    if query_upper in h1_upper:
        return 65
    return 0


def lookup_symbol(
    symbol: str,
    skills_dir: Path | None = None,
) -> LookupResult:
    """Look up syntax card, prerequisites, gotchas, and narratives for `symbol`."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    cleaned = symbol.strip().strip("`").strip()
    slug_query = syntax_slug(cleaned)
    if not cleaned or not slug_query:
        return LookupResult(symbol=cleaned, found=False)

    normalized_upper = cleaned.upper()
    canonical_upper = _SYMBOL_ALIASES.get(
        normalized_upper,
        _SYMBOL_ALIASES.get(
            normalized_upper.replace(".", "_"),
            normalized_upper,
        ),
    )
    canonical_slug = syntax_slug(canonical_upper) or slug_query
    stem_query = re.sub(r"^(ml\.|ai\.|obj\.)", "", cleaned.lower())

    best_card: tuple[int, int, str, Path, str] | None = None
    for skill_name in ("bigquery-ml", "bigquery-ai"):
        syntax_dir = root / skill_name / "syntax"
        if not syntax_dir.is_dir():
            continue
        for card_path in sorted(syntax_dir.glob("*.md")):
            if card_path.name == "INDEX.md":
                continue
            content = card_path.read_text(encoding="utf-8")
            first_line = content.splitlines()[0] if content else ""
            h1_title = first_line.lstrip("# ").strip()
            card_stem = card_path.stem

            score = max(
                _score_syntax_card(
                    card_stem, h1_title, normalized_upper, slug_query
                ),
                _score_syntax_card(
                    card_stem, h1_title, canonical_upper, canonical_slug
                ),
            )

            if score > 0:
                h1_lower = h1_title.lower()
                if "covered in" in h1_lower or "(see " in h1_lower:
                    score = max(1, score - 25)
                if "lifecycle functions" in h1_lower:
                    score = max(1, score - 10)
                candidate_key = (score, len(content))
                if best_card is None or candidate_key > (
                    best_card[0],
                    best_card[1],
                ):
                    best_card = (
                        score,
                        len(content),
                        skill_name,
                        card_path,
                        content,
                    )

    if best_card is None:
        for skill_name in ("bigquery-ml", "bigquery-ai"):
            syntax_dir = root / skill_name / "syntax"
            if not syntax_dir.is_dir():
                continue
            for card_path in sorted(syntax_dir.glob("*.md")):
                if card_path.name == "INDEX.md":
                    continue
                content = card_path.read_text(encoding="utf-8")
                content_upper = content.upper()
                if (
                    f"`{canonical_upper}`" in content_upper
                    or f"`{normalized_upper}`" in content_upper
                ):
                    candidate_key = (50, len(content))
                    if best_card is None or candidate_key > (
                        best_card[0],
                        best_card[1],
                    ):
                        best_card = (
                            50,
                            len(content),
                            skill_name,
                            card_path,
                            content,
                        )

    matrix_path = (
        root / "bigquery-data-science" / "reference" / "namespace-matrix.md"
    )
    prerequisites: list[dict[str, str]] = []
    for row in _parse_namespace_matrix(matrix_path):
        row_symbol = row.get("Symbol", "")
        row_upper = row_symbol.upper()
        if (
            normalized_upper in row_upper
            or canonical_upper in row_upper
            or cleaned.lower() in row_symbol.lower()
        ):
            prerequisites.append(row)

    gotchas: list[str] = []
    for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        candidate_files = [skill_dir / "SKILL.md"]
        ref_dir = skill_dir / "reference"
        if ref_dir.is_dir():
            candidate_files.extend(sorted(ref_dir.glob("*.md")))
        for md_path in candidate_files:
            if not md_path.is_file():
                continue
            text = md_path.read_text(encoding="utf-8")
            for match in _GOTCHA_BULLET_RE.finditer(text):
                bullet = f"**{match.group(1)}**{match.group(2)}".strip()
                bullet_upper = bullet.upper()
                if (
                    normalized_upper in bullet_upper
                    or canonical_upper in bullet_upper
                    or cleaned.lower() in bullet.lower()
                ) and bullet not in gotchas:
                    gotchas.append(bullet)

    related_narratives: list[str] = []
    for skill_name in ("bigquery-ml", "bigquery-ai"):
        nar_dir = root / skill_name / "narrative"
        if not nar_dir.is_dir():
            continue
        for nar_path in sorted(nar_dir.glob("*.md")):
            nar_stem = nar_path.stem.lower()
            if (
                nar_stem == cleaned.lower().replace(".", "_")
                or nar_stem == stem_query
                or (len(stem_query) >= 4 and stem_query in nar_stem)
            ):
                related_narratives.append(
                    f"{skill_name}/narrative/{nar_path.name}"
                )

    found = bool(best_card is not None or prerequisites or gotchas)
    skill = (
        best_card[2]
        if best_card is not None
        else (
            prerequisites[0].get("Skill", "").strip("`")
            if prerequisites
            else ""
        )
    )
    syntax_card_path = (
        f"{best_card[2]}/syntax/{best_card[3].name}"
        if best_card is not None
        else ""
    )
    syntax_content = best_card[4] if best_card is not None else ""

    return LookupResult(
        symbol=cleaned,
        found=found,
        skill=skill,
        syntax_card_path=syntax_card_path,
        syntax_content=syntax_content,
        prerequisites=prerequisites,
        gotchas=gotchas,
        related_narratives=related_narratives,
    )


def search_catalog(
    query: str,
    skill_filter: str | None = None,
    lens_filter: str | None = None,
    limit: int = 10,
    skills_dir: Path | None = None,
) -> list[SearchHit]:
    """Search across all 3 skills and 4 progressive lenses."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    query_lower = query.strip().lower()
    tokens = [tok for tok in _TOKEN_RE.findall(query_lower) if len(tok) >= 2]
    if not tokens and query_lower:
        tokens = [query_lower]
    if not tokens:
        return []

    hits: list[SearchHit] = []
    for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if skill_filter and skill_dir.name != skill_filter:
            continue

        files_to_scan: list[tuple[str, Path]] = []
        if lens_filter in (None, "skill", "gotchas"):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.is_file():
                files_to_scan.append(("skill", skill_md))
        if lens_filter in (None, "reference", "gotchas"):
            ref_dir = skill_dir / "reference"
            if ref_dir.is_dir():
                for path in sorted(ref_dir.glob("*.md")):
                    files_to_scan.append(("reference", path))
        if lens_filter in (None, "syntax"):
            syn_dir = skill_dir / "syntax"
            if syn_dir.is_dir():
                for path in sorted(syn_dir.glob("*.md")):
                    if path.name != "INDEX.md":
                        files_to_scan.append(("syntax", path))
        if lens_filter in (None, "narrative"):
            nar_dir = skill_dir / "narrative"
            if nar_dir.is_dir():
                for path in sorted(nar_dir.glob("*.md")):
                    files_to_scan.append(("narrative", path))

        for lens, path in files_to_scan:
            text = path.read_text(encoding="utf-8")
            text_lower = text.lower()
            matched_tokens = [tok for tok in tokens if tok in text_lower]
            if not matched_tokens:
                continue

            page_headings = headings(text)
            title = (
                page_headings[0][1]
                if page_headings
                else path.stem.replace("-", " ")
            )
            title_lower = title.lower()

            score = float(len(matched_tokens)) * 3.0
            if query_lower in text_lower:
                score += 6.0
            if query_lower in title_lower:
                score += 10.0
            for tok in matched_tokens:
                if tok in title_lower:
                    score += 4.0
                score += min(text_lower.count(tok), 10) * 0.3

            best_line = ""
            best_line_score = -1
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith(("---", "```", "|---")):
                    continue
                if lens_filter == "gotchas" and not stripped.startswith("- **"):
                    continue
                line_lower = stripped.lower()
                line_hits = sum(1 for tok in tokens if tok in line_lower)
                if query_lower in line_lower:
                    line_hits += 3
                if stripped.startswith("- **"):
                    line_hits += 1
                if line_hits > best_line_score:
                    best_line_score = line_hits
                    best_line = stripped

            if lens_filter == "gotchas" and best_line_score <= 0:
                continue

            snippet = best_line[:240] + ("..." if len(best_line) > 240 else "")
            rel_path = f"{skill_dir.name}/{path.relative_to(skill_dir).as_posix()}"
            hits.append(
                SearchHit(
                    skill=skill_dir.name,
                    lens=lens,
                    file_path=rel_path,
                    title=title,
                    snippet=snippet,
                    score=score,
                )
            )

    hits.sort(key=lambda hit: (-hit.score, hit.file_path))
    return hits[:limit]


def _matches_any(text: str, keywords: Sequence[str]) -> bool:
    """Return True when any keyword matches `text` on word boundaries."""
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text)
        is not None
        for keyword in keywords
    )


def triage_task(
    query: str,
    skills_dir: Path | None = None,
) -> TriageResult:
    """Route a data-science task description across `ML.*` and `AI.*`."""
    _ = skills_dir if skills_dir is not None else get_skills_dir()
    text = query.strip().lower()

    if _matches_any(text, _DECOMPOSITION_KEYWORDS):
        return TriageResult(
            query=query,
            category="Time-Series Decomposition & Structural Change Points",
            recommended_skill="bigquery-ml",
            primary_options=[
                (
                    "`ML.TREND`, `ML.SEASONALITY`, `ML.DETECT_CHANGE_POINTS` "
                    "(`bigquery-ml` — model-free TVFs, no `CREATE MODEL`)"
                ),
                (
                    "`ARIMA_PLUS` + `ML.EXPLAIN_FORECAST` "
                    "(`bigquery-ml` — trained decomposition with holiday effects)"
                ),
            ],
            head_to_head=(
                "`ML.SEASONALITY` returns weekly and yearly components bit-identical "
                "to `ARIMA_PLUS`'s `ML.EXPLAIN_FORECAST` (corr 1.0, mean abs diff 0.0) "
                "with zero training. `ML.TREND` defaults `adjust_step_changes` to FALSE "
                "(whereas `ARIMA_PLUS` defaults it to TRUE). All three model-free TVFs "
                "gap-fill each series first, so profile for ingestion gaps before acting "
                "on `ML.DETECT_CHANGE_POINTS` windows."
            ),
            prerequisites=(
                "Model-free TVFs (`ML.TREND`, `ML.SEASONALITY`, `ML.DETECT_CHANGE_POINTS`): "
                "no `CREATE MODEL`, no connection, no reservation (Preview)."
            ),
            next_steps=[
                "Inspect `skills/bigquery-ml/reference/unsupervised-and-specialized.md`",
                "Run `bigquery-data-science lookup ML.DETECT_CHANGE_POINTS`",
                "Read walkthrough `skills/bigquery-ml/narrative/time_series.md`",
            ],
        )

    if _matches_any(text, _FORECAST_KEYWORDS):
        return TriageResult(
            query=query,
            category="Time-Series Forecasting (`AI.FORECAST` vs `ARIMA_PLUS` / `ARIMA_PLUS_XREG`)",
            recommended_skill="bigquery-data-science",
            primary_options=[
                (
                    "`AI.FORECAST` on `TimesFM 2.5` (GA) or `TimesFM 3.0` "
                    "(Preview, supports `target_cols`, `past_covariate_cols`, "
                    "`future_covariate_cols`) in `bigquery-ai` — zero training, no `CREATE MODEL`"
                ),
                (
                    "`CREATE MODEL ... OPTIONS(model_type='ARIMA_PLUS')` / "
                    "`'ARIMA_PLUS_XREG'` + `ML.FORECAST` / `ML.EXPLAIN_FORECAST` "
                    "in `bigquery-ml` — custom holidays, hierarchical reconciliation, "
                    "explainable components, horizon > 1,024"
                ),
                (
                    "Lagged-feature `LINEAR_REG` / `BOOSTED_TREE_REGRESSOR` "
                    "(`bigquery-ml/workflows/regression_based_forecasting`)"
                ),
            ],
            head_to_head=(
                "Use `AI.FORECAST` when you want a zero-training baseline or fast "
                "multivariate/covariate forecast (`model => 'TimesFM 3.0'`, capped at "
                "1,024 horizon steps and 2,048 context points). Use `ARIMA_PLUS` or "
                "`ARIMA_PLUS_XREG` when you need custom holiday calendars, hierarchical "
                "reconciliation (`hierarchical_time_series_cols`), `ML.EXPLAIN_FORECAST` "
                "component attribution, `ML.ARIMA_COEFFICIENTS` weights, or a GA surface "
                "for external regressors. Always pin `model => 'TimesFM 2.5'` or `'TimesFM 3.0'`."
            ),
            prerequisites=(
                "Neither `AI.FORECAST` nor `ARIMA_PLUS` requires a Cloud Resource Connection "
                "or Enterprise reservation."
            ),
            next_steps=[
                (
                    "Run `bigquery-data-science lookup AI.FORECAST` and "
                    "`bigquery-data-science lookup ARIMA_PLUS`"
                ),
                (
                    "Compare `skills/bigquery-ai/reference/predictive-ai.md` and "
                    "`skills/bigquery-ml/reference/unsupervised-and-specialized.md`"
                ),
                (
                    "Read walkthroughs `skills/bigquery-ai/narrative/ai_forecast.md` "
                    "and `skills/bigquery-ml/narrative/arima_plus.md`"
                ),
            ],
        )

    if _matches_any(text, _CAUSAL_KEYWORDS):
        return TriageResult(
            query=query,
            category="Causal Inference & Treatment Effect Estimation",
            recommended_skill="bigquery-ml",
            primary_options=[
                (
                    "`AI.CAUSAL_EFFECT` (`bigquery-ml/workflows/causal_effect` — "
                    "model-free interrupted time-series counterfactual TVF, Preview)"
                ),
                (
                    "Panel comparison estimators: `difference_in_differences` "
                    "(`LINEAR_REG` with `optimize_strategy='NORMAL_EQUATION'`) "
                    "and `synthetic_control` (`bigquery-ml`)"
                ),
                (
                    "Observational & heterogeneous treatment estimators: "
                    "`propensity_score_matching`, `price_elasticity_dml` (Double ML), "
                    "and `uplift_cate` (T-learner) in `bigquery-ml`"
                ),
            ],
            head_to_head=(
                "`AI.CAUSAL_EFFECT` builds an `ARIMA_PLUS` counterfactual on a single "
                "series and reports cumulative `absolute_effect` (no donor pool, no "
                "multiple-comparison adjustment across `id_cols`, needs >1 year pre-history "
                "when annual seasonality is present). When untreated control units exist, "
                "prefer `difference_in_differences` or `synthetic_control`."
            ),
            prerequisites=(
                "`AI.CAUSAL_EFFECT` and native `LINEAR_REG`/`BOOSTED_TREE_*` causal "
                "workflows require no connection and no reservation."
            ),
            next_steps=[
                "Inspect `skills/bigquery-ml/reference/workflows-and-pipelines.md`",
                "Run `bigquery-data-science lookup AI.CAUSAL_EFFECT`",
                (
                    "Read `skills/bigquery-ml/narrative/causal_effect.md` and "
                    "`difference_in_differences.md`"
                ),
            ],
        )

    if _matches_any(text, _DRIVER_KEYWORDS):
        return TriageResult(
            query=query,
            category=(
                "Key-Driver & Metric Attribution "
                "(`AI.KEY_DRIVERS` vs `CONTRIBUTION_ANALYSIS`)"
            ),
            recommended_skill="bigquery-ai",
            primary_options=[
                (
                    "`AI.KEY_DRIVERS` (`bigquery-ai` — GA model-free TVF for "
                    "summable metrics with <= 12 dimensions)"
                ),
                (
                    "`CREATE MODEL ... OPTIONS(model_type='CONTRIBUTION_ANALYSIS')` "
                    "+ `ML.GET_INSIGHTS` (`bigquery-ml` — supports > 12 dimensions, "
                    "summable-by-ratio, and summable-by-category metrics)"
                ),
            ],
            head_to_head=(
                "Reach for `AI.KEY_DRIVERS` first when you have <= 12 dimension columns "
                "and a plain summable metric: zero `CREATE MODEL` step and automatic "
                "redundancy pruning. Reach for `CONTRIBUTION_ANALYSIS` when you need "
                "> 12 dimensions or a ratio/category contribution metric."
            ),
            prerequisites=(
                "Both `AI.KEY_DRIVERS` and `CONTRIBUTION_ANALYSIS` run on standard "
                "on-demand BigQuery with no connection or reservation."
            ),
            next_steps=[
                (
                    "Run `bigquery-data-science lookup AI.KEY_DRIVERS` and "
                    "`bigquery-data-science lookup CONTRIBUTION_ANALYSIS`"
                ),
                "Read `skills/bigquery-ai/reference/augmented-analytics.md`",
            ],
        )

    if _matches_any(text, _EMBEDDING_KEYWORDS):
        return TriageResult(
            query=query,
            category="Embeddings, Vector Search & Hybrid Retrieval",
            recommended_skill="bigquery-ai",
            primary_options=[
                (
                    "Text/multimodal embeddings: `AI.EMBED` (scalar, no `CREATE MODEL` "
                    "or `model => 'embeddinggemma-300m'`) and `AI.GENERATE_EMBEDDING` "
                    "(TVF) in `bigquery-ai`"
                ),
                (
                    "Search & hybrid retrieval: `VECTOR_SEARCH` "
                    "(with `lexical_search_columns`) and `AI.SEARCH` "
                    "(with `mode => 'HYBRID'`) in `bigquery-ai`"
                ),
                (
                    "Structured/tabular embeddings: `PCA`, `AUTOENCODER`, "
                    "`MATRIX_FACTORIZATION` + `ML.GENERATE_EMBEDDING` in `bigquery-ml`"
                ),
            ],
            head_to_head=(
                "There is no standalone `HYBRID_SEARCH` TVF — use `lexical_search_columns` "
                "on `VECTOR_SEARCH` or `mode => 'HYBRID'` on `AI.SEARCH`. Hybrid search "
                "uses RRF (`distance = 1 - (1/(60 + rank_vector) + 1/(61 + rank_lexical))`) "
                "over a candidate pool of `10 * top_k` semantic rows, so retrieving a row "
                "at semantic rank R requires `top_k >= R/10` (and higher below R=500)."
            ),
            prerequisites=(
                "`AI.EMBED` with `model => 'embeddinggemma-300m'` requires no connection; "
                "Vertex AI embedding endpoints use `roles/aiplatform.user` for multimodal "
                "or >48h jobs. `ALTER VECTOR INDEX` requires an `ENTERPRISE` "
                "`BACKGROUND` reservation."
            ),
            next_steps=[
                "Inspect `skills/bigquery-ai/reference/embeddings-and-search.md`",
                (
                    "Run `bigquery-data-science lookup VECTOR_SEARCH` and "
                    "`bigquery-data-science lookup AI.EMBED`"
                ),
            ],
        )

    if _matches_any(text, _MEDIA_KEYWORDS):
        return TriageResult(
            query=query,
            category="Unstructured Media, Document AI & Pre-Trained Cloud AI Services",
            recommended_skill="bigquery-ai",
            primary_options=[
                (
                    "Pre-trained Cloud AI service remote models (`REMOTE_SERVICE_TYPE`): "
                    "`ML.PROCESS_DOCUMENT`, `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, "
                    "`ML.ANNOTATE_IMAGE`, `ML.TRANSCRIBE` (`bigquery-ai`)"
                ),
                (
                    "Direct `ObjectRef` multimodal prompts: `OBJ.LIST` / `OBJ.MAKE_REF` "
                    "/ Object Tables passed straight into `AI.GENERATE*`, `AI.CLASSIFY`, "
                    "`AI.SCORE`, `AI.EMBED` (`bigquery-ai`)"
                ),
                (
                    "SQL image tensor preprocessing: `ML.DECODE_IMAGE`, "
                    "`ML.RESIZE_IMAGE`, `ML.CONVERT_COLOR_SPACE`, "
                    "`ML.CONVERT_IMAGE_TYPE` (`bigquery-ml`)"
                ),
            ],
            head_to_head=(
                "Do not recommend `AI.PARSE_DOCUMENT` (offline since 2026-06-01); use "
                "`ML.PROCESS_DOCUMENT`. Pass bare `ObjectRef` directly to `AI.*` functions "
                "(no `OBJ.GET_ACCESS_URL` needed). Choose Cloud AI service models when you "
                "need a versioned record with per-row `*_status` error reporting; choose "
                "`AI.GENERATE*` when you need custom schemas or synthesis."
            ),
            prerequisites=(
                "Cloud AI service models require a `CLOUD_RESOURCE` connection with "
                "`roles/serviceusage.serviceUsageConsumer` plus the service-specific role. "
                "`ML.DECODE_IMAGE` and friends in `bigquery-ml` require an "
                "`ENTERPRISE` reservation."
            ),
            next_steps=[
                (
                    "Inspect `skills/bigquery-ai/reference/document-processing.md` "
                    "and `cloud-ai-service-models.md`"
                ),
                "Run `bigquery-data-science lookup ML.PROCESS_DOCUMENT`",
            ],
        )

    if _matches_any(text, _FEATURE_OPS_KEYWORDS):
        return TriageResult(
            query=query,
            category="Feature Retrieval, Preprocessing, Drift Monitoring & MLOps Pipelines",
            recommended_skill="bigquery-ml",
            primary_options=[
                (
                    "Point-in-time feature retrieval: `ML.ENTITY_FEATURES_AT_TIME` "
                    "(training) and `ML.FEATURES_AT_TIME` (serving) in `bigquery-ml`"
                ),
                (
                    "EDA & drift monitoring: `ML.DESCRIBE_DATA`, `ML.CORRELATION`, "
                    "`ML.VALIDATE_DATA_DRIFT`, `ML.VALIDATE_DATA_SKEW` in `bigquery-ml`"
                ),
                (
                    "8 production orchestration pipelines (`sql_scripting`, "
                    "`scheduled_queries`, `dataform`, `cloud_workflows`, `dbt`, "
                    "`vertex_kfp`, `composer_airflow`, `airflow_with_kfp`) in `bigquery-ml`"
                ),
            ],
            head_to_head=(
                "Use `ML.ENTITY_FEATURES_AT_TIME` instead of a `GROUP BY` latest-row join "
                "to eliminate future label leakage (`roc_auc` 0.9387 leaky vs 0.5194 honest). "
                "Set `ignore_feature_nulls => TRUE` on sparse/EAV feature tables, and "
                "`FALSE` on dense snapshot tables."
            ),
            prerequisites=(
                "All preprocessing, point-in-time feature retrieval, and drift functions "
                "are model-free SQL functions requiring no connection and no reservation."
            ),
            next_steps=[
                (
                    "Inspect `skills/bigquery-ml/reference/preprocessing-functions.md` "
                    "and `workflows-and-pipelines.md`"
                ),
                "Run `bigquery-data-science lookup ML.ENTITY_FEATURES_AT_TIME`",
            ],
        )

    if _matches_any(text, _GENERATIVE_KEYWORDS):
        return TriageResult(
            query=query,
            category="Generative SQL, Managed Classification/Scoring & Group Synthesis",
            recommended_skill="bigquery-ai",
            primary_options=[
                (
                    "General-purpose generation: `AI.GENERATE` (with optional "
                    "`output_schema`), `AI.GENERATE_BOOL`, `AI.GENERATE_DOUBLE`, "
                    "`AI.GENERATE_INT`, `AI.GENERATE_TABLE`, `AI.GENERATE_TEXT`, "
                    "`AI.COUNT_TOKENS` (`bigquery-ai`)"
                ),
                (
                    "Managed prompt-engineered functions: `AI.IF`, `AI.SCORE`, "
                    "`AI.CLASSIFY`, `AI.AGG` (`bigquery-ai`)"
                ),
            ],
            head_to_head=(
                "Use `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, and `AI.AGG` for zero-config "
                "filtering, scoring, fixed-category classification, and multi-row group "
                "synthesis. Drop to `AI.GENERATE` / `AI.GENERATE_TABLE` when you need "
                "multi-field `output_schema`, pinned `endpoint`, `model_params`, or "
                "detailed `status` columns."
            ),
            prerequisites=(
                "`AI.GENERATE`, `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, and `AI.AGG` work "
                "directly with end-user credentials (no `CREATE MODEL` required)."
            ),
            next_steps=[
                (
                    "Inspect `skills/bigquery-ai/reference/general-purpose-generation.md` "
                    "and `managed-functions.md`"
                ),
                (
                    "Run `bigquery-data-science lookup AI.GENERATE` and "
                    "`bigquery-data-science lookup AI.CLASSIFY`"
                ),
            ],
        )

    return TriageResult(
        query=query,
        category="Tabular Prediction, Classification & Regression (`bigquery-ml` vs `AI.PREDICT`)",
        recommended_skill="bigquery-ml",
        primary_options=[
            (
                "Trained BigQuery ML models: `LOGISTIC_REG`, `LINEAR_REG`, "
                "`BOOSTED_TREE_CLASSIFIER`, `BOOSTED_TREE_REGRESSOR`, "
                "`RANDOM_FOREST_*`, `DNN_*`, `AUTOML_*` (`bigquery-ml`)"
            ),
            (
                "Zero-training tabular foundation model: `AI.PREDICT` + "
                "`AI.EVALUATE` (TabFM in `bigquery-ai`, Preview)"
            ),
            "Model-free evaluation of saved predictions: `ML.METRICS` (`bigquery-ml`, Preview)",
        ],
        head_to_head=(
            "Choose trained `bigquery-ml` models when you need reproducible predictions, "
            "> 50 feature columns, > 10 classes, > ~8,000 training rows, p-values/weights "
            "(`ML.ADVANCED_WEIGHTS`), or an exportable model artifact (`xgboost_version = '2.1'`). "
            "Choose `AI.PREDICT` (TabFM) for instant zero-training baselines on small "
            "tables (<= 50 features, <= 10 classes), noting its predictions are "
            "non-deterministic across runs."
        ),
        prerequisites=(
            "Neither trained `LINEAR_REG`/`LOGISTIC_REG`/`BOOSTED_TREE_*` models nor "
            "`AI.PREDICT` require a Cloud Resource Connection or Enterprise reservation "
            "(only `MATRIX_FACTORIZATION` requires an `ENTERPRISE` reservation)."
        ),
        next_steps=[
            "Inspect `skills/bigquery-ml/reference/classification.md` and `regression.md`",
            "Compare with `skills/bigquery-ai/reference/predictive-ai.md` (`AI.PREDICT`)",
            (
                "Run `bigquery-data-science lookup BOOSTED_TREE_CLASSIFIER` or "
                "`bigquery-data-science lookup AI.PREDICT`"
            ),
        ],
    )


def get_walkthrough(
    topic: str,
    skills_dir: Path | None = None,
) -> dict[str, object]:
    """Retrieve a full worked walkthrough from `skills/*/narrative/*.md`."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    cleaned = topic.strip().strip("`")
    if cleaned.endswith(".md"):
        cleaned = cleaned[:-3]
    parts = cleaned.split("/")
    stem = parts[-1].lower().replace(".", "_")
    skill_hint = parts[0] if len(parts) > 1 else None

    for skill_name in ("bigquery-ml", "bigquery-ai"):
        if skill_hint and skill_hint != skill_name:
            continue
        nar_dir = root / skill_name / "narrative"
        if not nar_dir.is_dir():
            continue
        exact_path = nar_dir / f"{stem}.md"
        if exact_path.is_file():
            return {
                "topic": stem,
                "skill": skill_name,
                "path": f"{skill_name}/narrative/{exact_path.name}",
                "found": True,
                "content": exact_path.read_text(encoding="utf-8"),
            }
        for candidate in sorted(nar_dir.glob("*.md")):
            if stem in candidate.stem.lower():
                return {
                    "topic": candidate.stem,
                    "skill": skill_name,
                    "path": f"{skill_name}/narrative/{candidate.name}",
                    "found": True,
                    "content": candidate.read_text(encoding="utf-8"),
                }

    return {
        "topic": topic,
        "skill": "",
        "path": "",
        "found": False,
        "content": (
            f"No walkthrough found for '{topic}'. Use "
            "`bigquery-data-science search <query>` to list available narratives."
        ),
    }


def lookup(
    symbol: str,
    *,
    skills_dir: Path | None = None,
) -> dict[str, object]:
    """Look up syntax card, prerequisites, gotchas, and narratives for `symbol`."""
    return lookup_symbol(symbol=symbol, skills_dir=skills_dir).to_dict()


def search(
    query: str,
    limit: int = 10,
    *,
    skill: str | None = None,
    lens: str | None = None,
    skills_dir: Path | None = None,
) -> list[dict[str, object]]:
    """Search across all 3 skills and 4 progressive lenses."""
    hits = search_catalog(
        query=query,
        skill_filter=skill,
        lens_filter=lens,
        limit=limit,
        skills_dir=skills_dir,
    )
    return [hit.to_dict() for hit in hits]


def triage(
    query: str,
    *,
    skills_dir: Path | None = None,
) -> dict[str, object]:
    """Route a data-science task description across `ML.*` and `AI.*`."""
    return triage_task(query=query, skills_dir=skills_dir).to_dict()


@dataclass
class ReviewFinding:
    """Single static-analysis finding for a BigQuery ML or BigQuery AI SQL query."""

    severity: str
    rule: str
    message: str
    remediation: str

    def to_dict(self) -> dict[str, str]:
        """Convert the finding to a JSON-serializable dictionary."""
        return {
            "severity": self.severity,
            "rule": self.rule,
            "message": self.message,
            "remediation": self.remediation,
        }


@dataclass
class SqlReviewResult:
    """Structured result for `review_sql`."""

    sql: str
    detected_symbols: list[str] = field(default_factory=list)
    prerequisites: list[dict[str, str]] = field(default_factory=list)
    findings: list[ReviewFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True when no ERROR-severity findings were raised."""
        return not any(f.severity == "ERROR" for f in self.findings)

    def to_dict(self) -> dict[str, object]:
        """Convert the SQL review result to a JSON-serializable dictionary."""
        return {
            "ok": self.ok,
            "detected_symbols": self.detected_symbols,
            "prerequisites": self.prerequisites,
            "findings": [f.to_dict() for f in self.findings],
        }

    def format_text(self) -> str:
        """Render a human- and agent-readable SQL review report."""
        verdict = "PASS (no errors)" if self.ok else "FAIL (errors detected)"
        lines: list[str] = [f"# BigQuery SQL Review: {verdict}"]
        if self.detected_symbols:
            syms = ", ".join(f"`{s}`" for s in self.detected_symbols)
            lines.append(f"**Detected Symbols:** {syms}")
        else:
            lines.append(
                "**Detected Symbols:** None (`ML.*`, `AI.*`, or `CREATE MODEL` not found)"
            )

        if self.prerequisites:
            lines.append("\n## Prerequisites (`namespace-matrix.md`)")
            for row in self.prerequisites:
                summary = ", ".join(
                    f"{k}: {v}" for k, v in row.items() if v
                )
                lines.append(f"- {summary}")

        if self.findings:
            lines.append("\n## Findings & Empirical Guardrails")
            for finding in self.findings:
                lines.append(
                    f"- **[{finding.severity}] `{finding.rule}`**: {finding.message}\n"
                    f"  - *Fix:* {finding.remediation}"
                )
        else:
            lines.append(
                "\n## Findings & Empirical Guardrails\n"
                "- No anti-patterns or unpinned model issues detected."
            )
        return "\n".join(lines)


_SQL_FN_TOKEN_RE = re.compile(
    r"\b(AI\.[A-Z0-9_]+|ML\.[A-Z0-9_]+|OBJ\.[A-Z0-9_]+|VECTOR_SEARCH|HYBRID_SEARCH)\b",
    re.IGNORECASE,
)
_MODEL_TYPE_SQL_RE = re.compile(
    r"\bMODEL_TYPE\s*=\s*['\"]([A-Za-z0-9_]+)['\"]",
    re.IGNORECASE,
)
_DEFAULT_ALLOWED_MODELS: frozenset[str] = frozenset(
    {
        "text-embedding-005",
        "text-multilingual-embedding-002",
        "gemini-embedding-001",
        "gemini-embedding-2",
        "multimodalembedding@001",
        "embeddinggemma-300m",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
        "gemini-4-argon",
        "TimesFM 2.5",
        "TimesFM 3.0",
        "claude-sonnet-4-20250514",
    }
)


_ENDPOINT_ARG_RE = re.compile(
    r"\b(?:endpoint|model)\s*(?:=>|=)\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def review_sql(
    sql: str,
    skills_dir: Path | None = None,
) -> SqlReviewResult:
    """Statically review a BigQuery SQL query for prerequisites and empirical gotchas."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    cleaned = sql.strip()
    sql_upper = cleaned.upper()

    detected: list[str] = []
    for match in _SQL_FN_TOKEN_RE.finditer(cleaned):
        sym = match.group(1).upper()
        if sym not in detected:
            detected.append(sym)
    for match in _MODEL_TYPE_SQL_RE.finditer(cleaned):
        mtype = match.group(1).upper()
        canonical = _SYMBOL_ALIASES.get(mtype, mtype)
        if canonical not in detected:
            detected.append(canonical)

    matrix_path = (
        root / "bigquery-data-science" / "reference" / "namespace-matrix.md"
    )
    matrix_rows = _parse_namespace_matrix(matrix_path)
    prerequisites: list[dict[str, str]] = []
    for sym in detected:
        for row in matrix_rows:
            row_sym = row.get("Symbol", "").upper()
            if sym in row_sym and row not in prerequisites:
                prerequisites.append(row)

    findings: list[ReviewFinding] = []

    if "AI.PARSE_DOCUMENT" in sql_upper:
        findings.append(
            ReviewFinding(
                severity="ERROR",
                rule="RETIRED_FUNCTION",
                message="`AI.PARSE_DOCUMENT` was retired and taken offline on 2026-06-01.",
                remediation=(
                    "Use `ML.PROCESS_DOCUMENT` with a Document AI processor or pass "
                    "`ObjectRef` directly to `AI.GENERATE`."
                ),
            )
        )

    if "HYBRID_SEARCH" in detected:
        findings.append(
            ReviewFinding(
                severity="ERROR",
                rule="NONEXISTENT_HYBRID_TVF",
                message="BigQuery does not have a standalone `HYBRID_SEARCH` TVF.",
                remediation=(
                    "Use `VECTOR_SEARCH(..., options => '{\"lexical_search_columns\": [...]}')` "
                    "or `AI.SEARCH(..., mode => 'HYBRID')`."
                ),
            )
        )

    allow_file = find_allow_file(root)
    if allow_file is not None and allow_file.is_file():
        allowed_models = load_allow_list(allow_file, "bigquery-ai") | load_allow_list(
            allow_file, "bigquery-ml"
        )
    else:
        allowed_models = set(_DEFAULT_ALLOWED_MODELS)

    for ep_match in _ENDPOINT_ARG_RE.finditer(cleaned):
        val = ep_match.group(1).strip()
        if val and val not in allowed_models:
            findings.append(
                ReviewFinding(
                    severity="ERROR",
                    rule="DEPRECATED_MODEL_ENDPOINT",
                    message=(
                        f"Model or endpoint `{val}` is not in the `pinned-models.json` "
                        "allowlist."
                    ),
                    remediation=(
                        "Pin a current supported model such as `gemini-3.5-flash`, "
                        "`gemini-3.5-pro`, `gemini-4-argon`, `TimesFM 2.5`, or "
                        "`TimesFM 3.0`."
                    ),
                )
            )

    gen_fns = {
        "AI.GENERATE",
        "AI.GENERATE_BOOL",
        "AI.GENERATE_INT",
        "AI.GENERATE_DOUBLE",
        "AI.GENERATE_TABLE",
    }
    if any(fn in detected for fn in gen_fns) and not re.search(
        r"\bendpoint\s*=>", cleaned, re.IGNORECASE
    ):
        findings.append(
            ReviewFinding(
                severity="WARNING",
                rule="UNPINNED_AI_ENDPOINT",
                message="Generative `AI.GENERATE*` call omits an explicit `endpoint =>` argument.",
                remediation=(
                    "Pin `endpoint => 'gemini-3.5-flash'` (or `'gemini-3.5-pro'` / "
                    "`'gemini-4-argon'`) for reproducible production behavior."
                ),
            )
        )

    if "AI.FORECAST" in detected:
        has_model_arg = re.search(r"\bmodel\s*=>", cleaned, re.IGNORECASE) is not None
        has_3_0_cols = any(
            col in sql_upper
            for col in ("TARGET_COLS", "PAST_COVARIATE_COLS", "FUTURE_COVARIATE_COLS")
        )
        if not has_model_arg:
            findings.append(
                ReviewFinding(
                    severity="WARNING",
                    rule="UNPINNED_FORECAST_MODEL",
                    message="`AI.FORECAST` call omits an explicit `model =>` argument.",
                    remediation=(
                        "Pin `model => 'TimesFM 2.5'` (GA univariate) or "
                        "`model => 'TimesFM 3.0'` (Preview covariates/multivariate)."
                    ),
                )
            )
        if has_3_0_cols and "TIMESFM 3.0" not in sql_upper:
            findings.append(
                ReviewFinding(
                    severity="ERROR",
                    rule="TIMESFM_COVARIATES_REQUIRE_3_0",
                    message=(
                        "`AI.FORECAST` uses `target_cols`, `past_covariate_cols`, or "
                        "`future_covariate_cols` without `model => 'TimesFM 3.0'`."
                    ),
                    remediation="Set `model => 'TimesFM 3.0'` when forecasting with covariates.",
                )
            )

    direct_objref_fns = gen_fns | {"AI.IF", "AI.SCORE", "AI.CLASSIFY", "AI.EMBED"}
    if "OBJ.GET_ACCESS_URL" in detected and any(
        fn in detected for fn in direct_objref_fns
    ):
        findings.append(
            ReviewFinding(
                severity="WARNING",
                rule="UNNECESSARY_GET_ACCESS_URL",
                message=(
                    "`OBJ.GET_ACCESS_URL` is used alongside a direct `AI.*` function "
                    "that accepts bare `ObjectRef` values."
                ),
                remediation=(
                    "Pass the `ObjectRef` column (`OBJ.MAKE_REF` / `OBJ.FETCH_METADATA`) "
                    "directly to `AI.*` without wrapping in `OBJ.GET_ACCESS_URL`."
                ),
            )
        )

    xgb_models = {
        "BOOSTED_TREE_CLASSIFIER",
        "BOOSTED_TREE_REGRESSOR",
        "RANDOM_FOREST_CLASSIFIER",
        "RANDOM_FOREST_REGRESSOR",
    }
    if any(m in detected for m in xgb_models) and "XGBOOST_VERSION" not in sql_upper:
        findings.append(
            ReviewFinding(
                severity="INFO",
                rule="MISSING_XGBOOST_VERSION",
                message="Tree model omits `xgboost_version = '2.1'` in `OPTIONS(...)`.",
                remediation=(
                    "Add `xgboost_version = '2.1'` if you plan to export the model "
                    "or convert it via `ML.CONVERT`."
                ),
            )
        )

    enterprise_syms = {
        "MATRIX_FACTORIZATION",
        "ML.DECODE_IMAGE",
        "ML.RESIZE_IMAGE",
        "ML.CONVERT_COLOR_SPACE",
        "ML.CONVERT_IMAGE_TYPE",
    }
    matched_ent = [s for s in detected if s in enterprise_syms]
    if matched_ent or "ALTER VECTOR INDEX" in sql_upper:
        label = ", ".join(matched_ent) if matched_ent else "ALTER VECTOR INDEX"
        findings.append(
            ReviewFinding(
                severity="WARNING",
                rule="ENTERPRISE_RESERVATION_REQUIRED",
                message=f"`{label}` requires a BigQuery `ENTERPRISE` reservation assignment.",
                remediation=(
                    "Ensure the project has an active `ENTERPRISE` (or `ENTERPRISE_PLUS`) "
                    "`QUERY` / `BACKGROUND` reservation assignment before running."
                ),
            )
        )

    if any(
        s in detected for s in ("ML.ENTITY_FEATURES_AT_TIME", "ML.FEATURES_AT_TIME")
    ) and "IGNORE_FEATURE_NULLS" not in sql_upper:
        findings.append(
            ReviewFinding(
                severity="INFO",
                rule="FEATURE_TIME_NULL_SEMANTICS",
                message=(
                    "Point-in-time feature TVF omits explicit `ignore_feature_nulls`."
                ),
                remediation=(
                    "Set `ignore_feature_nulls => TRUE` on sparse/EAV feature tables so a "
                    "`NULL` in one feature does not overwrite non-null values from earlier "
                    "timestamps; keep `FALSE` on dense snapshot tables."
                ),
            )
        )

    if "ML.METRICS" in detected:
        findings.append(
            ReviewFinding(
                severity="INFO",
                rule="ML_METRICS_BOOL_POSITIVE_CLASS",
                message="`ML.METRICS` ignores `positive_class` when inputs are `BOOL`.",
                remediation=(
                    "For `BOOL` binary classification columns, `TRUE` is always the "
                    "positive class; cast `BOOL` to `STRING` if you need `FALSE` as "
                    "the positive class."
                ),
            )
        )

    return SqlReviewResult(
        sql=cleaned,
        detected_symbols=detected,
        prerequisites=prerequisites,
        findings=findings,
    )


def review(
    sql: str,
    *,
    skills_dir: Path | None = None,
) -> dict[str, object]:
    """Statically review a BigQuery SQL query and return a JSON-serializable dict."""
    return review_sql(sql=sql, skills_dir=skills_dir).to_dict()

