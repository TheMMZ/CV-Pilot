import {chromium} from 'playwright-core';
import {mkdirSync} from 'node:fs';
const browser=await chromium.launch({channel:'msedge',headless:true});
try {
const page=await browser.newPage({viewport:{width:1440,height:1050}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:4317/app');await page.waitForFunction(()=>document.querySelector('#profile-json').value.length>10);
mkdirSync('qa',{recursive:true});await page.screenshot({path:'qa/desktop.png',fullPage:true});
await page.getByRole('button',{name:'Try a sample'}).click();await page.getByRole('button',{name:'Find my matches'}).click();await page.getByText('Recognized skill coverage',{exact:true}).waitFor();
await page.getByRole('button',{name:'Create tailored CV'}).click();await page.getByText('Tailored CV saved.',{exact:false}).waitFor();
const app=page.locator('.application').first();await app.locator('select').selectOption('Ready');await page.getByText('Status updated.',{exact:false}).waitFor();
const href=await app.getByRole('link',{name:'Review CV / PDF'}).getAttribute('href');
await page.goto('http://127.0.0.1:4317'+href);await page.getByRole('heading',{name:'Experience',exact:true}).waitFor();await page.goto('http://127.0.0.1:4317/app');
await page.reload();await page.locator('.nav[data-tab="tracker"]').click();await page.waitForFunction(()=>document.querySelector('.application select')?.value==='Ready');
await page.locator('.nav[data-tab="evidence"]').click();await page.getByRole('heading',{name:'Your project evidence.'}).waitFor();const saved=await (await page.request.get('http://127.0.0.1:4317/api/state')).json();if(await page.locator('.repo').count()!==(saved.github?.repositories.length||0))throw Error('Missing GitHub projects');
await page.locator('.nav[data-tab="workbench"]').click();await page.setViewportSize({width:390,height:844});await page.emulateMedia({reducedMotion:'reduce'});await page.screenshot({path:'qa/mobile.png',fullPage:true});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Horizontal overflow');
if(errors.length)throw Error(errors.join('\n'));console.log('PASS: desktop + mobile, sample analysis, draft persistence, status update, CV preview, GitHub evidence. No page errors.');} finally {await browser.close();}
