import importlib
from app.schemas.mod import ModEntry,ModSearchResponse

def test_startup_routes_import_with_search_contract():
    module=importlib.import_module('app.main')
    assert module.app.title=='MrPackMaker'
    assert ModSearchResponse(results=[ModEntry(id='x',source='modrinth',name='x')]).total==0

def test_search_response_is_typed_and_empty_safe():
    value=ModSearchResponse()
    assert value.results==[] and value.available_sources=={}
