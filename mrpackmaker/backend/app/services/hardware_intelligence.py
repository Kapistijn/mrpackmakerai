from __future__ import annotations
import re
GPU_TIERS={'rtx 4090':12,'rtx 4080':10,'rtx 4070':8,'rtx 5060':8,'rtx 4060':6,'rtx 3060':6,'rx 7900':12,'rx 7800 xt':10,'rx 7700':8,'rx 6800':8,'gtx 1660':4}
def gpu_capability(name,profile=None):
 text=(name or '').casefold()
 for key,tier in GPU_TIERS.items():
  if key in text:return {'name':name,'tier':tier,'known':True}
 return {'name':name,'tier':{'low_end':4,'mid_range':6,'high_end':8,'extreme':12}.get(profile,6),'known':False}
def cpu_capability(name):
 text=(name or '').casefold();cores=8;score=70
 if any(x in text for x in ('ryzen 9','i9','threadripper')):cores,score=16,98
 elif any(x in text for x in ('ryzen 7','i7')):cores,score=12,90
 elif any(x in text for x in ('ryzen 5','i5')):cores,score=8,78
 elif any(x in text for x in ('celeron','pentium','athlon')):cores,score=4,45
 return {'name':name,'cores':cores,'score':score,'known':bool(name)}
def hardware_fit(hw,performance):
 gpu=gpu_capability(hw.get('gpu'),hw.get('profile'));cpu=cpu_capability(hw.get('cpu'));ram=hw.get('ram_gb');resolution=hw.get('resolution','1920x1080') or '1920x1080';pixels=1;match=re.match(r'(\d+)x(\d+)',resolution)
 if match:pixels=(int(match.group(1))*int(match.group(2)))/(1920*1080)
 vram_need=performance['vram_gb']*pixels;gpu_score=max(0,min(100,round(gpu['tier']/max(vram_need,1)*100)));ram_score=100 if not ram else max(0,min(100,round(ram/performance['ram_gb']*100)));fps_target=hw.get('target_fps');refresh=hw.get('refresh_rate');effective_target=max(x for x in (fps_target or 0,refresh or 0) if x) if (fps_target or refresh) else 0;fps_score=100 if not effective_target else max(0,min(100,round(performance['expected_fps']['low']/effective_target*100)));score=round(gpu_score*.4+cpu['score']*.2+ram_score*.2+fps_score*.2)
 return {'score':score,'status':'fit' if score>=80 else 'warning' if score>=60 else 'blocked','gpu':gpu,'cpu':cpu,'resolution_multiplier':round(pixels,2),'vram_required_gb':round(vram_need,1),'effective_fps_target':effective_target,'reason':'Hardware profile meets the estimated pack requirements.' if score>=80 else 'Reduce shaders/worldgen or use a stronger hardware profile.'}
def selection_hints(project):
 gpu=gpu_capability(getattr(project,'hardware_gpu',None),getattr(project,'hardware_profile',None));cpu=cpu_capability(getattr(project,'hardware_cpu',None));ram=getattr(project,'target_ram_gb',None);target=max(getattr(project,'target_fps',0) or 0,getattr(project,'hardware_refresh_rate',0) or 0)
 low=(ram is not None and ram<=6) or gpu['tier']<=4 or cpu['score']<=50
 return {'low_hardware':low,'gpu_tier':gpu['tier'],'cpu_score':cpu['score'],'target_fps':target,'avoid_queries':['shader','worldgen','dimension','particles'] if low else [],'prefer_queries':['performance','optimization'] if low or target>=120 else []}
