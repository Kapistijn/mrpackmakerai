from __future__ import annotations
import json,zipfile
from pathlib import PurePosixPath
from urllib.parse import urlparse
from app.schemas.mod import ModEntry,ModHash

def read_manifest(path):
 try:
  with zipfile.ZipFile(path) as archive:
   if 'modrinth.index.json' not in archive.namelist():raise ValueError('MRPack is missing modrinth.index.json')
   manifest=json.loads(archive.read('modrinth.index.json'))
 except (OSError,zipfile.BadZipFile,json.JSONDecodeError) as exc:raise ValueError(f'Invalid MRPack archive: {exc}') from exc
 if manifest.get('formatVersion')!=1 or manifest.get('game')!='minecraft':raise ValueError('Unsupported MRPack manifest format')
 return manifest

def import_manifest(path,resolve_mod=None):
 manifest=read_manifest(path);deps=manifest.get('dependencies',{});mc=deps.get('minecraft');loader=next(((k,v) for k,v in deps.items() if k!='minecraft'),(None,None))
 if not mc or not loader[0] or not loader[1]:raise ValueError('MRPack manifest is missing Minecraft or loader metadata')
 mods=[]
 for entry in manifest.get('files',[]):
  pack_path=entry.get('path','');pure=PurePosixPath(pack_path)
  if not pack_path.startswith(('mods/','shaderpacks/','resourcepacks/')) or pure.is_absolute() or '..' in pure.parts:raise ValueError(f'Unsafe imported file path: {pack_path}')
  name=pure.name;downloads=entry.get('downloads') or []
  if not name or not downloads or not isinstance(downloads[0],str) or urlparse(downloads[0]).scheme!='https':raise ValueError(f'Invalid download metadata for {pack_path}')
  categories=['shader'] if pack_path.startswith('shaderpacks/') else ['resourcepack'] if pack_path.startswith('resourcepacks/') else []
  mods.append(ModEntry(id=name,source='imported',name=name,slug=name,file_name=name,file_size=entry.get('fileSize'),download_url=downloads[0],hashes=ModHash(**entry.get('hashes',{})),categories=categories,install_path=pack_path))
 return {'minecraft_version':mc,'loader':loader[0],'loader_version':loader[1],'mods':mods,'manifest':manifest}
