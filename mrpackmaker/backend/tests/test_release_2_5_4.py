"""Regression coverage for the 2.5.4 startup-crash fix and launcher hardening."""
from pathlib import Path

import app

ROOT = Path(__file__).resolve().parents[2]


def test_version_is_single_sourced_and_bumped():
    assert app.__version__ == '2.5.4'
    import app.main as main_module
    assert main_module.app.version == '2.5.4'


def test_health_route_reports_version():
    from app.api.routes import health
    assert health.__version__ == '2.5.4'


def test_start_bat_no_longer_has_ampersand_crash():
    text = (ROOT / 'start.bat').read_text(encoding='utf-8', errors='ignore')
    # The literal caret-escaped redirection is what PowerShell rejected with
    # AmpersandNotAllowed. It must be gone and delegated to the .ps1 engine.
    assert '2^>^&1' not in text
    assert 'scripts\\start.ps1' in text


def test_start_ps1_streams_logs_without_caret_escaping():
    ps1 = (ROOT / 'scripts' / 'start.ps1').read_text(encoding='utf-8', errors='ignore')
    assert '2^>^&1' not in ps1
    assert 'Tee-Object' in ps1
    assert '2>&1' in ps1
    # The launcher must surface the version and the target URL.
    assert '2.5.4' in ps1


def test_installer_reports_versions_and_is_bumped():
    ps1 = (ROOT / 'scripts' / 'install.ps1').read_text(encoding='utf-8', errors='ignore')
    assert 'Python check:' in ps1
    assert 'Node check:' in ps1
    assert '2.5.4' in ps1
