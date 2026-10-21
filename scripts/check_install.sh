#!/usr/bin/env bash
#
# check_install.sh — build the sdist and wheel via `uv build`, verify artifact hygiene
# (wheel < 1.5 MB, zero .ipynb files, zero relative links in PyPI Description), install
# the wheel into an isolated virtualenv with zero network/extra dependencies, and smoke-test
# the CLI (`list`, `install`, `lookup`, `triage`) and stdio MCP server (`initialize`,
# `tools/list`, `tools/call`).

set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname -- "$SCRIPT_DIR")"

WORK="$(mktemp -d)"
KEEP=0
[[ "${1:-}" == "--keep" ]] && KEEP=1
cleanup() { [[ $KEEP -eq 1 ]] && echo "left behind: $WORK" || rm -rf "$WORK"; }
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

echo "1. Building wheel and sdist via uv build..."
UV_NO_CONFIG=1 uv build -o "$WORK/dist" --project "$REPO_ROOT" >/dev/null
WHEEL="$(echo "$WORK"/dist/*.whl)"
SDIST="$(echo "$WORK"/dist/*.tar.gz)"
echo "   wheel: $(basename "$WHEEL")"
echo "   sdist: $(basename "$SDIST")"

echo "2. Verifying wheel and sdist size (< 1.5 MB) and zero .ipynb files..."
python3 - "$WHEEL" "$SDIST" <<'PY' || fail "artifact size or content gate failed"
import os
import sys
import tarfile
import zipfile

wheel_path, sdist_path = sys.argv[1], sys.argv[2]
wheel_bytes = os.path.getsize(wheel_path)
sdist_bytes = os.path.getsize(sdist_path)

assert wheel_bytes < 1_500_000, f"Wheel too large: {wheel_bytes:,} bytes (>= 1.5 MB)"
assert sdist_bytes < 1_500_000, f"Sdist too large: {sdist_bytes:,} bytes (>= 1.5 MB)"

with zipfile.ZipFile(wheel_path) as zf:
    wheel_names = zf.namelist()
    ipynb_in_wheel = [n for n in wheel_names if n.endswith(".ipynb")]
    assert not ipynb_in_wheel, f"Wheel contains .ipynb files: {ipynb_in_wheel}"
    skill_files = [n for n in wheel_names if "_skills/" in n and n.endswith("SKILL.md")]
    assert len(skill_files) == 3, f"Expected 3 SKILL.md files in wheel, found {skill_files}"

with tarfile.open(sdist_path, "r:gz") as tf:
    sdist_names = tf.getnames()
    ipynb_in_sdist = [n for n in sdist_names if n.endswith(".ipynb")]
    assert not ipynb_in_sdist, f"Sdist contains .ipynb files: {ipynb_in_sdist}"
    sdist_rel_names = [n.partition("/")[2] for n in sdist_names]
    for forbidden in (".github/", ".agents/", ".claude/", "uv.lock", "bigquery-ml/", "bigquery-ai/"):
        leaked = [n for n in sdist_rel_names if n.startswith(forbidden)]
        assert not leaked, f"Sdist leaked excluded path {forbidden}: {leaked[:3]}"

print(f"   wheel: {wheel_bytes:,} B ({len(wheel_names)} files, 0 .ipynb)")
print(f"   sdist: {sdist_bytes:,} B ({len(sdist_names)} files, 0 .ipynb)")
PY

echo "3. Installing wheel into isolated temporary virtualenv (zero extra deps)..."
UV_NO_CONFIG=1 uv venv "$WORK/venv" >/dev/null 2>&1
UV_NO_CONFIG=1 uv pip install --quiet --no-deps --python "$WORK/venv/bin/python" "$WHEEL"
BIN="$WORK/venv/bin"

[[ -x "$BIN/bigquery-data-science" ]] || fail "bigquery-data-science console script missing in venv"

echo "4. Verifying CLI commands (list, install, lookup, triage, bump-version --check)..."
LIST_OUT="$("$BIN/bigquery-data-science" list)" || fail "bigquery-data-science list failed"
grep -q "bigquery-data-science" <<<"$LIST_OUT" || fail "list missing bigquery-data-science"
grep -q "bigquery-ml" <<<"$LIST_OUT" || fail "list missing bigquery-ml"
grep -q "bigquery-ai" <<<"$LIST_OUT" || fail "list missing bigquery-ai"

"$BIN/bigquery-data-science" bump-version --check --repo-root "$REPO_ROOT" >/dev/null || fail "bump-version --check failed"

TARGET_DIR="$WORK/installed-skills"
"$BIN/bigquery-data-science" install --target "$TARGET_DIR" >/dev/null || fail "install failed"
[[ -f "$TARGET_DIR/bigquery-data-science/SKILL.md" ]] || fail "installed bigquery-data-science/SKILL.md missing"
[[ -f "$TARGET_DIR/bigquery-ml/SKILL.md" ]] || fail "installed bigquery-ml/SKILL.md missing"
[[ -f "$TARGET_DIR/bigquery-ai/SKILL.md" ]] || fail "installed bigquery-ai/SKILL.md missing"

ARIMA_OUT="$("$BIN/bigquery-data-science" lookup ARIMA_PLUS)" || fail "lookup ARIMA_PLUS failed"
grep -qi "ARIMA_PLUS" <<<"$ARIMA_OUT" || fail "lookup ARIMA_PLUS output missing ARIMA_PLUS"

FORECAST_OUT="$("$BIN/bigquery-data-science" lookup AI.FORECAST)" || fail "lookup AI.FORECAST failed"
grep -qi "AI.FORECAST" <<<"$FORECAST_OUT" || fail "lookup AI.FORECAST output missing AI.FORECAST"

TRIAGE_OUT="$("$BIN/bigquery-data-science" triage "forecast daily sales")" || fail "triage failed"
grep -qi "forecast" <<<"$TRIAGE_OUT" || fail "triage output missing forecast guidance"

echo "5. Verifying stdio MCP server (initialize + tools/list + tools/call) and PyPI METADATA..."
"$BIN/python" - <<'PY' || fail "MCP stdio round-trip or PyPI metadata check failed"
import importlib.metadata
import json
import re
import subprocess
import sys

meta = importlib.metadata.metadata("bigquery-data-science")
desc = meta["Description"]
assert desc and len(desc) > 500, "PyPI Description metadata is missing or truncated"
rel_links = re.findall(r"\]\((?!https?://|#|mailto:)([^)]+)\)", desc)
assert not rel_links, f"Un-rewritten relative links in PyPI Description: {rel_links}"
assert "```mermaid" not in desc, "Un-substituted ```mermaid block in PyPI Description"

requests = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "0.7.0"}}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "triage_bigquery_task", "arguments": {"query": "forecast daily sales"}}},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "lookup_bigquery_syntax", "arguments": {"symbol": "ARIMA_PLUS"}}},
]
payload = "\n".join(json.dumps(r) for r in requests) + "\n"
proc = subprocess.run(
    [sys.executable, "-m", "bigquery_data_science.cli", "mcp"],
    input=payload,
    capture_output=True,
    text=True,
    check=True,
)
responses = [json.loads(line) for line in proc.stdout.strip().splitlines() if line.strip()]
assert len(responses) >= 4, f"Expected 4 JSON-RPC responses, got {len(responses)}"
tool_names = {t["name"] for t in responses[1]["result"]["tools"]}
expected_tools = {
    "triage_bigquery_task",
    "lookup_bigquery_syntax",
    "search_bigquery_gotchas",
    "get_bigquery_walkthrough",
}
assert expected_tools <= tool_names, f"Missing MCP tools: {expected_tools - tool_names}"
assert not responses[2]["result"].get("isError"), f"triage_bigquery_task returned error: {responses[2]}"
assert not responses[3]["result"].get("isError"), f"lookup_bigquery_syntax returned error: {responses[3]}"
print(f"   MCP tools verified: {sorted(tool_names)}")
print("   0 relative links in built PyPI Description")
PY

echo "install ok"
