# Changelog

Notable changes to the `oci-runtime` repo. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow the git tags
(`vMAJOR.MINOR.PATCH`, annotated, never moved).

## [Unreleased]

## [0.5.0] - 2026-10-19

First release. The package content is the in-tree `src/shared/oci-runtime` package (version
`0.4.0` there) imported with `git subtree split`, history preserved, plus the build-context API
change (architecture spine AD-6). The version moves forward to `0.5.0`; it never moves backwards.

### Added

- `resolve_build_context(*, package, override=None, env_var=None, env=None, import_name=None)` —
  resolves the container build-context root from four sources in a fixed priority (override → env
  → PEP 610 `direct_url.json` → package walk). The marker is a directory containing
  `pyproject.toml` **and** `src/<import_name>/`.
- `BuildContextRoot(root, source)` — the resolved root plus the source that produced it.
- `import_name_for(package)` — the documented derivation rule: every `-` becomes `_`; callers with
  a different distribution name pass `import_name=` explicitly.
- Repo harness copied byte-for-byte from `mu`: `scripts/worktree-guard.sh`, `skills-lock.json`,
  `_bmad/`, `.agents/skills/`, `.opencode/`, `tickets/_template/`, `tickets/_fixtures/`,
  `tickets/LIFECYCLE.md`.
- `Makefile` fresh-clone verbs (`sync`, `test`, `lint`, `format`, `check`, `hermetic`,
  `lock-check`, `docs-check`, `gates`, `build`, `install`, `clean`, `ci-gates-parity`),
  `.github/workflows/gates.yml`, `scripts/ci-gates-parity.py` and
  `scripts/engine-skip-report.py`.
- MIT `LICENSE`, `README.md`, `AGENTS.md`, `CLAUDE.md` symlink, ticket `REQ-001-repo-birth`, the
  OpenSpec change `repo-birth`, the `build-context-locator` capability spec and the
  `repo-harness` change spec.

### Changed

- `source_locator`: the marker is now the single-repo marker (`pyproject.toml` +
  `src/<import_name>`). The legacy monorepo marker (`src/cli-tools` + `src/shared`) is kept only
  for the deprecated alias. The four-source priority order and every `source` label are unchanged.
- `pyproject.toml`: version `0.4.0` → `0.5.0`; added release metadata (`readme`, `license`,
  `license-files`, classifiers), `hatchling>=1.27`, and a sdist `only-include` list so the harness
  trees stay out of the artifact. `[tool.uv.sources]` remains empty.
- Test suite: the locator tests now cover the new marker (new root, package-dir and deep-nested
  candidates, explicit `import_name`), the rejection of the monorepo root, a pyproject-only root
  and a `src/`-only root, the full override → env → PEP 610 → package priority order, and the
  deprecated alias's either-marker behaviour and `DeprecationWarning`. The legacy-marker fixtures
  are retained for the alias path. Count: `1095 passed, 2 skipped` before; `1107 passed,
  2 skipped` after.

### Removed

- The tracked `.coverage` artifact (test output, not source).

### Deprecated

- `resolve_source_root` — use `resolve_build_context`; the alias accepts either marker set and is
  removed in 0.6.0.
