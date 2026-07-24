import importlib
from app.schemas.mod import ModEntry, ModSearchResponse

def test_mod_search_response_contract_is_importable():
    response = ModSearchResponse(results=[ModEntry(id='x', source='modrinth', name='Test')], total=1)
    assert response.results[0].id == 'x'
    assert response.total == 1

def test_application_imports_all_routes():
    module = importlib.import_module('app.main')
    assert module.app.title == 'MrPackMaker'
