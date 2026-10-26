"""Unified CLI for `bigquery-data-science` user commands and maintainer tooling."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from bigquery_data_science import __version__
from bigquery_data_science.catalog import (
    lookup_symbol,
    review_sql,
    search_catalog,
    triage_task,
)
from bigquery_data_science.installer import (
    DEFAULT_KERNEL_DISPLAY_NAME,
    DEFAULT_KERNEL_NAME,
    get_skill_path,
    get_skills_dir,
    install_kernel,
    install_mcp_config,
    install_skills,
    list_bundled_skills,
)
from bigquery_data_science.mcp_server import serve_stdio
from bigquery_data_science.tooling.bump_version import (
    bump_version,
    check_version_lockstep,
)
from bigquery_data_science.tooling.convert_notebook import (
    convert_notebook,
    convert_notebook_to_file,
)
from bigquery_data_science.tooling.crossrefs import check_crossrefs
from bigquery_data_science.tooling.link_policy import check_project
from bigquery_data_science.tooling.manifest import (
    check_all_manifests,
    source_projects,
    write_manifest,
)
from bigquery_data_science.tooling.markdown_check import check_markdown_files
from bigquery_data_science.tooling.narrative_drift import (
    check_all_narratives,
    sync_all_narratives,
)
from bigquery_data_science.tooling.notebook_claims import check_notebook_claims
from bigquery_data_science.tooling.pinned_models import (
    check_pinned_models,
    find_allow_file,
    load_allow_list,
)
from bigquery_data_science.tooling.reference_structure import check_reference
from bigquery_data_science.tooling.run_notebook import (
    DEFAULT_CELL_TIMEOUT_SECONDS,
    execute_notebook,
)
from bigquery_data_science.tooling.sql_companions import check_sql_companions
from bigquery_data_science.tooling.status_labels import check_status_labels
from bigquery_data_science.tooling.sync_syntax import (
    check_syntax_sync,
    sync_all_syntax,
)
from bigquery_data_science.tooling.validate import (
    ValidationResult,
    validate_all,
    validate_skill,
)


def _cmd_list(args: argparse.Namespace) -> int:
    skills = list_bundled_skills()
    if getattr(args, "as_json", False):
        print(json.dumps(skills, indent=2))
        return 0
    for info in skills:
        print(
            f"{info['name']} (v{info['version']}) — "
            f"refs: {info['reference_count']}, "
            f"syntax: {info['syntax_count']}, "
            f"narratives: {info['narrative_count']}\n"
            f"  {info['description']}"
        )
    return 0


def _cmd_path(args: argparse.Namespace) -> int:
    try:
        resolved = get_skill_path(args.skill)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(resolved)
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    target = "all" if args.target == "both" else str(args.target)
    dest_str = args.dest or args.project_dir
    dest = Path(dest_str) if dest_str else None
    global_install = bool(args.global_install or args.scope == "user")
    installed = install_skills(
        target=target,
        dest=dest,
        global_install=global_install,
        symlink=bool(args.symlink),
    )
    mode = "symlinked" if args.symlink else "copied"
    for item in installed:
        print(f"{mode}: {item}")
    if getattr(args, "mcp", False):
        mcp_paths = install_mcp_config(
            target=target,
            dest=dest,
            global_install=global_install,
        )
        for cfg_path in mcp_paths:
            print(f"registered mcp: {cfg_path}")
    return 0


def _cmd_kernel(args: argparse.Namespace) -> int:
    user_flag = not bool(args.sys_prefix)
    return install_kernel(
        user=user_flag,
        name=str(args.name),
        display_name=str(args.display_name),
    )


def _cmd_lookup(args: argparse.Namespace) -> int:
    result = lookup_symbol(str(args.symbol))
    if getattr(args, "as_json", False):
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.format_text())
    return 0 if result.found else 1


def _cmd_search(args: argparse.Namespace) -> int:
    hits = search_catalog(
        query=str(args.query),
        skill_filter=args.skill,
        lens_filter=args.lens,
        limit=int(args.limit),
    )
    if getattr(args, "as_json", False):
        print(json.dumps([hit.to_dict() for hit in hits], indent=2))
        return 0
    if not hits:
        print(f"No matches found for '{args.query}'.")
        return 0
    for hit in hits:
        print(hit.format_text())
        print()
    return 0


def _cmd_triage(args: argparse.Namespace) -> int:
    result = triage_task(str(args.query))
    if getattr(args, "as_json", False):
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.format_text())
    return 0


def _cmd_review_sql(args: argparse.Namespace) -> int:
    raw = str(args.sql).strip()
    sql_text = raw
    try:
        candidate = Path(raw)
        if candidate.is_file():
            sql_text = candidate.read_text(encoding="utf-8")
        elif raw.lower().endswith(".sql") and " " not in raw:
            print(f"ERROR: SQL file not found: {raw}", file=sys.stderr)
            return 1
    except OSError:
        pass
    result = review_sql(sql_text)
    if getattr(args, "as_json", False):
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.format_text())
    return 0 if result.ok else 1


def _cmd_mcp(_args: argparse.Namespace) -> int:
    return serve_stdio()


def _print_validation_result(name: str, res: ValidationResult) -> None:
    status = "OK" if res.ok else "FAIL"
    print(f"[{status}] {name}")
    for warning in res.warnings:
        print(f"  WARN: {warning}")
    for error in res.errors:
        print(f"  ERR:  {error}", file=sys.stderr)


def _cmd_validate(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if not target.exists():
        target = get_skills_dir()
    if args.all or not (target / "SKILL.md").is_file():
        results = validate_all(target)
        for name, res in results.items():
            _print_validation_result(name, res)
        return 0 if all(r.ok for r in results.values()) else 1
    res = validate_skill(target)
    _print_validation_result(target.name, res)
    return 0 if res.ok else 1


def _cmd_sync_syntax(args: argparse.Namespace) -> int:
    skills_root = Path(args.skills_root)
    repo_root = Path(args.repo_root)
    if args.check:
        errors = check_syntax_sync(
            skills_root=skills_root,
            repo_root=repo_root,
            skill_name=args.skill,
        )
        if errors:
            for err in errors:
                print(f"FAIL: {err}", file=sys.stderr)
            return 1
        print("OK: all syntax cards in sync")
        return 0

    written = sync_all_syntax(
        skills_root=skills_root,
        repo_root=repo_root,
        skill_name=args.skill,
    )
    for skill_name, paths in written.items():
        print(f"Synced {len(paths)} file(s) in {skill_name}/syntax/")
    return 0


def _cmd_check_syntax_sync(args: argparse.Namespace) -> int:
    errors = check_syntax_sync(
        skills_root=Path(args.skills_root),
        repo_root=Path(args.repo_root),
        skill_name=args.skill,
    )
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: all syntax cards in sync")
    return 0


def _infer_subproject_root(notebook_path: Path) -> Path:
    resolved = notebook_path.resolve()
    for parent in resolved.parents:
        if parent.name in ("bigquery-ml", "bigquery-ai"):
            return parent
    return resolved.parent


def _cmd_convert_notebook(args: argparse.Namespace) -> int:
    nb_path = Path(args.notebook).resolve()
    subproject_root = (
        Path(args.subproject_root).resolve()
        if args.subproject_root
        else _infer_subproject_root(nb_path)
    )
    if args.output:
        out_path = Path(args.output)
        convert_notebook_to_file(nb_path, subproject_root, out_path)
        print(f"Wrote {out_path}")
    else:
        print(convert_notebook(nb_path, subproject_root))
    return 0


def _cmd_check_narratives(args: argparse.Namespace) -> int:
    skills_root = Path(args.skills_root)
    repo_root = Path(args.repo_root)
    if getattr(args, "fix", False):
        count = sync_all_narratives(skills_root, repo_root)
        print(f"Synced {count} narrative file(s)")
        return 0
    results = check_all_narratives(skills_root, repo_root)
    any_failed = False
    for name, res in results.items():
        status = "OK" if res.ok else "FAIL"
        print(f"[{status}] {name} ({res.checked} narratives checked)")
        for missing in res.missing_source:
            print(f"  MISSING: {missing}", file=sys.stderr)
        for stale in res.stale:
            print(f"  STALE:   {stale}", file=sys.stderr)
        if not res.ok:
            any_failed = True
    return 1 if any_failed else 0


def _cmd_sync_narratives(args: argparse.Namespace) -> int:
    count = sync_all_narratives(Path(args.skills_root), Path(args.repo_root))
    print(f"Synced {count} narrative file(s)")
    return 0


def _cmd_check_links(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    raw_sub = Path(args.subproject)
    subproject = (
        raw_sub.resolve()
        if raw_sub.exists()
        else (repo_root / raw_sub).resolve()
    )
    siblings: list[Path] = []
    for sib in args.sibling or []:
        sib_path = Path(sib)
        siblings.append(
            sib_path.resolve()
            if sib_path.exists()
            else (repo_root / sib_path).resolve()
        )
    res = check_project(subproject, siblings, repo_root)
    status = "OK" if res.ok else "FAIL"
    print(f"[{status}] {subproject.name} ({res.scanned} files scanned)")
    for violation in res.violations:
        print(f"  VIOLATION: {violation.format(subproject)}", file=sys.stderr)
    return 0 if res.ok else 1


def _cmd_check_reference(args: argparse.Namespace) -> int:
    subproject = Path(args.subproject).resolve()
    res = check_reference(subproject)
    status = "OK" if res.ok else "FAIL"
    print(f"[{status}] {subproject.name}/reference ({res.checked} files)")
    for error in res.errors:
        print(f"  ERR: {error}", file=sys.stderr)
    return 0 if res.ok else 1


def _cmd_check_pinned_models(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    raw_sub = Path(args.subproject)
    subproject = (
        raw_sub.resolve()
        if raw_sub.exists()
        else (repo_root / raw_sub).resolve()
    )
    if args.allow_file:
        allow_file = Path(args.allow_file)
        if not allow_file.is_absolute() and not allow_file.exists():
            allow_file = repo_root / allow_file
    else:
        allow_file = find_allow_file(repo_root / "skills") or (
            repo_root / "skills" / "pinned-models.json"
        )
    allowed = load_allow_list(allow_file, subproject, repo_root)
    res = check_pinned_models(subproject, allowed)
    status = "OK" if res.ok else "FAIL"
    print(f"[{status}] {subproject.name} ({len(res.pins)} model pins checked)")
    for pin in res.unlisted:
        print(f"  UNLISTED: {pin.format(subproject)}", file=sys.stderr)
    return 0 if res.ok else 1


def _cmd_manifest(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if args.check:
        errors = check_all_manifests(target)
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1 if errors else 0

    if (target / "SKILL.md").is_file() and not args.all:
        manifest_path, ver = write_manifest(
            target,
            version=args.version,
            source_project=args.source_project,
        )
        print(f"Wrote {manifest_path} (v{ver})")
        return 0

    for skill_dir in sorted(p for p in target.iterdir() if p.is_dir()):
        if (skill_dir / "SKILL.md").is_file():
            manifest_path, ver = write_manifest(
                skill_dir,
                version=args.version,
                source_project=args.source_project,
            )
            print(f"Wrote {manifest_path} (v{ver})")
    return 0


def _cmd_bump_version(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    if args.check:
        try:
            errors = check_version_lockstep(
                repo_root=repo_root,
                expected_version=args.version,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        if errors:
            for err in errors:
                print(f"FAIL: {err}", file=sys.stderr)
            return 1
        print("OK: all version locations in lockstep")
        return 0

    if not args.version:
        print(
            "ERROR: version argument is required unless --check is passed.",
            file=sys.stderr,
        )
        return 1

    try:
        updated = bump_version(
            repo_root=repo_root,
            new_version=str(args.version),
            release_date=args.date,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for path in updated:
        rel = path.relative_to(repo_root) if path.is_relative_to(repo_root) else path
        print(f"Updated {rel}")
    print(f"OK: stamped version {args.version} across {len(updated)} file(s)")
    return 0


def _cmd_check_status_labels(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_root = Path(args.skills_root).resolve()
    errors = check_status_labels(repo_root=repo_root, skills_root=skills_root)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: all Preview/GA status labels in sync")
    return 0


def _cmd_check_crossrefs(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    errors = check_crossrefs(repo_root=repo_root)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: all workflow <-> function/model cross-references in sync")
    return 0


def _cmd_run_notebook(args: argparse.Namespace) -> int:
    nb_path = Path(args.notebook).resolve()
    repo_root = Path(args.repo_root).resolve()
    skills_root = Path(args.skills_root).resolve()
    try:
        res = execute_notebook(
            notebook_path=nb_path,
            kernel_name=str(args.kernel),
            timeout_seconds=int(args.timeout),
            allow_errors=bool(args.allow_errors),
            sync_narratives=bool(args.sync_narratives),
            repo_root=repo_root,
            skills_root=skills_root,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    status = "OK" if res.ok else "FAIL"
    print(
        f"[{status}] {res.notebook_path.name} "
        f"({res.executed_cells} code cells executed)"
    )
    for cell_idx, ename, evalue in res.error_cells:
        print(
            f"  ERR (cell {cell_idx}): {ename}: {evalue}",
            file=sys.stderr,
        )
    if res.synced_narratives:
        print(f"  Synced {res.synced_narratives} narrative file(s)")
    return 0 if (res.ok or args.allow_errors) else 1


def _cmd_check_notebook_claims(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    repo_root = Path(args.repo_root).resolve()
    errors = check_notebook_claims(target=target, repo_root=repo_root)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: all high-precision notebook prose claims verified against outputs")
    return 0


def _cmd_check_markdown(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    errors = check_markdown_files(repo_root=repo_root)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: all Markdown fences, GFM tables, and vertical Mermaid diagrams valid")
    return 0


def _cmd_check_sql_companions(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_root = Path(args.skills_root).resolve()
    errors = check_sql_companions(repo_root=repo_root, skills_root=skills_root)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: all .ipynb -> .sql companions in sync and passed static SQL review")
    return 0


def _cmd_sweep(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    skills_root_arg = str(
        getattr(args, "skills_root_opt", None)
        or getattr(args, "skills_root", "skills")
    )
    skills_root = Path(skills_root_arg).resolve()
    failed = False

    print("1. Validating skills (SKILL.md, reference/, syntax/ < 25 KB, narrative/)...")
    val_results = validate_all(skills_root)
    for name, vres in val_results.items():
        _print_validation_result(name, vres)
        if not vres.ok:
            failed = True

    print("2. Checking skill manifests and lockstep version parity...")
    manifest_errors = check_all_manifests(skills_root)
    if (repo_root / "pyproject.toml").is_file():
        manifest_errors.extend(check_version_lockstep(repo_root))
    for err in manifest_errors:
        print(f"  ERR: {err}", file=sys.stderr)
        failed = True
    if not manifest_errors:
        print("  [OK] all skill.manifest.json and version lockstep files in sync")

    print("3. Checking Lens 3 syntax card synchronization...")
    syn_errors = check_syntax_sync(skills_root=skills_root, repo_root=repo_root)
    for err in syn_errors:
        print(f"  ERR: {err}", file=sys.stderr)
        failed = True
    if not syn_errors:
        print("  [OK] all 137 syntax cards in sync")

    print("4. Checking Lens 4 narrative drift against source notebooks...")
    nar_results = check_all_narratives(skills_root, repo_root)
    for name, nres in nar_results.items():
        status = "OK" if nres.ok else "FAIL"
        print(f"  [{status}] {name} ({nres.checked} narratives)")
        if not nres.ok:
            failed = True

    projects = source_projects(skills_root) or ["bigquery-ml", "bigquery-ai"]
    project_paths = [repo_root / p for p in projects if (repo_root / p).is_dir()]

    print("5. Checking domain reference structure, link policy, and pinned models...")
    allow_file = find_allow_file(skills_root) or (skills_root / "pinned-models.json")
    for proj_path in project_paths:
        ref_res = check_reference(proj_path)
        if not ref_res.ok:
            for error in ref_res.errors:
                print(f"  ERR ({proj_path.name}): {error}", file=sys.stderr)
            failed = True
        else:
            print(f"  [OK] {proj_path.name} reference structure")

        siblings = [p for p in project_paths if p != proj_path]
        link_res = check_project(proj_path, siblings, repo_root)
        if not link_res.ok:
            for violation in link_res.violations:
                print(
                    f"  VIOLATION ({proj_path.name}): {violation.format(proj_path)}",
                    file=sys.stderr,
                )
            failed = True
        else:
            print(f"  [OK] {proj_path.name} links ({link_res.scanned} files scanned)")

        if allow_file.is_file():
            allowed = load_allow_list(allow_file, proj_path, repo_root)
            pin_res = check_pinned_models(proj_path, allowed)
            if not pin_res.ok:
                for pin in pin_res.unlisted:
                    print(
                        f"  UNLISTED ({proj_path.name}): {pin.format(proj_path)}",
                        file=sys.stderr,
                    )
                failed = True
            else:
                print(
                    f"  [OK] {proj_path.name} pinned models ({len(pin_res.pins)} checked)"
                )

    sync_headers_script = repo_root / "architectures" / "headers" / "sync_headers.py"
    if sync_headers_script.is_file():
        print("6. Checking notebook and markdown headers (sync_headers.py --check)...")
        proc = subprocess.run(
            [sys.executable, str(sync_headers_script), "--check"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(proc.stdout, file=sys.stderr)
            print(proc.stderr, file=sys.stderr)
            failed = True
        else:
            print("  [OK] sync_headers.py --check passed")

    if len(project_paths) == 2:
        print(
            "7. Checking status labels, cross-references, numeric claims, and Markdown/Mermaid..."
        )
        status_errors = check_status_labels(repo_root=repo_root, skills_root=skills_root)
        for err in status_errors:
            print(f"  ERR (status-labels): {err}", file=sys.stderr)
            failed = True
        if not status_errors:
            print("  [OK] Preview vs GA status labels consistent")

        xref_errors = check_crossrefs(repo_root=repo_root)
        for err in xref_errors:
            print(f"  ERR (crossrefs): {err}", file=sys.stderr)
            failed = True
        if not xref_errors:
            print("  [OK] bidirectional notebook cross-references verified")

        claim_errors = check_notebook_claims(target=repo_root, repo_root=repo_root)
        for err in claim_errors:
            print(f"  ERR (notebook-claims): {err}", file=sys.stderr)
            failed = True
        if not claim_errors:
            print("  [OK] high-precision notebook prose claims verified")

        md_errors = check_markdown_files(repo_root=repo_root)
        for err in md_errors:
            print(f"  ERR (markdown): {err}", file=sys.stderr)
            failed = True
        if not md_errors:
            print("  [OK] Markdown fences, GFM tables, and vertical Mermaid diagrams valid")

        sql_comp_errors = check_sql_companions(
            repo_root=repo_root,
            skills_root=skills_root,
        )
        for err in sql_comp_errors:
            print(f"  ERR (sql-companions): {err}", file=sys.stderr)
            failed = True
        if not sql_comp_errors:
            print(
                "  [OK] .ipynb -> .sql companions in sync and passed static SQL review"
            )

    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level `bigquery-data-science` CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="bigquery-data-science",
        description=(
            "BigQuery Data Science Agent Skills installer, offline lookup/triage "
            "CLI, stdio MCP server, and maintainer verification suite."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List bundled skills and file counts.")
    p_list.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit structured JSON output.",
    )
    p_list.set_defaults(func=_cmd_list)

    p_path = sub.add_parser("path", help="Print path to skills/ or a specific skill.")
    p_path.add_argument("skill", nargs="?", default=None, help="Optional skill name.")
    p_path.set_defaults(func=_cmd_path)

    p_install = sub.add_parser(
        "install",
        help="Install skills into .agents/skills, .claude/skills, or a custom directory.",
    )
    p_install.add_argument(
        "--target",
        default="agents",
        help="Target harness ('agents', 'claude', 'all', 'both', or custom path).",
    )
    p_install.add_argument(
        "--dest",
        default=None,
        help="Destination workspace root directory (defaults to current directory).",
    )
    p_install.add_argument(
        "--project-dir",
        dest="project_dir",
        default=None,
        help="Alias for --dest.",
    )
    p_install.add_argument(
        "--global",
        dest="global_install",
        action="store_true",
        help="Install into the user home directory (~/.agents/skills or ~/.claude/skills).",
    )
    p_install.add_argument(
        "--scope",
        choices=("project", "user"),
        default="project",
        help="Installation scope ('project' or 'user').",
    )
    p_install.add_argument(
        "--symlink",
        action="store_true",
        help="Create relative symlinks instead of copying skill directories.",
    )
    p_install.add_argument(
        "--copy",
        action="store_true",
        help="Copy skill directories (default behavior).",
    )
    p_install.add_argument(
        "--mcp",
        action="store_true",
        help="Also register the bigquery-data-science stdio MCP server in client config.",
    )
    p_install.set_defaults(func=_cmd_install)

    p_kernel = sub.add_parser(
        "kernel",
        help="Register the unified 'bigquery-data-science' Jupyter kernelspec.",
    )
    p_kernel.add_argument(
        "--user",
        action="store_true",
        default=True,
        help="Install into the user Jupyter kernels directory (default).",
    )
    p_kernel.add_argument(
        "--sys-prefix",
        action="store_true",
        help="Install into sys.prefix instead of user home.",
    )
    p_kernel.add_argument(
        "--name",
        default=DEFAULT_KERNEL_NAME,
        help=f"Kernelspec name (default: {DEFAULT_KERNEL_NAME}).",
    )
    p_kernel.add_argument(
        "--display-name",
        default=DEFAULT_KERNEL_DISPLAY_NAME,
        help=f"Kernelspec display name (default: {DEFAULT_KERNEL_DISPLAY_NAME!r}).",
    )
    p_kernel.set_defaults(func=_cmd_kernel)

    p_lookup = sub.add_parser(
        "lookup",
        help="Look up syntax card, prerequisites, gotchas, and narratives for a symbol.",
    )
    p_lookup.add_argument("symbol", help="Model type or SQL function (e.g. ARIMA_PLUS).")
    p_lookup.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit structured JSON output.",
    )
    p_lookup.set_defaults(func=_cmd_lookup)

    p_search = sub.add_parser(
        "search",
        help="Search across all 4 skills and 4 progressive lenses.",
    )
    p_search.add_argument("query", help="Search keywords or phrase.")
    p_search.add_argument("--skill", default=None, help="Optional skill filter.")
    p_search.add_argument("--lens", default=None, help="Optional lens filter.")
    p_search.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum results to return (default: 10).",
    )
    p_search.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit structured JSON output.",
    )
    p_search.set_defaults(func=_cmd_search)

    p_triage = sub.add_parser(
        "triage",
        help="Arbitrate between BigQuery ML and BigQuery AI for a task.",
    )
    p_triage.add_argument("query", help="Task description (e.g. 'forecast daily sales').")
    p_triage.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit structured JSON output.",
    )
    p_triage.set_defaults(func=_cmd_triage)

    p_rev = sub.add_parser(
        "review-sql",
        help="Statically audit a BigQuery SQL query or .sql file for prerequisites and gotchas.",
    )
    p_rev.add_argument("sql", help="GoogleSQL query string or path to a .sql file.")
    p_rev.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit structured JSON output.",
    )
    p_rev.set_defaults(func=_cmd_review_sql)

    p_mcp = sub.add_parser("mcp", help="Run the zero-dependency stdio MCP server.")
    p_mcp.set_defaults(func=_cmd_mcp)

    p_validate = sub.add_parser("validate", help="Validate skill directory structure.")
    p_validate.add_argument(
        "path",
        nargs="?",
        default="skills",
        help="Skill directory or skills root (default: skills).",
    )
    p_validate.add_argument(
        "--all",
        action="store_true",
        help="Validate all skill subdirectories under path.",
    )
    p_validate.set_defaults(func=_cmd_validate)

    p_sync_syn = sub.add_parser(
        "sync-syntax",
        help="Slice domain reference/*.md by H2 into skills/<domain>/syntax/*.md.",
    )
    p_sync_syn.add_argument(
        "skills_root",
        nargs="?",
        default="skills",
        help="Skills root directory (default: skills).",
    )
    p_sync_syn.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_sync_syn.add_argument("--skill", default=None, help="Optional single skill name.")
    p_sync_syn.add_argument(
        "--check",
        action="store_true",
        help="Check syntax synchronization without modifying files.",
    )
    p_sync_syn.set_defaults(func=_cmd_sync_syntax)

    p_chk_syn = sub.add_parser(
        "check-syntax-sync",
        help="Verify that skills/*/syntax/*.md match domain reference/*.md.",
    )
    p_chk_syn.add_argument(
        "skills_root",
        nargs="?",
        default="skills",
        help="Skills root directory (default: skills).",
    )
    p_chk_syn.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_chk_syn.add_argument("--skill", default=None, help="Optional single skill name.")
    p_chk_syn.set_defaults(func=_cmd_check_syntax_sync)

    p_conv = sub.add_parser(
        "convert-notebook",
        help="Convert a source .ipynb notebook into a Lens 4 narrative markdown file.",
    )
    p_conv.add_argument("notebook", help="Path to source .ipynb file.")
    p_conv.add_argument(
        "--subproject-root",
        default=None,
        help="Domain subproject root (e.g. bigquery-ml or bigquery-ai).",
    )
    p_conv.add_argument(
        "-o",
        "--output",
        default=None,
        help="Optional output markdown file path (writes to stdout if omitted).",
    )
    p_conv.set_defaults(func=_cmd_convert_notebook)

    p_chk_nar = sub.add_parser(
        "check-narratives",
        help="Verify that skills/*/narrative/*.md match source notebooks.",
    )
    p_chk_nar.add_argument(
        "skills_root",
        nargs="?",
        default="skills",
        help="Skills root directory (default: skills).",
    )
    p_chk_nar.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_chk_nar.add_argument(
        "--fix",
        action="store_true",
        help="Regenerate stale narrative files in place.",
    )
    p_chk_nar.set_defaults(func=_cmd_check_narratives)

    p_sync_nar = sub.add_parser(
        "sync-narratives",
        help="Regenerate all skills/*/narrative/*.md files from source notebooks.",
    )
    p_sync_nar.add_argument(
        "skills_root",
        nargs="?",
        default="skills",
        help="Skills root directory (default: skills).",
    )
    p_sync_nar.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_sync_nar.set_defaults(func=_cmd_sync_narratives)

    p_links = sub.add_parser(
        "check-links",
        help="Verify relative links and #anchors inside a subproject.",
    )
    p_links.add_argument("subproject", help="Subproject path (e.g. bigquery-ml).")
    p_links.add_argument(
        "--sibling",
        action="append",
        default=[],
        help="Allowed sibling subproject path (repeatable).",
    )
    p_links.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_links.set_defaults(func=_cmd_check_links)

    p_ref = sub.add_parser(
        "check-reference",
        help="Verify 1:1 RESOURCES.md <-> reference/*.md coverage and heading depth.",
    )
    p_ref.add_argument("subproject", help="Subproject path (e.g. bigquery-ml).")
    p_ref.set_defaults(func=_cmd_check_reference)

    p_pin = sub.add_parser(
        "check-pinned-models",
        help="Verify all model/endpoint references against pinned-models.json.",
    )
    p_pin.add_argument("subproject", help="Subproject path (e.g. bigquery-ml).")
    p_pin.add_argument(
        "--allow-file",
        default=None,
        help="Path to pinned-models.json allowlist.",
    )
    p_pin.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_pin.set_defaults(func=_cmd_check_pinned_models)

    p_mf = sub.add_parser(
        "manifest",
        help="Generate or verify skill.manifest.json files.",
    )
    p_mf.add_argument(
        "path",
        nargs="?",
        default="skills",
        help="Skill directory or skills root (default: skills).",
    )
    p_mf.add_argument(
        "--all",
        action="store_true",
        help="Update all skill subdirectories under path.",
    )
    p_mf.add_argument("--version", default=None, help="Explicit version string.")
    p_mf.add_argument(
        "--source-project",
        default=None,
        help="Explicit source_project name.",
    )
    p_mf.add_argument(
        "--check",
        action="store_true",
        help="Verify manifests without writing.",
    )
    p_mf.set_defaults(func=_cmd_manifest)

    p_bump = sub.add_parser(
        "bump-version",
        help="Stamp or verify lockstep Semantic Version across package, plugin, and skill files.",
    )
    p_bump.add_argument(
        "version",
        nargs="?",
        default=None,
        help="Target Semantic Version string (e.g. '0.8.1'). Optional when --check is passed.",
    )
    p_bump.add_argument(
        "--check",
        action="store_true",
        help="Verify lockstep version parity across all files without writing.",
    )
    p_bump.add_argument(
        "--date",
        default=None,
        help="Release date string (YYYY-MM-DD) for CITATION.cff (defaults to today).",
    )
    p_bump.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_bump.set_defaults(func=_cmd_bump_version)

    p_stat = sub.add_parser(
        "check-status-labels",
        help=(
            "Verify Preview vs GA status label consistency across READMEs, "
            "references, and skills."
        ),
    )
    p_stat.add_argument(
        "skills_root",
        nargs="?",
        default="skills",
        help="Skills root directory (default: skills).",
    )
    p_stat.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_stat.set_defaults(func=_cmd_check_status_labels)

    p_xref = sub.add_parser(
        "check-crossrefs",
        help="Verify bidirectional Functions/Models used <-> Featured in notebook links.",
    )
    p_xref.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_xref.set_defaults(func=_cmd_check_crossrefs)

    p_run_nb = sub.add_parser(
        "run-notebook",
        help="Execute a Jupyter notebook headlessly with cwd and mTLS environment configured.",
    )
    p_run_nb.add_argument("notebook", help="Path to the .ipynb file to execute.")
    p_run_nb.add_argument(
        "--kernel",
        default=DEFAULT_KERNEL_NAME,
        help=f"Jupyter kernel name (default: {DEFAULT_KERNEL_NAME}).",
    )
    p_run_nb.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_CELL_TIMEOUT_SECONDS,
        help=f"Per-cell timeout in seconds (default: {DEFAULT_CELL_TIMEOUT_SECONDS}).",
    )
    p_run_nb.add_argument(
        "--allow-errors",
        action="store_true",
        help="Continue executing remaining cells when a cell raises an error.",
    )
    p_run_nb.add_argument(
        "--sync-narratives",
        action="store_true",
        help="Regenerate skills/*/narrative/*.md after successful execution.",
    )
    p_run_nb.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_run_nb.add_argument(
        "--skills-root",
        default="skills",
        help="Skills root directory (default: skills).",
    )
    p_run_nb.set_defaults(func=_cmd_run_notebook)

    p_claims = sub.add_parser(
        "check-notebook-claims",
        help="Audit high-precision decimal claims in notebook prose against cell outputs.",
    )
    p_claims.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Notebook path or directory root to audit (default: .).",
    )
    p_claims.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_claims.set_defaults(func=_cmd_check_notebook_claims)

    p_md = sub.add_parser(
        "check-markdown",
        help="Verify code fences, GFM table compilation, and vertical-first Mermaid layout.",
    )
    p_md.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_md.set_defaults(func=_cmd_check_markdown)

    p_sql_comp = sub.add_parser(
        "check-sql-companions",
        help=(
            "Verify .ipynb -> .sql companion coverage and run review-sql across "
            "all .sql files."
        ),
    )
    p_sql_comp.add_argument(
        "skills_root",
        nargs="?",
        default="skills",
        help="Skills root directory (default: skills).",
    )
    p_sql_comp.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_sql_comp.set_defaults(func=_cmd_check_sql_companions)

    p_sweep = sub.add_parser(
        "sweep",
        help="Run the complete maintainer verification gate across the repository.",
    )
    p_sweep.add_argument(
        "skills_root",
        nargs="?",
        default="skills",
        help="Skills root directory (default: skills).",
    )
    p_sweep.add_argument(
        "--skills-root",
        dest="skills_root_opt",
        default=None,
        help="Optional override for skills root directory.",
    )
    p_sweep.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .).",
    )
    p_sweep.set_defaults(func=_cmd_sweep)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point returning POSIX exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return 1
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
