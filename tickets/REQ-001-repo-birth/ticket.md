---
id: REQ-001
title: "Birth the oci-runtime repo (mu-strict), cut the AD-6 build-context API over, and tag v0.5.0"
kind: requirement
status: done
lane: 3
links:
  openspec: repo-birth
  bmad: none
worktree: .worktrees/req-001/
branch: ticket/req-001-closeout
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
  master` → `eb880c2f5e2c571c8bf79c76bf363855dc8885f8` (the pre-slice value; `master` has since
  advanced to `56fc4b7e…` with the slice's own downstream steps — see Closeout, "`master`
  reconciliation").

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

Closed 2026-10-21 on `ticket/req-001-closeout` (guard worktree `.worktrees/req-001/`), fast-forwarded
onto `main`. The slice itself is `bfaa616` (planning) + `b631dfa` (implementation) on
`ticket/req-001-repo-birth`; the annotated tag `v0.5.0` peels to `b631dfa`, so the released commit is
the tested commit.

**Audit before closing (the "10/10 closed" report was checked, not trusted).** Every acceptance box
was re-run on 2026-10-21 against the published repo. All ten hold. What was actually stale was the
**ledger**: this section was still the placeholder, `status` still said `in-progress`, `INDEX.md`
still filed the item under Requirements, and the `repo-birth` OpenSpec change was still open. This
closeout fixes only those four records — no code, packaging, gate, workflow or tag changed.

**Worktree exception (birth only).** The guard creates a branch from a clean `main`, and this repo
had no `main` before the first scaffold, so the first two commits were made on
`ticket/req-001-repo-birth` in the clone (same exception as the sibling births). This closeout is the
first item to use the guard normally: `bash scripts/worktree-guard.sh create req-001 closeout` →
`worktree=.worktrees/req-001/`, `branch=ticket/req-001-closeout`, exit 0.

Evidence (commands from the repo root unless a path is named):

| Claim | Command | Result |
| --- | --- | --- |
| Repo is public, `main` is default | `gh api repos/RandomGenericUsername/oci-runtime --jq '.private,.visibility,.default_branch'` | `false`, `public`, `main`, exit 0 |
| History preserved | `git log --oneline \| wc -l` | `43` = 41 imported from split tip `18c37fdc03d5bdcd293468b5af66146ef6b50e1c` + `bfaa616` + `b631dfa` |
| Harness byte-identical | `diff -r /home/inumaki/Development/mu/<path> <path>` for all eight paths | `MATCH` × 8 (`scripts/worktree-guard.sh`, `skills-lock.json`, `_bmad`, `.agents/skills`, `.opencode`, `tickets/_template`, `tickets/_fixtures`, `tickets/LIFECYCLE.md`), exit 0 |
| AGENTS carries the contract | `rg -c "Evidence:\|Verify:" AGENTS.md`; `test -L CLAUDE.md` | `7`; symlink, exit 0 |
| Flag contract stays resolver-side | `rg -n "source-root\|--context" src` | one hit, `src/oci_runtime/source_locator.py:22` (docstring), exit 0 |
| Gates | `make gates` | test `1107 passed, 2 skipped in 24.53s`; lint `All checks passed!`; hermetic `1107 passed, 2 skipped in 24.08s` (skips: `Lima parser not yet implemented`, `Windows-only`); `uv lock --check` → `Resolved 10 packages`; docs-check silent → exit 0 |
| Workflow ↔ Makefile parity | `make ci-gates-parity` | `PASS gates=['docs-check', 'hermetic', 'lint', 'lock-check', 'test'] jobs=['ci-gates-parity', 'docs-check', 'hermetic', 'lint', 'lock-check', 'release', 'test'] exempt=['ci-gates-parity', 'release']`, exit 0 |
| Specs and change valid | `openspec validate --specs --strict`; `openspec validate repo-birth --strict` | `Totals: 1 passed, 0 failed (1 items)`, exit 0; `Change 'repo-birth' is valid`, exit 0 |
| Fresh clone at the tag is green | `git clone --branch v0.5.0 --depth 1 https://github.com/RandomGenericUsername/oci-runtime.git /tmp/opencode/oci-freshclone && make sync && make gates && make build` | `SYNC_EXIT=0`, `GATES_EXIT=0`, `BUILD_EXIT=0`; same `1107 passed, 2 skipped`; `dist/oci_runtime-0.5.0-py3-none-any.whl` + `dist/oci_runtime-0.5.0.tar.gz` |
| Isolated tag install reports 0.5.0 | fresh `uv venv` + `uv pip install "oci-runtime @ git+https://github.com/RandomGenericUsername/oci-runtime@v0.5.0"`, then `python -c "importlib.metadata.version('oci-runtime')"` | `0.5.0`; module imported from the fresh venv's `site-packages`; `hasattr(oci_runtime, 'resolve_build_context')` → `True` |
| Tag is annotated and points at the released commit | `git cat-file -p v0.5.0`; `git rev-parse v0.5.0^{}` | object `38ce267ce966a831ba0617bc5a97660564f7880a`, `type commit`; peels to `b631dfa511f5710d6e171d2ac3f0cdf58bc738af` = `main` HEAD |
| Tag is anonymously fetchable, one line | `GIT_TERMINAL_PROMPT=0 git -c credential.helper= ls-remote https://github.com/RandomGenericUsername/oci-runtime 'refs/tags/v0.5.0'` | `38ce267ce966a831ba0617bc5a97660564f7880a	refs/tags/v0.5.0` — exactly one line, exit 0 |
| Release carries both artifacts | `gh release view v0.5.0 --json tagName,isDraft,isPrerelease,assets --jq '.assets[].name'` | `oci_runtime-0.5.0-py3-none-any.whl`, `oci_runtime-0.5.0.tar.gz`; `isDraft=false`, `isPrerelease=false` |
| CI is green | `gh run list -R RandomGenericUsername/oci-runtime --limit 3 --json status,conclusion,headBranch` | 2 runs, both `completed`/`success`: `main` (`39364291235`), `v0.5.0` (`39364516953`) |
| The tag run releases; the `main` run skips release | `gh run view 39364516953 --json jobs`; `gh run view 39364291235 --json jobs` | tag run: all seven jobs `success` incl. `release`; `main` run: six gates `success`, `release` `skipped` |
| `dotfiles-v3` untouched, clean | `git -C /home/inumaki/Development/dotfiles-v3 rev-parse master`; `git ... status --porcelain \| wc -l` | `56fc4b7efcd410f59f194f5560c6e7d2962f7386`; `0` |
| This repo has no write path into `dotfiles-v3` | `rg -n "dotfiles-v3" src scripts Makefile .github pyproject.toml` | one hit, a comment in `src/oci_runtime/source_locator.py:60` — no script, hook or task writes there |

### `master` reconciliation (last acceptance box)

`eb880c2f5e2c571c8bf79c76bf363855dc8885f8` was `dotfiles-v3` `master` before the slice and is the
value that box was written and verified against. `master` has since advanced **15 commits**
(`git rev-list --count eb880c2..master` → `15`) and none of them are birth-slice edits made from
here: they are the slice's own next steps executed in *that* repo —
`2a9229ec chore(deps): consume oci-runtime v0.5.0 from its repo`,
`e39caac6 feat(build): build CLI images from the package repo root`,
`e954c767 test(gates): assert oci-runtime tree retired`,
`8e8de381 chore(openspec): retire src/cli-tools and src/shared`,
`0bc85765 feat(provisioning): install itr from its pinned repo`
(`git -C /home/inumaki/Development/dotfiles-v3 log --oneline eb880c2..master | tail -5`). The
property the box asserts — this birth did not modify `dotfiles-v3` — holds; the literal SHA in the
box is date-stamped, which is why it is annotated rather than rewritten.

Verify: `git -C /home/inumaki/Development/dotfiles-v3 log --oneline eb880c2..master` → those 15
commits; `rg -n "dotfiles-v3" src scripts Makefile .github pyproject.toml` → comment only.

Slice commits (oldest first, all now on `main`):

| Commit | Subject |
| --- | --- |
| `bfaa616` | `docs: adopt the operating contract, ticket ledger, and build-context spec` |
| `b631dfa` | `feat: extract oci-runtime with the repo-root build-context locator` |
| closeout | `docs(REQ-001): close repo-birth with closeout evidence and archive the change` |
