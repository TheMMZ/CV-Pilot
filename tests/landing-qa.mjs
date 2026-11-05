import {chromium} from 'playwright-core';
import assert from 'node:assert/strict';
import {mkdirSync} from 'node:fs';
const browser=await chromium.launch({channel:'msedge',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:4317');await page.getByRole('heading',{name:'You’ve built the skills. Now open doors.'}).waitFor();mkdirSync('qa',{recursive:true});await page.screenshot({path:'qa/landing-desktop.png',fullPage:true});
 const before=await page.locator('.cv-paper').evaluate(e=>getComputedStyle(e).transform);await page.mouse.wheel(0,450);await page.waitForTimeout(500);const after=await page.locator('.cv-paper').evaluate(e=>getComputedStyle(e).transform);assert.notEqual(before,after,'Hero illustration must respond to scroll');
 await page.locator('#how-it-works').scrollIntoViewIfNeeded();await page.screenshot({path:'qa/landing-walkthrough.png'});
 await page.getByRole('link',{name:'Enter the application studio'}).click();await page.waitForURL('**/app');await page.locator('#profile-json').waitFor({state:'attached'});await page.waitForFunction(()=>document.querySelector('#profile-json').value.length>10);
 await page.locator('.nav[data-tab=evidence]').click();await page.waitForURL('**/app#evidence');await page.locator('#evidence').waitFor({state:'visible'});await page.locator('.nav[data-tab=tracker]').click();await page.waitForURL('**/app#tracker');await page.goBack();await page.locator('#evidence').waitFor({state:'visible'});
 await page.locator('a.brand').click();await page.waitForURL('http://127.0.0.1:4317/');await page.getByRole('heading',{name:'You’ve built the skills. Now open doors.'}).waitFor();
 await page.setViewportSize({width:390,height:844});await page.emulateMedia({reducedMotion:'reduce'});await page.goto('http://127.0.0.1:4317');await page.screenshot({path:'qa/landing-mobile.png',fullPage:true});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.getByText('Does it apply to jobs automatically?',{exact:true}).click();await page.getByText('Automatic application submission is not implemented yet.',{exact:false}).waitFor();
 assert.equal(await page.locator('.cv-paper').evaluate(e=>getComputedStyle(e).animationName),'none');assert.deepEqual(errors,[]);console.log('PASS: landing renders, scroll transforms change, workspace navigation, tab history, back to landing, mobile/reduced-motion, FAQ.');
}finally{await browser.close();}
