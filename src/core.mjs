const taxonomy = {
 Python:['python'], SQL:['sql','t-sql'], JavaScript:['javascript','js'], TypeScript:['typescript'], Java:['java'], 'C++':['c++'],
 PostgreSQL:['postgresql','postgres'], MySQL:['mysql'], 'SQL Server':['sql server'], JSONB:['jsonb'], React:['react','reactjs'],
 'Node.js':['node.js','nodejs','node js'], Express:['express','express.js'], 'REST APIs':['rest api','rest apis','restful'],
 Docker:['docker'], Git:['git'], GitHub:['github'], 'Node-RED':['node-red'], Capacitor:['capacitor'], IndexedDB:['indexeddb'],
 Snowflake:['snowflake'], Airflow:['airflow'], dbt:['dbt'], Kafka:['kafka'], Spark:['spark','pyspark'], pandas:['pandas'],
 NumPy:['numpy'], 'scikit-learn':['scikit-learn','sklearn'], PyTorch:['pytorch'], TensorFlow:['tensorflow'],
 OpenCV:['opencv'], YOLO:['yolo'], OCR:['ocr'], AWS:['aws','amazon web services'], Azure:['azure'], GCP:['gcp','google cloud'],
 Kubernetes:['kubernetes','k8s'], Streamlit:['streamlit'], Tableau:['tableau'], 'Power BI':['power bi'],
 'Machine learning':['machine learning'], 'Data engineering':['data engineering'], 'Data science':['data science'],
 HTML:['html','html5'], CSS:['css','css3'], Laravel:['laravel'], PHP:['php'], SQLite:['sqlite']
};
function mentions(text, term) {
 const escaped=term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 return new RegExp(`(?<![a-z0-9])${escaped}(?![a-z0-9])`,'i').test(text);
}
export function extractSkills(text='') {return Object.entries(taxonomy).filter(([,terms])=>terms.some(t=>mentions(text,t))).map(([s])=>s);}
export function analyze(profile,repositories,job) {
 const required=extractSkills(job.description+' '+job.title);
 const sources=[];
 for (const skill of profile.skills) sources.push({skill,source:'Master CV',kind:'profile',note:'Self-reported skill'});
 profile.experience.forEach(e=>extractSkills(e.bullets.join(' ')).forEach(skill=>sources.push({skill,source:e.organization,kind:'experience',note:e.bullets.find(b=>extractSkills(b).includes(skill))})));
 const projects=repositories.filter(r=>r.verified && !r.fork).map(r=>({...r,matched:extractSkills([r.description,r.readme,...(r.languages||[])].join(' ')).filter(s=>required.includes(s))}));
 for(const r of projects) for(const skill of extractSkills([r.description,r.readme,...r.languages].join(' '))) sources.push({skill,source:r.name,kind:'repository',url:r.url,note:'Mentioned in repository metadata or README; review ownership and implementation.'});
 const matched=required.map(skill=>({skill,evidence:sources.filter(s=>s.skill.toLowerCase()===skill.toLowerCase())})).filter(s=>s.evidence.length);
 const missing=required.filter(s=>!matched.some(m=>m.skill===s));
 const ranked=projects.sort((a,b)=>b.matched.length-a.matched.length||a.name.localeCompare(b.name));
 return {required,matched,missing,score:required.length?Math.round(matched.length/required.length*100):null,projects:ranked.filter(r=>r.matched.length).slice(0,3),method:'Recognized keyword coverage, not an ATS score or hiring prediction. Repository mentions are evidence to review, not proof of proficiency.'};
}
export function tailor(profile,repositories,job) {
 const analysis=analyze(profile,repositories,job);
 const rank=b=>extractSkills(b).filter(s=>analysis.required.includes(s)).length;
 const experience=profile.experience.map(e=>({...e,bullets:[...e.bullets].sort((a,b)=>rank(b)-rank(a))}));
 const relevant=new Set(analysis.matched.map(m=>m.skill));
 const skills=[...profile.skills].sort((a,b)=>Number(relevant.has(b))-Number(relevant.has(a)));
 return {profile:{...profile,skills,experience},job,analysis,generatedAt:new Date().toISOString(),strategy:'Evidence-first: retain original facts, prioritize relevant bullets, and surface matching repositories. Planned projects remain labeled.'};
}
export const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function resumeHtml(draft){
 const {profile:p,job,analysis}=draft,e=escapeHtml;
 const entry=x=>`<article><b>${e(x.title)}</b><span>${e(x.dates)}</span><div>${e(x.organization)}</div>${x.bullets?`<ul>${x.bullets.map(b=>`<li>${e(b)}</li>`).join('')}</ul>`:''}</article>`;
 return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${e(p.name)} - ${e(job.title)}</title><style>@page{size:A4;margin:16mm}body{font:11pt/1.45 Arial;color:#172438;max-width:780px;margin:35px auto;padding:20px}h1{font-size:25pt;margin:0}h2{font-size:11pt;text-transform:uppercase;border-bottom:1px solid #aaa;padding-bottom:4px;margin-top:22px}p{margin:6px 0}article{margin:13px 0;break-inside:avoid}span{float:right;font-size:10pt}ul{padding-left:20px;margin-top:5px}a{color:inherit}.toolbar{background:#eef3fa;padding:16px;margin-bottom:25px}button{padding:8px 15px;cursor:pointer}@media print{body{margin:0;padding:0;font-size:10pt}.toolbar{display:none}h2{margin-top:16px}}</style></head><body><div class="toolbar">Review this version for ${e(job.title)} at ${e(job.company)}. <button onclick="window.print()">Print / Save as PDF</button></div><h1>${e(p.name)}</h1><p>${e(p.headline)}</p><p>${e(p.email)} · ${e(p.phone)} · github.com/${e(p.github)}</p><h2>Profile</h2><p>${e(p.summary)}</p><h2>Skills</h2><p>${p.skills.map(e).join(' · ')}</p><h2>Experience</h2>${p.experience.map(entry).join('')}<h2>Education</h2>${p.education.map(entry).join('')}<h2>Projects</h2>${analysis.projects.map(r=>`<article><b>${e(r.name)}</b> · Repository evidence to review<p>${e(r.description||'Repository imported from GitHub.')}</p><a href="${e(r.url)}">${e(r.url)}</a></article>`).join('')}${p.projects.map(r=>`<article><b>${e(r.name)}</b> · ${e(r.status)}<p>${e(r.description)}</p></article>`).join('')}<h2>Languages</h2><p>${p.languages.map(e).join(' · ')}</p></body></html>`;
}
