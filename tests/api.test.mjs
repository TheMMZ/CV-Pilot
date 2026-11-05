import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtempSync,readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const root=new URL('../',import.meta.url);
test('HTTP workflow validates input, stores immutable snapshots, and persists statuses',async()=>{
 const child=spawn(process.execPath,['src/server.mjs'],{cwd:root,env:{...process.env,PORT:'4318',DATA_DIR:mkdtempSync(join(tmpdir(),'cv-pilot-test-')),PROFILE_FILE:'profile.example.json'},stdio:['ignore','pipe','pipe']});
 try{
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Server did not start')),15000);child.once('error',reject);child.stdout.on('data',d=>{if(d.toString().includes('running')){clearTimeout(timer);resolve();}});});
  const call=(route,method='GET',value,headers={})=>fetch('http://127.0.0.1:4318/api/'+route,{method,headers:{'Content-Type':'application/json',...headers},...(value?{body:JSON.stringify(value)}:{})});
  assert.equal((await call('drafts','POST',{title:'x'})).status,400);
  assert.equal((await call('profile','PUT',{}, {Origin:'https://example.com'})).status,403);
  const job={title:'Data Engineering Intern',company:'Integration test',description:'Build Python and PostgreSQL pipelines with Docker. Snowflake is preferred.'};
  const draft=await (await call('drafts','POST',job)).json();assert(draft.id);assert(draft.analysis.missing.includes('Snowflake'));
  assert.equal((await call('applications/'+draft.id,'PATCH',{status:'Ready'})).status,200);
  let state=await (await call('state')).json();assert.equal(state.applications[0].status,'Ready');
  const original=state.profile.name;state.profile.name='Updated candidate';await call('profile','PUT',state.profile);
  const html=await (await call('applications/'+draft.id+'/resume')).text();assert(html.includes(original));assert(!html.includes('Updated candidate'));
  assert.equal((await call('applications/'+draft.id,'PATCH',{status:'Auto-submitted'})).status,400);
 }finally{child.kill();}
});
