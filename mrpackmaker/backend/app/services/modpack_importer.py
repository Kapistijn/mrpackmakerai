from __future__ import annotations
import json,zipfile
from app.schemas.mod import ModEntry,ModHash
def read_manifest(path):
 with zipfile.ZipFile(path) as archive:return json.loads(archive.read('modrinth.index.json'))
def import_manifest(path,resolve_mod):
 manifest=read_manifest(path);deps=manifest.get('dependencies',{});mc=deps.get('minecraft');loader=next(((k,v) for k,v in deps.items() if k!='minecraft'),(None,None));mods=[]
 for entry in manifest.get('files',[]):
  name=entry.get('path','').split('/')[-1];mods.append(ModEntry(id=name,source='imported',name=name,slug=name,file_name=name,file_size=entry.get('fileSize'),download_url=(entry.get('downloads') or [None])[0],hashes=ModHash(**entry.get('hashes',{})),categories=[]))
 return {'minecraft_version':mc,'loader':loader[0],'loader_version':loader[1],'mods':mods,'manifest':manifest}
