from __future__ import annotations
import inspect
from app.models.project import Project
from app.models.pack_snapshot import PackSnapshot
from app.schemas.mod import ModDependency,ModEntry,ModHash
from app.services.ai_orchestrator import AIOrchestrator
from app.services.dependency_analysis import analyze_dependencies
from app.services.hardware_intelligence import selection_hints
from app.services.mrpack_paths import is_safe_install_path
from app.services.mrpack_validation import validate_export_inputs

def mod(name,deps=()):
 return ModEntry(id=name,source='modrinth',name=name,slug=name,dependencies=list(deps),file_name=name+'.jar',file_size=10,download_url='https://cdn.modrinth.com/'+name+'.jar',hashes=ModHash(sha1='a'*40))
def project():return Project(name='p',description='',minecraft_version='1.20.1',loader='fabric',theme='survival',resolved_loader_version='0.15.11')
def test_legacy_unsafe_filename_contract_and_traversal_protection():
 codes=[x.code for x in validate_export_inputs(project(),[mod('../outside')])]
 assert 'unsafe_file_name' in codes
 assert not is_safe_install_path('../outside.jar') and is_safe_install_path('config/a.json')
def test_dependency_metadata_reports_contextual_issues():
 a=mod('a',(ModDependency(project_id='b',dependency_type='required',loaders=['forge'],minecraft_versions=['1.19.2'],version_range='>=2'),))
 report=analyze_dependencies([a],minecraft_version='1.20.1',loader='fabric')
 assert {'missing','loader_conflict','minecraft_conflict'} <= {x['type'] for x in report['issues']}
 assert all({'cause','affected_mods','confidence','recommended_fixes'} <= set(x) for x in report['issues'])
def test_hardware_changes_selection_hints():
 low=Project(name='low',description='',minecraft_version='1.20.1',loader='fabric',theme='survival',target_ram_gb=4,hardware_gpu='GTX 1660',hardware_cpu='Intel Celeron')
 high=Project(name='high',description='',minecraft_version='1.20.1',loader='fabric',theme='survival',target_ram_gb=32,hardware_gpu='RTX 4090',hardware_cpu='Ryzen 9')
 assert selection_hints(low)['low_hardware'] and not selection_hints(high)['low_hardware']
def test_snapshot_state_schema_is_complete():
 assert {'project_json','mods_json','analysis_json','hardware_json','pack_metadata_json','generated_files_json'} <= set(PackSnapshot.__table__.columns.keys())
def test_generation_source_contains_backend_compatibility_gate_before_analysis():
 source=inspect.getsource(AIOrchestrator.generate)
 assert source.index('repair_project_dependencies') < source.index('persist_analysis') < source.index('self._emit')
