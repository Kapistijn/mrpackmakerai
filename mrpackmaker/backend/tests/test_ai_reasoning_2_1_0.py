from app.schemas.mod import ModEntry,ModHash
from app.services.ai_reasoning import build_mod_memory,critique_pack,missing_categories,confidence_for,alternatives_for

def mod(name,categories=(),downloads=100):return ModEntry(id=name,source='modrinth',name=name,slug=name.lower(),summary=' '.join(categories),categories=list(categories),downloads=downloads,file_name=name+'.jar',download_url='https://cdn.modrinth.com/'+name+'.jar',hashes=ModHash(sha1='a'*40))
def test_mod_memory_contains_roles_reason_confidence_and_facts():
 result=build_mod_memory(mod('Create',('technology','automation')),reason='Matches factory intent',confidence=93)
 assert result['roles'] and result['reason']=='Matches factory intent' and result['confidence']==93 and result['downloads']==100
def test_critique_finds_missing_categories_and_overlap():
 result=critique_pack([mod('Terrain A',('worldgen',)),mod('Terrain B',('worldgen',))],['automation','world generation'])
 assert 'automation' in result['missing_categories'] and result['synergy']['conflicts']
def test_confidence_and_alternatives_are_deterministic():
 current=mod('Create',('technology','automation'),100);alts=[current,mod('Tech Reborn',('technology','automation'),90),mod('Factory',('automation',),80)]
 assert confidence_for(current,['automation'])>50 and alternatives_for(current,alts)
