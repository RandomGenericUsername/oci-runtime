"""Locate the source checkout used as a container image build context.

An image build needs the *source tree* of the CLI that owns the Dockerfile, not
the installed package: ``docker build`` / ``podman build`` copy ``pyproject.toml``,
``uv.lock`` and ``src/`` from the build context. When running from a source
checkout the package files already resolve to the repo, but from an installed
tool they resolve to the tool's site-packages, which contains only the packaged
Python code.

The build-context contract (architecture spine AD-6) is:

**A build context root is a directory that contains ``pyproject.toml`` AND
``src/<import_name>/``.**

``import_name`` is derived deterministically from ``package`` by replacing every
``-`` with ``_`` (``color-scheme-generator`` -> ``color_scheme_generator``). A
consumer whose distribution name does not match its import package passes
``import_name=`` explicitly; the rule is never guessed from the filesystem.

This module rediscovers that root from, in priority order:

1. an explicit ``override`` path (the CLI's ``--context`` flag; ``--source-root``
   remains an alias of it for one minor),
2. an env var named by the caller (``CSG_SOURCE_ROOT`` / ``WEG_SOURCE_ROOT``),
3. the PEP 610 ``direct_url.json`` the installer wrote into the package's
   ``.dist-info`` (uv and pip both record the original ``file://`` source path),
4. a walk up from the package location (source checkout / editable install,
   where the repo is still on disk).

If nothing resolves, :class:`SourceRootNotFoundError` is raised — the image
build cannot proceed, so the CLI must fail loudly instead of silently producing
a stale image (AD-16: behavioural compatibility, not layout preservation).

:func:`resolve_source_root` is the pre-0.5.0 name. It is deprecated for one
minor: it accepts **either** the new build-context marker **or** the legacy
monorepo marker (``src/cli-tools`` AND ``src/shared`` under one root), so
in-tree consumers keep working through the split. New code must call
:func:`resolve_build_context`.
"""

from __future__ import annotations

import json
import os
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, distribution
from importlib.resources import files as resource_files
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from oci_runtime.domain.exceptions import SourceRootNotFoundError

# The build-context marker: a repo root carries a project file and one import
# package directory. `src/<import_name>` is checked against the derived name.
_BUILD_CONTEXT_PROJECT_FILE = "pyproject.toml"

# The legacy monorepo marker (pre-split `dotfiles-v3`): a root contains both
# `src/cli-tools` and `src/shared`. Kept only for the deprecated alias so that
# callers still running against the monorepo keep building until the last
# in-tree copy is deleted (AD-16).
_LEGACY_REPO_MARKER_DIRS = (("src", "cli-tools"), ("src", "shared"))

# Backwards-compatible private name: the legacy marker tuple was exported as
# `_REPO_MARKER_DIRS` before 0.5.0.
_REPO_MARKER_DIRS = _LEGACY_REPO_MARKER_DIRS


@dataclass(frozen=True)
class BuildContextRoot:
    """The resolved build-context root plus how it was discovered."""

    root: Path
    source: str


# Pre-0.5.0 name for the same value object. Kept importable for one minor so
# existing callers and their type annotations keep working.
SourceRoot = BuildContextRoot


def import_name_for(package: str) -> str:
    """Return the deterministic import name for a distribution name.

    The rule is one substitution, documented rather than discovered:
    ``package.replace("-", "_")``. Consumers whose distribution name differs
    from their import package pass ``import_name=`` to the resolver instead of
    relying on a guess.
    """
    return package.replace("-", "_")


def _build_context_root_from_candidate(candidate: Path, import_name: str) -> Path | None:
    """Return the build-context root that contains ``candidate``, or None.

    Walks up from ``candidate`` looking for the first ancestor that carries a
    ``pyproject.toml`` file and a ``src/<import_name>`` directory. Works both
    when ``candidate`` is the repo root itself and when it is any directory
    inside the repo (package dir, ``src/``, a test directory, ...).
    """
    for parent in (candidate, *candidate.parents):
        project_file = parent / _BUILD_CONTEXT_PROJECT_FILE
        package_dir = parent / "src" / import_name
        if project_file.is_file() and package_dir.is_dir():
            return parent
    return None


def _legacy_repo_root_from_candidate(candidate: Path) -> Path | None:
    """Return the monorepo root that contains ``candidate``, or None.

    Deprecated with :func:`resolve_source_root`; accepts only the pre-split
    ``src/cli-tools`` + ``src/shared`` layout.
    """
    for parent in (candidate, *candidate.parents):
        if all((parent.joinpath(*part)).is_dir() for part in _LEGACY_REPO_MARKER_DIRS):
            return parent
    return None


def _repo_root_from_candidate(candidate: Path) -> Path | None:
    """Deprecated private alias for the legacy monorepo marker check."""
    return _legacy_repo_root_from_candidate(candidate)


def _direct_url_package_dir(package: str) -> Path | None:
    """Return the install-source directory recorded by PEP 610, or None."""
    try:
        dist = distribution(package)
    except PackageNotFoundError:
        return None
    try:
        raw = dist.read_text("direct_url.json")
    except (OSError, AttributeError):
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    url = data.get("url")
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "file":
        return None
    return Path(url2pathname(parsed.path))


def _resource_package_dir(package: str) -> Path | None:
    """Return the on-disk package directory from ``importlib.resources``.

    Only meaningful for source checkouts and editable installs, where the
    package files live inside the repo. From a regular installed tool this
    returns the site-packages package dir, which carries no repo marker.
    """
    try:
        res = resource_files(package)
    except (ModuleNotFoundError, TypeError, NotImplementedError):
        return None
    try:
        pkg_path = Path(str(res))
    except (TypeError, ValueError):
        return None
    if not pkg_path.is_dir():
        return None
    return pkg_path


def _candidate_sources(
    *,
    package: str,
    override: str | Path | None,
    env_var: str | None,
    env: Mapping[str, str] | None,
) -> list[tuple[str, Path]]:
    """Collect the four candidate sources in priority order.

    A candidate may not match the marker; the caller decides which marker to
    apply. Unreadable or malformed PEP 610 metadata is treated as "no
    candidate" rather than an error, so the chain falls through as documented.

    A relative ``override`` is accepted as given (resolved by the caller's
    working directory semantics of ``Path``); the marker walk still applies.
    """
    candidates: list[tuple[str, Path]] = []

    if override is not None:
        candidates.append(("override", Path(override)))

    if env_var is not None:
        value = (env if env is not None else os.environ).get(env_var)
        if value:
            candidates.append(("env", Path(value)))

    pkg_dir = _direct_url_package_dir(package)
    if pkg_dir is not None:
        candidates.append(("direct_url", pkg_dir))

    pkg_dir = _resource_package_dir(package)
    if pkg_dir is not None:
        candidates.append(("package", pkg_dir))

    return candidates


def resolve_build_context(
    *,
    package: str,
    override: str | Path | None = None,
    env_var: str | None = None,
    env: Mapping[str, str] | None = None,
    import_name: str | None = None,
) -> BuildContextRoot:
    """Resolve the build-context root for ``package``.

    Priority: ``override`` > ``env_var`` > PEP 610 ``direct_url.json`` > package
    walk. A candidate is accepted only when it contains ``pyproject.toml`` and
    ``src/<import_name>``; the legacy monorepo marker is **not** accepted here
    (that is the whole point of the cutover, AD-5/AD-6).

    ``import_name`` defaults to ``package.replace("-", "_")``. Raises
    :class:`SourceRootNotFoundError` when no candidate matches.
    """
    resolved_import = import_name if import_name is not None else import_name_for(package)

    for source, candidate in _candidate_sources(
        package=package, override=override, env_var=env_var, env=env
    ):
        root = _build_context_root_from_candidate(candidate, resolved_import)
        if root is not None:
            return BuildContextRoot(root=root, source=source)

    raise SourceRootNotFoundError(package=package, env_var=env_var)


def resolve_source_root(
    *,
    package: str,
    override: str | Path | None = None,
    env_var: str | None = None,
    env: Mapping[str, str] | None = None,
    import_name: str | None = None,
) -> BuildContextRoot:
    """Deprecated alias of :func:`resolve_build_context` (removed in 0.6.0).

    Accepts **either** marker set: the new build-context marker
    (``pyproject.toml`` + ``src/<import_name>``) or the legacy monorepo marker
    (``src/cli-tools`` + ``src/shared``). The either-marker behaviour is what
    keeps in-tree consumers building during the migration (AD-6, AD-16); new
    code must call :func:`resolve_build_context`, which accepts only the new
    marker.

    Emits :class:`DeprecationWarning` on every call.
    """
    warnings.warn(
        "resolve_source_root() is deprecated; use resolve_build_context(). "
        "It accepts the legacy monorepo marker and will be removed in 0.6.0.",
        DeprecationWarning,
        stacklevel=2,
    )

    resolved_import = import_name if import_name is not None else import_name_for(package)

    for source, candidate in _candidate_sources(
        package=package, override=override, env_var=env_var, env=env
    ):
        root = _build_context_root_from_candidate(candidate, resolved_import)
        if root is None:
            root = _legacy_repo_root_from_candidate(candidate)
        if root is not None:
            return BuildContextRoot(root=root, source=source)

    raise SourceRootNotFoundError(package=package, env_var=env_var)
