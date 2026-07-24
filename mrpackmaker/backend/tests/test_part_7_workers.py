import asyncio
from app.schemas.mod import ModEntry
from app.services.worker_generation import AsyncCoalescingCache,WorkerCandidate,WorkerDirective,WorkerGenerationEngine


def mod(name, source='modrinth'):
    return ModEntry(id=name,source=source,name=name,slug=name,summary='',downloads=1,categories=[],loaders=[],dependencies=[],project_url='',hashes={})


def candidate(index, score, mods):
    return WorkerCandidate(WorkerDirective(index,index,'focus'),mods,score=score,intent_coverage=score,compatibility=score,performance=score,dependency_quality=score,confidence=score)


def test_worker_count_accepts_practical_range_without_hardcoded_list():
    assert WorkerGenerationEngine.validate_worker_count(2) == 2
    assert WorkerGenerationEngine.validate_worker_count(24) == 24


def test_merge_rounds_reduce_any_worker_count_to_one_and_preserve_unique_mods():
    result, rounds = WorkerGenerationEngine.merge_rounds([candidate(i, i, [mod(f'mod-{i}')]) for i in range(9)])
    assert len(rounds) >= 1
    assert result.mods
    assert len({item.id for item in result.mods}) == 9


def test_shared_cache_coalesces_identical_inflight_requests():
    async def run():
        cache = AsyncCoalescingCache(); calls = 0
        async def fetch():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return ([mod('shared')], 1)
        values = await asyncio.gather(*(cache.get_or_fetch('same', fetch) for _ in range(8)))
        assert calls == 1
        assert all(value[0][0].id == 'shared' for value in values)
    asyncio.run(run())
