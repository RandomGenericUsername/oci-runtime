from __future__ import annotations

import json
from pathlib import Path

import pytest

from oci_runtime.domain.exceptions import SourceRootNotFoundError
from oci_runtime.source_locator import (
    BuildContextRoot,
    SourceRoot,
    _direct_url_package_dir,
    _repo_root_from_candidate,
    import_name_for,
    resolve_build_context,
    resolve_source_root,
)

# A package name that is not installed in the test environment, so the
# direct_url / package candidates are always empty and an override that does
# not match the marker really does raise.
UNINSTALLED = "not_installed_pkg_xyz"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A post-split repo root: <root>/pyproject.toml + <root>/src/sample_pkg/."""
    root = tmp_path / "cli-repo"
    (root / "src" / "sample_pkg").mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nname = "sample-pkg"\n')
    return root


@pytest.fixture
def legacy_repo(tmp_path: Path) -> Path:
    """A pre-split monorepo root: <root>/src/{cli-tools,shared}/."""
    root = tmp_path / "dotfiles-repo"
    (root / "src" / "cli-tools").mkdir(parents=True)
    (root / "src" / "shared").mkdir(parents=True)
    return root


class TestImportNameRule:
    def test_hyphens_become_underscores(self) -> None:
        assert import_name_for("color-scheme-generator") == "color_scheme_generator"

    def test_underscore_name_is_unchanged(self) -> None:
        assert import_name_for("oci_runtime") == "oci_runtime"


class TestBuildContextRootFromCandidate:
    def test_repo_root_is_accepted(self, repo: Path) -> None:
        # The public probe from the slice gate: the new marker resolves.
        result = resolve_build_context(package="sample-pkg", override=repo)
        assert result == BuildContextRoot(root=repo, source="override")

    def test_package_dir_resolves_up_to_repo_root(self, repo: Path) -> None:
        pkg = repo / "src" / "sample_pkg"
        result = resolve_build_context(package="sample-pkg", override=pkg)
        assert result.root == repo
        assert result.source == "override"

    def test_deep_nested_candidate_resolves(self, repo: Path) -> None:
        nested = repo / "src" / "sample_pkg" / "domain" / "deep"
        nested.mkdir(parents=True)
        assert resolve_build_context(package="sample-pkg", override=nested).root == repo

    def test_explicit_import_name_overrides_the_rule(self, repo: Path) -> None:
        # package name and import dir genuinely differ for this caller.
        result = resolve_build_context(
            package="distribution-name",
            import_name="sample_pkg",
            override=repo,
        )
        assert result.root == repo

    def test_legacy_monorepo_root_is_rejected(self, legacy_repo: Path) -> None:
        # AD-6: the new API accepts only the build-context marker. A monorepo
        # checkout has no pyproject.toml + src/<pkg> at its root.
        with pytest.raises(SourceRootNotFoundError):
            resolve_build_context(package=UNINSTALLED, override=legacy_repo)

    def test_pyproject_only_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "no-package"
        root.mkdir()
        (root / "pyproject.toml").write_text('[project]\nname = "x"\n')
        with pytest.raises(SourceRootNotFoundError):
            resolve_build_context(package=UNINSTALLED, override=root)

    def test_src_package_without_pyproject_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "no-project"
        (root / "src" / UNINSTALLED).mkdir(parents=True)
        with pytest.raises(SourceRootNotFoundError):
            resolve_build_context(package=UNINSTALLED, override=root)

    def test_other_package_dir_is_not_a_match(self, repo: Path) -> None:
        # pyproject.toml exists but src/<other> does not: marker must be exact.
        with pytest.raises(SourceRootNotFoundError):
            resolve_build_context(package="another-package", override=repo)


class TestResolveBuildContextPriority:
    def test_override_wins_over_env_and_pep610(
        self, repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_root = tmp_path / "from-env"
        (env_root / "src" / "sample_pkg").mkdir(parents=True)
        (env_root / "pyproject.toml").write_text("[project]\n")
        pep_root = tmp_path / "from-pep610"
        (pep_root / "src" / "sample_pkg").mkdir(parents=True)
        (pep_root / "pyproject.toml").write_text("[project]\n")
        monkeypatch.setattr(
            "oci_runtime.source_locator._direct_url_package_dir", lambda p: pep_root
        )
        monkeypatch.setattr(
            "oci_runtime.source_locator._resource_package_dir", lambda p: None
        )

        result = resolve_build_context(
            package="sample-pkg",
            override=repo,
            env_var="SAMPLE_SOURCE_ROOT",
            env={"SAMPLE_SOURCE_ROOT": str(env_root)},
        )
        assert (result.root, result.source) == (repo, "override")

    def test_env_wins_over_pep610(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_root = repo
        pep_root = repo.parent / "pep610"
        (pep_root / "src" / "sample_pkg").mkdir(parents=True)
        (pep_root / "pyproject.toml").write_text("[project]\n")
        monkeypatch.setattr(
            "oci_runtime.source_locator._direct_url_package_dir", lambda p: pep_root
        )
        monkeypatch.setattr(
            "oci_runtime.source_locator._resource_package_dir", lambda p: None
        )
        result = resolve_build_context(
            package="sample-pkg",
            env_var="SAMPLE_SOURCE_ROOT",
            env={"SAMPLE_SOURCE_ROOT": str(env_root)},
        )
        assert (result.root, result.source) == (repo, "env")

    def test_pep610_wins_over_package_walk(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pep_root = repo
        pkg_root = repo.parent / "package-walk"
        (pkg_root / "src" / "sample_pkg").mkdir(parents=True)
        (pkg_root / "pyproject.toml").write_text("[project]\n")
        monkeypatch.setattr(
            "oci_runtime.source_locator._direct_url_package_dir", lambda p: pep_root
        )
        monkeypatch.setattr(
            "oci_runtime.source_locator._resource_package_dir", lambda p: pkg_root
        )
        result = resolve_build_context(package="sample-pkg")
        assert (result.root, result.source) == (repo, "direct_url")

    def test_package_walk_is_the_last_resort(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "oci_runtime.source_locator._direct_url_package_dir", lambda p: None
        )
        monkeypatch.setattr(
            "oci_runtime.source_locator._resource_package_dir", lambda p: repo
        )
        result = resolve_build_context(package="sample-pkg")
        assert (result.root, result.source) == (repo, "package")

    def test_missing_everywhere_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oci_runtime.source_locator._direct_url_package_dir", lambda p: None
        )
        monkeypatch.setattr(
            "oci_runtime.source_locator._resource_package_dir", lambda p: None
        )
        with pytest.raises(SourceRootNotFoundError) as exc:
            resolve_build_context(package=UNINSTALLED, env_var="SAMPLE_SOURCE_ROOT")
        assert "source repo" in str(exc.value)
        assert "SAMPLE_SOURCE_ROOT" in str(exc.value)


class TestDeprecatedAlias:
    def test_new_repo_root_is_accepted(self, repo: Path) -> None:
        with pytest.warns(DeprecationWarning, match="resolve_build_context"):
            result = resolve_source_root(package="sample-pkg", override=repo)
        assert result == SourceRoot(root=repo, source="override")

    def test_legacy_monorepo_root_is_still_accepted(self, legacy_repo: Path) -> None:
        with pytest.warns(DeprecationWarning):
            result = resolve_source_root(package=UNINSTALLED, override=legacy_repo)
        assert result.root == legacy_repo
        assert result.source == "override"

    def test_alias_reports_direct_url_source(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "oci_runtime.source_locator._direct_url_package_dir", lambda p: repo
        )
        monkeypatch.setattr(
            "oci_runtime.source_locator._resource_package_dir", lambda p: None
        )
        with pytest.warns(DeprecationWarning):
            result = resolve_source_root(package="sample-pkg")
        assert (result.root, result.source) == (repo, "direct_url")

    def test_alias_raises_when_nothing_matches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "oci_runtime.source_locator._direct_url_package_dir", lambda p: None
        )
        monkeypatch.setattr(
            "oci_runtime.source_locator._resource_package_dir", lambda p: None
        )
        with pytest.warns(DeprecationWarning), pytest.raises(SourceRootNotFoundError):
            resolve_source_root(package=UNINSTALLED)


class TestLegacyMarkerHelper:
    """The private helper keeps its pre-0.5.0 behaviour for the alias path only."""

    def test_candidate_is_repo_root(self, legacy_repo: Path) -> None:
        assert _repo_root_from_candidate(legacy_repo) == legacy_repo

    def test_candidate_is_deep_nested(self, legacy_repo: Path) -> None:
        pkg = (
            legacy_repo
            / "src"
            / "cli-tools"
            / "color-scheme-generator"
            / "src"
            / "color_scheme_generator"
        )
        pkg.mkdir(parents=True)
        assert _repo_root_from_candidate(pkg) == legacy_repo

    def test_no_marker_returns_none(self, tmp_path: Path) -> None:
        assert _repo_root_from_candidate(tmp_path / "no-such-dir") is None


def _fake_dist(direct_url_content: str) -> object:
    dist = type("FakeDist", (), {})()
    dist.read_text = lambda _name: direct_url_content
    return dist


class TestDirectUrlPackageDir:
    def test_parses_file_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        pkg = tmp_path / "csg"
        pkg.mkdir()
        monkeypatch.setattr(
            "oci_runtime.source_locator.distribution",
            lambda _pkg: _fake_dist(
                json.dumps({"url": pkg.as_uri(), "dir_info": {}})
            ),
        )
        assert _direct_url_package_dir("color_scheme_generator") == pkg

    def test_editable_url_parsed_the_same(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pkg = tmp_path / "csg"
        pkg.mkdir()
        monkeypatch.setattr(
            "oci_runtime.source_locator.distribution",
            lambda _pkg: _fake_dist(
                json.dumps({"url": pkg.as_uri(), "dir_info": {"editable": True}})
            ),
        )
        assert _direct_url_package_dir("p") == pkg

    def test_non_file_url_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oci_runtime.source_locator.distribution",
            lambda _pkg: _fake_dist(
                json.dumps({"url": "https://example.com/csg.tar.gz", "dir_info": {}})
            ),
        )
        assert _direct_url_package_dir("p") is None

    def test_missing_package_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oci_runtime.source_locator.distribution",
            lambda _pkg: (_ for _ in ()).throw(
                __import__("importlib.metadata", fromlist=["PackageNotFoundError"]).PackageNotFoundError("p")
            ),
        )
        assert _direct_url_package_dir("p") is None

    def test_bad_json_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oci_runtime.source_locator.distribution",
            lambda _pkg: _fake_dist("{not json"),
        )
        assert _direct_url_package_dir("p") is None
