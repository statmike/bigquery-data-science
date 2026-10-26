"""Offline unit tests for installer, catalog lookup/search/triage, CLI, and MCP server."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import io
import json
import subprocess
from pathlib import Path

import pytest

import bigquery_data_science
from bigquery_data_science.adk import (
    get_bigquery_tools,
)
from bigquery_data_science.adk import (
    get_bigquery_walkthrough as adk_get_walkthrough,
)
from bigquery_data_science.adk import (
    lookup_bigquery_syntax as adk_lookup,
)
from bigquery_data_science.adk import (
    review_bigquery_sql as adk_review,
)
from bigquery_data_science.adk import (
    search_bigquery_gotchas as adk_search,
)
from bigquery_data_science.adk import (
    triage_bigquery_task as adk_triage,
)
from bigquery_data_science.catalog import (
    get_walkthrough,
    lookup_symbol,
    review,
    review_sql,
    search_catalog,
    triage_task,
)
from bigquery_data_science.cli import main
from bigquery_data_science.installer import (
    available_skills,
    discover_federated_skill_dirs,
    get_skill_path,
    get_skills_dir,
    install_kernel,
    install_mcp_config,
    install_skills,
    list_bundled_skills,
)
from bigquery_data_science.mcp_server import handle_message, serve_stdio


def test_get_skills_dir_and_list_bundled_skills() -> None:
    skills_dir = get_skills_dir()
    assert skills_dir.is_dir()
    skills = list_bundled_skills()
    assert len(skills) == 4
    by_name = {str(item["name"]): item for item in skills}
    assert set(by_name) == {
        "bigquery-data-science",
        "bigquery-ml",
        "bigquery-ai",
        "bigquery-mlops",
    }
    assert by_name["bigquery-data-science"]["reference_count"] == 2
    assert by_name["bigquery-ml"]["syntax_count"] == 93
    assert by_name["bigquery-ml"]["narrative_count"] == 61
    assert by_name["bigquery-ai"]["syntax_count"] == 44
    assert by_name["bigquery-ai"]["narrative_count"] == 43
    assert by_name["bigquery-mlops"]["reference_count"] == 4
    assert by_name["bigquery-mlops"]["syntax_count"] == 0
    assert by_name["bigquery-mlops"]["narrative_count"] == 0
    assert available_skills() == [
        "bigquery-data-science",
        "bigquery-ml",
        "bigquery-ai",
        "bigquery-mlops",
    ]


def test_list_bundled_skills_edge_cases(tmp_path: Path) -> None:
    assert list_bundled_skills(tmp_path / "missing_dir") == []

    custom_root = tmp_path / "skills"
    extra_dir = custom_root / "custom-extra-skill"
    extra_dir.mkdir(parents=True)
    (extra_dir / "SKILL.md").write_text(
        "---\nname: custom-extra-skill\ndescription: Custom skill.\n---\n# Title\n",
        encoding="utf-8",
    )
    (extra_dir / "skill.manifest.json").write_text(
        "{invalid json", encoding="utf-8"
    )
    listed = list_bundled_skills(custom_root)
    assert len(listed) == 1
    assert listed[0]["name"] == "custom-extra-skill"
    assert listed[0]["version"] == bigquery_data_science.__version__


def test_get_skill_path_and_unknown_skill_error() -> None:
    assert get_skill_path() == get_skills_dir()
    ml_path = get_skill_path("bigquery-ml")
    assert (ml_path / "SKILL.md").is_file()
    with pytest.raises(FileNotFoundError, match="Unknown skill"):
        get_skill_path("nonexistent-skill-xyz")


def test_discover_federated_skill_dirs_and_broken_entrypoint_resilience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    discovered = discover_federated_skill_dirs()
    assert discovered
    assert any((d / "bigquery-ml" / "SKILL.md").is_file() for d in discovered)

    class _BrokenEntryPoint:
        name = "broken_ep"

        def load(self) -> object:
            raise RuntimeError("broken entry point")

    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        lambda group: [_BrokenEntryPoint()],
    )
    fallback_dirs = discover_federated_skill_dirs()
    assert len(fallback_dirs) == 1


def test_install_skills_copy_and_symlink_and_idempotency(
    tmp_path: Path,
) -> None:
    copied = install_skills(target="all", dest=tmp_path, symlink=False)
    assert len(copied) == 8
    for name in (
        "bigquery-data-science",
        "bigquery-ml",
        "bigquery-ai",
        "bigquery-mlops",
    ):
        agent_skill = tmp_path / ".agents" / "skills" / name
        claude_skill = tmp_path / ".claude" / "skills" / name
        assert (agent_skill / "SKILL.md").is_file()
        assert not agent_skill.is_symlink()
        assert (claude_skill / "SKILL.md").is_file()

    # Overwrite with symlinks idempotently
    linked = install_skills(target="agents", dest=tmp_path, symlink=True)
    assert len(linked) == 4
    for name in (
        "bigquery-data-science",
        "bigquery-ml",
        "bigquery-ai",
        "bigquery-mlops",
    ):
        agent_skill = tmp_path / ".agents" / "skills" / name
        assert agent_skill.is_symlink()
        assert (agent_skill / "SKILL.md").is_file()


def test_install_skills_global_and_file_conflict_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = tmp_path / "fake_home"
    claude_skills = fake_home / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    # Create a conflicting regular file where the skill directory will be installed
    (claude_skills / "bigquery-ml").write_text("conflict", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: fake_home)
    installed = install_skills(
        target="claude",
        global_install=True,
        symlink=False,
    )
    assert len(installed) == 4
    assert (claude_skills / "bigquery-ml" / "SKILL.md").is_file()


def test_install_skills_custom_target_directory(tmp_path: Path) -> None:
    custom_dir = tmp_path / "custom_skills_bundle"
    installed = install_skills(target=str(custom_dir), symlink=False)
    assert len(installed) == 4
    for name in (
        "bigquery-data-science",
        "bigquery-ml",
        "bigquery-ai",
        "bigquery-mlops",
    ):
        assert (custom_dir / name / "SKILL.md").is_file()


def test_install_kernel_with_and_without_ipykernel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jup_dir = tmp_path / "jupyter_data"
    monkeypatch.setenv("JUPYTER_DATA_DIR", str(jup_dir))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, check=False: subprocess.CompletedProcess(cmd, 0),
    )
    rc = install_kernel(
        user=True,
        name="bigquery-data-science",
        display_name="BigQuery Data Science",
    )
    assert rc == 0
    kernel_json = jup_dir / "kernels" / "bigquery-data-science" / "kernel.json"
    assert kernel_json.is_file()
    payload = json.loads(kernel_json.read_text(encoding="utf-8"))
    assert payload["display_name"] == "BigQuery Data Science"

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert install_kernel() == 1


def test_lookup_symbol_arima_plus_and_case_insensitivity() -> None:
    upper_res = lookup_symbol("ARIMA_PLUS")
    lower_res = lookup_symbol("arima_plus")
    tick_res = lookup_symbol("`ARIMA_PLUS`")
    assert upper_res.found is True
    assert upper_res.skill == "bigquery-ml"
    assert "TIME_SERIES_TIMESTAMP_COL" in upper_res.format_text()
    assert lower_res.syntax_card_path == upper_res.syntax_card_path
    assert tick_res.syntax_card_path == upper_res.syntax_card_path
    assert any(
        "arima_plus.md" in nar for nar in upper_res.related_narratives
    )


def test_lookup_symbol_across_ai_and_ml_functions() -> None:
    for symbol, expected_skill in (
        ("AI.FORECAST", "bigquery-ai"),
        ("ML.ENTITY_FEATURES_AT_TIME", "bigquery-ml"),
        ("VECTOR_SEARCH", "bigquery-ai"),
        ("ML.PROCESS_DOCUMENT", "bigquery-ai"),
    ):
        res = bigquery_data_science.lookup(symbol)
        assert res["found"] is True
        assert res["skill"] == expected_skill


def test_lookup_symbol_empty_whitespace_and_backticks_return_not_found() -> None:
    for invalid_symbol in ("", "   ", "`", "```", "!!!"):
        res = lookup_symbol(invalid_symbol)
        assert res.found is False
        assert res.syntax_card_path == ""
        assert res.prerequisites == []
        assert res.gotchas == []


def test_lookup_symbol_canonical_aliases_and_body_fallback(
    tmp_path: Path,
) -> None:
    for alias in (
        "linear_regression",
        "logistic_regression",
        "WIDE_AND_DEEP_CLASSIFIER",
        "WIDE_AND_DEEP_REGRESSOR",
        "ML.GET_INSIGHTS",
        "IMPORT MODEL",
        "REMOTE MODEL",
        "VERTEX_AI_MODEL_ID",
        "TIMESFM",
        "TABFM",
        "arima-plus",
    ):
        res = lookup_symbol(alias)
        assert res.found is True, f"Expected alias {alias} to resolve"
        assert res.syntax_card_path, (
            f"Expected non-empty syntax_card_path for {alias}"
        )

    # Test secondary body-token fallback when H1/stem do not match
    custom_skills = tmp_path / "skills"
    syn_dir = custom_skills / "bigquery-ml" / "syntax"
    syn_dir.mkdir(parents=True)
    (syn_dir / "multi-function-card.md").write_text(
        "# Specialized Evaluation Card\n\nUse `ML.CUSTOM_COMPANION_TVF` for evaluation.\n",
        encoding="utf-8",
    )
    body_res = lookup_symbol(
        "ML.CUSTOM_COMPANION_TVF",
        skills_dir=custom_skills,
    )
    assert body_res.found is True
    assert body_res.syntax_card_path == "bigquery-ml/syntax/multi-function-card.md"


def test_lookup_unknown_symbol_returns_not_found() -> None:
    res = lookup_symbol("NONEXISTENT_BQ_FUNCTION_999")
    assert res.found is False
    assert "No exact syntax card" in res.format_text()


def test_search_catalog_filters_and_limits() -> None:
    hits = search_catalog("useQueryCache", limit=3)
    assert 1 <= len(hits) <= 3
    gotcha_hits = search_catalog(
        "ignore_feature_nulls",
        skill_filter="bigquery-ml",
        lens_filter="gotchas",
        limit=5,
    )
    assert gotcha_hits
    assert all(hit.skill == "bigquery-ml" for hit in gotcha_hits)

    for lens_name in ("skill", "reference", "syntax", "narrative"):
        lens_hits = search_catalog(
            "ARIMA_PLUS",
            skill_filter="bigquery-ml",
            lens_filter=lens_name,
            limit=2,
        )
        assert lens_hits
        assert all(hit.lens == lens_name for hit in lens_hits)

    assert search_catalog("") == []
    assert search_catalog("   ") == []
    one_char_hits = search_catalog("a", limit=2)
    assert len(one_char_hits) <= 2

    empty_hits = bigquery_data_science.search("xyznonexistenttoken999888")
    assert empty_hits == []


def test_triage_task_across_all_nine_domains_and_word_boundaries() -> None:
    decomp = triage_task("decompose seasonal time series with ML.TREND")
    assert "Time-Series Decomposition" in decomp.category
    assert "ML.TREND" in decomp.format_text()

    forecast = triage_task("forecast daily store sales with holidays")
    assert "Time-Series Forecasting" in forecast.category
    assert "ARIMA_PLUS" in forecast.format_text()
    assert "AI.FORECAST" in forecast.format_text()

    causal = triage_task("estimate causal treatment effect of a promo")
    assert "Causal Inference" in causal.category
    assert "AI.CAUSAL_EFFECT" in causal.format_text()
    assert "difference_in_differences" in causal.format_text()

    drivers = triage_task("why did revenue metric move across segments")
    assert "Key-Driver" in drivers.category
    assert "AI.KEY_DRIVERS" in drivers.format_text()
    assert "CONTRIBUTION_ANALYSIS" in drivers.format_text()

    rag = triage_task("hybrid vector and keyword search over SKU catalog")
    assert "Embeddings, Vector Search" in rag.category
    assert "VECTOR_SEARCH" in rag.format_text()

    docs = triage_task("extract fields from invoice PDFs and transcribe audio")
    assert "Unstructured Media" in docs.category
    assert "ML.PROCESS_DOCUMENT" in docs.format_text()

    leakage = triage_task("prevent point in time feature store label leakage")
    assert "Feature Retrieval" in leakage.category
    assert "ML.ENTITY_FEATURES_AT_TIME" in leakage.format_text()

    gen_sql = triage_task("summarize support tickets with AI.GENERATE and gemini")
    assert "Generative SQL" in gen_sql.category
    assert "AI.GENERATE" in gen_sql.format_text()

    tabular = triage_task("predict customer churn probability from tabular features")
    assert "Tabular Prediction" in tabular.category

    # Word-boundary collision regression checks (BUG-2)
    logistic = triage_task("train logistic regression classifier")
    assert "Tabular Prediction" in logistic.category

    categorical = triage_task("encode categorical columns for linear regression")
    assert "Feature Retrieval" in categorical.category

    average_spend = triage_task(
        "predict average customer spend from tabular features"
    )
    assert "Tabular Prediction" in average_spend.category

    provision = triage_task("provisioned throughput quota for gemini")
    assert "Generative SQL" in provision.category
    assert provision.recommended_skill == "bigquery-ai"
    assert provision.recommended_skills == [
        "bigquery-ai",
        "bigquery-ml",
        "bigquery-mlops",
    ]

    # Production MLOps & Multi-Skill Composition routing (Phase 5)
    mlops_orch = triage_task(
        "schedule retraining pipeline with Kubeflow KFP and Vertex AI Model Registry"
    )
    assert "MLOps Pipelines" in mlops_orch.category
    assert mlops_orch.recommended_skill == "bigquery-mlops"
    assert "bigquery-mlops" in mlops_orch.recommended_skills
    assert "bigquery-ml" in mlops_orch.recommended_skills
    assert "**Collaborating Skills:**" in mlops_orch.format_text()
    assert mlops_orch.to_dict()["recommended_skills"] == mlops_orch.recommended_skills

    mlops_ai_pipe = triage_task(
        "orchestrate AI.GENERATE and VECTOR_SEARCH with Cloud Workflows"
    )
    assert set(mlops_ai_pipe.recommended_skills) >= {
        "bigquery-ai",
        "bigquery-mlops",
    }

    mlops_wf = triage_task(
        "orchestrate BigQuery pipelines with Cloud Workflows and Dataform"
    )
    assert mlops_wf.recommended_skill == "bigquery-mlops"
    assert "bigquery-ai" in mlops_wf.recommended_skills

    mlops_drift = triage_task(
        "monitor feature drift with ML.VALIDATE_DATA_DRIFT and export ONNX"
    )
    assert mlops_drift.recommended_skill == "bigquery-mlops"
    assert "ML.VALIDATE_DATA_DRIFT" in mlops_drift.format_text()

    assert set(forecast.recommended_skills) >= {"bigquery-ml", "bigquery-ai"}
    assert set(leakage.recommended_skills) >= {"bigquery-ml", "bigquery-mlops"}


def test_get_walkthrough_resolves_narratives_and_variants() -> None:
    found = get_walkthrough("arima_plus")
    assert found["found"] is True
    assert found["skill"] == "bigquery-ml"
    assert "CREATE OR REPLACE MODEL" in str(found["content"])

    with_md = get_walkthrough("arima_plus.md")
    assert with_md["found"] is True
    assert with_md["path"] == "bigquery-ml/narrative/arima_plus.md"

    with_prefix = get_walkthrough("bigquery-ai/ai_forecast")
    assert with_prefix["found"] is True
    assert with_prefix["skill"] == "bigquery-ai"

    substring_match = get_walkthrough("xreg")
    assert substring_match["found"] is True
    assert substring_match["topic"] == "arima_plus_xreg"

    for mlops_topic in (
        "pipeline_scheduled_queries",
        "pipeline_dataform",
        "validate_data_drift",
        "export_model",
        "import_model",
        "remote_model",
    ):
        wt_res = get_walkthrough(mlops_topic)
        assert wt_res["found"] is True, f"Expected walkthrough for {mlops_topic}"

    missing = get_walkthrough("nonexistent_walkthrough_999")
    assert missing["found"] is False


def test_mcp_server_jsonrpc_protocol_and_tools() -> None:
    init_resp = handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    assert init_resp is not None
    result = init_resp["result"]
    assert isinstance(result, dict)
    assert result["serverInfo"]["version"] == bigquery_data_science.__version__

    # Notification returns None
    assert (
        handle_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        is None
    )

    ping_resp = handle_message({"jsonrpc": "2.0", "id": 10, "method": "ping"})
    assert ping_resp == {"jsonrpc": "2.0", "id": 10, "result": {}}

    list_resp = handle_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    assert list_resp is not None
    tools = list_resp["result"]["tools"]  # type: ignore[index]
    tool_names = {t["name"] for t in tools}
    assert tool_names == {
        "triage_bigquery_task",
        "lookup_bigquery_syntax",
        "search_bigquery_gotchas",
        "get_bigquery_walkthrough",
        "review_bigquery_sql",
    }

    for call_id, name, args in (
        (3, "triage_bigquery_task", {"query": "forecast sales"}),
        (31, "triage_bigquery_task", {"task": "forecast sales"}),
        (4, "lookup_bigquery_syntax", {"symbol": "AI.FORECAST"}),
        (
            5,
            "search_bigquery_gotchas",
            {"query": "useQueryCache", "limit": False},
        ),
        (
            51,
            "search_bigquery_gotchas",
            {"query": "useQueryCache", "limit": -5},
        ),
        (
            52,
            "search_bigquery_gotchas",
            {"query": "xyznonexistenttoken999888"},
        ),
        (6, "get_bigquery_walkthrough", {"topic": "ai_forecast"}),
        (
            61,
            "review_bigquery_sql",
            {"sql": "SELECT AI.GENERATE('hi', endpoint => 'gemini-3.5-flash')"},
        ),
    ):
        call_resp = handle_message(
            {
                "jsonrpc": "2.0",
                "id": call_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": args},
            }
        )
        assert call_resp is not None
        call_res = call_resp["result"]
        assert isinstance(call_res, dict)
        assert call_res["isError"] is False
        assert call_res["content"][0]["text"]

    # Invalid/empty tool arguments return isError=True
    for bad_id, bad_name, bad_args in (
        (90, "triage_bigquery_task", {"query": "   "}),
        (91, "lookup_bigquery_syntax", {"symbol": "```"}),
        (92, "search_bigquery_gotchas", {"query": ""}),
        (93, "get_bigquery_walkthrough", {"topic": ""}),
        (94, "review_bigquery_sql", {"sql": "   "}),
    ):
        bad_resp = handle_message(
            {
                "jsonrpc": "2.0",
                "id": bad_id,
                "method": "tools/call",
                "params": {"name": bad_name, "arguments": bad_args},
            }
        )
        assert bad_resp is not None
        assert bad_resp["result"]["isError"] is True  # type: ignore[index]

    err_method = handle_message(
        {"jsonrpc": "2.0", "id": 7, "method": "unknown/method"}
    )
    assert err_method is not None
    assert err_method["error"]["code"] == -32601  # type: ignore[index]

    err_tool = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        }
    )
    assert err_tool is not None
    assert err_tool["result"]["isError"] is True  # type: ignore[index]


def test_mcp_serve_stdio_content_length_and_error_recovery() -> None:
    ping_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
    ping_bytes = ping_req.encode()
    framed = (
        f"Content-Length: {len(ping_bytes)}\r\n"
        "Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n"
        "\r\n"
    ).encode() + ping_bytes

    notif_line = (
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        + "\n"
    ).encode()
    bad_header = b"Content-Length: invalid\r\n"
    bad_json = b"{malformed json\n"
    non_dict = b"[1, 2, 3]\n"
    line_req = (
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}) + "\n"
    ).encode()

    in_stream = io.BytesIO(
        b"\n"
        + framed
        + b"\n"
        + notif_line
        + bad_header
        + bad_json
        + non_dict
        + line_req
    )
    out_stream = io.BytesIO()
    assert serve_stdio(stdin=in_stream, stdout=out_stream) == 0

    lines = [
        json.loads(line)
        for line in out_stream.getvalue().decode("utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 3
    assert lines[0] == {"jsonrpc": "2.0", "id": 1, "result": {}}
    assert lines[1]["error"]["code"] == -32700
    assert lines[2] == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_cli_user_and_maintainer_subcommands_end_to_end(tmp_path: Path) -> None:
    assert main(["list"]) == 0
    assert main(["path", "bigquery-ai"]) == 0
    assert main(["path", "nonexistent-skill-xyz"]) == 1
    assert (
        main(
            [
                "install",
                "--target",
                "agents",
                "--dest",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert main(["lookup", "ARIMA_PLUS"]) == 0
    assert main(["lookup", "NONEXISTENT_SYMBOL_999"]) == 1
    assert main(["search", "TimesFM", "--limit", "2"]) == 0
    assert main(["search", "xyznonexistenttoken999888"]) == 0
    assert main(["triage", "forecast daily demand"]) == 0
    assert main(["validate", "skills", "--all"]) == 0
    assert main(["check-syntax-sync", "skills", "--repo-root", "."]) == 0
    assert main(["sync-syntax", "skills", "--repo-root", ".", "--check"]) == 0
    assert main(["check-narratives", "skills", "--repo-root", "."]) == 0
    assert main(["manifest", "skills", "--check"]) == 0
    assert main(["check-reference", "bigquery-ml"]) == 0
    assert (
        main(
            [
                "check-links",
                "bigquery-ml",
                "--sibling",
                "bigquery-ai",
                "--repo-root",
                ".",
            ]
        )
        == 0
    )
    assert (
        main(["check-pinned-models", "bigquery-ml", "--repo-root", "."]) == 0
    )


def test_mcp_resources_and_prompts_protocol() -> None:
    res_list = handle_message(
        {"jsonrpc": "2.0", "id": 100, "method": "resources/list", "params": {}}
    )
    assert res_list is not None
    resources = res_list["result"]["resources"]  # type: ignore[index]
    uris = {r["uri"] for r in resources}
    assert "bqds://skill/bigquery-data-science" in uris
    assert "bqds://skill/bigquery-mlops" in uris
    assert "bqds://reference/bigquery-data-science/namespace-matrix" in uris
    assert "bqds://reference/bigquery-data-science/cross-skill-playbooks" in uris
    assert "bqds://reference/bigquery-mlops/orchestration-and-pipelines" in uris

    tmpl_list = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "resources/templates/list",
            "params": {},
        }
    )
    assert tmpl_list is not None
    templates = tmpl_list["result"]["resourceTemplates"]  # type: ignore[index]
    assert len(templates) == 4

    for idx, uri in enumerate(
        (
            "bqds://skill/bigquery-ml",
            "bqds://reference/bigquery-data-science/namespace-matrix",
            "bqds://reference/bigquery-mlops/feature-store-and-point-in-time",
            "bqds://syntax/bigquery-ai/aiforecast",
            "bqds://syntax/bigquery-ml/arima-plus",
            "bqds://syntax/ARIMA_PLUS",
            "bqds://narrative/bigquery-ai/ai_agg",
            "bqds://narrative/bigquery-ml/pipeline_scheduled_queries",
            "bqds://narrative/arima_plus",
        ),
        start=110,
    ):
        read_resp = handle_message(
            {
                "jsonrpc": "2.0",
                "id": idx,
                "method": "resources/read",
                "params": {"uri": uri},
            }
        )
        assert read_resp is not None
        contents = read_resp["result"]["contents"]  # type: ignore[index]
        assert contents[0]["uri"] == uri
        assert contents[0]["text"]

    for bad_uri in (
        "http://example.com/bad",
        "bqds://../secret",
        "bqds://skill/nonexistent",
        "bqds://unknown_lens/foo/bar",
        "bqds://syntax/NONEXISTENT_999",
    ):
        bad_read = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 130,
                "method": "resources/read",
                "params": {"uri": bad_uri},
            }
        )
        assert bad_read is not None
        assert bad_read["error"]["code"] == -32602  # type: ignore[index]

    prompts_list = handle_message(
        {"jsonrpc": "2.0", "id": 140, "method": "prompts/list", "params": {}}
    )
    assert prompts_list is not None
    prompt_names = {p["name"] for p in prompts_list["result"]["prompts"]}  # type: ignore[index]
    assert prompt_names == {
        "design_bigquery_pipeline",
        "audit_bigquery_sql",
        "compare_ml_vs_ai",
        "prevent_feature_leakage",
    }

    for idx, (pname, pargs) in enumerate(
        (
            (
                "design_bigquery_pipeline",
                {"goal": "forecast sales", "constraints": "daily"},
            ),
            ("audit_bigquery_sql", {"sql": "SELECT AI.FORECAST(TABLE t)"}),
            ("compare_ml_vs_ai", {"task": "churn prediction"}),
            ("prevent_feature_leakage", {}),
        ),
        start=150,
    ):
        p_resp = handle_message(
            {
                "jsonrpc": "2.0",
                "id": idx,
                "method": "prompts/get",
                "params": {"name": pname, "arguments": pargs},
            }
        )
        assert p_resp is not None
        assert p_resp["result"]["messages"][0]["content"]["text"]  # type: ignore[index]

    for bad_pname, bad_pargs in (
        ("design_bigquery_pipeline", {}),
        ("audit_bigquery_sql", {}),
        ("compare_ml_vs_ai", {}),
        ("unknown_prompt", {}),
    ):
        bad_p = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 160,
                "method": "prompts/get",
                "params": {"name": bad_pname, "arguments": bad_pargs},
            }
        )
        assert bad_p is not None
        assert bad_p["error"]["code"] == -32602  # type: ignore[index]


def test_review_sql_detects_all_empirical_guardrails(tmp_path: Path) -> None:
    clean_sql = (
        "SELECT AI.GENERATE('Summarize', endpoint => 'gemini-3.5-flash') "
        "FROM my_dataset.my_table"
    )
    clean_res = review_sql(clean_sql)
    assert clean_res.ok is True
    assert "AI.GENERATE" in clean_res.detected_symbols
    assert clean_res.findings == []
    assert "PASS" in clean_res.format_text()

    bad_sql = """
    CREATE OR REPLACE MODEL `my_ds.bst`
    OPTIONS(model_type = 'BOOSTED_TREE_CLASSIFIER') AS
    SELECT
      AI.PARSE_DOCUMENT(doc),
      AI.GENERATE(OBJ.GET_ACCESS_URL(ref, 'r')),
      AI.GENERATE('text', endpoint => 'gemini-1.5-pro')
    FROM HYBRID_SEARCH(TABLE my_ds.idx, 'query')
    JOIN ML.FORECAST(MODEL m)
    JOIN AI.FORECAST(TABLE s, data_col => 'y', timestamp_col => 'ts', past_covariate_cols => ['x'])
    JOIN ML.ENTITY_FEATURES_AT_TIME(TABLE e, TABLE f)
    JOIN ML.METRICS(TABLE p)
    JOIN ML.DECODE_IMAGE(ref)
    """
    bad_res = review_sql(bad_sql)
    assert bad_res.ok is False
    rules = {f.rule for f in bad_res.findings}
    assert "RETIRED_FUNCTION" in rules
    assert "NONEXISTENT_HYBRID_TVF" in rules
    assert "DEPRECATED_MODEL_ENDPOINT" in rules
    assert "UNPINNED_FORECAST_MODEL" in rules
    assert "TIMESFM_COVARIATES_REQUIRE_3_0" in rules
    assert "UNNECESSARY_GET_ACCESS_URL" in rules
    assert "MISSING_XGBOOST_VERSION" in rules
    assert "ENTERPRISE_RESERVATION_REQUIRED" in rules
    assert "FEATURE_TIME_NULL_SEMANTICS" in rules
    assert "ML_METRICS_BOOL_POSITIVE_CLASS" in rules
    assert "FAIL" in bad_res.format_text()

    dict_res = review(clean_sql)
    assert dict_res["ok"] is True

    sql_file = tmp_path / "query.sql"
    sql_file.write_text(clean_sql, encoding="utf-8")
    assert main(["review-sql", str(sql_file)]) == 0
    assert main(["review-sql", str(sql_file), "--json"]) == 0
    assert main(["review-sql", "SELECT AI.PARSE_DOCUMENT(x)"]) == 1


def test_cli_json_flags_and_install_mcp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert main(["list", "--json"]) == 0
    assert main(["lookup", "AI.AGG", "--json"]) == 0
    assert main(["search", "TimesFM", "--limit", "2", "--json"]) == 0
    assert main(["triage", "forecast daily demand", "--json"]) == 0

    # Project-scoped install --mcp preserves existing keys
    mcp_file = tmp_path / ".mcp.json"
    mcp_file.write_text(
        json.dumps({"mcpServers": {"other-server": {"command": "other"}}}),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "install",
                "--target",
                "agents",
                "--dest",
                str(tmp_path),
                "--mcp",
            ]
        )
        == 0
    )
    loaded = json.loads(mcp_file.read_text(encoding="utf-8"))
    assert "other-server" in loaded["mcpServers"]
    assert loaded["mcpServers"]["bigquery-data-science"] == {
        "command": "bigquery-data-science",
        "args": ["mcp"],
    }

    # Global install_mcp_config across targets
    fake_home = tmp_path / "fake_home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    global_paths = install_mcp_config(target="all", global_install=True)
    assert len(global_paths) == 2
    assert (fake_home / ".claude.json").is_file()
    assert (fake_home / ".gemini" / "settings.json").is_file()


def test_adk_toolset_wrappers() -> None:
    tools = get_bigquery_tools()
    assert len(tools) == 5
    triage_dict = adk_triage("forecast daily store sales")
    assert "Time-Series Forecasting" in str(triage_dict["category"])
    lookup_dict = adk_lookup("AI.AGG")
    assert lookup_dict["found"] is True
    hits = adk_search("TimesFM", skill="bigquery-ai", limit=2)
    assert len(hits) == 2
    wt = adk_get_walkthrough("ai_agg")
    assert wt["found"] is True
    rev = adk_review("SELECT AI.GENERATE('hi', endpoint => 'gemini-3.5-flash')")
    assert rev["ok"] is True

