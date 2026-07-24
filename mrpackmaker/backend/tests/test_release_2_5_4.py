"""Regression coverage for the 2.5.4/2.5.5 startup fixes."""
from pathlib import Path

import app

ROOT = Path(__file__).resolve().parents[2]


def test_version_is_single_sourced_and_bumped():
    assert app.__version__ == '2.5.5'
    import app.main as main_module
    assert main_module.app.version == '2.5.5'


def test_health_route_reports_version():
    from app.api.routes import health
    assert health.__version__ == '2.5.5'


def test_start_bat_no_longer_has_ampersand_crash_and_is_current():
    text = (ROOT / 'start.bat').read_text(encoding='utf-8', errors='ignore')
    assert '2^>^&1' not in text
    assert 'scripts\\start.ps1' in text
    assert '2.5.5' in text


def test_start_ps1_uses_quote_safe_preflight_and_streaming():
    ps1 = (ROOT / 'scripts' / 'start.ps1').read_text(encoding='utf-8', errors='ignore')
    assert '2^>^&1' not in ps1
    assert 'Tee-Object' in ps1
    assert '2>&1' in ps1
    assert 'import app.main; print(1)' in ps1
    assert 'Backend launcher not found' in ps1
    assert 'between 1 and 65535' in ps1
    assert '2.5.5' in ps1


def test_installer_reports_versions_and_is_bumped():
    ps1 = (ROOT / 'scripts' / 'install.ps1').read_text(encoding='utf-8', errors='ignore')
    assert 'Python check:' in ps1
    assert 'Node check:' in ps1
    assert '2.5.5' in ps1
