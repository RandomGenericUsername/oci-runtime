# repo-harness Specification

## Purpose

The repo-harness capability is the operating contract this repository was born with: the `mu`
harness copied byte-for-byte, work routed through tickets and guard-created worktrees instead of
`main`, a fresh clone that rebuilds with `make sync && make gates && make build`, container-engine
tests that report their skips instead of hiding them, and releases that exist only as annotated,
immutable tags with reproducible artifacts. It is what makes every later change here auditable from
a clean clone.

## Requirements

### Requirement: the mu harness is present and byte-identical

The repo SHALL contain `scripts/worktree-guard.sh` (executable), `skills-lock.json`, `_bmad/`,
`.agents/skills/`, `.opencode/`, `tickets/_template/`, `tickets/_fixtures/` and
`tickets/LIFECYCLE.md`, each byte-identical to `/home/inumaki/Development/mu`.

Source: spine AD-12; `mu/AGENTS.md` §2; `ARCHITECTURE-SPINE.md` § Repo Birth Checklist items 3–6.

#### Scenario: guard is executable and clean-tree safe

- **WHEN** `bash scripts/worktree-guard.sh check-clean` runs on a clean tree
- **THEN** it exits 0

#### Scenario: a dirty tree is refused

- **WHEN** any tracked file is modified and `check-clean` runs
- **THEN** it exits 1 and prints `main is dirty, address it first`

#### Scenario: copied trees match their source

- **WHEN** `diff -r /home/inumaki/Development/mu/_bmad _bmad` runs
- **THEN** the output is empty and the exit code is 0

### Requirement: work routes through tickets and never lands on main

Every change SHALL have a ticket under `tickets/<id>-<slug>/ticket.md` whose status matches
`tickets/INDEX.md`, and item work SHALL happen on `ticket/<id>-<slug>` created by
`scripts/worktree-guard.sh create <id> <slug>`.

Source: `mu/AGENTS.md` §3; `mu/tickets/LIFECYCLE.md`; spine Consistency Conventions (Branch /
worktree).

#### Scenario: ticket and INDEX agree

- **WHEN** `rg -n "<id>" tickets/INDEX.md tickets/<id>-<slug>/ticket.md` runs
- **THEN** both files match, and the status token in each is the same

#### Scenario: the guard creates the worktree and branch

- **WHEN** `bash scripts/worktree-guard.sh create req-002 example` runs on a clean `main`
- **THEN** it prints `worktree=.worktrees/req-002/` and `branch=ticket/req-002-example`

### Requirement: a fresh clone passes the gate set

`make sync && make gates && make build` SHALL exit 0 on a fresh clone, where
`GATES = test lint hermetic lock-check docs-check`, and `hermetic` SHALL pass with `HOME` and all
four `XDG_*` variables pointed at empty temp dirs.

Source: spine AD-8, AD-12, AD-14; birth checklist items 9–11.

#### Scenario: gates on a fresh clone

- **WHEN** `git clone <repo> /tmp/x && cd /tmp/x && make sync && make gates` runs
- **THEN** every gate exits 0 and `make hermetic` reports the same test count as `make test`

#### Scenario: build produces both artifacts

- **WHEN** `make build` runs
- **THEN** `dist/oci_runtime-0.5.0-*.whl` and `dist/oci_runtime-0.5.0.tar.gz` exist

#### Scenario: workflow and Makefile agree

- **WHEN** `make ci-gates-parity` runs
- **THEN** it prints `PASS ...` and exits 0; adding a gate without a job (or the reverse) exits 1

### Requirement: container-engine skips are reported, never hidden

The test job SHALL run the suite with skip reasons printed and SHALL run
`scripts/engine-skip-report.py` on the pytest log. The report SHALL fail when no test passed and
SHALL print the pass and skip counts otherwise. No container-engine test may be removed or
unconditionally skipped to make CI green.

Source: spine AD-14; `docs/investigation/S2-provisioning-addressing.md` §7 (no gate ran these
suites); slice S3 step 6.

#### Scenario: a run with no engine reports skips

- **WHEN** the suite runs without a reachable engine
- **THEN** the report prints `<N> passed, <M> skipped` plus each skip reason, and exits 0

#### Scenario: an empty pass is a failure

- **WHEN** the log records `0 passed` and any number of skips
- **THEN** the report exits 1

### Requirement: a release is a tag with reproducible artifacts

An annotated `vMAJOR.MINOR.PATCH` tag SHALL be created only after the gates are green,
`CHANGELOG.md` SHALL describe the release, and CI SHALL attach the sdist and wheel built from
that commit to the GitHub Release. A published tag is never moved or deleted.

Source: spine AD-9; OPEN-3 (git-tag-only, no PyPI); OPEN-5 (MIT `LICENSE` before the first tag);
OPEN-9 (first tag `v0.5.0`, forward-only from `0.4.0`).

#### Scenario: the first tag resolves to one commit

- **WHEN** `git ls-remote --tags origin v0.5.0` runs with credentials disabled
- **THEN** it prints exactly one line ending in `refs/tags/v0.5.0`, and
  `git rev-parse v0.5.0^{commit}` names the released commit

#### Scenario: the release carries both artifacts

- **WHEN** `gh release view v0.5.0 --json assets --jq '.assets[].name'` runs
- **THEN** it lists `oci_runtime-0.5.0-py3-none-any.whl` and `oci_runtime-0.5.0.tar.gz`
