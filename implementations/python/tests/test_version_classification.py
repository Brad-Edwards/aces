"""GOV-901 version-literal classification tests.

The ecosystem versioning policy
(``specs/evolution/versioning-deprecation-and-migration.md``) requires version
identifiers on the Python-distribution surface to derive from the installed
distribution metadata (the release-please-owned source of truth), and to fall
back to the honest PEP 440 sentinel ``0.0.0+unknown`` when the distribution is
not installed — never a plausible-looking hard-coded release such as ``0.1.0``
that would imply a compatibility guarantee the repository cannot honour.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, entry_points, version
from importlib.util import find_spec

from typer.testing import CliRunner

NOT_INSTALLED_SENTINEL = "0.0.0+unknown"
DISHONEST_LITERAL = "0.1.0"
RETIRED_IMPORT_NAMES = (
    "aces",
    "aces_sdl",
    "aces_backend_libvirt",
    "aces_backend_protocols",
    "aces_backend_stubs",
    "aces_cli",
    "aces_conformance",
    "aces_contracts",
    "aces_mcp",
    "aces_operations",
    "aces_processor",
    "aces_reference_backend",
    "aces_runtime",
)


def test_raes_namespace_version_derives_from_distribution() -> None:
    import raes

    assert raes.__version__ == version("raes")


def test_retired_aces_namespaces_are_absent() -> None:
    assert all(find_spec(name) is None for name in RETIRED_IMPORT_NAMES)


def test_cli_version_reports_installed_distribution() -> None:
    from raes_cli.main import app

    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout == f"raes {version('raes')}\n"


def test_cli_help_uses_raes_project_identity() -> None:
    from raes_cli.main import app

    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "RAES" in result.stdout


def test_console_scripts_hard_cut_to_raes_names() -> None:
    scripts = {
        entry_point.name
        for entry_point in entry_points(group="console_scripts")
        if entry_point.value in {"raes_cli.main:app", "raes_mcp.server:main"}
    }

    assert {"raes", "raes-mcp"} <= scripts
    assert "aces" not in scripts
    assert "aces-mcp" not in scripts


def test_cli_version_fallback_is_honest_sentinel(monkeypatch) -> None:
    import raes_cli.main as cli_main

    def _raise(_distribution: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(cli_main, "version", _raise)
    result = CliRunner().invoke(cli_main.app, ["--version"])

    assert result.exit_code == 0
    assert NOT_INSTALLED_SENTINEL in result.stdout
    assert DISHONEST_LITERAL not in result.stdout


def test_control_plane_api_version_derives_from_distribution() -> None:
    from raes_runtime.control_plane_api import _control_plane_api_version

    assert _control_plane_api_version() == version("raes")


def test_control_plane_api_version_fallback_is_honest_sentinel(monkeypatch) -> None:
    import raes_runtime.control_plane_api as control_plane_api

    def _raise(_distribution: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(control_plane_api, "distribution_version", _raise)

    assert control_plane_api._control_plane_api_version() == NOT_INSTALLED_SENTINEL


def test_control_plane_app_openapi_version_matches_distribution() -> None:
    from raes_runtime.control_plane import RuntimeControlPlane
    from raes_runtime.control_plane_api import create_control_plane_app

    from raes_backend_stubs.stubs import create_stub_target

    app = create_control_plane_app(RuntimeControlPlane(create_stub_target()))

    assert app.title == "RAES Runtime Control Plane"
    assert app.version == version("raes")
