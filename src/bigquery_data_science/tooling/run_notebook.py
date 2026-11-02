"""Headless Jupyter notebook runner using `jupyter_client` and `nbformat`."""

from __future__ import annotations

import os
import queue
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bigquery_data_science.installer import (
    DEFAULT_KERNEL_DISPLAY_NAME,
    DEFAULT_KERNEL_NAME,
)
from bigquery_data_science.tooling.narrative_drift import sync_all_narratives

DEFAULT_CELL_TIMEOUT_SECONDS = 600
DEFAULT_PROJECT_PLACEHOLDER = "your-gcp-project-id"
DEFAULT_PROJECT_NUMBER_PLACEHOLDER = "projects/000000000000"
DEFAULT_BQCX_NUMBER_PLACEHOLDER = "bqcx-000000000000-"
DEFAULT_SERVICE_AGENT_NUMBER_PLACEHOLDER = "service-000000000000@"
_IOPUB_POLL_SECONDS = 1.0
_PROJECT_ENV_KEYS: tuple[str, ...] = (
    "GOOGLE_CLOUD_PROJECT",
    "GCLOUD_PROJECT",
    "GCP_PROJECT",
)
_PROJECT_NUMBER_PATH_RE = re.compile(
    r"""projects/(?!0{11,13}(?=/|$|["'\s,\\<>)\]}:;\x1b?&#]|\.(?!\d)))\d{11,13}(?=/|$|["'\s,\\<>)\]}:;\x1b?&#]|\.(?!\d))"""
)
_BQCX_PROJECT_NUMBER_RE = re.compile(
    r"((?:\x1b\[[0-9;]*[A-Za-z])+|(?<![A-Za-z0-9-]))bqcx-(?!0{11,13}-)\d{11,13}-"
)
_SERVICE_AGENT_PROJECT_NUMBER_RE = re.compile(
    r"((?:\x1b\[[0-9;]*[A-Za-z])+|(?<![A-Za-z0-9-]))service-(?!0{11,13}@)\d{11,13}@"
)


@dataclass(frozen=True)
class NotebookRunResult:
    """Summary of a headless notebook execution run."""

    notebook_path: Path
    executed_cells: int
    error_cells: list[tuple[int, str, str]]
    synced_narratives: int = 0
    sanitized_outputs: int = 0

    @property
    def ok(self) -> bool:
        """Return True when zero cells raised unhandled execution errors."""
        return not self.error_cells


def _load_dotenv_into_env(env: dict[str, str], start_dir: Path) -> None:
    """Load `KEY=VALUE` pairs from the nearest ancestor `.env` into `env`."""
    for candidate_dir in [start_dir.resolve(), *start_dir.resolve().parents]:
        dotenv_path = candidate_dir / ".env"
        if not dotenv_path.is_file():
            continue
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            clean_key = key.strip()
            clean_value = value.strip().strip("'\"")
            if clean_key and clean_value and not env.get(clean_key, "").strip():
                env[clean_key] = clean_value
        break


def _build_execution_env(cwd: Path | None = None) -> dict[str, str]:
    """Build subprocess environment with `.env`, quota project, and `PATH`."""
    env = dict(os.environ)
    _load_dotenv_into_env(env, cwd if cwd is not None else Path.cwd())
    project_id = ""
    for env_key in _PROJECT_ENV_KEYS:
        candidate = env.get(env_key, "").strip()
        if candidate:
            project_id = candidate
            break
    if project_id and project_id != DEFAULT_PROJECT_PLACEHOLDER:
        existing_quota = env.get("GOOGLE_CLOUD_QUOTA_PROJECT", "").strip()
        if not existing_quota or existing_quota == DEFAULT_PROJECT_PLACEHOLDER:
            env["GOOGLE_CLOUD_QUOTA_PROJECT"] = project_id
    env["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
    local_bin = str(Path.home() / ".local" / "bin")
    current_path = env.get("PATH", "")
    if local_bin not in current_path.split(os.pathsep):
        env["PATH"] = f"{local_bin}{os.pathsep}{current_path}" if current_path else local_bin
    return env


def _detect_runtime_project_ids(env: Mapping[str, str]) -> set[str]:
    """Collect candidate runtime GCP project IDs from `env` and ADC."""
    candidates: set[str] = set()
    for env_key in _PROJECT_ENV_KEYS:
        value = env.get(env_key, "").strip()
        if value and value != DEFAULT_PROJECT_PLACEHOLDER:
            candidates.add(value)
    try:
        import google.auth

        _, adc_project = google.auth.default()
        if adc_project and str(adc_project) != DEFAULT_PROJECT_PLACEHOLDER:
            candidates.add(str(adc_project))
    except Exception:
        pass
    return candidates


def scrub_output(
    text: str,
    project_ids: Iterable[str] = (),
    placeholder: str = DEFAULT_PROJECT_PLACEHOLDER,
) -> str:
    """Scrub runtime GCP project IDs and 11-13 digit project numbers."""
    scrubbed = text
    for project_id in dict.fromkeys(project_ids):
        if project_id and project_id != placeholder:
            scrubbed = scrubbed.replace(project_id, placeholder)
    scrubbed = _PROJECT_NUMBER_PATH_RE.sub(DEFAULT_PROJECT_NUMBER_PLACEHOLDER, scrubbed)
    scrubbed = _BQCX_PROJECT_NUMBER_RE.sub(rf"\g<1>{DEFAULT_BQCX_NUMBER_PLACEHOLDER}", scrubbed)
    return _SERVICE_AGENT_PROJECT_NUMBER_RE.sub(
        rf"\g<1>{DEFAULT_SERVICE_AGENT_NUMBER_PLACEHOLDER}", scrubbed
    )


def _scrub_value(
    value: Any,
    targets: Sequence[str] | list[str],
    placeholder: str,
) -> tuple[Any, bool]:
    """Recursively scrub `str`, `list`, and `dict` values without altering numbers."""
    if isinstance(value, str):
        scrubbed_text = scrub_output(value, targets, placeholder=placeholder)
        return scrubbed_text, scrubbed_text != value
    if isinstance(value, list):
        changed = False
        scrubbed_list: list[Any] = []
        for item in value:
            new_item, item_changed = _scrub_value(item, targets, placeholder)
            scrubbed_list.append(new_item)
            changed = changed or item_changed
        return (scrubbed_list if changed else value), changed
    if isinstance(value, dict):
        changed = False
        scrubbed_dict: dict[Any, Any] = {}
        for key, item_value in value.items():
            new_key, key_changed = (
                _scrub_value(key, targets, placeholder) if isinstance(key, str) else (key, False)
            )
            new_value, value_changed = _scrub_value(item_value, targets, placeholder)
            scrubbed_dict[new_key] = new_value
            changed = changed or key_changed or value_changed
        return (scrubbed_dict if changed else value), changed
    return value, False


def sanitize_notebook_outputs(
    notebook: Any,
    project_ids: Iterable[str],
    placeholder: str = DEFAULT_PROJECT_PLACEHOLDER,
) -> int:
    """Replace runtime `project_ids` and `projects/<number>` in cell outputs."""
    targets = [
        project_id
        for project_id in dict.fromkeys(project_ids)
        if project_id and project_id != placeholder
    ]

    sanitized_count = 0
    for cell in getattr(notebook, "cells", []):
        if getattr(cell, "cell_type", None) != "code":
            continue
        for output in getattr(cell, "outputs", []):
            changed = False
            if "text" in output:
                new_text, text_changed = _scrub_value(output["text"], targets, placeholder)
                if text_changed:
                    output["text"] = new_text
                    changed = True

            data = output.get("data")
            if isinstance(data, dict):
                for mime_type, mime_value in list(data.items()):
                    new_value, value_changed = _scrub_value(mime_value, targets, placeholder)
                    if value_changed:
                        data[mime_type] = new_value
                        changed = True

            metadata = output.get("metadata")
            if isinstance(metadata, dict):
                for meta_key, meta_value in list(metadata.items()):
                    new_key, key_changed = (
                        _scrub_value(meta_key, targets, placeholder)
                        if isinstance(meta_key, str)
                        else (meta_key, False)
                    )
                    new_meta, meta_changed = _scrub_value(meta_value, targets, placeholder)
                    if key_changed:
                        del metadata[meta_key]
                        metadata[new_key] = new_meta
                        changed = True
                    elif meta_changed:
                        metadata[meta_key] = new_meta
                        changed = True

            if "evalue" in output and isinstance(output["evalue"], str):
                new_evalue, eval_changed = _scrub_value(output["evalue"], targets, placeholder)
                if eval_changed:
                    output["evalue"] = new_evalue
                    changed = True

            traceback_lines = output.get("traceback")
            if isinstance(traceback_lines, list):
                new_traceback, traceback_changed = _scrub_value(
                    traceback_lines, targets, placeholder
                )
                if traceback_changed:
                    output["traceback"] = new_traceback
                    changed = True

            if changed:
                sanitized_count += 1

    return sanitized_count


def _resolve_kernel_name(requested: str) -> str:
    """Return `requested` if installed in Jupyter kernelspecs, else `'python3'`."""
    import jupyter_client

    jc_mod: Any = jupyter_client
    try:
        specs = jc_mod.kernelspec.find_kernel_specs()
        if requested in specs:
            return requested
    except Exception:
        pass
    return "python3"


def execute_notebook(
    notebook_path: Path,
    kernel_name: str = DEFAULT_KERNEL_NAME,
    timeout_seconds: int = DEFAULT_CELL_TIMEOUT_SECONDS,
    allow_errors: bool = False,
    sync_narratives: bool = False,
    repo_root: Path | None = None,
    skills_root: Path | None = None,
    sanitize_outputs: bool = True,
) -> NotebookRunResult:
    """Execute `notebook_path` in-place with `cwd` set to its parent folder."""
    import jupyter_client
    import nbformat

    jc_mod: Any = jupyter_client
    nb_mod: Any = nbformat

    resolved_nb = notebook_path.resolve()
    if not resolved_nb.is_file():
        raise FileNotFoundError(f"Notebook not found: {resolved_nb}")

    notebook = nb_mod.read(resolved_nb, as_version=4)
    effective_kernel = _resolve_kernel_name(kernel_name)
    env = _build_execution_env(cwd=resolved_nb.parent)

    km = jc_mod.KernelManager(kernel_name=effective_kernel)
    km.start_kernel(cwd=str(resolved_nb.parent), env=env)
    kc = km.client()
    kc.start_channels()

    executed_cells = 0
    error_cells: list[tuple[int, str, str]] = []

    try:
        kc.wait_for_ready(timeout=60)
        exec_count = 0
        display_targets: dict[str, list[tuple[list[Any], int]]] = {}
        for cell_idx, cell in enumerate(notebook.cells):
            if getattr(cell, "cell_type", None) != "code":
                continue
            source = str(getattr(cell, "source", "")).strip()
            if not source:
                cell.outputs = []
                cell.execution_count = None
                continue

            exec_count += 1
            executed_cells += 1
            msg_id = kc.execute(cell.source, store_history=True)
            outputs: list[Any] = []

            while True:
                try:
                    msg = kc.get_iopub_msg(timeout=timeout_seconds)
                except queue.Empty as exc:
                    raise TimeoutError(
                        f"Cell {cell_idx} timed out after {timeout_seconds}s"
                    ) from exc

                if msg.get("parent_header", {}).get("msg_id") != msg_id:
                    continue

                msg_type = msg.get("msg_type", "")
                content = msg.get("content", {})

                if msg_type == "status" and content.get("execution_state") == "idle":
                    break
                if msg_type == "stream":
                    outputs.append(
                        nb_mod.v4.new_output(
                            "stream",
                            name=content.get("name", "stdout"),
                            text=content.get("text", ""),
                        )
                    )
                elif msg_type in ("display_data", "update_display_data"):
                    transient = content.get("transient")
                    display_id = (
                        transient.get("display_id") if isinstance(transient, dict) else None
                    )
                    has_display_id = isinstance(display_id, str) and bool(display_id)
                    if (
                        msg_type == "update_display_data"
                        and has_display_id
                        and str(display_id) in display_targets
                    ):
                        for target_outputs, target_idx in display_targets[str(display_id)]:
                            target_outputs[target_idx]["data"] = content.get("data", {})
                            target_outputs[target_idx]["metadata"] = content.get("metadata", {})
                    else:
                        new_out = nb_mod.v4.new_output(
                            "display_data",
                            data=content.get("data", {}),
                            metadata=content.get("metadata", {}),
                        )
                        if has_display_id:
                            display_targets.setdefault(str(display_id), []).append(
                                (outputs, len(outputs))
                            )
                        outputs.append(new_out)
                elif msg_type == "execute_result":
                    outputs.append(
                        nb_mod.v4.new_output(
                            "execute_result",
                            data=content.get("data", {}),
                            metadata=content.get("metadata", {}),
                            execution_count=exec_count,
                        )
                    )
                elif msg_type == "error":
                    ename = str(content.get("ename", "Error"))
                    evalue = str(content.get("evalue", ""))
                    outputs.append(
                        nb_mod.v4.new_output(
                            "error",
                            ename=ename,
                            evalue=evalue,
                            traceback=content.get("traceback", []),
                        )
                    )
                    error_cells.append((cell_idx, ename, evalue))

            cell.outputs = outputs
            cell.execution_count = exec_count
            if error_cells and not allow_errors:
                break
    finally:
        kc.stop_channels()
        km.shutdown_kernel(now=True)

    notebook.metadata.setdefault("kernelspec", {})
    notebook.metadata["kernelspec"]["name"] = DEFAULT_KERNEL_NAME
    notebook.metadata["kernelspec"]["display_name"] = DEFAULT_KERNEL_DISPLAY_NAME
    notebook.metadata["kernelspec"]["language"] = "python"

    sanitized = 0
    if sanitize_outputs:
        sanitized = sanitize_notebook_outputs(
            notebook,
            _detect_runtime_project_ids(env),
        )

    nb_mod.write(notebook, resolved_nb)

    synced = 0
    if sync_narratives and (not error_cells or allow_errors):
        resolved_repo = repo_root.resolve() if repo_root is not None else Path.cwd().resolve()
        resolved_skills = (
            skills_root.resolve() if skills_root is not None else (resolved_repo / "skills")
        )
        if resolved_skills.is_dir():
            synced = sync_all_narratives(resolved_skills, resolved_repo)

    return NotebookRunResult(
        notebook_path=resolved_nb,
        executed_cells=executed_cells,
        error_cells=error_cells,
        synced_narratives=synced,
        sanitized_outputs=sanitized,
    )
