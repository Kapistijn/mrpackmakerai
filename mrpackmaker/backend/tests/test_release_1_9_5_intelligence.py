from app.schemas.mod import ModEntry, ModHash
from app.services.pack_intelligence import quality_report, synergy_report, performance_estimate, variant_plan, natural_language_plan

def mod(name, categories=(), downloads=100000):
    return ModEntry(id=name, source='modrinth', name=name, slug=name.lower().replace(' ', '-'), summary=' '.join(categories), categories=list(categories), downloads=downloads, file_name=name+'.jar', download_url='https://cdn.modrinth.com/data/x/'+name+'.jar', hashes=ModHash(sha1='a'*40))

def test_quality_report_is_explainable():
    result = quality_report([mod('Farmer', ('food','farming')), mod('Season', ('season','weather'))])
    assert set(result['scores']) == {'realism','immersion','performance','compatibility','content_balance'}
    assert result['explanation']

def test_synergy_and_worldgen_conflict_are_not_strictly_blocking():
    result = synergy_report([mod('Terrain A', ('worldgen','terrain')), mod('Terrain B', ('worldgen','biome'))])
    assert result['conflicts'][0]['risk'] == 'high'
    assert result['conflicts'][0]['type'] == 'world_generation_overlap'

def test_performance_simulator_and_variants():
    result = performance_estimate([mod('Worldgen', ('worldgen','structures'))] * 20, shader_support='enabled')
    assert result['ram_gb'] >= 4 and result['expected_fps']['high'] > result['expected_fps']['low']
    assert [item['tier'] for item in variant_plan('Pack', [mod('A')]*400)] == ['lite','balanced','ultimate']

def test_natural_language_edit_is_approval_gated():
    result = natural_language_plan('maak de nachten enger', [mod('A')])
    assert result['approval_required'] is True
    assert 'horror ambience' in result['add_queries']
