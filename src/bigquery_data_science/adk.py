"""Google Agent Development Kit (ADK) function-tool wrappers.

Provides zero-dependency, strongly-typed Python functions with Google-style
docstrings ready to pass directly into ``google.adk.Agent(tools=get_bigquery_tools())``.
"""

from __future__ import annotations

from collections.abc import Callable

from bigquery_data_science.catalog import (
    get_walkthrough,
    lookup,
    review,
    search,
    triage,
)


def triage_bigquery_task(query: str) -> dict[str, object]:
    """Arbitrate between BigQuery ML and BigQuery AI for a data science task.

    Args:
        query: Natural-language description of the data science or SQL task
            (for example, 'forecast daily store sales with holidays').

    Returns:
        Dictionary containing the task category, recommended primary skill,
        ranked SQL/model options, empirical tradeoffs, prerequisites, and next steps.
    """
    return triage(query)


def lookup_bigquery_syntax(symbol: str) -> dict[str, object]:
    """Look up the syntax card, prerequisites, and gotchas for a BigQuery symbol.

    Args:
        symbol: BigQuery ML model_type or SQL function name (for example,
            'ARIMA_PLUS', 'AI.FORECAST', 'AI.AGG', or 'VECTOR_SEARCH').

    Returns:
        Dictionary containing the syntax card content, prerequisite rows from
        namespace-matrix.md, empirical gotchas, and related walkthrough paths.
    """
    return lookup(symbol)


def search_bigquery_gotchas(
    query: str,
    skill: str = "",
    limit: int = 10,
) -> list[dict[str, object]]:
    """Search empirical gotchas, reference guides, syntax cards, and walkthroughs.

    Args:
        query: Keywords or phrase to search for across the bundled skills.
        skill: Optional skill name filter ('bigquery-data-science', 'bigquery-ml',
            'bigquery-ai', or 'bigquery-mlops'). Leave empty to search all four skills.
        limit: Maximum number of ranked hits to return (default: 10).

    Returns:
        List of ranked search hit dictionaries with skill, lens, file_path,
        title, snippet, and relevance score.
    """
    skill_filter = skill.strip() if skill and skill.strip() else None
    safe_limit = limit if isinstance(limit, int) and limit > 0 else 10
    return search(query, limit=safe_limit, skill=skill_filter)


def get_bigquery_walkthrough(topic: str) -> dict[str, object]:
    """Retrieve a complete Lens 4 narrative walkthrough markdown document.

    Args:
        topic: Walkthrough topic stem (for example, 'arima_plus', 'ai_forecast',
            'ai_agg', or 'feature_store').

    Returns:
        Dictionary containing topic, skill, path, found status, and full markdown
        content with GitHub provenance links.
    """
    return get_walkthrough(topic)


def review_bigquery_sql(sql: str) -> dict[str, object]:
    """Statically audit a BigQuery SQL query for prerequisites and empirical gotchas.

    Args:
        sql: GoogleSQL query string using BigQuery ML (CREATE MODEL / ML.*) or
            BigQuery AI (AI.* / VECTOR_SEARCH / OBJ.*).

    Returns:
        Dictionary containing ok status, detected symbols, prerequisite rows,
        and structured findings (severity, rule, message, remediation).
    """
    return review(sql)


def get_bigquery_tools() -> list[Callable[..., object]]:
    """Return the 5 BigQuery Data Science tool callables for Google ADK agents."""
    return [
        triage_bigquery_task,
        lookup_bigquery_syntax,
        search_bigquery_gotchas,
        get_bigquery_walkthrough,
        review_bigquery_sql,
    ]


__all__ = [
    "get_bigquery_tools",
    "get_bigquery_walkthrough",
    "lookup_bigquery_syntax",
    "review_bigquery_sql",
    "search_bigquery_gotchas",
    "triage_bigquery_task",
]
