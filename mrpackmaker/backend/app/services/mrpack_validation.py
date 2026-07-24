"""Strict validation shared by compatibility checks and MRPack export."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse
from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.mod_resolver import mod_identity
from app.services.mrpack_paths import is_safe_install_path,validate_install_path
ALLOWED_DOWNLOAD_HOSTS=('cdn.modrinth.com','github.com','raw.githubusercontent.com','objects.githubusercontent.com','gitlab.com','codeberg.org','cdn.curseforge.com','media.forgecdn.net','edge.forgecdn.net')
@dataclass(frozen=True)
class ExportIssue: code:str;message:str
class MrpackValidationError(ValueError):
 def __init__(self,issues:list[ExportIssue]):self.issues=issues;super().__init__('; '.join(i.message for i in issues))
def mod_key(mod:ModEntry)->str:return f'{mod.source}:{mod.id}'
def _safe_mod_filename(filename:str)->bool:
 # Legacy contract: path-like filenames report unsafe_file_name first.
 return isinstance(filename,str) and bool(filename) and '/' not in filename and '\\' not in filename and filename not in {'.','..'} and PurePosixPath(filename).name==filename
def install_path_for(mod:ModEntry)->str|None:
 if not mod.file_name:return None
 explicit=getattr(mod,'install_path',None)
 if explicit:
  try:return validate_install_path(explicit)
  except ValueError:return None
 text=' '.join(mod.categories).casefold()
 return f"shaderpacks/{mod.file_name}" if 'shader' in text else f"resourcepacks/{mod.file_name}" if 'resourcepack' in text or 'resource pack' in text else f"mods/{mod.file_name}"
def _host_allowed(netloc:str)->bool:
 host=netloc.lower().split('@')[-1].split(':')[0];return any(host==a or host.endswith('.'+a) for a in ALLOWED_DOWNLOAD_HOSTS)
def validate_export_inputs(project:Project,mods:list[ModEntry])->list[ExportIssue]:
 issues=[];selected=getattr(project,'loader_version',None);resolved=getattr(project,'resolved_loader_version',None)
 if not selected and not resolved:issues.append(ExportIssue('loader_version_missing','The selected loader version has not been resolved.'))
 if not mods:issues.append(ExportIssue('no_mods','At least one compatible mod is required for export.'))
 seen_keys=set();seen_ids={};seen_paths=set();seen_hashes={}
 for mod in mods:
  key=mod_key(mod)
  if key in seen_keys:issues.append(ExportIssue('duplicate_mod',f"Mod '{key}' is selected more than once."))
  seen_keys.add(key);identity=mod_identity(mod);previous=seen_ids.get(identity)
  if previous and previous!=key:issues.append(ExportIssue('duplicate_project',f"'{mod.name}' duplicates project '{previous}' across catalog sources."))
  seen_ids[identity]=key
  if not mod.file_name:issues.append(ExportIssue('file_missing',f'{mod.name} has no resolved file.'));continue
  if not _safe_mod_filename(mod.file_name):issues.append(ExportIssue('unsafe_file_name',f'{mod.name} has an unsafe file name.'));continue
  path=install_path_for(mod)
  if not path or not is_safe_install_path(path):issues.append(ExportIssue('unsafe_install_path',f'{mod.name} has an unsupported install path.'));continue
  if path in seen_paths:issues.append(ExportIssue('duplicate_file',f"Multiple mods use '{path}'."))
  seen_paths.add(path)
  if not mod.download_url:issues.append(ExportIssue('download_missing',f'{mod.name} has no download URL.'))
  else:
   parsed=urlparse(mod.download_url)
   if parsed.scheme!='https' or not parsed.netloc:issues.append(ExportIssue('download_invalid',f'{mod.name} must use a valid HTTPS download URL.'))
   elif not _host_allowed(parsed.netloc):issues.append(ExportIssue('download_host_not_allowed',f"{mod.name} downloads from an unapproved host '{parsed.netloc}'."))
  for digest in (mod.hashes.sha1,mod.hashes.sha512):
   if digest:
    previous_hash=seen_hashes.get(digest.lower())
    if previous_hash and previous_hash!=key:issues.append(ExportIssue('duplicate_hash',f'{mod.name} shares a file hash with {previous_hash}.'))
    seen_hashes[digest.lower()]=key
  if not (mod.hashes.sha1 or mod.hashes.sha512):issues.append(ExportIssue('hash_missing',f'{mod.name} has no SHA-1 or SHA-512 hash.'))
  if not mod.file_size or mod.file_size<=0:issues.append(ExportIssue('size_missing',f'{mod.name} has no valid file size.'))
 return list(dict.fromkeys(issues))
