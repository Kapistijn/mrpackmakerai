"""Validated Modrinth MRPack ZIP generator."""
from __future__ import annotations
import json,logging,os,re,tempfile,zipfile
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from app.config import config
from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.pack_assets import override_files
from app.services.pack_profile import PackProfile,profile_from_project
from app.services.mrpack_validation import ExportIssue,MrpackValidationError,install_path_for,validate_export_inputs
from app.services.mrpack_paths import is_safe_install_path
logger=logging.getLogger(__name__)
LOADER_DEPENDENCY_KEYS={LoaderType.FABRIC:'fabric-loader',LoaderType.FORGE:'forge',LoaderType.NEOFORGE:'neoforge'}
def _sanitize_filename(name:str)->str:
 safe=re.sub(r'[^\w\s-]','',name).strip().replace(' ','-');return safe or 'modpack'
class MrpackGenerator:
 def build_index(self,project:Project,mods:list[ModEntry],profile:PackProfile|None=None)->dict[str,Any]:
  loader=LoaderType(project.loader);selected_loader=project.loader_version or project.resolved_loader_version
  if not selected_loader:raise MrpackValidationError([ExportIssue('loader_version_missing','The selected loader version has not been resolved.')])
  key=LOADER_DEPENDENCY_KEYS[loader];index={'formatVersion':1,'game':'minecraft','versionId':datetime.now(timezone.utc).strftime('%Y.%m.%d-%H%M%S'),'name':project.name,'summary':project.description,'files':[],'dependencies':{'minecraft':project.minecraft_version,key:selected_loader}}
  for mod in mods:
   path=install_path_for(mod)
   if not path or not is_safe_install_path(path):raise MrpackValidationError([ExportIssue('unsafe_install_path',f'{mod.name} has an unsafe install path.')])
   index['files'].append({'path':path,'hashes':{a:v for a,v in {'sha1':mod.hashes.sha1,'sha512':mod.hashes.sha512}.items() if v},'downloads':[mod.download_url],'fileSize':mod.file_size})
  return index
 def build_overrides(self,profile:PackProfile,mods:list[ModEntry])->dict[str,str]:return override_files(profile,mods)
 def _validate_archive(self,path:Path)->None:
  with zipfile.ZipFile(path,'r') as archive:
   if archive.testzip():raise RuntimeError('Corrupt ZIP member')
   members=archive.namelist()
   if 'modrinth.index.json' not in members:raise RuntimeError('Missing modrinth.index.json')
   if any(not is_safe_install_path(name) for name in members if name!='modrinth.index.json'):raise RuntimeError('Archive contains an unsafe path')
   index=json.loads(archive.read('modrinth.index.json'));deps=index.get('dependencies',{})
   if index.get('formatVersion')!=1 or index.get('game')!='minecraft':raise RuntimeError('Invalid MRPack metadata')
   if not deps.get('minecraft') or not any(key!='minecraft' for key in deps):raise RuntimeError('MRPack is missing loader metadata')
   for entry in index.get('files',[]):
    if not is_safe_install_path(entry.get('path')) or not entry.get('hashes') or not entry.get('downloads') or not entry.get('fileSize'):raise RuntimeError('MRPack contains an unresolved file')
 def write_pack(self,index:dict[str,Any],overrides:dict[str,str],output_path:Path)->Path:
  output_path=Path(output_path);output_path.parent.mkdir(parents=True,exist_ok=True);descriptor,temp_name=tempfile.mkstemp(prefix=f'.{output_path.stem}-',suffix='.mrpack',dir=output_path.parent);os.close(descriptor);temp=Path(temp_name)
  try:
   with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('modrinth.index.json',json.dumps(index,indent=2))
    for relative_path,content in (overrides or {}).items():
     safe='overrides/'+relative_path
     if not is_safe_install_path(safe):raise RuntimeError(f'Unsafe override path: {relative_path}')
     archive.writestr(safe,content)
   self._validate_archive(temp);temp.replace(output_path)
  finally:
   if temp.exists():temp.unlink(missing_ok=True)
  logger.info('Generated and validated MRPack: %s',output_path);return output_path
 def generate(self,project:Project)->Path:
  mods=[ModEntry.model_validate(raw) for raw in json.loads(project.mods_json or '[]')];issues=validate_export_inputs(project,mods)
  if issues:raise MrpackValidationError(issues)
  profile=profile_from_project(project);index=self.build_index(project,mods,profile);overrides=self.build_overrides(profile,mods);config.output_dir.mkdir(parents=True,exist_ok=True);return self.write_pack(index,overrides,config.output_dir/f'{_sanitize_filename(project.name)}.mrpack')
