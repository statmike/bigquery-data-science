"""Multi-agent skill installer, Jupyter kernel helper, and entry-point discovery."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from bigquery_data_science.tooling.manifest import MANIFEST_FILENAME

SUPPORTED_TARGETS: frozenset[str] = frozenset({"agents", "claude", "all"})
ENTRYPOINT_GROUP = "statmike.agent_skills"
DEFAULT_KERNEL_NAME = "bigquery-data-science"
DEFAULT_KERNEL_DISPLAY_NAME = "BigQuery Data Science"
SKILL_NAMES: tuple[str, ...] = (
    "bigquery-data-science",
    "bigquery-ml",
    "bigquery-ai",
    "bigquery-mlops",
)

_DESCRIPTION_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)


def get_skills_dir() -> Path:
    """Return the path to the bundled `skills/` directory.

    Checks the wheel-packaged `bigquery_data_science/_skills` directory first,
    then falls back to `<repo_root>/skills` when running from a source checkout.
    """
    package_dir = Path(__file__).resolve().parent
    bundled = package_dir / "_skills"
    if bundled.is_dir() and (bundled / "bigquery-data-science").is_dir():
        return bundled
    repo_skills = package_dir.parents[1] / "skills"
    if repo_skills.is_dir():
        return repo_skills
    return bundled


def get_skill_path(
    skill_name: str | None = None,
    skills_dir: Path | None = None,
) -> Path:
    """Return the filesystem path to `skills/` or a named skill directory."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    if skill_name is None:
        return root
    candidate = root / skill_name
    if not candidate.is_dir():
        raise FileNotFoundError(
            f"Unknown skill '{skill_name}'. Available skills: "
            f"{', '.join(SKILL_NAMES)}"
        )
    return candidate


def _extract_skill_description(skill_md_path: Path) -> str:
    """Extract the one-line description from `SKILL.md` frontmatter."""
    if not skill_md_path.is_file():
        return ""
    text = skill_md_path.read_text(encoding="utf-8")
    match = _DESCRIPTION_RE.search(text)
    if not match:
        return ""
    return match.group(1).strip().strip("'\"")


def list_bundled_skills(
    skills_dir: Path | None = None,
) -> list[dict[str, object]]:
    """Return metadata and file counts for every bundled skill."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    if not root.is_dir():
        return []

    skills: list[dict[str, object]] = []
    ordered_dirs = [
        root / name for name in SKILL_NAMES if (root / name).is_dir()
    ]
    extra_dirs = [
        path
        for path in sorted(root.iterdir())
        if path.is_dir()
        and (path / "SKILL.md").is_file()
        and path.name not in SKILL_NAMES
    ]

    import bigquery_data_science

    for skill_dir in [*ordered_dirs, *extra_dirs]:
        manifest_path = skill_dir / MANIFEST_FILENAME
        version = bigquery_data_science.__version__
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if isinstance(manifest, dict) and "version" in manifest:
                    version = str(manifest["version"])
            except (OSError, json.JSONDecodeError):
                pass

        ref_dir = skill_dir / "reference"
        syn_dir = skill_dir / "syntax"
        nar_dir = skill_dir / "narrative"
        ref_count = len(list(ref_dir.glob("*.md"))) if ref_dir.is_dir() else 0
        syn_count = (
            len([p for p in syn_dir.glob("*.md") if p.name != "INDEX.md"])
            if syn_dir.is_dir()
            else 0
        )
        nar_count = len(list(nar_dir.glob("*.md"))) if nar_dir.is_dir() else 0

        skills.append(
            {
                "name": skill_dir.name,
                "version": version,
                "description": _extract_skill_description(
                    skill_dir / "SKILL.md"
                ),
                "path": str(skill_dir),
                "reference_count": ref_count,
                "syntax_count": syn_count,
                "narrative_count": nar_count,
            }
        )
    return skills


def discover_federated_skill_dirs() -> list[Path]:
    """Discover skill directories registered under `statmike.agent_skills`."""
    discovered: dict[str, Path] = {
        "bigquery_data_science": get_skills_dir().resolve()
    }
    entry_points = importlib.metadata.entry_points(group=ENTRYPOINT_GROUP)
    for entry_point in entry_points:
        try:
            loader = entry_point.load()
            resolved = loader() if callable(loader) else loader
            discovered[entry_point.name] = Path(str(resolved)).resolve()
        except Exception:
            continue
    return list(discovered.values())


def _resolve_target_dirs(
    target: str,
    dest: Path | None,
    global_install: bool,
) -> list[Path]:
    """Resolve destination skill parent directories for `install_skills`."""
    base_dir = (
        Path.home()
        if global_install
        else (dest.expanduser() if dest is not None else Path.cwd())
    )
    if target == "agents":
        return [base_dir / ".agents" / "skills"]
    if target == "claude":
        return [base_dir / ".claude" / "skills"]
    if target == "all":
        return [
            base_dir / ".agents" / "skills",
            base_dir / ".claude" / "skills",
        ]
    return [Path(target).expanduser()]


def install_skills(
    target: str = "agents",
    dest: Path | None = None,
    global_install: bool = False,
    symlink: bool = False,
    skills_dir: Path | None = None,
) -> list[Path]:
    """Install bundled skills into `.agents/skills`, `.claude/skills`, or a path."""
    source_root = (
        skills_dir if skills_dir is not None else get_skills_dir()
    ).resolve()
    target_dirs = _resolve_target_dirs(
        target=target,
        dest=dest,
        global_install=global_install,
    )

    installed_paths: list[Path] = []
    skill_sources = [
        path
        for path in sorted(source_root.iterdir())
        if path.is_dir() and (path / "SKILL.md").is_file()
    ]

    for target_dir in target_dirs:
        target_dir.mkdir(parents=True, exist_ok=True)
        for skill_src in skill_sources:
            destination = target_dir / skill_src.name
            if destination.is_symlink() or destination.is_file():
                destination.unlink()
            elif destination.is_dir():
                shutil.rmtree(destination)

            if symlink:
                relative_target = os.path.relpath(
                    skill_src,
                    start=target_dir.resolve(),
                )
                destination.symlink_to(
                    relative_target,
                    target_is_directory=True,
                )
            else:
                shutil.copytree(skill_src, destination)
            installed_paths.append(destination)

    return installed_paths


def install_kernel(
    user: bool = True,
    name: str = DEFAULT_KERNEL_NAME,
    display_name: str = DEFAULT_KERNEL_DISPLAY_NAME,
) -> int:
    """Register the `bigquery-data-science` Jupyter kernelspec via `ipykernel`."""
    if importlib.util.find_spec("ipykernel") is None:
        print(
            "ipykernel is not installed in this Python environment.\n"
            "Install the notebook extra first:\n"
            '  uv sync --extra notebooks\n'
            '  # or: pip install "bigquery-data-science[notebooks]"',
            file=sys.stderr,
        )
        return 1

    command = [
        sys.executable,
        "-m",
        "ipykernel",
        "install",
        *(["--user"] if user else []),
        "--name",
        name,
        "--display-name",
        display_name,
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode == 0:
        jup_data = os.environ.get("JUPYTER_DATA_DIR")
        if jup_data:
            kdir = Path(jup_data) / "kernels" / name
            kjson = kdir / "kernel.json"
            if not kjson.is_file():
                kdir.mkdir(parents=True, exist_ok=True)
                kjson.write_text(
                    json.dumps(
                        {
                            "argv": [
                                sys.executable,
                                "-m",
                                "ipykernel_launcher",
                                "-f",
                                "{connection_file}",
                            ],
                            "display_name": display_name,
                            "language": "python",
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
    return completed.returncode


bundled_skills_root = get_skills_dir


def available_skills(skills_dir: Path | None = None) -> list[str]:
    """Return sorted skill names available in `skills_dir`."""
    return [str(s["name"]) for s in list_bundled_skills(skills_dir)]


def _resolve_mcp_config_paths(
    target: str,
    dest: Path | None,
    global_install: bool,
) -> list[Path]:
    """Resolve MCP client configuration file paths for `install_mcp_config`."""
    if global_install:
        home = Path.home()
        if target == "claude":
            return [home / ".claude.json"]
        if target == "agents":
            return [home / ".gemini" / "settings.json"]
        if target == "all":
            return [
                home / ".claude.json",
                home / ".gemini" / "settings.json",
            ]
        return [Path(target).expanduser() / ".mcp.json"]

    base_dir = dest.expanduser() if dest is not None else Path.cwd()
    if target in ("agents", "claude", "all"):
        return [base_dir / ".mcp.json"]
    custom = Path(target).expanduser()
    if custom.suffix == ".json":
        return [custom]
    return [custom / ".mcp.json"]


def install_mcp_config(
    target: str = "agents",
    dest: Path | None = None,
    global_install: bool = False,
    command: str = "bigquery-data-science",
) -> list[Path]:
    """Non-destructively register the `bigquery-data-science mcp` stdio server."""
    config_paths = _resolve_mcp_config_paths(
        target=target,
        dest=dest,
        global_install=global_install,
    )
    updated: list[Path] = []
    for cfg_path in config_paths:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {}
        if cfg_path.is_file():
            try:
                loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    payload = loaded
            except (OSError, json.JSONDecodeError):
                payload = {}

        raw_servers = payload.get("mcpServers")
        servers: dict[str, object] = (
            dict(raw_servers) if isinstance(raw_servers, dict) else {}
        )
        servers["bigquery-data-science"] = {
            "command": command,
            "args": ["mcp"],
        }
        payload["mcpServers"] = servers
        cfg_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        updated.append(cfg_path)
    return updated

