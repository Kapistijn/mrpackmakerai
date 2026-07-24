import importlib
from app.schemas.mod import ModEntry,ModSearchResponse
from app.api.routes.imports import MAX_MRPACK_BYTES

def test_startup_and_search_contracts_import_cleanly():
    module=importlib.import_module('app.main')
    assert module.app.title=='MrPackMaker'
    assert ModSearchResponse(results=[ModEntry(id='x',source='modrinth',name='x')]).total==0

def test_upload_limit_is_explicit_and_safe():
    assert MAX_MRPACK_BYTES==512*1024*1024

def test_empty_search_response_is_stable():
    response=ModSearchResponse()
    assert response.results==[] and response.available_sources=={}
