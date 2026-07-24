from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_worker_page_is_routed_and_reachable_from_navigation():
    app = (ROOT / 'frontend' / 'src' / 'App.tsx').read_text(encoding='utf-8')
    layout = (ROOT / 'frontend' / 'src' / 'components' / 'Layout.tsx').read_text(encoding='utf-8')
    page = (ROOT / 'frontend' / 'src' / 'pages' / 'WorkerGeneration.tsx').read_text(encoding='utf-8')
    assert 'WorkerGeneration' in app and '/project/:id/workers' in app
    assert 'Workers' in layout and "projectLink('workers')" in layout
    for required in ('startWorkerGeneration', 'target_mods', 'merge_rounds', 'Validated candidate ready'):
        assert required in page or required in (ROOT / 'frontend' / 'src' / 'lib' / 'api.ts').read_text(encoding='utf-8')


def test_worker_api_contract_is_registered():
    routes = (ROOT / 'backend' / 'app' / 'api' / 'routes' / 'ai.py').read_text(encoding='utf-8')
    client = (ROOT / 'frontend' / 'src' / 'lib' / 'api.ts').read_text(encoding='utf-8')
    assert '/generate/{project_id}/workers' in routes
    assert 'startWorkerGeneration' in client


def test_verification_contract_covers_compile_build_and_smoke_boundaries():
    workflow = (ROOT.parent / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')
    assert 'compileall' in workflow
    assert 'pytest' in workflow
    assert 'npm run build' in workflow
    assert 'verify_release.py' in workflow
