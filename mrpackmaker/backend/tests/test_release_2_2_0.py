"""2.2.0: robust MRPack import + moved advanced settings."""
from __future__ import annotations
import json,zipfile
import pytest
from app.services.modpack_importer import import_manifest
from app.schemas.project import ProjectCreate,ProjectUpdate
from app.models.enums import LoaderType,ThemeType

def _write(path,files):
 manifest={'formatVersion':1,'game':'minecraft','dependencies':{'minecraft':'1.20.1','fabric-loader':'0.15.11'},'files':files}
 with zipfile.ZipFile(path,'w') as z:z.writestr('modrinth.index.json',json.dumps(manifest))
 return str(path)

def test_import_accepts_non_mods_paths_and_skips_undownloadable(tmp_path):
 path=_write(tmp_path/'p.mrpack',[
  {'path':'mods/a.jar','fileSize':3,'downloads':['https://cdn.modrinth.com/a.jar'],'hashes':{'sha1':'a'*40}},
  {'path':'config/b.json','fileSize':2,'downloads':['https://cdn.modrinth.com/b.json'],'hashes':{'sha1':'b'*40}},
  {'path':'mods/c.jar','downloads':[],'hashes':{}},
 ])
 result=import_manifest(path,None)
 assert [m.file_name for m in result['mods']]==['a.jar','b.json']
 assert result['loader']=='fabric-loader' and result['minecraft_version']=='1.20.1'

def test_import_still_reads_a_plain_mods_pack(tmp_path):
 path=_write(tmp_path/'p.mrpack',[{'path':'mods/a.jar','fileSize':3,'downloads':['https://cdn.modrinth.com/a.jar'],'hashes':{'sha1':'a'*40}}])
 result=import_manifest(path,None)
 assert result['mods'][0].file_name=='a.jar' and result['mods'][0].install_path=='mods/a.jar'

def test_import_rejects_path_traversal(tmp_path):
 path=_write(tmp_path/'p.mrpack',[{'path':'../evil.jar','downloads':['https://x/evil.jar'],'hashes':{}}])
 with pytest.raises(ValueError):import_manifest(path,None)

def test_import_requires_at_least_one_download(tmp_path):
 path=_write(tmp_path/'p.mrpack',[{'path':'mods/c.jar','downloads':[],'hashes':{}}])
 with pytest.raises(ValueError):import_manifest(path,None)

def test_project_create_accepts_moved_advanced_fields():
 body=ProjectCreate(minecraft_version='1.20.1',loader=LoaderType.FABRIC,name='n',description='d',theme=ThemeType.SURVIVAL,gameplay_style=['exploration','combat'],qol_level='high',hardware_profile='mid_range',multiplayer_mode='co_op',world_style='realistic',progression='quest_driven')
 assert body.gameplay_style==['exploration','combat'] and body.world_style=='realistic' and body.progression=='quest_driven'

def test_project_update_accepts_moved_advanced_fields():
 body=ProjectUpdate(gameplay_style=['building'],qol_level='maximum',world_style='overhauled')
 assert body.gameplay_style==['building'] and body.qol_level=='maximum' and body.world_style=='overhauled'
