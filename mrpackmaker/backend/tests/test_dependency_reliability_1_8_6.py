import asyncio
import pytest
from app.models.enums import LoaderType
from app.schemas.mod import ModDependency, ModEntry, ModHash
from app.services.dependency_resolver import DependencyResolver
from app.services.mod_resolver import ModResolver
from app.services.source_registry import ModSourceRegistry

def make(name, deps=(), loader='fabric', mc='1.20.1'):
    return ModEntry(id=name, source='modrinth', name=name, slug=name, loaders=[loader], selected_version=mc, file_name=f'{name}.jar', file_size=1, download_url=f'https://cdn.modrinth.com/{name}.jar', hashes=ModHash(sha1='a'*40), dependencies=list(deps))
class Provider:
    source_id='modrinth'; available=True
    def __init__(self, values): self.values=values; self.calls=0
    async def get_mod_detail(self, mod_id, mc, loader):
        self.calls += 1; item=self.values.get(mod_id)
        return item if item and item.selected_version == mc and loader.value in item.loaders else None
    async def search(self,*a,**k): return [],0
    async def close(self): pass
def run(values, root, **kwargs):
    provider=Provider(values); result=asyncio.run(DependencyResolver(ModResolver(registry=ModSourceRegistry([provider]))).resolve_pack([root], '1.20.1', LoaderType.FABRIC, **kwargs)); return result, provider
def test_graph_closes_nested_dependencies_and_stops_on_no_progress():
    root=make('root',[ModDependency(project_id='x')]); x=make('x',[ModDependency(project_id='y')]); result, _=run({'x':x,'y':make('y')},root)
    assert result.complete and {m.id for m in result.mods} == {'root','x','y'} and result.events[-1].action == 'complete'
def test_missing_dependency_has_actionable_reason_and_suggestion():
    result, _=run({},make('root',[ModDependency(project_id='missing')]))
    assert not result.complete and 'No compatible fabric 1.20.1' in result.failures[0].reason and result.failures[0].suggestion
def test_cycle_is_reported_before_retry_loop():
    a=make('a',[ModDependency(project_id='b')]); b=make('b',[ModDependency(project_id='a')]); result, _=run({'b':b},a)
    assert result.cycles and result.cycles[0] == ('modrinth:a','modrinth:b')
def test_wrong_loader_is_not_retried_indefinitely():
    result, provider=run({'lib':make('lib',loader='forge')},make('root',[ModDependency(project_id='lib')]))
    assert not result.complete and provider.calls == 1
def test_duplicate_dependency_is_not_added_twice():
    root=make('root',[ModDependency(project_id='lib'),ModDependency(project_id='lib')]); result,_=run({'lib':make('lib')},root)
    assert result.complete and [m.id for m in result.mods].count('lib') == 1
