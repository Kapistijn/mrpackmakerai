from __future__ import annotations
import json,zipfile
from urllib.parse import urlparse
from app.schemas.mod import ModEntry,ModHash
from app.services.mrpack_paths import validate_install_path
from app.services.mrpack_validation import ALLOWED_DOWNLOAD_HOSTS

def read_manifest(path):
 try:
  with zipfile.ZipFile(path) as archive:
   if 'modrinth.index.json' not in archive.namelist():raise ValueError('MRPack is missing modrinth.index.json')
   manifest=json.loads(archive.read('modrinth.index.json'))
 except (OSError,zipfile.BadZipFile,json.JSONDecodeError) as exc:raise ValueError(f'Invalid MRPack archive: {exc}') from exc
 if manifest.get('formatVersion')!=1 or manifest.get('game')!='minecraft':raise ValueError('Unsupported MRPack manifest format')
 return manifest

def read_pack_info(path):
 try:
  with zipfile.ZipFile(path) as archive: raw=archive.read('overrides/pack_info.json') if 'overrides/pack_info.json' in archive.namelist() else b'{}'
  value=json.loads(raw);return value if isinstance(value,dict) else {}
 except (OSError,zipfile.BadZipFile,json.JSONDecodeError,KeyError):return {}

def _host_allowed(url):
 parsed=urlparse(url);host=parsed.netloc.lower().split('@')[-1].split(':')[0]
 return parsed.scheme=='https' and any(host==a or host.endswith('.'+a) for a in ALLOWED_DOWNLOAD_HOSTS)
def import_manifest(path,resolve_mod=None):
 manifest=read_manifest(path);deps=manifest.get('dependencies',{});mc=deps.get('minecraft');loader=next(((k,v) for k,v in deps.items() if k!='minecraft'),(None,None))
 if not mc or not loader[0] or not loader[1]:raise ValueError('MRPack manifest is missing Minecraft or loader metadata')
 mods=[]
 for entry in manifest.get('files',[]):
  pack_path=entry.get('path','')
  try:pack_path=validate_install_path(pack_path)
  except ValueError as exc:raise ValueError(str(exc)) from exc
  name=pack_path.rsplit('/',1)[-1];downloads=entry.get('downloads') or []
  if not name or not downloads or not isinstance(downloads[0],str) or not _host_allowed(downloads[0]):continue
  hashes={k:v for k,v in (entry.get('hashes') or {}).items() if k in {'sha1','sha512'}}
  categories=['shader'] if pack_path.startswith('shaderpacks/') else ['resourcepack'] if pack_path.startswith('resourcepacks/') else []
  mods.append(ModEntry(id=pack_path,source='imported',name=name,slug=name,file_name=name,file_size=entry.get('fileSize'),download_url=downloads[0],hashes=ModHash(**hashes),categories=categories,install_path=pack_path))
 if not mods:raise ValueError('MRPack does not contain any downloadable files')
 return {'minecraft_version':mc,'loader':loader[0],'loader_version':loader[1],'mods':mods,'manifest':manifest,'pack_info':read_pack_info(path)}
