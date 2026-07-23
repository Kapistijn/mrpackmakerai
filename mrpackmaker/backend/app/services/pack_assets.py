"""Concrete export assets and shader loader metadata."""
from __future__ import annotations
import json
from app.services.pack_profile import PackProfile, SHADER_OFF

def build_pack_info(profile: PackProfile) -> dict: return profile.as_pack_info()
def _render_distance(profile: PackProfile) -> int: return 16 if profile.recommended_ram_gb >= 16 else 12 if profile.recommended_ram_gb >= 8 else 8
def default_options_txt(profile: PackProfile) -> str:
    graphics='0' if profile.performance_profile=='performance' else '1'
    return '\n'.join([f'renderDistance:{_render_distance(profile)}',f'graphicsMode:{graphics}',f'maxFps:{profile.target_fps or 120}',f'entityShadows:{"false" if profile.performance_profile=="performance" else "true"}'])+'\n'
def shaderpack_metadata(profile: PackProfile) -> dict|None:
    if profile.shader_mode==SHADER_OFF:return None
    return {'mode':profile.shader_mode,'recommended_shaderpack':{'low':'ComplementaryUnbound (Potato preset)','medium':'ComplementaryReimagined (Medium preset)','high':'BSL / Complementary (High preset)'}[profile.shader_quality],'loader_required':True}
def override_files(profile: PackProfile,mods) -> dict[str,str]:
    info=json.dumps(build_pack_info(profile),indent=2)+'\n';files={'pack_info.json':info,'options.txt':default_options_txt(profile),'config/mrpackmaker-profile.json':info}
    metadata=shaderpack_metadata(profile)
    if metadata:
        metadata_text=json.dumps(metadata,indent=2)+'\n';files['shaderpacks/mrpackmaker-shader.json']=metadata_text
        # Kept as a factual human-readable companion for old consumers. It does
        # not claim that a shaderpack binary is bundled.
        files['shaderpacks/README.txt']='Shader support metadata is included. Install the recommended shaderpack separately; the resolved Iris/Oculus loader is included as a mod when enabled.\n'
    if profile.resourcepack_support:
        files['resourcepacks/mrpackmaker-resourcepack.json']='{\n  "supported": true\n}\n'
        files['resourcepacks/README.txt']='Resourcepack support metadata is included. Add compatible resourcepack files here.\n'
    return files
def shader_loader_queries(profile,loader):
    if profile.shader_mode==SHADER_OFF:return []
    return ['iris','sodium'] if (loader or '').casefold()=='fabric' else ['oculus','embeddium']
def is_shader_loader(mod):return any(x in ' '.join((mod.id,mod.slug,mod.name)).casefold() for x in ('iris','oculus'))
def ensure_shader_loader(candidates,profile):
    if profile.shader_mode==SHADER_OFF:return list(candidates)
    loaders=[m for m in candidates if is_shader_loader(m)]
    return ([loaders[0]]+[m for m in candidates if m is not loaders[0]]) if loaders else list(candidates)
