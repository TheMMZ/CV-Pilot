const headers=document.querySelectorAll('.faq details');
headers.forEach(item=>item.addEventListener('toggle',()=>{if(!item.open)return;headers.forEach(other=>{if(other!==item)other.open=false;});}));

const loader=document.querySelector('#workspace-loader');
const description=document.querySelector('#loader-description');
let pending;
function cancelLoading(){
 if(pending)pending.abort();pending=null;
 if(loader.open)loader.close();
 document.body.classList.remove('transition-open');
}
document.querySelector('#loader-close').addEventListener('click',cancelLoading);
loader.addEventListener('cancel',event=>{event.preventDefault();cancelLoading();});
window.addEventListener('pageshow',cancelLoading);
document.addEventListener('click',async event=>{
 const link=event.target.closest('a');
 if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||link.target||link.hasAttribute('download')||link.id==='loader-fallback')return;
 const destination=new URL(link.href,location.href);
 if(destination.origin!==location.origin||destination.pathname!=='/app'||!loader.showModal)return;
 event.preventDefault();if(pending)return;
 const controller=new AbortController();pending=controller;
 document.querySelector('#loader-fallback').hidden=true;
 loader.classList.remove('failed');description.textContent='Opening your workspace…';
 loader.showModal();document.body.classList.add('transition-open');
 const timeout=setTimeout(()=>controller.abort(),8000);
 try{
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  await Promise.all([
   Promise.all(['/health','/api/state'].map(async path=>{
    const response=await fetch(path,{signal:controller.signal});
    if(!response.ok)throw Error('Workspace could not be loaded.');
    await response.text();
   })),
   new Promise(resolve=>setTimeout(resolve,reduced?0:850))
  ]);
  if(pending!==controller||controller.signal.aborted)return;
  description.textContent='Your workspace is ready.';
  location.assign(destination.href);
 }catch(error){
  if(pending!==controller)return;
  pending=null;loader.classList.add('failed');
  description.textContent=error.name==='AbortError'?'The workspace is taking longer than expected. Try again.':'Could not open the workspace. Check that the local server is running.';
  document.querySelector('#loader-fallback').hidden=false;
 }finally{clearTimeout(timeout);}
});
