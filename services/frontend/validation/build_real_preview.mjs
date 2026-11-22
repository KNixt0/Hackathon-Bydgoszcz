import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const [root, input, destination] = process.argv.slice(2);
if (!root || !input || !destination) throw new Error('Usage: node build_real_preview.mjs FRONTEND_ROOT CAPTURE_JSON OUTPUT_HTML');
const capture = JSON.parse(fs.readFileSync(input, 'utf8'));
if (capture.records.length !== 3 || capture.records.some(record => !record.analysis || record.error)) throw new Error('Expected three successful real analyses');
const req=createRequire(path.join(root,'package.json'));
const {build}=await import(req.resolve('vite'));
const {default:react}=await import(req.resolve('@vitejs/plugin-react'));
const mock=`
import { defaultDateBounds } from ${JSON.stringify(path.join(root,'src/domain/dates.ts'))};
const capture = ${JSON.stringify(capture.records)};
const supervisorUser = {id:1,name:'Kierownik (podgląd)',email:'kierownik@podglad.local',role:'SUPERVISOR'};
const analystUser = {id:2,name:'Analityk (podgląd)',email:'analityk@podglad.local',role:'ANALYST'};
const records=new Map(capture.map((record,index)=>{
 const analysis=record.analysis;
 const at=analysis.source.fetched_at;
 const id='00000000-0000-4000-8000-'+String(index+1).padStart(12,'0');
 const inc={...analysis,id,status:'new',created_at:at,updated_at:at,user_reports_count:0,priority_score:analysis.risk_score,
 workflow:{assigned_to:null,processing_started_at:null,processing_finished_at:null,escalation_path:null,resolution_action:null,resolution_note:'',label:'unlabeled'}};
 inc.source.archive={html_key:null,screenshot_key:null};
 return [id,inc];
}));
const bounds=defaultDateBounds(new Date(Math.min(...[...records.values()].map(i=>Date.parse(i.created_at)))));
const now=Date.now(); const start=Date.parse(bounds.earliest);
function toSummary(i){return {...i,source:{platform:i.source.platform,url:i.source.url},advertiser:i.entities.advertiser?.name??null,firm:i.entities.investment_firm?.name??null,failed_rules:i.rules.filter(r=>r.status==='fail').map(r=>r.id)};}
const calibrationSet={items:[]};
let user=supervisorUser; let thresholds={flag:20,critical:70,updated_by:supervisorUser.email,updated_at:new Date().toISOString()};
let serial=1; const notifications=[]; const entries=[]; const jobs=[];
function record(action,incident_id,previous,value,reason=null){entries.unshift({id:serial++,at:new Date().toISOString(),actor_email:user.email,actor_role:user.role,action,incident_id,previous,new:value,reason});}
record('login',null,null,{method:'demo'});
const listeners=new Map();
const socket={connected:false,on(event,fn){if(!listeners.has(event))listeners.set(event,new Set());listeners.get(event).add(fn);return this;},off(event,fn){listeners.get(event)?.delete(fn);return this;},connect(){this.connected=true;this.emit('connect');return this;},disconnect(){this.connected=false;return this;},emit(event,value){listeners.get(event)?.forEach(fn=>fn(value));}};
window.__watchitSocket=socket;
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
window.fetch=async(input,init={})=>{
 if(init.signal?.aborted)throw new DOMException('Aborted','AbortError');
 const url=new URL(String(input),'https://watchit.preview');const p=url.pathname;const method=init.method??'GET';const body=init.body?JSON.parse(init.body):{};
 if(p==='/api/auth/config')return json({demo_login:true,authenticated:!!user});
 if(p==='/api/auth/me')return user?json({user}):json({detail:'Sesja wygasła'},401);
 if(p==='/api/auth/logout'){user=null;return new Response(null,{status:204});}
 if(p==='/api/auth/demo'||p==='/api/auth/login'){user=body.role==='ANALYST'||body.email===analystUser.email?analystUser:supervisorUser;return json({user});}
 if(!user)return json({detail:'Zaloguj się'},401);
 if(p==='/api/health')return json({status:'ok',ai:{reachable:true,llm_available:false,model:null},queue:true,storage:true});
 if(p==='/api/notifications')return json({items:notifications.filter(n=>n.user_id===user.id)});
 const notification=p.match(/^\\/api\\/notifications\\/(\\d+)\\/read$/);
 if(notification){const item=notifications.find(n=>n.id===Number(notification[1])&&n.user_id===user.id);if(!item)return json({},404);item.read_at=new Date().toISOString();return json(item);}
 if(p==='/api/settings/thresholds'){
  if(method==='PUT'){
   if(user.role!=='SUPERVISOR')return json({},403);
   const previous={...thresholds}; thresholds={...body,updated_by:user.email,updated_at:new Date().toISOString()};record('thresholds',null,previous,thresholds);
   for(const recipient of [analystUser,supervisorUser])notifications.unshift({id:serial++,user_id:recipient.id,created_at:new Date().toISOString(),read_at:null,message:user.name+' zmienił(a) kalibrację: '+previous.flag+' → '+body.flag+', krytyczne '+previous.critical+' → '+body.critical+'.',details:{actor:user.email,previous,new:thresholds}});
  }
  return json(thresholds);
 }
 if(p==='/api/incidents')return json({items:[...records.values()].map(i=>({...toSummary(i),workflow:i.workflow,failed_rule_details:i.rules.filter(r=>r.status==='fail')})),total:records.size,date_bounds:bounds});
 if(p==='/api/calibration')return json(calibrationSet);
 if(p==='/api/audit'){
  let items=entries.filter(e=>(!url.searchParams.get('actor')||e.actor_email===url.searchParams.get('actor'))&&(!url.searchParams.get('incident_id')||e.incident_id===url.searchParams.get('incident_id'))&&(!url.searchParams.get('action')||e.action===url.searchParams.get('action')));
  const sort={at:'at',actor:'actor_email',action:'action',incident_id:'incident_id',reason:'reason'}[url.searchParams.get('sort')]??'at';const direction=url.searchParams.get('order')==='asc'?1:-1;
  items.sort((a,b)=>String(a[sort]??'').localeCompare(String(b[sort]??''),'pl')*direction);
  const offset=Number(url.searchParams.get('offset'))||0;return json({items:items.slice(offset,offset+100),total:items.length});
 }
 if(p==='/api/stats/trends'){
  const period=url.searchParams.get('period');const end=Math.min(Date.now(),Date.parse(url.searchParams.get('to')||new Date().toISOString()));
  const begin=Math.max(start,Date.parse(url.searchParams.get('from')||new Date(end-(period==='24h'?86400000:(period==='7d'?7:30)*86400000)).toISOString()));
  const step=period==='24h'?3600000:86400000;const buckets=new Map();
  for(let at=Math.floor(begin/step)*step;at<=end;at+=step)buckets.set(new Date(at).toISOString(),[]);
  for(const inc of records.values()){const at=Date.parse(inc.created_at);if(at<begin||at>end)continue;const key=new Date(Math.floor(at/step)*step).toISOString();buckets.get(key)?.push({id:inc.id,risk_score:inc.risk_score,module:inc.primary_module,modules:inc.modules});}
  return json({days:[...buckets].map(([date,items])=>({date,items})),date_bounds:bounds,interval:period==='24h'?'hour':'day'});
 }
 if(p==='/api/scans'&&method==='GET')return json({items:jobs});
 if(p==='/api/scans'||p==='/api/demo/trigger'||p==='/api/samples/import'){
   return json({detail:'Podgląd zapisanych wyników: nowa analiza URL wymaga uruchomionej usługi.'},503);
 }
 const match=p.match(/^\\/api\\/incidents\\/([^/]+)(?:\\/(history|assign|transition|label))?$/);
 if(match){const inc=records.get(match[1]);if(!inc)return json({},404);const action=match[2];
  if(action==='history')return json({items:entries.filter(e=>e.incident_id===inc.id).slice().reverse()});
  if(method==='POST'){
   const previous={status:inc.status,...inc.workflow};
   if(action==='assign'){inc.workflow.assigned_to=user.email;inc.workflow.processing_started_at??=new Date().toISOString();}
   if(action==='label')inc.workflow.label=body.label;
   if(action==='transition'){inc.status=body.to;if(body.to==='in_review'){inc.workflow.assigned_to??=user.email;inc.workflow.processing_started_at??=new Date().toISOString();}if(['resolved','false_positive'].includes(body.to)){inc.workflow.processing_finished_at=new Date().toISOString();inc.workflow.resolution_note=body.reason;inc.workflow.resolution_action=body.resolution_action;}if(body.escalation_path)inc.workflow.escalation_path=body.escalation_path;}
   inc.updated_at=new Date().toISOString();record(action,inc.id,previous,{status:inc.status,...inc.workflow},body.reason);socket.emit('incident:updated',{...toSummary(inc),workflow:inc.workflow});
  }
  return json(inc);
 }
 if(p.startsWith('/api/evidence/'))return json({detail:'Archiwum nie zostało zapisane w tej próbie.'},404);
 return json({detail:'Ta funkcja wymaga uruchomionej pełnej aplikacji.'},404);
};
`;
const out='/tmp/watchit-real-preview-build';
await build({root,configFile:false,plugins:[react(),{
 name:'watchit-offline-preview',resolveId(id){if(id==='virtual:watchit-preview')return '\0watchit-preview';},load(id){if(id==='\0watchit-preview')return mock;},
 transform(code,id){if(id.endsWith('/src/main.tsx'))return 'import "virtual:watchit-preview";\n'+code.replaceAll('BrowserRouter','MemoryRouter').replace('<App />','<App socketFactory={() => (window as any).__watchitSocket} />');}
}],build:{outDir:out,emptyOutDir:true,chunkSizeWarningLimit:1400},logLevel:'warn'});
let html=fs.readFileSync(path.join(out,'index.html'),'utf8');
html=html.replace(/<link rel="icon"[^>]*>/,'');
html=html.replace(/<link[^>]*href="([^"]+\.css)"[^>]*>/,(tag,file)=>{
 let css=fs.readFileSync(path.join(out,file),'utf8');
 css=css.replace(/url\(([^)]+)\)/g,(whole,raw)=>{const f=raw.replace(/["']/g,'');if(!f.startsWith('/assets/'))return whole;const data=fs.readFileSync(path.join(out,f));return 'url(data:font/'+(f.endsWith('woff2')?'woff2':'woff')+';base64,'+data.toString('base64')+')';});
 return '<style>'+css+'</style>';
});
html=html.replace(/<script[^>]*src="([^"]+\.js)"[^>]*><\/script>/,(tag,file)=>'<script type="module">'+fs.readFileSync(path.join(out,file),'utf8').replace(/<\/script/gi,'<\\/script')+'</script>');
html=html.replace('<body>','<body><div style="padding:12px 24px;background:#fff;border-left:4px solid #1a2f8c;border-bottom:1px solid #ddd;font:14px/1.45 Public Sans,system-ui;color:#161616">3 rzeczywiste strony: BOŚ, XTB, PKO BP · pobrano 22.11.2026 · analiza lokalna bez modelu językowego · wyniki do weryfikacji · zmiany tylko w podglądzie</div>');
fs.writeFileSync(destination,html);
process.stdout.write('Preview created: '+html.length+' bytes\n');
