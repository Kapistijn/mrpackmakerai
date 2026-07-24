from pathlib import Path
import app
from app.schemas.project import ProjectSettings
from app.models.enums import LoaderType,ThemeType
ROOT=Path(__file__).resolve().parents[2]
def test_release_version_is_aligned():
 assert app.__version__=='2.5.6'
 assert '2.5.6' in (ROOT/'frontend/package.json').read_text(encoding='utf-8')
 assert "$Version = '2.5.6'" in (ROOT/'scripts/start.ps1').read_text(encoding='utf-8')
 assert "$Version='2.5.6'" in (ROOT/'scripts/install.ps1').read_text(encoding='utf-8')
def test_project_worker_count_defaults_and_bounds():
 value=ProjectSettings(minecraft_version='1.20.1',loader=LoaderType.FABRIC,name='x',description='x',theme=ThemeType.SURVIVAL)
 assert value.worker_count==4
 assert ProjectSettings.model_fields['worker_count'].default==4
