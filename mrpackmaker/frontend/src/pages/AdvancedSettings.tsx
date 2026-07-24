import {useEffect,useState} from 'react';
import {useNavigate,useParams} from 'react-router-dom';
import {useQuery,useMutation,useQueryClient} from '@tanstack/react-query';
import {api} from '../lib/api';
import {ShaderSupport} from '../types';
const GAMEPLAY=['exploration','boss fighting','building','automation','farming','magic progression','combat','story driven','multiplayer'];
const QOL=['none','normal','high','maximum'];
const HARDWARE=['low_end','mid_range','high_end','extreme'];
const MULTIPLAYER=['singleplayer','co_op','small_server','large_server','public_server','client_server'];
const WORLD_STYLE=['vanilla_plus','overhauled','extreme','realistic','fantasy','horror','skyblock','island','apocalypse'];
const PROGRESSION=['fast','normal','slow','expert','quest_driven','exploration_driven','technology_driven','magic_driven','adventure_driven'];
const num=(v:string)=>{const n=parseInt(v,10);return Number.isFinite(n)?n:undefined};
const opt=(v?:string)=>v&&v.trim()?v:undefined;
const toList=(v:string)=>v.split(',').map(x=>x.trim()).filter(Boolean);
export default function AdvancedSettings(){
  const {id}=useParams<{id:string}>();
  const navigate=useNavigate();
  const qc=useQueryClient();
  const projectId=Number(id);
  const {data:project}=useQuery({queryKey:['project',projectId],queryFn:()=>api.getProject(projectId),enabled:Number.isFinite(projectId)});
  const [minMods,setMinMods]=useState('');
  const [maxMods,setMaxMods]=useState('');
  const [ram,setRam]=useState('');
  const [fps,setFps]=useState('');
  const [shader,setShader]=useState<ShaderSupport>(ShaderSupport.OFF);
  const [visual,setVisual]=useState('');
  const [resourcepack,setResourcepack]=useState(false);
  const [styles,setStyles]=useState<string[]>([]);
  const [qol,setQol]=useState('');
  const [hardware,setHardware]=useState('');
  const [multiplayer,setMultiplayer]=useState('');
  const [worldStyle,setWorldStyle]=useState('');
  const [progression,setProgression]=useState('');
  const [required,setRequired]=useState('');
  const [forbidden,setForbidden]=useState('');
  const [creativity,setCreativity]=useState('balanced');
  const [strictness,setStrictness]=useState('balanced');
  const [depth,setDepth]=useState('standard');
  useEffect(()=>{
    if(!project)return;
    setMinMods(project.minimum_mods?String(project.minimum_mods):'');
    setMaxMods(project.maximum_mods?String(project.maximum_mods):'');
    setRam(project.target_ram_gb?String(project.target_ram_gb):'');
    setFps(project.target_fps?String(project.target_fps):'');
    setShader((project.shader_support as ShaderSupport)||ShaderSupport.OFF);
    setVisual(project.shader_quality||'');
    setResourcepack(!!project.resourcepack_support);
    setStyles(project.gameplay_style||[]);
    setQol(project.qol_level||'');
    setHardware(project.hardware_profile||'');
    setMultiplayer(project.multiplayer_mode||'');
    setWorldStyle(project.world_style||'');
    setProgression(project.progression||'');
    setRequired((project.required_mods||[]).join(', '));
    setForbidden((project.forbidden_mods||[]).join(', '));
    setCreativity(project.ai_creativity||'balanced');
    setStrictness(project.ai_strictness||'balanced');
    setDepth(project.discovery_depth||'standard');
  },[project]);
  const save=useMutation({mutationFn:()=>api.updateProject(projectId,{minimum_mods:num(minMods),maximum_mods:num(maxMods),target_ram_gb:num(ram),target_fps:num(fps),shader_support:shader,shader_quality:opt(visual),resourcepack_support:resourcepack,gameplay_style:styles,qol_level:opt(qol),hardware_profile:opt(hardware),multiplayer_mode:opt(multiplayer),world_style:opt(worldStyle),progression:opt(progression),required_mods:toList(required),forbidden_mods:toList(forbidden),ai_creativity:creativity,ai_strictness:strictness,discovery_depth:depth}),onSuccess:()=>{qc.invalidateQueries({queryKey:['project',projectId]});navigate(`/project/${projectId}`)}});
  const toggle=(v:string)=>setStyles(c=>c.includes(v)?c.filter(x=>x!==v):[...c,v]);
  const select=(label:string,value:string,setter:(v:string)=>void,values:string[])=>(<label className="block text-sm text-gray-300">{label}<select className="input mt-2" value={value} onChange={e=>setter(e.target.value)}><option value="">None / AI decides</option>{values.map(v=><option key={v}>{v}</option>)}</select></label>);
  if(!project)return <div className="card">Loading advanced settings...</div>;
  return <div className="card max-w-5xl">
    <h1 className="text-2xl font-bold text-gray-100 mb-2">Advanced Settings</h1>
    <p className="text-gray-400 mb-6">The same options offered in the create flow, editable per project. Leave anything empty and the AI decides from your prompt.</p>
    <div className="grid md:grid-cols-2 gap-5">
      <label className="block text-sm text-gray-300">Target mods<input className="input mt-2" type="number" min="1" max="500" placeholder="Automatic" value={minMods} onChange={e=>setMinMods(e.target.value)}/></label>
      <label className="block text-sm text-gray-300">Maximum mods<input className="input mt-2" type="number" min="1" max="500" placeholder="No limit" value={maxMods} onChange={e=>setMaxMods(e.target.value)}/></label>
      <label className="block text-sm text-gray-300">RAM (GB)<input className="input mt-2" type="number" min="1" max="128" placeholder="Automatic" value={ram} onChange={e=>setRam(e.target.value)}/></label>
      <label className="block text-sm text-gray-300">FPS target<input className="input mt-2" type="number" min="1" max="1000" placeholder="Automatic" value={fps} onChange={e=>setFps(e.target.value)}/></label>
      <label className="block text-sm text-gray-300">Shader support<select className="input mt-2" value={shader} onChange={e=>setShader(e.target.value as ShaderSupport)}><option value="off">Off / AI decides</option><option value="optional">Optional</option><option value="enabled">Required</option></select></label>
      {select('Visual quality',visual,setVisual,['low','medium','high','ultra'])}
      <fieldset className="md:col-span-2"><legend className="text-sm text-gray-300 mb-2">Gameplay style</legend><div className="flex flex-wrap gap-2">{GAMEPLAY.map(v=><button type="button" key={v} onClick={()=>toggle(v)} className={`px-3 py-2 rounded border text-sm ${styles.includes(v)?'border-accent bg-accent/20 text-white':'border-surface-border text-gray-400'}`}>{v}</button>)}</div></fieldset>
      {select('World style',worldStyle,setWorldStyle,WORLD_STYLE)}
      {select('Progression',progression,setProgression,PROGRESSION)}
      {select('QoL level',qol,setQol,QOL)}
      {select('Multiplayer',multiplayer,setMultiplayer,MULTIPLAYER)}
      {select('Hardware profile',hardware,setHardware,HARDWARE)}
      <label className="block text-sm text-gray-300">AI creativity<select className="input mt-2" value={creativity} onChange={e=>setCreativity(e.target.value)}><option>conservative</option><option>balanced</option><option>adventurous</option></select></label>
      <label className="block text-sm text-gray-300">AI strictness<select className="input mt-2" value={strictness} onChange={e=>setStrictness(e.target.value)}><option>balanced</option><option>strict</option></select></label>
      <label className="block text-sm text-gray-300">Search depth<select className="input mt-2" value={depth} onChange={e=>setDepth(e.target.value)}><option>shallow</option><option>standard</option><option>deep</option></select></label>
      <label className="inline-flex items-center gap-2 text-sm text-gray-300 md:col-span-2"><input type="checkbox" checked={resourcepack} onChange={e=>setResourcepack(e.target.checked)}/> Resourcepack support</label>
      <label className="block text-sm text-gray-300 md:col-span-2">Required mods<input className="input mt-2" value={required} placeholder="sodium, jei" onChange={e=>setRequired(e.target.value)}/></label>
      <label className="block text-sm text-gray-300 md:col-span-2">Forbidden mods<input className="input mt-2" value={forbidden} placeholder="optifine" onChange={e=>setForbidden(e.target.value)}/></label>
    </div>
    <div className="flex justify-end mt-8"><button className="btn btn-primary" disabled={save.isPending} onClick={()=>save.mutate()}>{save.isPending?'Saving...':'Save settings'}</button></div>
  </div>;
}
