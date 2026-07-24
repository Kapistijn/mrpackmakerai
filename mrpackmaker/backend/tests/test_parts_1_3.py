from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_startup_uses_native_process_logging_without_pipeline_error_records():
    text = (ROOT / 'scripts' / 'start.ps1').read_text(encoding='utf-8')
    assert 'ProcessStartInfo' in text
    assert 'RedirectStandardOutput' in text
    assert 'RedirectStandardError' in text
    assert 'ArgumentList.Add' not in text
    assert "@('-c','import app.main; print(1)')" in text


def test_navigation_keeps_core_sections_visible_without_project():
    text = (ROOT / 'frontend' / 'src' / 'components' / 'Layout.tsx').read_text(encoding='utf-8')
    for label in ('Dashboard', 'New Project', 'Projects', 'Advanced', 'Intelligence', 'Settings', 'API'):
        assert label in text
    assert "const projectPath=projectId?`/project/${projectId}`:'/'" in text
    assert 'onClick={e=>{if(!projectId)e.preventDefault()}}' in text


def test_intelligence_import_stays_on_page_and_loads_report():
    text = (ROOT / 'frontend' / 'src' / 'pages' / 'Intelligence.tsx').read_text(encoding='utf-8')
    assert 'Upload Existing MRPack' in text
    assert 'api.importMrpack(file)' in text
    assert 'setImportedReport' in text
    assert 'result.analysis?.report' in text
    assert 'Report loaded in this page' in text
