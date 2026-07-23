import asyncio
from app.models.enums import LoaderType
from app.schemas.mod import ModDependency, ModEntry, ModHash
from app.services.dependency_resolver import DependencyResolver
from app.services.mod_resolver import ModResolver
from app.services.requirements import parse_requirements
from app.services.source_registry import ModSourceRegistry

def test_plain_prompt_parses_mod_count_but_leaves_advanced_preferences_unset():
    requirements=parse_requirements('Maak een horror modpack met 150 mods',theme='horror')
    assert requirements.minimum_mods == 150
    assert requirements.target_ram_gb is None and requirements.target_fps is None
    assert requirements.shader_support is None and requirements.performance_preference is None
    assert requirements.hardware_profile is None and requirements.visual_quality is None

def test_optional_preferences_are_parsed_when_present():
    requirements=parse_requirements('{"advanced":{"target_ram_gb":8,"target_fps":60,"shader_support":"shader_compatible","performance_preference":"performance"}}')
    assert requirements.target_ram_gb==8 and requirements.target_fps==60 and requirements.shader_support=='shader_compatible'

def test_optional_none_values_stay_none():
    requirements=parse_requirements('{"advanced":{"target_ram_gb":null,"target_fps":null,"hardware_profile":null}}')
    assert requirements.target_ram_gb is None and requirements.target_fps is None and requirements.hardware_profile is None

def test_repair_events_are_exposed_for_nested_dependency_repairs():
    def mod(name,deps=()): return ModEntry(id=name,source='modrinth',name=name,slug=name,loaders=['fabric'],selected_version='1.20.1',file_name=f'{name}.jar',file_size=1,download_url=f'https://cdn.modrinth.com/{name}.jar',hashes=ModHash(sha1='a'*40),dependencies=list(deps))
    class Provider:
        source_id='modrinth'; available=True
        def __init__(self): self.values={'lib':mod('lib',[ModDependency(project_id='transitive')]),'transitive':mod('transitive')}
        async def get_mod_detail(self,mod_id,mc,loader): return self.values.get(mod_id)
        async def search(self,*a,**k): return [],0
        async def close(self): pass
    async def run():
        provider=Provider(); resolver=DependencyResolver(ModResolver(registry=ModSourceRegistry([provider])))
        return await resolver.resolve_pack([mod('root',[ModDependency(project_id='lib')])],'1.20.1',LoaderType.FABRIC)
    result=asyncio.run(run())
    assert result.complete and any(event.action=='add' for event in result.events)
