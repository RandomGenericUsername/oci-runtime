# oci-runtime

A runtime-agnostic OCI container abstraction for Python >= 3.12, with Docker and Podman adapters.

The package is hexagonal: ports describe engines, containers, images, networks, volumes,
transports and parsers; adapters implement them for the `docker` and `podman` CLIs; one
composition root (`RuntimeFactory`) wires a **declared** engine to its adapter. The engine is never
detected behind the caller's back — the consumer states which runtime it wants.

## Public surface

```python
from oci_runtime import (
    # domain
    ContainerState, NetworkMode, RestartPolicy, RuntimeKind, RuntimePreference,
    ContainerInfo, ExecResult, ImageInfo, NetworkInfo, PortMapping, PruneResult,
    RunConfig, VolumeInfo, VolumeMount, BuildContext,
    # ports
    ContainerEngine, BinaryResolver, RuntimeCapabilities, CancellationToken,
    ContainerManager, ImageManager, NetworkManager, VolumeManager,
    ContainerParser, ImageParser, NetworkParser, VolumeParser,
    Transport, StreamingTransport, TtyDetector, OutputStream,
    RuntimeDiscovery, RuntimeProvider, PtyTransport,
    # composition root
    RuntimeFactory, RuntimeFactoryConfig,
    # build-context locator
    BuildContextRoot, import_name_for, resolve_build_context, resolve_source_root,
)
```

Adapters are imported from their modules (`oci_runtime.adapters.parser.docker`,
`oci_runtime.adapters.provider.podman`, …), not from the package root.

The package has **no runtime dependencies** and imports no sibling repo. `[tool.uv.sources]` is
empty.

## Build-context contract

An image build needs the CLI's **source checkout**, not its site-packages: the Dockerfile copies
`pyproject.toml`, `uv.lock` and `src/` from the build context. `resolve_build_context` finds that
checkout.

A **build context root** is a directory that contains:

- `pyproject.toml`, and
- `src/<import_name>/`.

`import_name` is derived deterministically from the distribution name: every `-` becomes `_`
(`color-scheme-generator` → `color_scheme_generator`). A consumer whose distribution name differs
from its import package passes `import_name=` explicitly.

```python
from pathlib import Path
from oci_runtime import resolve_build_context

ctx = resolve_build_context(
    package="color-scheme-generator",
    override=Path("/path/to/color-scheme-generator"),  # --context
)
print(ctx.root, ctx.source)   # (<checkout>, 'override')
```

Sources are tried in a fixed priority:

| # | Source | Reported as | Candidate |
| --- | --- | --- | --- |
| 1 | explicit `override` (CLI `--context`) | `override` | the path handed in |
| 2 | caller-named env var (`CSG_SOURCE_ROOT`, `WEG_SOURCE_ROOT`) | `env` | the env value |
| 3 | PEP 610 `direct_url.json` | `direct_url` | the recorded `file://` source |
| 4 | package walk | `package` | the package directory and its parents |

If no candidate carries the marker, `SourceRootNotFoundError` is raised. Building an image from an
unknown context is impossible, so the CLI fails loudly instead of producing a stale image.

### Deprecated alias (removed in 0.6.0)

`resolve_source_root` is the pre-0.5.0 name. For one minor it accepts **either** the new marker
**or** the legacy monorepo marker (a root containing both `src/cli-tools` and `src/shared`), so
in-tree consumers keep building during the split. It emits `DeprecationWarning` on every call.
New code calls `resolve_build_context`, which rejects the monorepo layout.

The CLI flag contract that goes with it: the image-build verb takes `--context <checkout>`, and
`--source-root <checkout>` remains an alias of it for one minor. The flag lives in the CLI repos
(`csg`, `weg`); this package only owns the resolver.

### What a pre-split install can still do

An installed pre-split CLI keeps **running** — the runtime needs only `PATH`, the env allowlist
and writable output directories. It cannot **build images** from a post-split checkout, because its
legacy marker no longer exists there. That path fails loudly, which is the intended no-stale-image
behaviour; the next bootstrap replaces the tool with a pinned install.

## Install

From a checkout (development):

```bash
make sync          # uv sync --frozen
make gates         # test + lint + hermetic + lock-check + docs-check
make build         # sdist + wheel in dist/
```

As a consumer, pin an immutable tag — never a path and never a branch:

```toml
# pyproject.toml
dependencies = ["oci-runtime>=0.5.0"]

[tool.uv.sources]
oci-runtime = { git = "https://github.com/RandomGenericUsername/oci-runtime", tag = "v0.5.0" }
```

```bash
uv add "oci-runtime @ git+https://github.com/RandomGenericUsername/oci-runtime@v0.5.0"
```

A published tag is never moved or deleted; a fix ships as a new tag. PyPI is not a channel.

## What `dotfiles-v3` pins

`dotfiles-v3` consumes this repo as a pinned artifact (`v0.5.0` at first release) from the two
container-mode CLIs only:

- `src/cli-tools/color-scheme-generator/pyproject.toml` (`csg`)
- `src/cli-tools/wallpaper-effects-generator/pyproject.toml` (`weg`)

`itr` has no container mode and does not depend on this package. The runtime and provisioning do
not depend on it either. No consumer may use `path = ...` or `editable = true`.

## Tests and the container engines

The suite has hermetic unit/contract/conformance tests plus live integration tests that use a real
engine. A live test skips — with the engine's own error as the reason — when no engine or registry
is reachable; it is never deleted or silently disabled. `make test` prints skip reasons (`-rs`),
and CI runs `scripts/engine-skip-report.py` over the pytest log: it fails if the suite passed
nothing and prints the skip count otherwise.

```bash
make test
# 1107 passed, 2 skipped
#   SKIPPED ... Lima parser not yet implemented
#   SKIPPED ... Windows-only
```

## Release

Version in `pyproject.toml` + `CHANGELOG.md` entry → annotated tag `vX.Y.Z` → GitHub Actions builds
the sdist and wheel and attaches them to the GitHub Release.

## Repo harness

- `AGENTS.md` (with `CLAUDE.md` symlinked to it) is the operating contract: evidence rule,
  worktree discipline, planning-vs-implementation commits.
- `tickets/` is the work ledger (`INDEX.md`, `LIFECYCLE.md`, `_template/`).
- `openspec/` holds the specs and the change log (`config.yaml`, `specs/`, `changes/`).
- `scripts/worktree-guard.sh create <id> <slug>` makes `.worktrees/<id>/` on
  `ticket/<id>-<slug>`; never work on `main`.
- `.agents/skills/` + `skills-lock.json` and `_bmad/` are hash-pinned copies of the `mu` harness.

## License

MIT — see `LICENSE`.
