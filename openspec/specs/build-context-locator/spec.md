# build-context-locator Specification

## Purpose

A container image build needs the CLI's source checkout as context: the Dockerfile copies
`pyproject.toml`, `uv.lock` and `src/` from it. An installed tool resolves to site-packages
instead, so the checkout is rediscovered explicitly. This spec fixes the build-context marker, the
four-source priority order, the import-name rule, the deprecated alias and the error behaviour
(architecture spine AD-5, AD-6, AD-16).

The contract is deliberately a **single-repo** contract. The pre-split monorepo marker
(`src/cli-tools` + `src/shared`) is not a build context any more; accepting it in the new API would
recreate the layout assumption the split exists to remove.

## Requirements

### Requirement: a build context root is a single project root

A build context root SHALL be a directory that contains a `pyproject.toml` file **and** a
`src/<import_name>/` directory. The resolver SHALL walk up from each candidate to the first
ancestor satisfying both conditions, and SHALL accept a candidate that is the root itself or any
directory inside it.

Source: spine AD-2, AD-6; `src/oci_runtime/source_locator.py`
(`_build_context_root_from_candidate`).

#### Scenario: the repo root is accepted

- **WHEN** `resolve_build_context(package="sample-pkg", override=root)` runs with `root` holding
  `pyproject.toml` and `src/sample_pkg/`
- **THEN** it returns `BuildContextRoot(root=<root>, source="override")`

#### Scenario: a package directory resolves up to its root

- **WHEN** the override is `root/src/sample_pkg/domain`
- **THEN** the returned root is still `root`, and `source` is `"override"`

#### Scenario: a monorepo checkout is rejected

- **WHEN** the override points at a directory containing only `src/cli-tools/` and `src/shared/`
- **THEN** the new API raises `SourceRootNotFoundError`, while the deprecated alias still accepts
  it

#### Scenario: a partial marker is rejected

- **WHEN** the candidate contains `pyproject.toml` but no `src/<import_name>/`, or `src/<import_name>`
  but no `pyproject.toml`
- **THEN** it is not accepted and resolution continues to the next candidate

### Requirement: the import name is derived by a documented rule

`import_name` SHALL default to `package.replace("-", "_")`. A consumer whose distribution name
does not match its import package SHALL pass `import_name=` explicitly; the resolver SHALL NOT
guess by scanning the filesystem.

Source: spine AD-6; `import_name_for` in `src/oci_runtime/source_locator.py`.

#### Scenario: the documented derivation

- **WHEN** `import_name_for("color-scheme-generator")` is evaluated
- **THEN** it returns `"color_scheme_generator"`

#### Scenario: an explicit name wins

- **WHEN** `resolve_build_context(package="distribution-name", import_name="sample_pkg",
  override=root)` runs
- **THEN** the marker is checked against `src/sample_pkg/`, not `src/distribution_name/`

### Requirement: resolution keeps the four-source priority order

`resolve_build_context` SHALL try candidates in this order and return the first that matches the
marker: (1) explicit `override`, (2) the caller-named `env_var` read from `env` or `os.environ`,
(3) the PEP 610 `direct_url.json` recorded by the installer, (4) a walk up from the package
location. The reported `source` SHALL be `override`, `env`, `direct_url` or `package`
respectively.

Source: spine AD-6; `source_locator.py` (`_candidate_sources`, `resolve_build_context`).

#### Scenario: override beats env and PEP 610

- **WHEN** all three are present and each matches the marker
- **THEN** the result's `source` is `"override"`

#### Scenario: env beats PEP 610

- **WHEN** no override is passed and both the env var and the PEP 610 record match
- **THEN** the result's `source` is `"env"`

#### Scenario: PEP 610 beats the package walk

- **WHEN** only the PEP 610 record and the installed package directory are available
- **THEN** the result's `source` is `"direct_url"`

#### Scenario: the package walk is the last resort

- **WHEN** only the package location matches the marker
- **THEN** the result's `source` is `"package"`

#### Scenario: an unmatched candidate falls through

- **WHEN** the override exists but does not carry the marker
- **THEN** resolution continues with the env, PEP 610 and package candidates rather than failing on
  the first miss

### Requirement: a missing context fails loudly

When no candidate satisfies the marker, `resolve_build_context` SHALL raise
`SourceRootNotFoundError` naming the package and, when supplied, the env var. It SHALL NOT return
a fallback path and SHALL NOT build an image from an unknown context.

Source: spine AD-6, AD-16; `source_locator.py`; `domain/exceptions.py`
(`SourceRootNotFoundError`).

#### Scenario: nothing resolves

- **WHEN** no candidate matches and the package is not installed
- **THEN** `SourceRootNotFoundError` is raised and its message names the package and the env var

### Requirement: `resolve_source_root` is a deprecated either-marker alias

`resolve_source_root` SHALL remain importable for one minor, SHALL emit `DeprecationWarning` on
every call, and SHALL accept **either** the build-context marker or the legacy monorepo marker
(a root containing `src/cli-tools/` and `src/shared/`). It SHALL use the same four-source priority
order and report the same `source` labels. It is removed in `0.6.0`.

Source: spine AD-6, AD-16; `source_locator.py` (`resolve_source_root`).

#### Scenario: the alias accepts a new repo root

- **WHEN** `resolve_source_root` is called with a single-repo root
- **THEN** it returns the root and emits a `DeprecationWarning`

#### Scenario: the alias keeps the monorepo buildable through the migration

- **WHEN** `resolve_source_root` is called with a pre-split monorepo root
- **THEN** it returns that root instead of raising, so in-tree consumers keep working

#### Scenario: new code cannot depend on the legacy marker

- **WHEN** `resolve_build_context` is called with the same monorepo root
- **THEN** it raises `SourceRootNotFoundError`

### Requirement: the CLI flag contract keeps `--source-root` as an alias

The image-build verb in a consuming CLI SHALL take `--context <checkout>` as the canonical flag
and SHALL keep `--source-root <checkout>` as an alias of it for one minor. Both SHALL feed the
same resolver call. The flag lives in the CLI repos (`csg`, `weg`); this repository owns the
resolver only and SHALL NOT define a CLI verb.

Source: spine AD-6, AD-7; slice S3 step 6.

#### Scenario: both flags reach the same resolver

- **WHEN** a consumer parses `install --context X` or `install --source-root X`
- **THEN** both produce the same `override=X` argument to `resolve_build_context`

#### Scenario: this repo ships no build verb

- **WHEN** `rg -n "source-root|--context" src` runs at this repo's root
- **THEN** it matches only the locator's docstring, not a CLI parser

### Requirement: no run-time path depends on a checkout

The locator SHALL be required only by the image-build path. No run-time container, image, network
or volume operation SHALL read a source checkout or the build-context root.

Source: spine AD-6; `rg -n "resolve_build_context|resolve_source_root" src` returns the locator and
its re-export only.

#### Scenario: run-time operations do not resolve a checkout

- **WHEN** a runtime/manager/parser adapter is exercised
- **THEN** it never imports or calls the locator

### Requirement: one package, repo root is the package root

The repo SHALL hold one `pyproject.toml` at its root and one import package at
`src/oci_runtime/`; tests SHALL live in `tests/` and there SHALL be no nested project root or
second OpenSpec root under `src/`.

Source: spine AD-2.

#### Scenario: layout on a fresh clone

- **WHEN** `test -f pyproject.toml -a -d src/oci_runtime -a -d tests` runs at the repo root
- **THEN** it exits 0, and `find src -name pyproject.toml` prints nothing

#### Scenario: the suite runs from the root

- **WHEN** `make test` runs on a fresh clone
- **THEN** exit 0 and the reported test count covers every module in `tests/`
