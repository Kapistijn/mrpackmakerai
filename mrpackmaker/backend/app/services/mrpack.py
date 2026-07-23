"""Validated Modrinth MRPack ZIP generator."""
from __future__ import annotations
import json, logging, os, re, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app.config import config
from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.mrpack_validation import ExportIssue, MrpackValidationError, validate_export_inputs
logger=logging.getLogger(__name__)
LOADER_DEPENDENCY_KEYS={LoaderType.FABRIC:'fabric-loader',LoaderType.FORGE:'forge',LoaderType.NEOFORGE:'neoforge'}
def _sanitize_filename(name:str)->str:
    safe=re.sub(r'[^\w\s-]','',name).strip().replace(' ','-'); return safe or 'modpack'
class MrpackGenerator:
    def build_index(self,project:Project,mods:list[ModEntry])->dict[str,Any]:
        loader=LoaderType(project.loader); selected_loader=project.loader_version or project.resolved_loader_version
        if not selected_loader: raise MrpackValidationError([ExportIssue('loader_version_missing','The selected loader version has not been resolved.')])
        loader_key=LOADER_DEPENDENCY_KEYS[loader]
        index={'formatVersion':1,'game':'minecraft','versionId':datetime.now(timezone.utc).strftime('%Y.%m.%d-%H%M%S'),'name':project.name,'summary':project.description,'files':[],'dependencies':{'minecraft':project.minecraft_version,loader_key:selected_loader}}
        for mod in mods:
            index['files'].append({'path':f'mods/{mod.file_name}','hashes':{a:v for a,v in {'sha1':mod.hashes.sha1,'sha512':mod.hashes.sha512}.items() if v},'downloads':[mod.download_url],'fileSize':mod.file_size})
        return index
    def _validate_archive(self,path:Path)->None:
        with zipfile.ZipFile(path,'r') as archive:
            if archive.testzip(): raise RuntimeError('Corrupt ZIP member')
            members=archive.namelist()
            if 'modrinth.index.json' not in members: raise RuntimeError('Missing modrinth.index.json')
            if any(name.startswith(('/','\\')) or '..' in Path(name).parts for name in members): raise RuntimeError('Archive contains an unsafe path')
            index=json.loads(archive.read('modrinth.index.json'))
            if index.get('formatVersion')!=1 or index.get('game')!='minecraft': raise RuntimeError('Invalid MRPack metadata')
            dependencies=index.get('dependencies',{})
            if not dependencies.get('minecraft') or not any(key!='minecraft' for key in dependencies): raise RuntimeError('MRPack is missing loader metadata')
            for entry in index.get('files',[]):
                if not entry.get('path','').startswith('mods/') or not entry.get('hashes') or not entry.get('downloads') or not entry.get('fileSize'): raise RuntimeError('MRPack contains an unresolved file')
    def generate(self,project:Project)->Path:
        mods=[ModEntry.model_validate(raw) for raw in json.loads(project.mods_json or '[]')]; issues=validate_export_inputs(project,mods)
        if issues: raise MrpackValidationError(issues)
        index=self.build_index(project,mods); config.output_dir.mkdir(parents=True,exist_ok=True); output_path=config.output_dir/f'{_sanitize_filename(project.name)}.mrpack'; descriptor,temp_name=tempfile.mkstemp(prefix=f'.{_sanitize_filename(project.name)}-',suffix='.mrpack',dir=config.output_dir); os.close(descriptor); temp=Path(temp_name)
        try:
            with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as archive: archive.writestr('modrinth.index.json',json.dumps(index,indent=2))
            self._validate_archive(temp); temp.replace(output_path)
        finally:
            if temp.exists(): temp.unlink(missing_ok=True)
        logger.info('Generated and validated MRPack: %s',output_path); return output_path
