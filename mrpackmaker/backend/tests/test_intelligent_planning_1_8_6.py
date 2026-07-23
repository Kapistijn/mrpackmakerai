from app.schemas.mod import ModEntry, ModHash
from app.services.intelligent_planning import build_pack_design, review_pack
from app.services.requirements import parse_requirements

def mod(name, categories, summary='immersive atmosphere performance'):
    return ModEntry(id=name, source='modrinth', name=name, slug=name, categories=categories, summary=summary, file_name=f'{name}.jar', file_size=1, download_url=f'https://cdn.modrinth.com/{name}.jar', hashes=ModHash(sha1='a'*40))

def test_horror_design_expands_beyond_single_keyword():
    requirements=parse_requirements('horror modpack with 50 mods', theme='horror')
    design=build_pack_design(requirements)
    assert 'psychological horror' in design.search_queries
    assert 'sound' in design.search_queries
    assert 'lighting' in design.atmosphere
    assert sum(design.categories.values()) >= 50

def test_quality_review_penalizes_missing_compatibility_metadata():
    requirements=parse_requirements('horror')
    pack=[mod('good',['horror','sound']), mod('bad',['horror'])]
    pack[1].file_name=None
    quality=review_pack(pack,requirements)
    assert quality.compatibility < 1
    assert 0 <= quality.overall <= 1

def test_quality_review_is_deterministic():
    requirements=parse_requirements('horror')
    pack=[mod('one',['horror','sound']),mod('two',['worldgen','lighting'])]
    assert review_pack(pack,requirements)==review_pack(pack,requirements)
