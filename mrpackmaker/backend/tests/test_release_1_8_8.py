from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.mod import ModDependency,ModEntry,ModHash
from app.services.discovery_strategy import build_discovery_plan
from app.services.intent_analysis import analyze_intent
from app.services.pack_profile import build_pack_profile
from app.services.quality_scoring import score_mod_quality
from app.services.requirements import parse_requirements

def mod(name,summary='',categories=(),deps=()):return ModEntry(id=name,source='modrinth',name=name,slug=name,summary=summary,categories=list(categories),loaders=['fabric'],file_name=name+'.jar',file_size=10,download_url='https://cdn.modrinth.com/'+name+'.jar',hashes=ModHash(sha1='b'*40),dependencies=list(deps))
def test_constraint_is_machine_readable_and_parsed():
 r=parse_requirements('',required_mods=['Create'],forbidden_mods=['Magic Mod']);assert r.constraint.required_mods==('create',) and r.constraint.forbidden_mods==('magic mod',)
def test_creativity_and_discovery_change_scope():assert build_discovery_plan(10,'low').limit<build_discovery_plan(90,'high').limit and len(build_discovery_plan(10,'low').offsets)<len(build_discovery_plan(90,'high').offsets)
def test_taxonomy_examples():
 assert analyze_intent('realistic survival').realism_focus;assert 'technology' in analyze_intent('technology factory').categories;assert 'magic' in analyze_intent('fantasy magic adventure').categories;assert 'horror' in analyze_intent('hardcore zombie apocalypse').categories
def test_ram_profiles():
 low=build_pack_profile(parse_requirements('',target_ram_gb=4));heavy=build_pack_profile(parse_requirements('',target_ram_gb=32));assert not low.allow_heavy_worldgen and heavy.allow_heavy_worldgen
def test_scoring_does_not_make_modernfix_realism():
 profile=build_pack_profile(parse_requirements('',target_ram_gb=8));modern=score_mod_quality(mod('ModernFix','performance optimization memory',('optimization',)),analyze_intent('realistic survival'),profile);create=score_mod_quality(mod('Create','technology factory automation',('technology',)),analyze_intent('technology factory'),profile);assert modern.is_performance_mod and create.intent_match>modern.intent_match
def test_old_project_defaults_are_safe():
 p=Project(name='old',description='',minecraft_version='1.20.1',loader='fabric',theme='survival',difficulty='normal',performance_preference='balanced');assert p.shader_support=='off' and p.required_mods_json=='[]' and p.ai_creativity=='balanced'
def test_dependency_conflict_has_named_edges():
 root=mod('create',deps=[ModDependency(project_id='flywheel',dependency_type='required')]);assert root.dependencies[0].project_id=='flywheel'
