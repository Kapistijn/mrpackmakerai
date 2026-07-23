import {useEffect,useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {useMutation} from '@tanstack/react-query';
import {api} from '../lib/api';
import {ProjectSettings,LoaderType,ThemeType,DifficultyType,PerformancePreference,ShaderSupport} from '../types';
import {ArrowRight,Loader2,RefreshCw,ChevronDown,ChevronRight,Upload} from 'lucide-react';
const MINECRAFT_VERSIONS=['1.7.10','1.8.9','1.12.2','1.16.5','1.18.2','1.19.2','1.20.1','1.20.4','1.21','1.21.1','1.21.4'];
const LOADERS=[{value:LoaderType.FABRIC,label:'Fabric'},{value:LoaderType.FORGE,label:'Forge'},{value:LoaderType.NEOFORGE,label:'NeoForge'}];
const THEMES=[{value:ThemeType.TECHNOLOGY,label:'Technology'},{value:ThemeType.ADVENTURE,label:'Adventure'},{value:ThemeType.MAGIC,label:'Magic'},{value:ThemeType.EXPLORATION,label:'Exploration'},{value:ThemeType.SURVIVAL,label:'Survival'},{value:ThemeType.CUSTOM,label:'Custom'}];
const GAMEPLAY=['exploration','boss fighting','building','automation','farming','magic progression','combat','story driven','multiplayer'];
const QOL=['none','normal','high','maximum'];
const HARDWARE=['low_end','mid_range','high_end','extreme'];
const MULTIPLAYER=['singleplayer','co_op','small_server','large_server','public_server','client_server'];
const WORLD_STYLE=['vanilla_plus','overhauled','extreme','realistic','fantasy','horror','skyblock','island','apocalypse'];
const PROGRESSION=['fast','normal','slow','expert','quest_driven','exploration_driven','technology_driven','magic_driven','adventure_driven'];
const toList=(value:string)=>value.split(',').map(x=>x.trim()).filter(Boolean);
const opt=(v?:string)=>v&&v.trim()?v:undefined;
export default function NewProject(){
  const navigate=useNavigate();
  const [settings,setSettings]=useState<ProjectSettings>({minecraft_version:'1.20.1',loader:LoaderType.FABRIC,name:'',description:'',theme:ThemeType.TECHNOLOGY,theme_custom:'',difficulty:DifficultyType.NORMAL,performance_preference:PerformancePreference.BALANCED,target_ram_gb:8,target_fps:60,shader_support:ShaderSupport.OFF,shader_quality:'medium',resourcepack_support:false,required_mods:[],forbidden_mods:[],ai_creativity:'balanced',ai_strictness:'balanced',discovery_depth:'standard',gameplay_style:[],qol_level:'',hardware_profile:'',multiplayer_mode:'',world_style:'',progression:''});
  const [showAdvanced,setShowAdvanced]=useState(true);
  const [required,setRequired]=useState('');
  const [forbidden,setForbidden]=useState('');
  const [versions,setVersions]=useState<Array<{id:string;version:string;type:string}>>([]);
  const [loading,setLoading]=useState(false);
  const [importing,setImporting]=useState(false);
  const set=<K extends keyof ProjectSettings>(key:K,value:ProjectSettings[K])=>setSettings(s=>({...s,[key]:value}));
  const num=(v:string)=>{const n=parseInt(v,10);return Number.isFinite(n)?n:undefined};
  const toggleStyle=(v:string)=>setSettings(s=>{const cur=s.gameplay_style||[];return {...s,gameplay_style:cur.includes(v)?cur.filter(x=>x!==v):[...cur,v]}});
  const styleActive=(v:string)=>(settings.gameplay_style||[]).includes(v);
  const loadVersions=async()=>{setLoading(true);try{const r=await api.getLoaderVersions(settings.minecraft_version,settings.loader);setVersions(r.versions);set('loader_version',r.versions[0]?.version)}catch{setVersions([])}finally{setLoading(false)}};
  useEffect(()=>{void loadVersions()},[settings.minecraft_version,settings.loader]);
  const create=useMutation({mutationFn:(data:ProjectSettings)=>api.createProject(data),onSuccess:p=>navigate(`/project/${p.id}`),onError:e=>alert((e as Error).message)});
  const importPack=async(file:File)=>{setImporting(true);try{const result=await api.importMrpack(file);if(result.project_id)navigate(`/project/${result.project_id}/editor`)}catch(e){alert((e as Error).message)}finally{setImporting(false)}};
  const submit=(e:React.FormEvent)=>{e.preventDefault();if(!settings.name.trim())return alert('Please enter a project name');create.mutate({...settings,required_mods:toList(required),forbidden_mods:toList(forbidden),qol_level:opt(settings.qol_level),hardware_profile:opt(settings.hardware_profile),multiplayer_mode:opt(settings.multiplayer_mode),world_style:opt(settings.world_style),progression:opt(settings.progression),shader_quality:opt(settings.shader_quality)})};
  return <div className="max-w-2xl mx-auto">
    <div className="flex items-start justify-between mb-8">
      <div><h1 className="text-3xl font-bold text-gray-100 mb-2">Create New Project</h1><p className="text-gray-400">Describe the pack. Every advanced setting lives here, not hidden in another tab.</p></div>
      <label className="btn btn-secondary inline-flex items-center gap-2 cursor-pointer"><Upload className="w-4 h-4"/>{importing?'Importing...':'Upload .mrpack'}<input hidden type="file" accept=".mrpack" onChange={e=>{const f=e.target.files?.[0];if(f)void importPack(f)}}/></label>
    </div>
    <form onSubmit={submit} className="space-y-6">
      <div><label className="label">Project Name</label><input className="input" value={settings.name} onChange={e=>set('name',e.target.value)} required/></div>
      <div><label className="label">Description</label><textarea className="input min-h-[100px]" value={settings.description} onChange={e=>set('description',e.target.value)} required/></div>
      <div className="grid grid-cols-2 gap-4">
        <div><label className="label">Minecraft Version</label><select className="input" value={settings.minecraft_version} onChange={e=>set('minecraft_version',e.target.value)}>{MINECRAFT_VERSIONS.map(v=><option key={v}>{v}</option>)}</select></div>
        <div><label className="label">Loader</label><select className="input" value={settings.loader} onChange={e=>set('loader',e.target.value as LoaderType)}>{LOADERS.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></div>
      </div>
      <div className="card">
        <div className="flex justify-between"><label className="label">Loader Version</label><button type="button" className="text-xs text-accent" onClick={()=>void loadVersions()}><RefreshCw className="w-3 h-3 inline"/> Refresh</button></div>
        <select className="input" value={settings.loader_version||''} onChange={e=>set('loader_version',e.target.value||undefined)}><option value="">Auto-select latest compatible</option>{versions.map(v=><option key={v.id} value={v.version}>{v.version} ({v.type})</option>)}</select>
        {loading&&<p className="text-xs text-gray-500 mt-2">Loading compatible versions...</p>}
      </div>
      <div><label className="label">Theme</label><select className="input" value={settings.theme} onChange={e=>set('theme',e.target.value as ThemeType)}>{THEMES.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></div>
      {settings.theme===ThemeType.CUSTOM&&<input className="input" placeholder="Custom theme" value={settings.theme_custom} onChange={e=>set('theme_custom',e.target.value)}/>}
      <div className="grid grid-cols-2 gap-4">
        <div><label className="label">Difficulty</label><select className="input" value={settings.difficulty} onChange={e=>set('difficulty',e.target.value as DifficultyType)}><option value="casual">Casual</option><option value="normal">Normal</option><option value="hard">Hard</option><option value="expert">Expert</option></select></div>
        <div><label className="label">Performance</label><select className="input" value={settings.performance_preference} onChange={e=>set('performance_preference',e.target.value as PerformancePreference)}><option value="balanced">Balanced</option><option value="performance">Performance</option><option value="visuals">Visual quality</option></select></div>
      </div>
      <div className="card">
        <button type="button" className="w-full flex justify-between text-sm font-semibold" onClick={()=>setShowAdvanced(v=>!v)}><span>Advanced Settings (optional)</span>{showAdvanced?<ChevronDown className="w-4"/>:<ChevronRight className="w-4"/>}</button>
        {showAdvanced&&<div className="pt-5 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div><label className="label">Target mods</label><input className="input" type="number" min="1" max="500" value={settings.minimum_mods??''} onChange={e=>set('minimum_mods',num(e.target.value))}/></div>
            <div><label className="label">Maximum mods</label><input className="input" type="number" min="1" max="500" value={settings.maximum_mods??''} onChange={e=>set('maximum_mods',num(e.target.value))}/></div>
            <div><label className="label">RAM (GB)</label><input className="input" type="number" min="1" max="128" value={settings.target_ram_gb??''} onChange={e=>set('target_ram_gb',num(e.target.value))}/></div>
            <div><label className="label">FPS target</label><input className="input" type="number" min="1" max="1000" value={settings.target_fps??''} onChange={e=>set('target_fps',num(e.target.value))}/></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="label">Shader support</label><select className="input" value={settings.shader_support} onChange={e=>set('shader_support',e.target.value as ShaderSupport)}><option value="off">AI decides / none</option><option value="optional">Optional</option><option value="enabled">Required</option></select></div>
            <div><label className="label">Visual quality</label><select className="input" value={settings.shader_quality} onChange={e=>set('shader_quality',e.target.value)}><option value="">AI decides</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="ultra">Ultra</option></select></div>
          </div>
          <fieldset><legend className="label">Gameplay style</legend><div className="flex flex-wrap gap-2">{GAMEPLAY.map(v=><button type="button" key={v} onClick={()=>toggleStyle(v)} className={`px-3 py-2 rounded border text-sm ${styleActive(v)?'border-accent bg-accent/20 text-white':'border-surface-border text-gray-400'}`}>{v}</button>)}</div></fieldset>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="label">World style</label><select className="input" value={settings.world_style} onChange={e=>set('world_style',e.target.value)}><option value="">AI decides</option>{WORLD_STYLE.map(v=><option key={v} value={v}>{v}</option>)}</select></div>
            <div><label className="label">Progression</label><select className="input" value={settings.progression} onChange={e=>set('progression',e.target.value)}><option value="">AI decides</option>{PROGRESSION.map(v=><option key={v} value={v}>{v}</option>)}</select></div>
            <div><label className="label">Quality of life</label><select className="input" value={settings.qol_level} onChange={e=>set('qol_level',e.target.value)}><option value="">AI decides</option>{QOL.map(v=><option key={v} value={v}>{v}</option>)}</select></div>
            <div><label className="label">Multiplayer</label><select className="input" value={settings.multiplayer_mode} onChange={e=>set('multiplayer_mode',e.target.value)}><option value="">AI decides</option>{MULTIPLAYER.map(v=><option key={v} value={v}>{v}</option>)}</select></div>
            <div><label className="label">Hardware profile</label><select className="input" value={settings.hardware_profile} onChange={e=>set('hardware_profile',e.target.value)}><option value="">AI decides</option>{HARDWARE.map(v=><option key={v} value={v}>{v}</option>)}</select></div>
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-gray-300"><input type="checkbox" checked={!!settings.resourcepack_support} onChange={e=>set('resourcepack_support',e.target.checked)}/> Resourcepack support</label>
          <div><label className="label">Required mods</label><input className="input" placeholder="mod-a, mod-b" value={required} onChange={e=>setRequired(e.target.value)}/></div>
          <div><label className="label">Forbidden mods</label><input className="input" placeholder="optifine, mod-c" value={forbidden} onChange={e=>setForbidden(e.target.value)}/></div>
          <div className="grid grid-cols-3 gap-4">
            <div><label className="label">AI creativity</label><select className="input" value={settings.ai_creativity} onChange={e=>set('ai_creativity',e.target.value)}><option>conservative</option><option>balanced</option><option>adventurous</option></select></div>
            <div><label className="label">AI strictness</label><select className="input" value={settings.ai_strictness} onChange={e=>set('ai_strictness',e.target.value)}><option>balanced</option><option>strict</option></select></div>
            <div><label className="label">Search depth</label><select className="input" value={settings.discovery_depth} onChange={e=>set('discovery_depth',e.target.value)}><option>shallow</option><option>standard</option><option>deep</option></select></div>
          </div>
        </div>}
      </div>
      <div className="flex justify-end"><button className="btn btn-primary inline-flex items-center gap-2" disabled={create.isPending||loading}>{create.isPending?<><Loader2 className="w-4 animate-spin"/>Creating...</>:<>Create Project<ArrowRight className="w-4"/></>}</button></div>
    </form>
  </div>;
}
