from __future__ import annotations
import json,zipfile
import pytest
from app.models.project import Project
from app.models.pack_snapshot import PackSnapshot
from app.schemas.mod import ModDependency,ModEntry,ModHash
from app.services.dependency_analysis import analyze_dependencies
from app.services.hardware_intelligence import hardware_fit
from app.services.modpack_importer import import_manifest
from app.services.mrpack_paths import is_safe_install_path

def mod(name,categories=(),deps=()):
 return ModEntry(id=name,source='modrinth',name=name,slug=name,categories=list(categories),dependencies=list(deps),file_name=name+'.jar',file_size=10,download_url='https://cdn.modrinth.com/'+name+'.jar',hashes=ModHash(sha1='a'*40))
def test_single_path_policy_accepts_all_relative_instance_folders():
 for path in ('mods/a.jar','config/x.json','defaultconfigs/a.toml','kubejs/server.js','scripts/start.zs','resource_overrides/x.txt','shaderpacks/a.zip','resourcepacks/a.zip'):assert is_safe_install_path(path)
 assert not is_safe_install_path('/absolute/a.jar');assert not is_safe_install_path('../escape.jar');assert not is_safe_install_path('a/../b.jar')
def test_mixed_folder_manifest_imports_and_keeps_install_paths(tmp_path):
 manifest={'formatVersion':1,'game':'minecraft','dependencies':{'minecraft':'1.20.1','fabric-loader':'0.15.11'},'files':[{'path':p,'downloads':['https://cdn.modrinth.com/x'],'fileSize':1,'hashes':{'sha1':'a'*40}} for p in ('mods/a.jar','config/x.json','kubejs/server.js','defaultconfigs/a.toml','scripts/start.zs','resource_overrides/x.txt','shaderpacks/a.zip','resourcepacks/a.zip')]}
 path=tmp_path/'mixed.mrpack'
 with zipfile.ZipFile(path,'w') as archive:archive.writestr('modrinth.index.json',json.dumps(manifest))
 result=import_manifest(str(path));assert {m.install_path for m in result['mods']}=={x['path'] for x in manifest['files']}
def test_dependency_analysis_reports_cycles_missing_optional_and_incompatible():
 a=mod('a',deps=(ModDependency(project_id='b',dependency_type='required'),ModDependency(project_id='missing',dependency_type='required'),ModDependency(project_id='opt',dependency_type='optional'),ModDependency(project_id='bad',dependency_type='incompatible')));b=mod('b',deps=(ModDependency(project_id='a',dependency_type='required'),));bad=mod('bad')
 report=analyze_dependencies([a,b,bad]);types={x['type'] for x in report['issues']};assert 'cycle' in types and 'missing' in types and 'incompatible' in types;assert report['optional']
def test_real_hardware_names_and_resolution_affect_fit():
 performance={'ram_gb':14,'vram_gb':5,'expected_fps':{'low':120,'high':160}}
 weak=hardware_fit({'cpu':'Intel i5','gpu':'RTX 3060','ram_gb':16,'resolution':'3840x2160','refresh_rate':144,'target_fps':144},performance)
 strong=hardware_fit({'cpu':'Ryzen 9','gpu':'RTX 4090','ram_gb':32,'resolution':'1920x1080','refresh_rate':144,'target_fps':120},performance)
 assert strong['score']>weak['score'] and weak['resolution_multiplier']>strong['resolution_multiplier']
def test_snapshot_model_contains_complete_state_columns():
 assert {'project_json','mods_json','analysis_json','hardware_json','pack_metadata_json','generated_files_json'} <= set(PackSnapshot.__table__.columns.keys())
@pytest.mark.parametrize('loader', ['fabric','forge','neoforge'])
def test_project_defaults_remain_backward_compatible(loader):
 p=Project(name='legacy',description='',minecraft_version='1.20.1',loader=loader,theme='survival');assert p.mods_json=='[]' and p.shader_support=='off'
