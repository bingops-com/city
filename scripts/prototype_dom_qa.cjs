/* Exercise the shipped UI against the real HTTP handler and game without sockets. */
const fs=require('fs'),path=require('path'),vm=require('vm'),readline=require('readline'),{spawn}=require('child_process');
const {CanvasRecorder,toSVG}=require('./canvas_recorder.cjs');
const root=path.resolve(__dirname,'..'),output=path.join(root,'results/prototype');fs.mkdirSync(output,{recursive:true});
const save='/tmp/city-prototype-dom.sqlite';for(const suffix of ['','-wal','-shm']){try{fs.unlinkSync(save+suffix)}catch{}}
const bridge=spawn('python3',[path.join(__dirname,'prototype_bridge.py'),save],{stdio:['pipe','pipe','pipe']});
const pending=[];readline.createInterface({input:bridge.stdout}).on('line',line=>pending.shift()(JSON.parse(line)));
bridge.stderr.on('data',d=>process.stderr.write(d));const send=data=>new Promise(resolve=>{pending.push(resolve);bridge.stdin.write(JSON.stringify(data)+'\n');});
let cookie='',frame,now=1700000000000;const timers=[],draws=[];
class Element {
  constructor(tag,attrs,owner,doc){this.tag=tag;this.owner=owner;this.doc=doc;this.dataset={};this.listeners={};this.hidden=attrs.hidden!==undefined;this.disabled=attrs.disabled!==undefined;this.textContent='';this.classList={toggle:()=>{}};for(const [k,v] of Object.entries(attrs)){if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v;}this.id=attrs.id;}
  set innerHTML(value){this.html=value;this.doc.elements=this.doc.elements.filter(e=>e.owner!==this);this.doc.parse(value,this);}
  get innerHTML(){return this.html||'';}
  setAttribute(k,v){this[k]=v;}
  addEventListener(name,callback){this.listeners[name]=callback;}
  focus(){}
  click(){if(!this.disabled&&this.onclick)return this.onclick();}
  getBoundingClientRect(){return this.id==='map'?{left:0,top:0,width:1440,height:880}:{left:0,top:0,width:28,height:36};}
  setPointerCapture(){}
  getContext(){if(!this.context)this.context=new CanvasRecorder(this.id==='map'?draws:[]);return this.context;}
}
class Document {
  constructor(){this.elements=[];this.hidden=false;this.listeners={};this.parse(fs.readFileSync(path.join(root,'prototype/dist/index.html'),'utf8'),null);}
  parse(html,owner){for(const match of html.matchAll(/<([a-z][a-z0-9-]*)([^>]*?)>/gi)){const attrs={};for(const a of match[2].matchAll(/([a-zA-Z][\w-]*)(?:="([^"]*)")?/g))attrs[a[1]]=a[2]??'';const e=new Element(match[1],attrs,owner,this);this.elements.push(e);}}
  getElementById(id){return this.elements.find(e=>e.id===id);}
  querySelectorAll(selector){const match=selector.match(/^\[data-([\w-]+)\]$/);if(!match)return [];const key=match[1].replace(/-([a-z])/g,(_,c)=>c.toUpperCase());return this.elements.filter(e=>e.dataset[key]!==undefined);}
  addEventListener(name,callback){this.listeners[name]=callback;}
  createElement(tag){return new Element(tag,{},null,this);}
}
const document=new Document();class Clock extends Date {static now(){return now;}}
const context=vm.createContext({document,window:{matchMedia:()=>({matches:true}),addEventListener:()=>{}},console,Intl,Date:Clock,Math,Set,Map,JSON,Blob,URL,crypto:require('crypto').webcrypto,
  setTimeout,clearTimeout,setInterval:(f)=>{timers.push(f);return timers.length;},requestAnimationFrame:f=>{frame=f;},
  fetch:async(url,options={})=>{const req={path:url,method:options.method||'GET',headers:{Origin:'http://localhost:8092',Cookie:cookie}};if(options.body)req.payload=JSON.parse(options.body);const response=await send(req);if(response.error)throw new Error(response.error);if(response.headers['set-cookie'])cookie=response.headers['set-cookie'].split(';')[0];return {ok:response.status<400,json:async()=>JSON.parse(response.body)};}});
const element=(key,value)=>document.querySelectorAll(`[data-${key}]`).find(e=>e.dataset[key]===value);
async function until(fn){for(let i=0;i<500;i++){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw new Error('UI state not reached');}
(async()=>{try {
  vm.runInContext(fs.readFileSync(path.join(root,'prototype/dist/scene.js'),'utf8'),context);
  vm.runInContext(fs.readFileSync(path.join(root,'prototype/dist/app.js'),'utf8'),context);
  await until(()=>element('act','start'));await element('act','start').click();await until(()=>element('home','home_garden'));
  await element('home','home_garden').click();await until(()=>element('job','gardener'));await element('job','gardener').click();
  await until(()=>document.getElementById('panel').innerHTML.includes('Mon budget prévu'));
  await document.getElementById('advance').click();await until(()=>document.getElementById('panel').innerHTML.includes('Dernière journée'));
  const current=JSON.parse((await send({path:'/api/me',headers:{Cookie:cookie}})).body);
  document.hidden=true;document.listeners.visibilitychange();now+=3*86400000;timers.forEach(f=>f());await new Promise(r=>setTimeout(r,20));
  const offline=JSON.parse((await send({path:'/api/me',headers:{Cookie:cookie}})).body);
  if(current.world.day!==offline.world.day||current.player.cash_cents!==offline.player.cash_cents)throw new Error('Offline costs applied');
  document.hidden=false;document.listeners.visibilitychange();await element('goal','garden').click();await until(()=>element('act','go-goal'));
  element('act','go-goal').click();for(let i=0;i<500;i++){draws.length=0;frame(i*50);}
  await until(()=>element('act','complete_goal'));await element('act','complete_goal').click();await until(()=>document.getElementById('panel').innerHTML.includes('1 aménagement'));
  draws.length=0;frame(26000);fs.writeFileSync(path.join(output,'map-draw-operations.json'),JSON.stringify(draws));
  fs.writeFileSync(path.join(output,'map-closeup.svg'),toSVG(draws,1440,880));
  const scene=vm.runInContext('scene',context);
  scene.overview();draws.length=0;frame(26050);
  fs.writeFileSync(path.join(output,'map-preview.svg'),toSVG(draws,1440,880));
  const anchor=scene.worldAt(370,250);scene.zoomBy(1.8,370,250);const anchored=scene.worldAt(370,250);
  if(Math.hypot(anchor.x-anchored.x,anchor.y-anchored.y)>1e-8)throw new Error('Zoom changed the pointed world coordinate');
  scene.zoomBy(100);if(scene.zoom!==3.2)throw new Error('Zoom upper bound');
  scene.zoomBy(.0001);if(scene.zoom!==.65)throw new Error('Zoom lower bound');
  document.getElementById('overview').click();if(scene.zoom!==1)throw new Error('Overview did not reset zoom');
  const screen=scene.screen(22,19),roundtrip=scene.worldAt(screen.x,screen.y);
  if(Math.hypot(roundtrip.x-22,roundtrip.y-19)>1e-8)throw new Error('Inverse projection failed');
  scene.pan(50,30);if(scene.follow)throw new Error('Pan should stop follow');
  document.getElementById('follow').click();if(!scene.follow)throw new Error('Follow failed');
  const home=vm.runInContext('building("home_place")',context),roof=scene.screen(home.x+home.w/2,home.y+home.h/2,60);
  document.getElementById('map').listeners.pointerdown({pointerId:1,clientX:roof.x,clientY:roof.y});
  document.getElementById('map').listeners.pointerup({pointerId:1,clientX:roof.x,clientY:roof.y,type:'pointerup'});
  if(vm.runInContext('selected',context)!=='home_place')throw new Error('Roof click did not select its building');
  const el=document.getElementById('map'),beforePan={...scene.center};
  el.listeners.pointerdown({pointerId:2,clientX:500,clientY:400});
  el.listeners.pointermove({pointerId:2,clientX:550,clientY:440});
  el.listeners.pointerup({pointerId:2,clientX:550,clientY:440,type:'pointerup'});
  if(Math.hypot(scene.center.x-beforePan.x,scene.center.y-beforePan.y)<1)throw new Error('Drag did not pan');
  el.listeners.pointerdown({pointerId:3,clientX:300,clientY:300});
  el.listeners.pointerdown({pointerId:4,clientX:400,clientY:300});
  const beforePinch=scene.zoom;
  el.listeners.pointermove({pointerId:4,clientX:450,clientY:300});
  el.listeners.pointerup({pointerId:3,clientX:300,clientY:300,type:'pointerup'});
  el.listeners.pointerup({pointerId:4,clientX:450,clientY:300,type:'pointerup'});
  if(scene.zoom<=beforePinch)throw new Error('Pinch did not zoom');
  const desktop=el.getBoundingClientRect;
  el.getBoundingClientRect=()=>({left:0,top:0,width:390,height:440});scene.resize();
  const mobilePoint=scene.screen(11,27),mobileWorld=scene.worldAt(mobilePoint.x,mobilePoint.y);
  if(Math.hypot(mobileWorld.x-11,mobileWorld.y-27)>1e-8)throw new Error('Mobile inverse projection failed');
  scene.focus(11,27);draws.length=0;frame(26100);
  fs.writeFileSync(path.join(output,'map-mobile.svg'),toSVG(draws,390,440));
  el.getBoundingClientRect=desktop;scene.resize();
  const final=JSON.parse((await send({path:'/api/me',headers:{Cookie:cookie}})).body);
  if(final.player.completed_goals.length!==1||final.world.day!==1)throw new Error('Goal or day state incorrect');
  fs.writeFileSync(path.join(output,'dom-qa.json'),JSON.stringify({transport:'HTTP handler over byte streams',dom:'minimal DOM double; no browser layout validation',initial_choices:2,daily_required_actions:0,home:final.player.home,job:final.player.job,completed_goals:final.player.completed_goals,offline_three_days_no_penalty:true,wallet_cents:final.player.cash_cents,day:final.world.day,canvas_renderer_executed:true,oblique_projection_roundtrip:true,zoom_keeps_pointed_tile:true,zoom_bounds:[.65,3.2],overview_and_follow:true,roof_hit_testing:true,drag_pan:true,pinch_zoom:true},null,2));
  fs.writeFileSync(path.join(output,'browser-qa.json'),JSON.stringify({status:'blocked',reason:'Chromium launch and TCP socket binding are denied by the execution sandbox',alternative:'UI script exercised against real Python HTTP handler, economic model and SQLite; browser layout remains unverified'},null,2));
  console.log('UI flow passed against actual Python game and SQLite');
}finally{bridge.stdin.end();}})().catch(error=>{console.error(error);process.exitCode=1;});
