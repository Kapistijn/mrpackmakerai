from __future__ import annotations
import json,zipfile
from app.models.project import Project
from app.schemas.mod import ModEntry,ModHash
from app.services.modpack_importer import import_manifest

def test_project_constructor_defaults_all_new_fields():
 p=Project(name='legacy',description='',minecraft_version='1.20.1',loader='fabric',theme='survival')
 assert p.mods_json=='[]' and p.shader_support=='off' and p.required_mods_json=='[]' and p.forbidden_mods_json=='[]'
 assert p.ai_creativity=='balanced' and p.ai_strictness=='balanced' and p.discovery_depth=='standard'

def test_import_rejects_unsafe_manifest_path(tmp_path):
 path=tmp_path/'bad.mrpack';manifest={'formatVersion':1,'game':'minecraft','dependencies':{'minecraft':'1.20.1','fabric-loader':'0.15.11'},'files':[{'path':'../escape.jar','fileSize':1,'downloads':['https://cdn.modrinth.com/a.jar'],'hashes':{'sha1':'a'*40}}]}
 with zipfile.ZipFile(path,'w') as z:z.writestr('modrinth.index.json',json.dumps(manifest))
 try:import_manifest(str(path))
 except ValueError as exc:assert 'Unsafe' in str(exc)
 else:raise AssertionError('unsafe manifest was accepted')

def test_import_preserves_shader_install_path(tmp_path):
 path=tmp_path/'shader.mrpack';manifest={'formatVersion':1,'game':'minecraft','dependencies':{'minecraft':'1.20.1','fabric-loader':'0.15.11'},'files':[{'path':'shaderpacks/test.zip','fileSize':1,'downloads':['https://cdn.modrinth.com/test.zip'],'hashes':{'sha1':'a'*40}}]}
 with zipfile.ZipFile(path,'w') as z:z.writestr('modrinth.index.json',json.dumps(manifest))
 result=import_manifest(str(path));assert result['mods'][0].source=='imported' and result['mods'][0].install_path=='shaderpacks/test.zip'
