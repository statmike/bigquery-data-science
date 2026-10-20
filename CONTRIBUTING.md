# Contributing to `bigquery-data-science`

Thank you for your interest in contributing to `bigquery-data-science`. This repository unifies **104 live-executed BigQuery ML and BigQuery AI notebooks and SQL scripts**, **4-Lens Agent Skills** (`skills/`), and the **zero-dependency `bigquery-data-science` Python CLI and stdio MCP server** (`src/bigquery_data_science/`).

Issues and pull requests for bug fixes, documentation improvements, release-note updates, and workflow enhancements are welcome.

## Before You Open a Pull Request

- **Small fixes (typos, broken links, option updates):** Open a pull request directly with a clear description of the fix.
- **New notebooks, workflows, or skill restructuring:** Open an [issue](https://github.com/statmike/bigquery-data-science/issues) first to discuss scope and placement.
- Review [`skills/PLANS.md`](skills/PLANS.md), [`bigquery-ml/PLANS.md`](bigquery-ml/PLANS.md), and [`bigquery-ai/PLANS.md`](bigquery-ai/PLANS.md) for the authoring conventions and monthly BigQuery release-notes audit procedure.

## The Verification Gate

Run the full verification suite from the repository root before submitting a pull request (this is the exact gate that `.github/workflows/ci.yml` runs across Python 3.11, 3.12, and 3.13):

```bash
uv run ruff check src tests && \
  uv run mypy src && \
  uv run pytest -q && \
  uv run bigquery-data-science sweep && \
  python3 architectures/headers/sync_headers.py --check && \
  ./scripts/check_install.sh
```

- **Linted & Typed:** `ruff check src tests` and `mypy src` (strict mode) must exit with zero errors.
- **Tested:** `uv run pytest -q` runs the offline unit test suite covering version parity, README link rewriting, `uv.lock` public index hygiene, the skill installer, catalog `lookup`/`search`/`triage`, the stdio MCP server, and all maintainer tooling checks.
- **Skills & Reference Sweep:** `uv run bigquery-data-science sweep` validates all 3 skills (`validate --all`), markdown links and `#anchors` (`check-links`), `RESOURCES.md` coverage (`check-reference`), H2-sliced syntax cards (`check-syntax-sync`), model version pins (`check-pinned-models`), and extracted notebook narratives (`check-narratives`).
- **Headers:** `python3 architectures/headers/sync_headers.py --check` verifies all 104 notebooks and 19 domain markdown files carry current `statmike/bigquery-data-science` headers.
- **Cold-Install Smoke Gate:** `./scripts/check_install.sh` builds the wheel and sdist via `uv build`, verifies the wheel is `< 1.5 MB` with zero `.ipynb` files, installs it into an isolated virtualenv, and exercises the CLI and stdio MCP server.
- **Optional Local Pre-Commit Hooks:** Run `uv run pre-commit install` once after cloning to run `ruff check`, `mypy`, and `bigquery-data-science sweep` automatically on `git commit` (configured in [`.pre-commit-config.yaml`](.pre-commit-config.yaml)).

## Public-Repository & Credential Hygiene

Every contribution must follow these security and privacy rules:

- **Application Default Credentials (ADC) only:** Never load or commit service account JSON key files (`*-key.json`, `*.json.key`, `service-account*.json`). Notebooks and scripts authenticate exclusively via Application Default Credentials (`gcloud auth application-default login` locally or attached service accounts in Google Cloud runtimes).
- **Zero proprietary or customer data:** Never include customer names, internal hostnames, credentials, or hardcoded live personal/internal GCP project IDs in tracked code or configs.
- **Self-contained, reproducible workflows:** Notebooks rely on public datasets (`bigquery-public-data.*`), synthetic data generated in-notebook, or resources created by the workflow's own setup steps.

## Releasing

Releases are published to TestPyPI and PyPI via GitHub Actions OIDC Trusted Publishing ([`.github/workflows/release.yml`](.github/workflows/release.yml)) whenever a `v*` tag is pushed.

### Semantic Versioning (`X.Y.Z`)

- **Major (`X.0.0`) — Skills architecture, names & structural contract shifts:**
  - Changes in skills layout, naming, or hierarchy (`skills/`), packaging changes, or removing/incompatibly changing CLI subcommands, MCP tool schemas, or Python library public exports.
- **Minor (`X.Y.0`) — Multi-area monthly sweeps & capability rollouts:**
  - Multi-area updates spanning monthly upstream sweeps: adding new notebooks, workflows, foundation models, options, and synchronized 4-lens skill updates.
- **Patch (`X.Y.Z`) — Targeted single-area updates & fixes:**
  - Targeted single-area updates, isolated bug fixes, typo fixes, or individual notebook adjustments.

### 1. Version Bump & Changelog Lockstep

Update the version string across all 7 single-sourced locations (enforced by `tests/test_packaging.py`):
1. `pyproject.toml` (`[project].version`)
2. `src/bigquery_data_science/__init__.py` (`PackageNotFoundError` fallback literal)
3. `plugin.json` (`"version"`)
4. `.claude-plugin/marketplace.json` (`"version"`, `metadata.version`, and each entry in `"plugins"`)
5. `CITATION.cff` (`version` and `date-released`)
6. `CHANGELOG.md` (`## [X.Y.Z] - YYYY-MM-DD` section)
7. `skills/{bigquery-data-science,bigquery-ml,bigquery-ai}/skill.manifest.json` (`"version"`, regenerated via `uv run bigquery-data-science manifest --version X.Y.Z`)

Then re-lock with `UV_NO_CONFIG=1 uv lock` and run the full verification gate above.

### 2. Pre-Release Verification on TestPyPI (`vX.Y.Zrc1`)

1. Push an annotated release-candidate tag on `main`:
   ```bash
   git tag -a vX.Y.Zrc1 -m "Release candidate vX.Y.Zrc1"
   git push origin vX.Y.Zrc1
   ```
2. `.github/workflows/release.yml` verifies `vX.Y.Zrc1` matches `pyproject.toml` base version `X.Y.Z`, dynamically stamps `X.Y.Zrc1` in the build runner, and publishes to TestPyPI (`testpypi` environment).
3. Verify the TestPyPI package in an isolated environment:
   ```bash
   UV_NO_CONFIG=1 uvx \
     --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     --from bigquery-data-science==X.Y.Zrc1 \
     bigquery-data-science list
   ```

### 3. Production Release on PyPI (`vX.Y.Z`)

1. Push the annotated production tag on `main`:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```
2. Approve the `pypi` GitHub Environment deployment in GitHub Actions (`statmike` reviewer gate) to publish to PyPI and automatically create the GitHub Release with `dist/*` attached.

### 4. Patch / Hotfix Releases & CI Refusals

- For patch releases (`X.Y.Z+1`), branch from `main` (or from `vX.Y.Z`), apply the fix, bump all 7 version locations, and tag `vX.Y.Z+1`.
- CI and `release.yml` automatically refuse any build where the 7 version locations disagree, where `README.md` has broken or un-rewritten relative links, where the wheel exceeds `1.5 MB` or contains `.ipynb` files, or where the git tag does not match `pyproject.toml`.

## Contributor License Agreement

Contributions to this project must be accompanied by a [Contributor License Agreement](https://cla.developers.google.com/about) (CLA). You (or your employer) retain the copyright to your contribution; this simply gives permission to use and redistribute your contributions as part of the project.

If you have not already done so, please complete your CLA at <https://cla.developers.google.com/> before submitting a pull request.

## Community guidelines

This project follows [Google's Open Source Community Guidelines](https://opensource.google/conduct/) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

By contributing to `bigquery-data-science`, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

This is not an officially supported Google product. It is built on Google products and is neither endorsed nor supported by Google.
