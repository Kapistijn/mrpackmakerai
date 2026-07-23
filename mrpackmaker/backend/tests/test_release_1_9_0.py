from __future__ import annotations
import json,zipfile
from pathlib import Path
from app.models.project import Project
from app.schemas.mod import ModEntry,ModHash
from app.services.change_planner import plan_change
from app.services.crash_analyzer import analyze_crash
from app.services.conflict_resolver import conflict_options
from app.services.modpack_importer import import_manifest
from app.services.repair_engine import repair_report

def mod(name,categories=()):return ModEntry(id=name,source='modrinth',name=name,slug=name,categories=list(categories),file_name=name+'.jar',file_size=10,download_url='https://cdn.modrinth.com/'+name+'.jar',hashes=ModHash(sha1='a'*40))
def test_editor_plan_requires_approval_and_preserves_choices():
 plan=plan_change('remove all magic mods',[mod('Create',['technology']),mod('Wizardry',['magic'])])
 assert plan.requires_approval and 'Wizardry' in plan.remove_names and 'Create' not in plan.remove_names
def test_import_manifest_reads_runtime_and_mod_files(tmp_path):
 path=tmp_path/'pack.mrpack'
 manifest={'formatVersion':1,'game':'minecraft','dependencies':{'minecraft':'1.20.1','fabric-loader':'0.15.11'},'files':[{'path':'mods/a.jar','fileSize':3,'downloads':['https://cdn.modrinth.com/a.jar'],'hashes':{'sha1':'a'*40}}]}
 with zipfile.ZipFile(path,'w') as z:z.writestr('modrinth.index.json',json.dumps(manifest))
 result=import_manifest(str(path),None)
 assert result['minecraft_version']=='1.20.1' and result['loader']=='fabric-loader' and result['mods'][0].file_name=='a.jar'
def test_crash_analysis_and_repair():
 result=analyze_crash('Create requires Flywheel')
 assert result['status']=='conflict' and result['conflicts'][0]['left']=='Create'
 assert 'preserve both mods' in repair_report('Create requires Flywheel')['recommended']
def test_conflict_options_recommend_preserve_strategy():
 options=conflict_options([{'left':'Create','right':'OptiFine'}])[0]['solutions']
 assert options[0]['recommended'] and 'Create' in options[0]['label']
def test_legacy_project_still_has_generation_defaults():
 project=Project(name='legacy',description='',minecraft_version='1.20.1',loader='fabric',theme='survival')
 assert project.mods_json=='[]' and project.shader_support=='off'
