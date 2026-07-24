from __future__ import annotations
import json
import pytest
from app.models.project import Project
from app.schemas.mod import ModEntry,ModHash
from app.services.pack_analysis import analyze_mods
from app.services.pack_snapshots import create_snapshot

def mod(name,categories=(),downloads=100000):return ModEntry(id=name,source='modrinth',name=name,slug=name.lower(),categories=list(categories),downloads=downloads,file_name=name+'.jar',download_url='https://cdn.modrinth.com/'+name+'.jar',hashes=ModHash(sha1='a'*40))
def test_auto_intelligence_report_contains_quality_performance_conflicts_and_hardware():
 p=Project(name='pack',description='',minecraft_version='1.20.1',loader='fabric',theme='survival',target_ram_gb=8,target_fps=120,shader_support='enabled')
 report=analyze_mods(p,[mod('World A',('worldgen','terrain')),mod('World B',('worldgen','biome'))])
 assert report['quality']['scores']['compatibility']==100
 assert report['performance']['ram_gb']>=4
 assert report['synergy']['conflicts'][0]['risk']=='high'
 assert 'hardware' in report

def test_hardware_profile_changes_prediction():
 low=Project(name='low',description='',minecraft_version='1.20.1',loader='fabric',theme='survival',target_ram_gb=4,target_fps=144)
 high=Project(name='high',description='',minecraft_version='1.20.1',loader='fabric',theme='survival',target_ram_gb=32,target_fps=60)
 mods=[mod('Particles',('particle','visual')) for _ in range(40)]
 assert analyze_mods(low,mods)['hardware']['score']<analyze_mods(high,mods)['hardware']['score']
@pytest.mark.asyncio
async def test_snapshot_creation_and_restore_contract():
 assert create_snapshot and json
