"""Headless Jupyter notebook runner using `jupyter_client` and `nbformat`."""

from __future__ import annotations

import os
import queue
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bigquery_data_science.installer import (
    DEFAULT_KERNEL_DISPLAY_NAME,
    DEFAULT_KERNEL_NAME,
)
from bigquery_data_science.tooling.narrative_drift import sync_all_narratives

DEFAULT_CELL_TIMEOUT_SECONDS = 600
_IOPUB_POLL_SECONDS = 1.0


@dataclass(frozen=True)
class NotebookRunResult:
    """Summary of a headless notebook execution run."""

    notebook_path: Path
    executed_cells: int
    error_cells: list[tuple[int, str, str]]
    synced_narratives: int = 0

    @property
    def ok(self) -> bool:
        """Return True when zero cells raised unhandled execution errors."""
        return not self.error_cells


def _build_execution_env() -> dict[str, str]:
    """Build environment variables with mTLS disabled and `~/.local/bin` on `PATH`."""
    env = dict(os.environ)
    env["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
    local_bin = str(Path.home() / ".local" / "bin")
    current_path = env.get("PATH", "")
    if local_bin not in current_path.split(os.pathsep):
        env["PATH"] = f"{local_bin}{os.pathsep}{current_path}" if current_path else local_bin
    return env


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
    env = _build_execution_env()

    km = jc_mod.KernelManager(kernel_name=effective_kernel)
    km.start_kernel(cwd=str(resolved_nb.parent), env=env)
    kc = km.client()
    kc.start_channels()

    executed_cells = 0
    error_cells: list[tuple[int, str, str]] = []

    try:
        kc.wait_for_ready(timeout=60)
        exec_count = 0
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
                elif msg_type in ("display_data", " update_display_data"):
                    outputs.append(
                        nb_mod.v4.new_output(
                            "display_data",
                            data=content.get("data", {}),
                            metadata=content.get("metadata", {}),
                        )
                    )
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

    nb_mod.write(notebook, resolved_nb)

    synced = 0
    if sync_narratives and (not error_cells or allow_errors):
        resolved_repo = (
            repo_root.resolve()
            if repo_root is not None
            else Path.cwd().resolve()
        )
        resolved_skills = (
            skills_root.resolve()
            if skills_root is not None
            else (resolved_repo / "skills")
        )
        if resolved_skills.is_dir():
            synced = sync_all_narratives(resolved_skills, resolved_repo)

    return NotebookRunResult(
        notebook_path=resolved_nb,
        executed_cells=executed_cells,
        error_cells=error_cells,
        synced_narratives=synced,
    )
