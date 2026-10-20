# repo-birth

## Why

`oci-runtime` is the third package extracted from `dotfiles-v3` in the CLI/split programme (spine
`SLICES.md` § S3). The package already exists and is green in-tree, but a repository is not a valid
extraction target until it is mu-strict from its first commit (spine **AD-12**), and its locator is
not valid for the post-split world until the build-context cutover lands (spine **AD-6**).

Evidence: the package is 4 806 source lines over 60 test modules plus the S0b hermetic canary, and
its suite is green in-tree.
Verify: `find src -name '*.py' | xargs wc -l | tail -1` → `4806 total`;
`find tests -name 'test_*.py' | wc -l` → `61` (60 `test_*.py` plus the canary module counted
separately in the slice inventory); `uv run pytest -q` → `1095 passed, 2 skipped`.

Evidence: the split preserves history with `git subtree split`, not a fresh-root import (spine
OPEN-8, `SLICES.md` § Slice template step 2).
Verify: `git -C /home/inumaki/Development/dotfiles-v3 subtree split -P
src/shared/oci-runtime -b split/oci-runtime` → exit 0, tip `18c37fd`, 41 commits.

Evidence: the legacy locator hardcodes the monorepo marker and rejects every post-split checkout.
Verify: `src/shared/oci-runtime/src/oci_runtime/source_locator.py:37-39` in `dotfiles-v3` →
`_REPO_MARKER_DIRS = ("src", "cli-tools"), ("src", "shared")`;
`docs/investigation/S2-provisioning-addressing.md` §2.3 → `SourceRootNotFoundError` on an external
layout.

Evidence: the harness must be copied from `mu`, not re-authored (AD-12).
Verify: `diff /home/inumaki/Development/mu/skills-lock.json skills-lock.json` → empty; same for
`scripts/worktree-guard.sh`, `_bmad`, `.agents/skills`, `.opencode`, `tickets/_template`,
`tickets/_fixtures`, `tickets/LIFECYCLE.md`.

## What Changes

- Create the public repo `RandomGenericUsername/oci-runtime`, default branch `main`, from the
  `git subtree split` result of `src/shared/oci-runtime` (41 commits preserved).
- **AD-6, before the first tag**: add `resolve_build_context(*, package, override, env_var, env,
  import_name)` whose marker is `pyproject.toml` + `src/<import_name>`, with the same four-source
  priority (override → env → PEP 610 → package walk). The import name defaults to
  `package.replace("-", "_")`; a consumer with a different distribution name passes it explicitly.
- Keep `resolve_source_root` exported as a deprecated alias for one minor: it accepts either marker
  set (new repo root or legacy monorepo root) and emits `DeprecationWarning`. New code cannot use
  the legacy marker through `resolve_build_context`.
- Record the consumer-side flag contract — `--context` canonical, `--source-root` its alias for one
  minor — in the spec. The flag itself lives in the cli repos; this repo owns no CLI verb.
- Bump the package version to `0.5.0` (the imported code is `0.4.0`; the build-context API ships in
  the first tag, so versions never move backwards — OPEN-9).
- Install the mu-strict harness **byte-for-byte**: `scripts/worktree-guard.sh`, `skills-lock.json`,
  `_bmad/`, `.agents/skills/`, `.opencode/`, `tickets/_template/`, `tickets/_fixtures/`,
  `tickets/LIFECYCLE.md`.
- Add the repo contract: `AGENTS.md` (evidence rule, charter = container-engine abstraction +
  build-context contract, ticket routing, never work on main, planning vs implementation, release
  ritual), `CLAUDE.md` → `AGENTS.md`.
- Add the work ledger: `tickets/INDEX.md` (counting rule header), `tickets/REQ-001-repo-birth/`.
- Add the OpenSpec root: `openspec/config.yaml` (evidence rules, repo context),
  `openspec/specs/build-context-locator/` (the locator contract), and this change.
- Add a fresh-clone Makefile (`sync`, `test`, `lint`, `format`, `check`, `hermetic`, `lock-check`,
  `docs-check`, `gates`, `gates-ci`, `build`, `install`, `clean`, `ci-gates-parity`),
  `.github/workflows/gates.yml` (one job per gate + `ci-gates-parity` + tag release),
  `scripts/ci-gates-parity.py`, `scripts/engine-skip-report.py`, MIT `LICENSE`, `README.md`,
  `CHANGELOG.md`, `.gitignore`.
- Keep packaging honest: `[tool.uv.sources]` empty (no sibling dependency), the committed
  `uv.lock` current, and `uv build` producing the `oci_runtime-0.5.0` sdist + wheel.
- Make container-engine skips visible instead of convenient: `make test` prints skip reasons and CI
  runs `scripts/engine-skip-report.py`, which fails a run that passed nothing and prints the skip
  count otherwise. No test is removed or unconditionally skipped.

## Capabilities

- **New Capabilities:** `repo-harness` — the repo contract, ticket ledger, OpenSpec root, gate set
  and release ritual that make this repo a valid extraction target.
- **New Capability:** `build-context-locator` — the marker, four-source priority, import-name rule,
  deprecated either-marker alias and loud failure of the AD-6 cutover.
- **Modified Capabilities:** none in behaviour outside the locator. Container, image, network,
  volume, transport, parser, provider and factory behaviour is the imported behaviour.

## Non-goals (out of scope)

- **Not** rewiring `dotfiles-v3`: no consumer pin, no Dockerfile rewrite, no deletion of
  `src/shared/oci-runtime/`, no lock regeneration there. That is the next step of slice S3 in that
  repo/commit set.
- **Not** adding a CLI verb or the `--context`/`--source-root` parser here: the cli repos own their
  build verbs (AD-7). This repo documents the resolver side of the contract.
- **Not** changing engine detection, adapters, parsers or manager behaviour.
- **Not** modernizing the imported test modules for ruff; `lint` covers `src/` exactly as the
  in-tree Makefile did (follow-up ticket material).
- **Not** publishing to PyPI (OPEN-3): the release channel is a git tag plus GitHub Release
  artifacts.

## Impact

- New: `AGENTS.md`, `CLAUDE.md` (symlink), `Makefile`, `LICENSE`, `README.md`, `CHANGELOG.md`,
  `.gitignore`, `.github/workflows/gates.yml`, `scripts/ci-gates-parity.py`,
  `scripts/engine-skip-report.py`, `openspec/`, `tickets/`, and the copied harness trees.
- Modified: `pyproject.toml` (version, release metadata, hatchling floor, sdist `only-include`);
  `src/oci_runtime/source_locator.py` (new marker, new API, deprecated alias);
  `src/oci_runtime/__init__.py` (public exports); `tests/unit/domain/test_source_locator.py`
  (new-marker coverage + alias coverage); `tests/unit/contract/test_public_api.py` (new exports);
  `uv.lock` (root package version).
- Removed: the tracked `.coverage` artifact.
- Unchanged: every adapter, port, domain type and factory behaviour; every file in `dotfiles-v3`.
