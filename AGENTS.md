# AGENTS.md — oci-runtime operating contract

Canonical agent instructions for this repo. Claude (`CLAUDE.md` symlinks here), OpenCode, and all
BMAD/OpenSpec skills must follow this.

## 1. Evidence rule (hard requirement)

No suggestion "in the air". Every technical claim, recommendation, or design decision must carry testable evidence — at least one of:

- **Doc evidence:** file path + line range, or commit SHA, or URL + quoted section.
- **Prototype evidence:** a script/command in-repo that runs and prints the validating output. State the exact command and observed result.
- **Test evidence:** `command run → result` (exit code + key output). Failing-as-expected counts if it validates the claim.

Format: any non-trivial claim gets an `Evidence:` line and a `Verify:` line (how to reproduce in one command). If evidence doesn't exist yet, say `Evidence: MISSING — run <X> to produce it` and do not present the claim as fact.

## 2. Charter — the container-engine abstraction and build-context contract

- This repo owns one package: `oci-runtime` (import package `oci_runtime`). It is the
  runtime-agnostic OCI abstraction: ports for engines, containers, images, networks, volumes,
  transports and parsers; Docker and Podman adapters behind them; a composition root
  (`RuntimeFactory`) that wires a declared engine to its adapter.
- Public surface: the names in `oci_runtime.__all__`, including `ContainerEngine`,
  `RuntimeFactory`, `RuntimeFactoryConfig`, `RuntimeKind`, `RuntimePreference`, the manager and
  parser ports, the domain types, `BuildContextRoot`, `import_name_for`, `resolve_build_context`
  and the deprecated `resolve_source_root`.
  Evidence: `src/oci_runtime/__init__.py` (`__all__`), `tests/unit/contract/test_public_api.py`.
- **Runtime dependencies are empty.** The package imports no sibling repo and reads no path in
  another repo.
  Evidence: `pyproject.toml` `dependencies = []`; `[tool.uv.sources]` is empty.
- **Build-context contract (spine AD-6).** A build context root is a directory that contains
  `pyproject.toml` **and** `src/<import_name>/`. `resolve_build_context(*, package, override,
  env_var, env, import_name)` resolves it from four sources in a fixed priority — explicit
  override → env var → PEP 610 `direct_url.json` → package walk — and raises
  `SourceRootNotFoundError` when nothing matches. `import_name` defaults to
  `package.replace("-", "_")`; a consumer whose distribution name differs passes it explicitly.
  Evidence: `src/oci_runtime/source_locator.py`.
- **The legacy monorepo marker is deprecated.** `resolve_source_root` is the pre-0.5.0 name; for
  one minor it accepts either marker set (`pyproject.toml` + `src/<import_name>`, or the old
  `src/cli-tools` + `src/shared`) and emits `DeprecationWarning`. It is removed in 0.6.0; new code
  calls `resolve_build_context`, which rejects the monorepo layout.
- The locator is required only by the image-build verb. No run-time path depends on a checkout.
  A tool installed before the split keeps **running**; it cannot **build images** from a
  post-split checkout, and that failure is loud (`SourceRootNotFoundError`), never a stale image
  (spine AD-16).
- Consumers are `csg` and `weg` only; they pin an immutable git tag, never a path and never
  `editable = true` (spine AD-1, AD-3). `itr` has no container mode and must not depend on this
  package.
- This repo owns **no Dockerfile** and knows no CLI's build flags. The CLI repos own their
  Dockerfiles and their `install` verb; provisioning owns the pin, clone and build trigger
  (spine AD-5, AD-7). The `--context` flag's `--source-root` alias is a consumer-side contract
  recorded in `openspec/specs/build-context-locator/spec.md`.

## 3. How we work here

- Read files, run commands (`rg`, `git log`, `uv`, `pytest`, `openspec validate`), paste results.
  Prefer executed output over recalled text.
- When findings contradict an earlier claim, state the discrepancy and trust the evidence.
- Keep changes small, verifiable, committable. A suite that is green only on the author's host is
  not green: tests are hermetic (empty `HOME` / `XDG_*`, foreign cwd), enforced by
  `tests/conftest.py` plus the canary in `tests/test_hermetic_canary.py`.
  Verify: `make hermetic` → exit 0.
- **Container-engine tests must stay honest.** Live Docker/Podman tests skip with the real reason
  when an engine (or its registry) is unavailable; they are never deleted or silently disabled to
  make CI green. `make test` reports skip reasons (`-rs`), and CI runs
  `scripts/engine-skip-report.py` on the pytest log, which fails when the suite passed nothing and
  prints the skip count otherwise.
- `make lint` covers `src/` only, matching the in-tree Makefile this package was extracted with.
  The imported test modules carry pre-existing findings; modernizing them is a separate ticket,
  not part of a birth slice.

## 4. OpenSpec + BMAD routing (via tickets)

- All work starts as a ticket in `tickets/` (`_template/`, vocab + rollup in `INDEX.md`, flow in
  `LIFECYCLE.md`). Triage with `/triage` (lanes in `tickets/_fixtures/router-lanes.md`).
- Broad scope (package charter, public API evolution, dependency policy) → BMAD. Installed
  skills are exactly the seven in `skills-lock.json`: `bmad`, `bmad-architecture`, `bmad-build`,
  `bmad-product-brief`, `bmad-spec`, `bmod-core-tools`, `bmod-method` — say so when a step needs a
  missing skill instead of improvising.
- Bounded slices (one proposal + spec + design + tasks) → OpenSpec
  (`/opsx-propose`, `/opsx-apply`, `/opsx-archive`). Artifact rules in `openspec/config.yaml`
  restate this evidence rule per artifact.
- Never work on main: `scripts/worktree-guard.sh create <id> <slug>` scaffolds
  `ticket/<id>-<slug>` + `.worktrees/<id>/`, and aborts when the tree is dirty. Record
  worktree/branch in the ticket.

## 5. Planning vs implementation

- Planning edits (tickets, `openspec/` changes, docs) and implementation changes (code, packaging,
  harness) land in **separate commits**.
- Never mix planning edits with implementation in one commit or one turn.

## 6. Release ritual

- Green gates on the ticket branch → version bumped in `pyproject.toml` + `CHANGELOG.md` →
  annotated tag `vMAJOR.MINOR.PATCH` → CI builds sdist + wheel and attaches them to the GitHub
  Release → consumer pin bump in its own commit.
- A published tag is never moved or deleted; a fix is a new tag. PyPI is not a channel.
- The first tag is `v0.5.0`: the imported in-tree code was `0.4.0`, and the build-context API
  ships with the first tag, so versions never move backwards (spine OPEN-9).
  Evidence: `CHANGELOG.md` `0.5.0`; `git tag -l`.

## 7. Gates

- `make gates` = `test lint hermetic lock-check docs-check`; `make build` produces the sdist and
  wheel. CI (`.github/workflows/gates.yml`) runs one job per gate target plus `ci-gates-parity`,
  which compares the workflow's job set against `GATES` in the `Makefile`.
  Verify: `make gates && make build` → exit 0; `make ci-gates-parity` → exit 0.
