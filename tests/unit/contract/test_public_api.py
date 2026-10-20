import oci_runtime


class TestPublicAPI:
    def test_all_names_importable(self):
        for name in oci_runtime.__all__:
            assert getattr(oci_runtime, name) is not None

    def test_adapters_not_exported(self):
        for name in (
            "CliTransport",
            "CliRuntime",
            "DockerRuntimeProvider",
            "PodmanRuntimeProvider",
        ):
            assert name not in oci_runtime.__all__

    def test_runtime_kind_importable(self):
        from oci_runtime import RuntimeKind

        assert RuntimeKind is oci_runtime.RuntimeKind

    def test_build_context_api_is_public(self):
        from oci_runtime import (
            BuildContextRoot,
            import_name_for,
            resolve_build_context,
            resolve_source_root,
        )

        assert BuildContextRoot is oci_runtime.BuildContextRoot
        assert resolve_build_context is oci_runtime.resolve_build_context
        # Deprecated alias stays importable for one minor (AD-6).
        assert resolve_source_root is oci_runtime.resolve_source_root
        assert import_name_for("sample-pkg") == "sample_pkg"
        assert "resolve_build_context" in oci_runtime.__all__
        assert "resolve_source_root" in oci_runtime.__all__
