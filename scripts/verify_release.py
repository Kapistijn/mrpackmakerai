"""Fast, offline release gate for repository invariants.

Network-dependent AI/catalog and Windows smoke tests stay explicit follow-ups;
this gate verifies the checks that CI can run deterministically on Linux.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'mrpackmaker' / 'backend'
FRONTEND = ROOT / 'mrpackmaker' / 'frontend'


def require(path: Path, *needles: str) -> None:
    text = path.read_text(encoding='utf-8')
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f'{path}: missing required release contract: {missing}')


def main() -> int:
    subprocess.run([sys.executable, '-m', 'compileall', '-q', 'app', 'tests'], cwd=BACKEND, check=True)
    require(BACKEND / 'app' / 'main.py', 'FastAPI', 'include_router')
    require(BACKEND / 'app' / 'services' / 'mrpack_validation.py', 'validate_export_inputs')
    require(BACKEND / 'app' / 'services' / 'worker_generation.py', 'merge_rounds', 'AsyncCoalescingCache')
    require(BACKEND / 'app' / 'api' / 'routes' / 'ai.py', '/generate/{project_id}/workers')
    require(FRONTEND / 'src' / 'App.tsx', 'WorkerGeneration', '/project/:id/workers')
    require(FRONTEND / 'src' / 'pages' / 'WorkerGeneration.tsx', 'startWorkerGeneration', 'merge_rounds')
    require(ROOT / 'mrpackmaker' / 'start.bat', 'scripts\\start.ps1')
    require(ROOT / 'mrpackmaker' / 'scripts' / 'start.ps1', 'RedirectStandardOutput', 'RedirectStandardError')
    print('offline release verification: PASS')
    print('external smoke gates remain: AI provider, catalog, Windows PowerShell 5.1, MRPack round-trip')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
