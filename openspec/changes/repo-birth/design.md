# Design — repo birth

## Decisions

### D1. History comes from `git subtree split`, not a fresh root commit

The in-tree package has 41 commits, including the container-integration work, the parser
conformance fixtures and the S0b hermetic-fixture commit. A fresh import would make the extracted
repo's first commit unrelated to the code's history and would lose the "why" of all of it.
`git subtree split -P src/shared/oci-runtime` writes a branch whose tree is the package directory
and whose commits are the 41 that touched it.

Evidence: `git -C /home/inumaki/Development/dotfiles-v3 subtree split -P
src/shared/oci-runtime -b split/oci-runtime` → exit 0, tip `18c37fd`,
`git rev-list --count split/oci-runtime` → `41`.
Verify: `git log --oneline | wc -l` in this repo before the scaffold commit → `41`.

Consequence: the split branch was pushed as `main` in one push, so `main` starts at the imported
tree, and the scaffold lands on top.

### D2. The marker is the single-repo marker, checked by one function

`pyproject.toml` + `src/<import_name>` is the only marker the new API accepts. It is checked by
walking up from each candidate to the first ancestor that satisfies both halves, so a candidate may
be the repo root, the package directory or anything below it. The legacy marker is a **separate**
function (`_legacy_repo_root_from_candidate`) used only by the deprecated alias — keeping it out of
the new path is what makes "monorepo root accepted only via alias" mechanically true rather than a
convention.

Evidence: `src/oci_runtime/source_locator.py:95-108` (new marker),
`:111-122` (legacy marker), `:210-274` (new API / alias).
Verify: `uv run pytest tests/unit/domain/test_source_locator.py -q` → all pass, including
`test_legacy_monorepo_root_is_rejected` and `test_legacy_monorepo_root_is_still_accepted`.

### D3. The import-name rule is a documented substitution, not a filesystem guess

`package.replace("-", "_")` is deterministic and stated in the module docstring, the README and the
spec. A consumer whose distribution name differs passes `import_name=` explicitly. Scanning the
filesystem for "the one directory under src/" would silently accept a repo for the wrong package;
the explicit argument is the escape hatch.

Evidence: `import_name_for` in `src/oci_runtime/source_locator.py:84-93`; README § Build-context
contract; `openspec/specs/build-context-locator/spec.md` (import-name requirement).
Verify: `uv run python -c "from oci_runtime import import_name_for;
print(import_name_for('color-scheme-generator'))"` → `color_scheme_generator`.

### D4. The alias is either-marker and warns on every call

`resolve_source_root` must keep in-tree consumers building until the last in-tree copy is deleted
(AD-16). It tries the new marker first, then the legacy one, at every candidate in the same
priority order. `DeprecationWarning` with `stacklevel=2` points at the caller, and the docstring
names the removal version (`0.6.0`). `SourceRoot` remains an alias of `BuildContextRoot` so existing
type annotations and equality comparisons keep working.

Evidence: `src/oci_runtime/source_locator.py:240-274`; `SourceRoot = BuildContextRoot` at `:81`.
Verify: `uv run python -W error::DeprecationWarning -c "from oci_runtime import resolve_source_root;
resolve_source_root(package='oci-runtime')"` → exits non-zero with the deprecation message.

### D5. Harness files are copied, not re-authored

AD-12 requires the same `worktree-guard.sh` and the same `skills-lock.json` hashes as `mu`. The copy
set is exactly: `scripts/worktree-guard.sh`, `skills-lock.json`, `_bmad/`, `.agents/skills/`,
`.opencode/`, `tickets/_template/`, `tickets/_fixtures/`, `tickets/LIFECYCLE.md`.
`tickets/INDEX.md` is repo-specific (an empty ledger needs the counting rule, not `mu`'s rows), and
`AGENTS.md` is retargeted but keeps the evidence rule verbatim.

Evidence: `diff -r` per path against `mu` is empty (see `REQ-001-repo-birth`'s evidence table).
Verify: `diff -r /home/inumaki/Development/mu/_bmad _bmad && diff
/home/inumaki/Development/mu/skills-lock.json skills-lock.json`.

### D6. One branch exception, then the guard

The guard refuses to create a worktree from a dirty tree, and this repo has no `main` history to
branch from before the first scaffold commit. The first commits are therefore made on
`ticket/req-001-repo-birth` in the clone (the slice instruction), and every later item uses
`bash scripts/worktree-guard.sh create <id> <slug>`.

Evidence: `scripts/worktree-guard.sh` is copied and executable in the implementation commit; the
ticket records `worktree: none` and the exception in its Closeout.
Verify: `bash scripts/worktree-guard.sh check-clean` → exit 0 on a clean tree.

### D7. The Makefile's `GATES` is the single gate list; CI is compared to it

The workflow has one job per gate so a failure names the gate, but a hand-maintained job list
drifts. `scripts/ci-gates-parity.py` parses `GATES` from the `Makefile` and the job keys from the
workflow and fails on any unmatched entry in either direction. CI-only jobs (`ci-gates-parity`,
`release`) are declared with a reason; a stale declaration fails.

Evidence: `make ci-gates-parity` → `PASS gates=[...] jobs=[...] exempt=[...]`.
Verify: `make ci-gates-parity`.

### D8. Container-engine skips are reported, never hidden

The live integration tests use a real engine and a real registry, and they skip with the engine's
own error when either is unavailable. Deleting them or marking them unconditionally skipped would
make CI green by removing the only proof that the adapters work against a real CLI. Instead:
`make test` runs `pytest -q -rs` so every skip reason is printed, and the CI `test` job tees the log
and runs `scripts/engine-skip-report.py`. That script fails when `passed == 0` (the suite cannot be
green by skipping everything) and prints `N passed, M skipped` otherwise.

Evidence: `Makefile` `test` target (`pytest -q -rs`); `.github/workflows/gates.yml` (`test` job);
`scripts/engine-skip-report.py`.
Verify: `make test 2>&1 | tee /tmp/oci-test.log; python3 scripts/engine-skip-report.py
/tmp/oci-test.log` → exit 0 and a `passed`/`skipped` line; with an all-skipped log it exits 1.

### D9. `lint` covers `src/` and the source is already clean

The in-tree Makefile linted `src/` only, and the imported source passes ruff unchanged (`All checks
passed!`). Tests are not linted: the imported modules carry pre-existing findings whose fix would
rewrite test code, which a birth slice must not do.

Evidence: `uv run ruff check src` → `All checks passed!`.
Verify: `make lint`.

### D10. The version moves to `0.5.0` before tagging

The imported package is `0.4.0`, but the first tag must carry the build-context API and versions
never move backwards (OPEN-9). The bump is one line in `pyproject.toml`, `uv.lock` is regenerated,
and the CHANGELOG explains the continuity rule.

Evidence: `pyproject.toml` `version = "0.5.0"`; `uv.lock` root package `0.5.0`.
Verify: `uv lock --check && uv build` → exit 0; `ls dist/oci_runtime-0.5.0-*`.

## Verification plan

| Decision | Command | Expected |
| --- | --- | --- |
| D1 | `git log --oneline \| wc -l` | 41 imported commits before the scaffold |
| D2 | `uv run pytest tests/unit/domain/test_source_locator.py -q` | pass; monorepo rejected by the new API |
| D3 | `uv run python -c "from oci_runtime import import_name_for; print(import_name_for('a-b'))"` | `a_b` |
| D4 | `uv run pytest tests/unit/domain/test_source_locator.py -q -k Deprecated` | pass; `DeprecationWarning` asserted |
| D5 | `diff -r <mu-path> <path>` for each copied path | empty output, exit 0 |
| D6 | `bash scripts/worktree-guard.sh check-clean` | exit 0 |
| D7 | `make ci-gates-parity` | `PASS ...`, exit 0 |
| D8 | `python3 scripts/engine-skip-report.py <log>` | `N passed, M skipped`, exit 0 |
| D9 | `make lint` | exit 0 |
| D10 | `uv lock --check && uv build` | exit 0; `dist/oci_runtime-0.5.0-*.whl` + `.tar.gz` |
| Release | `git ls-remote --tags origin v0.5.0` | exactly one line (tag object) + peeled commit |
