import asyncio
from pathlib import Path
from app.schemas.mod import ModEntry
from app.services.cache import AsyncCoalescingCache
from app.services.worker_generation import WorkerCandidate,WorkerDirective,WorkerGenerationEngine
ROOT=Path(__file__).resolve().parents[2]
def mod(name,categories=None):return ModEntry(id=name,source='modrinth',name=name,slug=name,summary='',downloads=1,categories=categories or [],loaders=[],dependencies=[],project_url='',hashes={})
def candidate(i,score,items):return WorkerCandidate(WorkerDirective(i,i,'focus'),items,score=score,intent_coverage=score,compatibility=score,performance=score,dependency_quality=score,confidence=score)
def test_merge_records_quality_dimensions_and_reason():
 result,rounds=WorkerGenerationEngine.merge_rounds([candidate(1,80,[mod('a',['worldgen'])]),candidate(2,60,[mod('b',['utility'])])])
 comparison=rounds[0]['comparisons'][0]
 assert 'compatibility' in comparison['result'] and 'redundancy' in comparison['result'] and 'export_validity' in comparison['result']
 assert 'preserved unique content' in result.reasoning

def test_shared_cache_has_bounded_completed_storage():
 async def run():
  cache=AsyncCoalescingCache();calls=0
  async def fetch():
   nonlocal calls;calls+=1;return ('ok',1)
  assert await cache.get_or_fetch('x',fetch)==('ok',1)
  assert await cache.get_or_fetch('x',fetch)==('ok',1)
  assert calls==1
 asyncio.run(run())
def test_audit_report_records_scan_and_remaining_release_gates():
 text=(ROOT/'REPOSITORY_AUDIT_2_5_4.md').read_text(encoding='utf-8')
 assert 'TODO marker search' in text
 assert 'Remaining release gates' in text
