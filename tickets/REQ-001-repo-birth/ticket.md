---
id: REQ-001
title: "Birth the oci-runtime repo (mu-strict), cut the AD-6 build-context API over, and tag v0.5.0"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: repo-birth
  bmad: none
worktree: none
branch: ticket/req-001-repo-birth
---

# Birth the oci-runtime repo (mu-strict), cut the AD-6 build-context API over, and tag v0.5.0

## Requirement

Slice **S3** of the CLI-repos split SHALL create `RandomGenericUsername/oci-runtime` as a public
repo whose root is the imported `src/shared/oci-runtime` package, preserve that package's history
with `git subtree split`, install the `mu` harness byte-for-byte, replace the monorepo source
locator with the repo-root build-context locator (spine **AD-6**, **AD-16**), and cut the repo's
first tag (`v0.5.0`, forward-only from the in-tree `0.4.0`) only after the gates, packaging and CI
exist.

The package remains the **container-engine abstraction**: container, image, network, volume,
transport, parser, provider and factory behaviour is unchanged. `dotfiles-v3` is not modified — the
consumer rewire (csg/weg Dockerfiles + build verb) and the in-tree deletion are the next step of
the slice in that repo.

## Acceptance

- [x] The repo exists, is **public**, and its `main` carries the 41 imported commits from the
  subtree split.
  Verify: `gh api repos/RandomGenericUsername/oci-runtime --jq .private` → `false`;
  `git log --oneline | wc -l` → ≥ 41.
- [x] The harness is byte-identical to `mu` at every copied path.
  Verify: `diff` per path (see the evidence table) → empty, exit 0.
- [x] `AGENTS.md` carries the evidence rule and this repo's charter; `CLAUDE.md` is a symlink.
  Verify: `rg -c "Evidence:|Verify:" AGENTS.md` → ≥ 2; `test -L CLAUDE.md` → exit 0.
- [x] `resolve_build_context` accepts a single-repo root (`pyproject.toml` + `src/<import_name>`)
  and rejects the legacy monorepo root; `resolve_source_root` still accepts either marker and
  emits `DeprecationWarning`.
  Verify: `uv run pytest tests/unit/domain/test_source_locator.py -q` → pass.
- [x] The four-source priority order is unchanged and covered: override → env → PEP 610 →
  package walk; missing → `SourceRootNotFoundError`.
  Verify: `uv run pytest tests/unit/domain/test_source_locator.py -q -k Priority or missing` →
  pass.
- [x] `tickets/INDEX.md` lists this ticket with the same status as the frontmatter, and the
  OpenSpec change validates strictly.
  Verify: `openspec validate --specs --strict` and `openspec validate repo-birth --strict` →
  exit 0.
- [x] A fresh clone passes `make sync && make test && make gates && make build` and builds both
  artifacts.
  Verify: `uv sync --frozen && uv run pytest -q && make gates && make build` → exit 0;
  `ls dist/oci_runtime-0.5.0-*` → wheel + sdist.
- [x] `.github/workflows/gates.yml` exists and its job set equals `GATES` (plus declared CI-only
  jobs); the first run on `main` is green, and the engine-skip report is visible in the test job.
  Verify: `make ci-gates-parity` → `PASS ...`; `gh run list -R
  RandomGenericUsername/oci-runtime --limit 3 --json status,conclusion,headBranch`.
- [x] Annotated tag `v0.5.0` exists on the released commit, is anonymously fetchable, and its
  GitHub Release carries the wheel + sdist.
  Verify: `GIT_TERMINAL_PROMPT=0 git -c credential.helper= ls-remote
  https://github.com/RandomGenericUsername/oci-runtime 'refs/tags/v0.5.0'` → one line;
  `gh release view v0.5.0 --json assets --jq '.assets[].name'` → both artifacts.
- [x] `git status --porcelain` is empty in both repos; `dotfiles-v3` `master` is at the same SHA
  as before the slice.
  Verify: `git status --porcelain` → empty; `git -C /home/inumaki/Development/dotfiles-v3 rev-parse
  master` → `eb880c2f5e2c571c8bf79c76bf363855dc8885f8`.

## Out of scope

- Rewiring `dotfiles-v3` consumption (csg/weg pins, Dockerfile rewrite, build verb, deletion of
  `src/shared/oci-runtime/`). That lands in that repo in this slice's next step.
- The `--context`/`--source-root` CLI parser itself: it lives in the cli repos (AD-7); this repo
  owns the resolver and records the flag contract in the spec.
- Any engine, adapter, parser or manager behaviour change.
- PyPI publication.

## Evidence

| Claim | Command | Observed |
| --- | --- | --- |
| Preconditions | `gh repo view RandomGenericUsername/oci-runtime` | failed: `Could not resolve to a Repository` |
| dotfiles clean at slice start | `git -C /home/inumaki/Development/dotfiles-v3 status --porcelain` | empty; `master` = `eb880c2f5e2c571c8bf79c76bf363855dc8885f8` |
| Split history | `git subtree split -P src/shared/oci-runtime -b split/oci-runtime` | exit 0; tip `18c37fdc03d5bdcd293468b5af66146ef6b50e1c`; 41 commits |
| Baseline in-tree suite | `uv run pytest -q` (in `src/shared/oci-runtime`) | `1095 passed, 2 skipped` |
| Harness byte-copy | `diff -r mu/<path> <path>` for all eight paths | all `MATCH` |
| AD-6 suite | `uv run pytest -q -rs` | `1107 passed, 2 skipped` |
| Gates | `make gates` | see Closeout |
| Build | `uv build` | see Closeout |
| Fresh clone | `make sync && make gates && make build` | see Closeout |
| CI | `gh run list -R RandomGenericUsername/oci-runtime` | see Closeout |
| Release | `git ls-remote --tags origin v0.5.0`; `gh release view v0.5.0` | see Closeout |

## Closeout

Filled after the gates, CI and tag. The one branch exception: the first commits are made directly
on `ticket/req-001-repo-birth` in the clone because a brand-new repo has no `main` history for the
guard to branch from (same exception as the sibling births); every later item uses
`bash scripts/worktree-guard.sh create <id> <slug>`.
