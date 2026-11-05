import {createServer} from 'node:http';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,mkdirSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
import {z} from 'zod';
import {analyze,tailor,resumeHtml} from './core.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
const data=process.env.DATA_DIR||join(root,'data');mkdirSync(data,{recursive:true});
const db=new DatabaseSync(join(data,'cv-pilot.sqlite'));
db.exec('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS applications(id TEXT PRIMARY KEY,created TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL);');
const load=(key,fallback)=>{const row=db.prepare('SELECT value FROM settings WHERE key=?').get(key);return row?JSON.parse(row.value):fallback;};
const save=(key,value)=>db.prepare('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').run(key,JSON.stringify(value));
if(!load('profile',null))save('profile',JSON.parse(readFileSync(join(root,process.env.PROFILE_FILE||(existsSync(join(root,'profile.seed.json'))?'profile.seed.json':'profile.example.json')),'utf8').replace(/^\uFEFF/,'')));
const str=z.string().trim().max(2000), list=z.array(str).max(100);
const entry=z.object({title:str,organization:str,dates:str,bullets:list.optional()});
const profileSchema=z.object({name:str.min(1),headline:str,email:z.email(),phone:str,github:str,summary:str,skills:list,education:z.array(entry).max(20),experience:z.array(entry).max(30),projects:z.array(z.object({name:str,status:z.enum(['planned','in progress','completed']),description:str,skills:list})).max(30),languages:list});
const jobSchema=z.object({title:str.min(2),company:str.min(1),url:z.union([z.literal(''),z.url().refine(u=>/^https?:/.test(u),'Use an HTTP(S) URL')]).default(''),description:z.string().trim().min(30).max(40000)});
export async function githubImport(username,fetcher=fetch){
 if(!/^[a-z\d](?:[a-z\d-]{0,38})$/i.test(username))throw Error('Enter a valid GitHub username.');
 const headers={Accept:'application/vnd.github+json','User-Agent':'cv-pilot','X-GitHub-Api-Version':'2026-03-10'};
 // Public resources only. No credentials are required or read by this importer.
 const get=async path=>{const r=await fetcher('https://api.github.com'+path,{headers,signal:AbortSignal.timeout(15000)});if(!r.ok){const error=new Error(r.status===403||r.status===429?'GitHub rate limit reached. Try again later.':r.status===404?'GitHub account or repository not found.':`GitHub returned ${r.status}. Try again.`);error.status=r.status;throw error;}return r.json();};
 const user=await get(`/users/${username}`);let repos=[];
 for(let page=1;page<=5;page++){const batch=await get(`/users/${username}/repos?per_page=100&sort=updated&page=${page}`);repos.push(...batch);if(batch.length<100)break;}
 const selected=repos.filter(r=>!r.fork&&!r.archived).slice(0,15);const warnings=[];
 const results=[];
 // Sequential requests avoid a burst against GitHub's unauthenticated API.
 for(const r of selected){
  let readme='',languages=r.language?[r.language]:[];
  try{const a=await get(`/repos/${username}/${r.name}/readme`);readme=Buffer.from(a.content||'','base64').toString('utf8').slice(0,16000);}catch(e){if(e.status!==404)warnings.push(`${r.name}: README unavailable (${e.message})`);}
  results.push({id:r.id,name:r.name,url:r.html_url,description:r.description||'',languages,readme,topics:r.topics||[],fork:false,verified:true,updatedAt:r.pushed_at,importedAt:new Date().toISOString()});
 }
 return {username:user.login,repositories:results,warnings,totalPublic:repos.length,limit:15,note:'Imports up to 15 recently updated, non-fork, non-archived public repositories. README and primary language only; source code and private repositories are not analyzed.'};
}
async function body(req){let text='';for await(const b of req){text+=b;if(Buffer.byteLength(text)>500000)throw Object.assign(Error('Request is too large.'),{code:413});}try{return JSON.parse(text||'{}');}catch{throw Object.assign(Error('Invalid JSON.'),{code:400});}}
function reply(res,status,value,type='application/json'){res.writeHead(status,{'Content-Type':type+'; charset=utf-8','X-Content-Type-Options':'nosniff','Cache-Control':'no-store'});res.end(type==='application/json'?JSON.stringify(value):value);}
export const server=createServer(async(req,res)=>{
 try{
  const port=process.env.PORT||4317;
  if(![`127.0.0.1:${port}`,`localhost:${port}`].includes(req.headers.host)){reply(res,403,{error:'Local connections only.'});return;}
  if(req.headers.origin&&!['http://'+req.headers.host].includes(req.headers.origin)){reply(res,403,{error:'Cross-origin requests are not allowed.'});return;}
  const url=new URL(req.url,'http://'+req.headers.host), path=url.pathname;
  if(req.method==='GET'&&path==='/api/state'){reply(res,200,{profile:load('profile',{}),github:load('github',null),applications:db.prepare('SELECT * FROM applications ORDER BY created DESC').all().map(a=>({...JSON.parse(a.payload),id:a.id,status:a.status,created:a.created}))});return;}
  if(req.method==='PUT'&&path==='/api/profile'){const p=profileSchema.parse(await body(req));save('profile',p);reply(res,200,{ok:true});return;}
  if(req.method==='POST'&&path==='/api/github'){const {username}=z.object({username:z.string().min(1).max(39)}).parse(await body(req));const result=await githubImport(username);save('github',result);reply(res,200,result);return;}
  if(req.method==='POST'&&path==='/api/analyze'){const job=jobSchema.parse(await body(req));reply(res,200,analyze(load('profile',{}),load('github',{repositories:[]}).repositories,job));return;}
  if(req.method==='POST'&&path==='/api/drafts'){const job=jobSchema.parse(await body(req)),draft=tailor(load('profile',{}),load('github',{repositories:[]}).repositories,job);const id=randomUUID();db.prepare('INSERT INTO applications VALUES(?,?,?,?)').run(id,new Date().toISOString(),'Draft',JSON.stringify(draft));reply(res,201,{id,...draft});return;}
  const app=path.match(/^\/api\/applications\/([\w-]+)(\/resume)?$/);
  if(app){const row=db.prepare('SELECT * FROM applications WHERE id=?').get(app[1]);if(!row){reply(res,404,{error:'Application not found.'});return;}
   if(req.method==='GET'&&app[2]){reply(res,200,resumeHtml(JSON.parse(row.payload)),'text/html');return;}
   if(req.method==='PATCH'&&!app[2]){const {status}=z.object({status:z.enum(['Draft','Ready','Applied','Interview','Rejected','Offer'])}).parse(await body(req));db.prepare('UPDATE applications SET status=? WHERE id=?').run(status,row.id);reply(res,200,{ok:true});return;}
  }
  const files={'/':'landing.html','/app':'index.html','/app/':'index.html','/app.js':'app.js','/style.css':'style.css','/landing.css':'landing.css','/landing.js':'landing.js','/transitions.css':'transitions.css'};
  if(req.method==='GET'&&files[path]){reply(res,200,readFileSync(join(root,'public',files[path]),'utf8'),path.endsWith('.js')?'text/javascript':path.endsWith('.css')?'text/css':'text/html');return;}
  reply(res,404,{error:'Not found.'});
 }catch(error){const validation=error instanceof z.ZodError;reply(res,error.code===413?413:error.code===400||validation?400:502,{error:validation?error.issues.map(i=>i.path.join('.')+': '+i.message).join('; '):error.message});}
});
if(process.argv[1]&&fileURLToPath(import.meta.url)===process.argv[1])server.listen(Number(process.env.PORT||4317),'127.0.0.1',()=>console.log(`CV Pilot running at http://127.0.0.1:${process.env.PORT||4317}`));
