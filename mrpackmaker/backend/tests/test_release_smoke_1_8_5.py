import json
import zipfile

import pytest

from app.schemas.mod import ModEntry, ModHash
from app.services.mrpack import MrpackGenerator
from app.services.mrpack_validation import MrpackValidationError


def _project(resolved_loader_version="0.15.11"):
    return type("Project", (), {
        "loader": "fabric",
        "loader_version": None,
        "resolved_loader_version": resolved_loader_version,
        "minecraft_version": "1.20.1",
        "name": "release smoke",
        "description": "smoke test",
        "mods_json": json.dumps([
            ModEntry(id="example", source="modrinth", name="Example", slug="example", file_name="example.jar", file_size=12, download_url="https://cdn.modrinth.com/example.jar", hashes=ModHash(sha1="a" * 40)).model_dump(mode="json")
        ]),
    })()


def test_mrpack_generator_writes_valid_downloadable_archive(tmp_path, monkeypatch):
    import app.services.mrpack as mrpack_module
    monkeypatch.setattr(type(mrpack_module.config), "output_dir", property(lambda _config: tmp_path))
    output = MrpackGenerator().generate(_project())
    assert output.parent == tmp_path
    assert output.exists() and output.suffix == ".mrpack"
    with zipfile.ZipFile(output) as archive:
        index = json.loads(archive.read("modrinth.index.json"))
        assert index["dependencies"]["minecraft"] == "1.20.1"
        assert index["dependencies"]["fabric-loader"] == "0.15.11"
        assert index["files"][0]["path"] == "mods/example.jar"


def test_mrpack_generator_rejects_unresolved_loader_before_archive_creation(tmp_path, monkeypatch):
    import app.services.mrpack as mrpack_module
    monkeypatch.setattr(type(mrpack_module.config), "output_dir", property(lambda _config: tmp_path))
    with pytest.raises(MrpackValidationError, match="loader version"):
        MrpackGenerator().generate(_project(None))
    assert list(tmp_path.iterdir()) == []
