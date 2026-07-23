import asyncio
import pytest
from app.models.enums import LoaderType
from app.schemas.mod import ModDependency, ModEntry, ModHash
from app.services.dependency_resolver import DependencyResolver
from app.services.mod_resolver import ModResolver
from app.services.source_registry import ModSourceRegistry

def run(coro): return asyncio.run(coro)
def mod(mod_id, dependencies=(), loaders=('fabric',), version='1.20.1'):
    return ModEntry(id=mod_id, source='modrinth', name=mod_id, slug=mod_id, loaders=list(loaders), selected_version=version, file_name=f'{mod_id}.jar', file_size=10, download_url=f'https://cdn.modrinth.com/{mod_id}.jar', hashes=ModHash(sha1='a'*40), dependencies=list(dependencies))
class Provider:
    source_id='modrinth'; available=True
    def __init__(self, values): self.values=values
    async def get_mod_detail(self, mod_id, mc_version, loader):
        item=self.values.get(mod_id)
        return item if item and item.selected_version == mc_version and loader.value in item.loaders else None
    async def search(self,*args,**kwargs): return [],0
    async def close(self): pass
def resolver(values): return DependencyResolver(ModResolver(registry=ModSourceRegistry([Provider(values)])))
def test_required_dependency_is_added():
    root=mod('root',[ModDependency(project_id='library', dependency_type='required')]); result=run(resolver({'library':mod('library')}).resolve_pack([root],'1.20.1',LoaderType.FABRIC)); assert result.complete and {m.id for m in result.mods} == {'root','library'}
def test_embedded_is_not_added():
    root=mod('root',[ModDependency(project_id='embedded', dependency_type='embedded')]); result=run(resolver({'embedded':mod('embedded')}).resolve_pack([root],'1.20.1',LoaderType.FABRIC)); assert result.complete and [m.id for m in result.mods] == ['root']
def test_wrong_loader_rejected():
    root=mod('root',[ModDependency(project_id='library', dependency_type='required')]); result=run(resolver({'library':mod('library',loaders=('forge',))}).resolve_pack([root],'1.20.1',LoaderType.FABRIC)); assert not result.complete
def test_wrong_minecraft_rejected():
    root=mod('root',[ModDependency(project_id='library', dependency_type='required')]); result=run(resolver({'library':mod('library',version='1.20.2')}).resolve_pack([root],'1.20.1',LoaderType.FABRIC)); assert not result.complete
def test_large_pack_closes_dependencies():
    deps=[ModDependency(project_id=f'lib-{i}', dependency_type='required') for i in range(42)]
    root=mod('root',deps); values={f'lib-{i}':mod(f'lib-{i}') for i in range(42)}; result=run(resolver(values).resolve_pack([root],'1.20.1',LoaderType.FABRIC)); assert result.complete and len(result.mods)==43
