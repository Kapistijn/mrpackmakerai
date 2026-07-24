from __future__ import annotations
import json,zipfile
from pathlib import PurePosixPath
from urllib.parse import urlparse
from app.schemas.mod import ModEntry,ModHash

# Modrinth places downloadable files under mods/, but the format allows any
# in-instance relative path (config/, kubejs/, resourcepacks/, ...). Only the
# first two map to a special install category; everything else is passed
# through with its explicit install_path so it round-trips on export.
_CATEGORY_PREFIXES={'shaderpacks/':'shader','resourcepacks/':'resourcepack'}

def read_manifest(path):
 try:
  with zipfile.ZipFile(path) as archive:
   names=set(archive.namelist())
   if 'modrinth.index.json' not in names:raise ValueError('MRPack is missing modrinth.index.json')
   manifest=json.loads(archive.read('modrinth.index.json'))
 except (OSError,zipfile.BadZipFile,json.JSONDecodeError) as exc:raise ValueError(f'Invalid MRPack archive: {exc}') from exc
 if manifest.get('formatVersion')!=1 or manifest.get('game')!='minecraft':raise ValueError('Unsupported MRPack manifest format')
 return manifest

def read_pack_info(path):
 try:
  with zipfile.ZipFile(path) as archive:
   raw=archive.read('overrides/pack_info.json') if 'overrides/pack_info.json' in archive.namelist() else b'{}'
  value=json.loads(raw)
  return value if isinstance(value,dict) else {}
 except (OSError,zipfile.BadZipFile,json.JSONDecodeError,KeyError):return {}

def _category_for(pack_path):
 for prefix,category in _CATEGORY_PREFIXES.items():
  if pack_path.startswith(prefix):return [category]
 return []

def import_manifest(path,resolve_mod=None):
 manifest=read_manifest(path);deps=manifest.get('dependencies',{});mc=deps.get('minecraft');loader=next(((k,v) for k,v in deps.items() if k!='minecraft'),(None,None))
 if not mc or not loader[0] or not loader[1]:raise ValueError('MRPack manifest is missing Minecraft or loader metadata')
 mods=[]
 for entry in manifest.get('files',[]):
  pack_path=entry.get('path','');pure=PurePosixPath(pack_path)
  # Security only: never accept absolute paths or parent traversal. Do NOT
  # reject a whole pack just because a file lives outside mods/.
  if not pack_path or pure.is_absolute() or '..' in pure.parts:raise ValueError(f'Unsafe imported file path: {pack_path}')
  name=pure.name;downloads=entry.get('downloads') or []
  # Files without a usable https download (client/server-excluded or override
  # provided) are skipped rather than failing the entire import.
  if not name or not downloads or not isinstance(downloads[0],str) or urlparse(downloads[0]).scheme!='https':continue
  hashes={k:v for k,v in (entry.get('hashes') or {}).items() if k in {'sha1','sha512'}}
  mods.append(ModEntry(id=name,source='imported',name=name,slug=name,file_name=name,file_size=entry.get('fileSize'),download_url=downloads[0],hashes=ModHash(**hashes),categories=_category_for(pack_path),install_path=pack_path))
 if not mods:raise ValueError('MRPack does not contain any downloadable mod files')
 return {'minecraft_version':mc,'loader':loader[0],'loader_version':loader[1],'mods':mods,'manifest':manifest,'pack_info':read_pack_info(path)}
