# Tasks

## 1. Import and scaffold (≤2h)

- [x] 1.1 Create the public repo and push the subtree-split branch as `main`; verify the 41
  imported commits are present.
  Verify: `git log --oneline | wc -l` → `41` before the scaffold commit; `gh api
  repos/RandomGenericUsername/oci-runtime --jq .private` → `false`.
- [x] 1.2 Copy the mu harness byte-for-byte (`scripts/worktree-guard.sh`, `skills-lock.json`,
  `_bmad/`, `.agents/skills/`, `.opencode/`, `tickets/_template/`, `tickets/_fixtures/`,
  `tickets/LIFECYCLE.md`).
  Verify: `diff` against `/home/inumaki/Development/mu/<path>` for each → empty, exit 0; `test -x
  scripts/worktree-guard.sh` → exit 0.
- [x] 1.3 Write `AGENTS.md` (evidence rule, container-engine + build-context charter, ticket
  routing, worktree discipline, planning-vs-implementation, release ritual) and `CLAUDE.md` →
  `AGENTS.md`.
  Verify: `test -L CLAUDE.md` → exit 0; `rg -c "Evidence:|Verify:" AGENTS.md` → ≥ 2.

## 2. AD-6 build-context cutover (≤2h)

- [x] 2.1 Add `resolve_build_context` with the marker `pyproject.toml` + `src/<import_name>`;
  `import_name` defaults to `package.replace("-", "_")` and is documented as the rule.
  Verify: `uv run python -c "from pathlib import Path; from oci_runtime import
  resolve_build_context; ..."` on a temp root → `BuildContextRoot(root=..., source='override')`.
- [x] 2.2 Keep `resolve_source_root` as a deprecated either-marker alias emitting
  `DeprecationWarning`; keep `SourceRoot` as the value-object alias.
  Verify: `uv run pytest tests/unit/domain/test_source_locator.py -q -k "Deprecated or Legacy"` →
  pass.
- [x] 2.3 Record the consumer-side flag contract (`--context` canonical, `--source-root` alias) in
  the spec; assert this repo defines no CLI verb.
  Verify: `rg -n "source-root|--context" src` → only the locator docstring.
- [x] 2.4 Bump the version to `0.5.0` and regenerate the lock.
  Verify: `uv lock --check` → exit 0; `uv build` → `dist/oci_runtime-0.5.0-*` wheel + sdist.

## 3. Ledger and specs (≤2h)

- [x] 3.1 Add `tickets/INDEX.md` with the counting-rule header and `tickets/REQ-001-repo-birth/`.
  Verify: `rg -n "REQ-001" tickets/INDEX.md tickets/REQ-001-repo-birth/ticket.md` → both hit.
- [x] 3.2 Add `openspec/config.yaml`, `openspec/specs/build-context-locator/spec.md`, and the
  `repo-birth` change (proposal, design, tasks, spec delta).
  Verify: `openspec validate --specs --strict` and `openspec validate repo-birth --strict` → exit 0.

## 4. Gates and release (≤2h)

- [x] 4.1 Add the fresh-clone `Makefile` and `scripts/ci-gates-parity.py`; make every verb run
  from `$(CURDIR)`.
  Verify: `make gates` → exit 0; `make ci-gates-parity` → `PASS ...`.
- [x] 4.2 Add `.github/workflows/gates.yml` with one job per gate, `ci-gates-parity`, a tag-only
  `release` job, and the `engine-skip-report` step in the test job.
  Verify: `make ci-gates-parity` → exit 0 (the workflow is parsed, not grepped);
  `python3 scripts/engine-skip-report.py <pytest.log>` → `N passed, M skipped`, exit 0.
- [x] 4.3 Prove the suite and packaging on a fresh clone: `uv sync --frozen`, `uv run pytest -q`,
  `make gates`, `uv build`.
  Verify: `uv run pytest -q` → `1107 passed, 2 skipped`; `ls dist/oci_runtime-0.5.0-*` lists a
  wheel and an sdist.
- [x] 4.4 Tag annotated `v0.5.0` after the gates and CI exist; push the tag; confirm the Release
  carries both artifacts.
  Verify: `GIT_TERMINAL_PROMPT=0 git -c credential.helper= ls-remote
  https://github.com/RandomGenericUsername/oci-runtime 'refs/tags/v0.5.0'` → exactly one line;
  `gh release view v0.5.0 --json assets --jq '.assets[].name'` → wheel + sdist.

## 5. Closeout (≤0.5h)

- [x] 5.1 Tick acceptance, record commands + results in the ticket, move the INDEX entry to Done.
  Verify: `git status --porcelain` → empty after the merge; `rg -n "REQ-001" tickets/INDEX.md` →
  the Done section lists it.
