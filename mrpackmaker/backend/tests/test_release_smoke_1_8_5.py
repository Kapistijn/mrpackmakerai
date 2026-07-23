import json
import zipfile
from pathlib import Path

from app.services.mrpack import MrpackGenerator
from app.schemas.mod import ModEntry, ModHash


def test_mrpack_generator_writes_valid_downloadable_archive(tmp_path, monkeypatch):
    import app.services.mrpack as mrpack_module
    monkeypatch.setattr(mrpack_module.config, 'output_dir', tmp_path)
    project = type('Project', (), {
        'loader': 'fabric', 'loader_version': None, 'resolved_loader_version': '0.15.11',
        'minecraft_version': '1.20.1', 'name': 'release smoke', 'description': 'smoke test',
        'mods_json': json.dumps([ModEntry(id='example', source='modrinth', name='Example', slug='example', file_name='example.jar', file_size=12, download_url='https://cdn.modrinth.com/example.jar', hashes=ModHash(sha1='a' * 40)).model_dump(mode='json')]),
    })()
    output = MrpackGenerator().generate(project)
    assert output.exists() and output.suffix == '.mrpack'
    with zipfile.ZipFile(output) as archive:
        index = json.loads(archive.read('modrinth.index.json'))
        assert index['dependencies']['minecraft'] == '1.20.1'
        assert index['dependencies']['fabric-loader'] == '0.15.11'
        assert index['files'][0]['path'] == 'mods/example.jar'
