"use strict";
const $ = (id) => document.getElementById(id);
const canvas = $("map"), ctx = canvas.getContext("2d");
ctx.imageSmoothingEnabled = true;
const scene = new window.CityScene(canvas);
let world, state = null, busy = false, paused = false, selected = "townhall", path = [], toastTimer;
let player = {x:22,y:19,dir:2,walk:0}, people = [], nextDay = Date.now()+60000, lastTime = 0, moveSave = null;
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const keys = new Set(), blocked = new Set();
let budgetOpen=false;
const money = (c) => new Intl.NumberFormat("fr-FR", {maximumFractionDigits:2}).format(c/100);
const escape = (s) => String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

async function api(url, body) {
  const response = await fetch(url, body === undefined ? {cache:"no-store"} : {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const data = await response.json();
  if(!response.ok) throw new Error(data.error || "La ville ne répond pas. Réessaie dans un instant.");
  return data;
}
function toast(message) { $("toast").textContent=message; $("toast").hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$("toast").hidden=true,5000); }
async function action(name,payload={}) {
  if(busy) return;
  busy=true; render();
  try {
    state=await api("/api/action",{id:crypto.randomUUID(),action:name,payload}); world=state.world;
    if(name==="home") { const b=building(state.player.home); player.x=b.door[0];player.y=b.door[1]; await savePosition(); selected="townhall"; scene.focus(player.x,player.y); }
    if(name==="job") {nextDay=Date.now()+60000;toast("Tu es installé. Le quotidien se fait tout seul.");}
    if(name==="advance") { nextDay=Date.now()+60000; toast("Nouvelle journée. Ton budget est à jour."); }
    if(name==="complete_goal") toast("Ton aménagement est prêt !");
  } catch(e) { toast(e.message); }
  finally {busy=false;render();}
}
async function start() {
  if(busy) return;
  busy=true;
  try { state=await api("/api/session",{}); world=state.world;player.x=state.player.position[0];player.y=state.player.position[1]; }
  catch(e) {toast(e.message);}
  finally {busy=false;render();}
}
function building(id) {return world.places.buildings.find(b=>b.id===id);}
function canWalk(x,y) {return x>=0&&y>=0&&x<48&&y<30&&!blocked.has(`${x},${y}`);}
function findPath(x,y,tx,ty) {
  x=Math.round(x);y=Math.round(y);
  if(!canWalk(tx,ty)) return [];
  const queue=[[x,y]], seen=new Map([[`${x},${y}`,null]]);let target=null;
  for(let i=0;i<queue.length;i++) {const [cx,cy]=queue[i];if(cx===tx&&cy===ty){target=[cx,cy];break;}
    for(const [dx,dy] of [[0,1],[1,0],[0,-1],[-1,0]]) {const nx=cx+dx,ny=cy+dy,key=`${nx},${ny}`;if(canWalk(nx,ny)&&!seen.has(key)){seen.set(key,[cx,cy]);queue.push([nx,ny]);}}
  }
  if(!target) return [];
  const result=[];let node=target;while(node&&(node[0]!==x||node[1]!==y)){result.push(node);node=seen.get(`${node[0]},${node[1]}`);}return result.reverse();
}
function go(id) {const b=building(id);if(!b)return;selected=id;path=findPath(player.x,player.y,...b.door);scene.follow=true;scene.focus(player.x,player.y);render();canvas.focus({preventScroll:true});}
async function savePosition() {
  if(!state) return;
  const x=Math.round(player.x),y=Math.round(player.y);
  if(!canWalk(x,y)) return;
  try {await api("/api/move",{x,y});$("save-status").textContent="Sauvegarde à jour";} catch(e){$("save-status").textContent="Sauvegarde en attente";}
}
function scheduleSave(){clearTimeout(moveSave);moveSave=setTimeout(savePosition,350);}
function nearest() {return world?.places.buildings.find(b=>Math.abs(player.x-b.door[0])+Math.abs(player.y-b.door[1])<2.5);}
function button(label,act,cls="primary") {return `<button class="${cls}" data-act="${act}" ${busy?"disabled":""}>${label}</button>`;}
function icon(kind){
 const drawings={home:'<path d="M3 12 14 3l11 9v13H6V12" fill="#d6b793"/><path d="m2 13 12-10 12 10" fill="none" stroke="#aa7c65" stroke-width="3"/><path d="M12 25V15h6v10" fill="#809985"/>',garden:'<path d="M14 25V10M14 17C2 17 3 5 3 5s11-1 11 12M14 14C25 14 25 3 25 3S14 3 14 14" fill="#83a86d" stroke="#69845e" stroke-width="1.4"/>',delivery:'<path d="M3 9h20v14H3z" fill="#a8c0c5"/><path d="m3 9 10-6 10 6M13 3v20" fill="none" stroke="#668991" stroke-width="2"/><path d="M2 25h23" stroke="#8b9c88" stroke-width="2"/>',bench:'<path d="M3 7h22v8H3zM2 18h24M5 18v7M23 18v7" fill="#c3a17d" stroke="#9b886d" stroke-width="3"/>'};
 return '<span class="choice-icon" aria-hidden="true"><svg viewBox="0 0 28 28">'+(drawings[kind]||drawings.home)+'</svg></span>';
}
function choice(label,detail,attribute,value,kind,disabled=false){
 return '<button class="choice" data-'+attribute+'="'+value+'" '+(busy||disabled?'disabled':'')+'>'+icon(kind)+'<span class="choice-copy"><strong>'+label+'</strong><small>'+detail+'</small></span></button>';
}
function guides(){
 if(!state)return [{id:"townhall",label:"J"}];
 if(!state.player.home)return [{id:"home_place",label:"1"},{id:"home_garden",label:"2"}];
 if(!state.player.job)return [{id:"farm",label:"♧"},{id:"market",label:"↗"}];
 if(state.player.goal)return [{id:state.goals[state.player.goal].location,label:"✓"}];
 return [];
}
function render(){
 if(!world)return;
 $("day-label").textContent='Jour '+Math.max(1,world.day);
 $("wallet").textContent=state?money(state.player.cash_cents)+' pièces':'Visite libre';
 $("advance").disabled=busy||!state?.player.job;
 $("pause").textContent=paused?'Reprendre':'Pause';$("pause").setAttribute('aria-pressed',String(paused));
 $("backup").hidden=!state;$("home-nav").hidden=!state?.player.home;
 if(state?.player.home)$("home-nav").dataset.place=state.player.home;
 document.querySelectorAll('[data-place]').forEach(b=>b.classList.toggle('active',b.dataset.place===selected));
 let html='',progress='Bienvenue',welcome='Jeanne t’attend à la mairie.';
 if(!state){html='<h2>Bienvenue chez toi.</h2><p>Choisis une maison, puis une activité.</p>'+button('M’installer','start')+'<p class="hint">Tu peux aussi te promener.</p>';}
 else if(!state.player.home){
  progress='1 / 2';welcome='Les repères 1 et 2 indiquent les maisons.';
  html='<h2>Quelle maison ?</h2><p>'+money(state.player.rent_cents)+' pièces / jour, dans les deux maisons.</p>'
   +choice('1 · Maison de la place','Au cœur du quartier','home','home_place','home')
   +choice('2 · Maison du jardin','Près des arbres','home','home_garden','garden');
 }else if(!state.player.job){
  progress='2 / 2';welcome='Choisis une activité qui te plaît.';
  html='<h2>Une activité.</h2><p>+'+money(state.player.wage_net_cents)+' pièces / jour. Automatiquement.</p>'
   +choice('Jardinier','Prendre soin du quartier','job','gardener','garden')
   +choice('Livreur','Relier les voisins','job','delivery','delivery');
 }else{
  progress='Installé';const p=state.player;
  welcome=path.length?'Suis les petits points jusqu’à '+building(selected).name+'.':'Promène-toi. Le quotidien est pris en charge.';
  if(p.goal){const g=state.goals[p.goal],place=building(g.location),near=Math.abs(player.x-place.door[0])+Math.abs(player.y-place.door[1])<=3;
   welcome=near?'Tu es arrivé. Ton projet peut commencer.':'Ton projet t’attend aux '+(g.location==='farm'?'jardins.':'ateliers.');
   html='<h2>'+escape(g.name)+'</h2><p>'+money(g.cost_cents)+' pièces, tout compris.</p><div class="goal-location">⌖ '+escape(building(g.location).name)+'</div>'
    +(near?button('Réaliser cet aménagement','complete_goal'):button('Rejoindre le lieu','go-goal'))
    +button('Une autre idée','other-goal','secondary');
  }else if(selected==='market'||selected==='bakery'){
   html='<h2>'+escape(building(selected).name)+'</h2><p>Ton panier est déjà pris en charge.</p>'+button('Mes envies','notebook','secondary');
  }else{
   html='<h2>Une petite envie ?</h2>'
    +choice((p.completed_goals.includes('garden')?'✓ ':'')+'Un jardin fleuri','8 pièces · aux jardins','goal','garden','garden',p.completed_goals.includes('garden'))
    +choice((p.completed_goals.includes('bench')?'✓ ':'')+'Un banc pour les voisins','8 pièces · à l’atelier','goal','bench','bench',p.completed_goals.includes('bench'))
    +'<p class="hint">Facultatif. Tu peux juste explorer.</p>';
  }
  html+='<div class="routine-chip">'+escape(state.jobs[p.job].name)+' · automatique</div><div class="balance-line"><span>Reste prévu / jour</span><strong class="'+(p.daily_balance_cents>=0?'positive':'negative')+'">'+(p.daily_balance_cents>=0?'+':'')+money(p.daily_balance_cents)+' pièces</strong></div>';
  html+='<details id="budget-details" class="budget-details" '+(budgetOpen?'open':'')+'><summary>Mon budget prévu</summary><div class="budget"><div><span>Revenu net</span><strong>+'+money(p.wage_net_cents)+'</strong></div><div><span>Panier</span><strong>−'+money(p.food_price_cents)+'</strong></div><div><span>Loyer</span><strong>−'+money(p.rent_cents)+'</strong></div></div>';
  if(p.journal.length)html+='<section class="journal"><h3>Dernière journée</h3>'+p.journal.map(j=>'<div><span>'+escape(j.label)+'</span><strong>'+(j.cents>0?'+':'')+money(j.cents)+'</strong></div>').join('')+'</section>';
  html+='</details>';
  if(p.completed_goals.length)html+='<div class="completed">'+p.completed_goals.length+' aménagement'+(p.completed_goals.length>1?'s':'')+' réalisé'+(p.completed_goals.length>1?'s':'')+'.</div>';
 }
 $("panel").innerHTML=html;$("progress").textContent=progress;$("welcome").textContent=welcome;
 $("guide-icon").textContent=!state?.player.home?'⌂':!state.player.job?'♧':state.player.goal?'⌖':'✓';
 $("routine-note").textContent=state?.player.job?'Travail, courses, loyer : automatique. Reviens sans pénalité.':'Deux choix. Puis le quotidien se fait tout seul.';
 const details=$("budget-details");if(details)details.ontoggle=()=>budgetOpen=details.open;
 document.querySelectorAll('[data-act]').forEach(b=>b.onclick=()=>{
  const a=b.dataset.act;
  if(a==='start')return start();
  if(a==='go-goal')return go(state.goals[state.player.goal].location);
  if(a==='other-goal'){selected='townhall';return action('cancel_goal');}
  if(a==='notebook'){selected='townhall';return render();}
  if(a==='complete_goal')return savePosition().then(()=>action(a));
 });
 document.querySelectorAll('[data-home]').forEach(b=>b.onclick=()=>action('home',{home:b.dataset.home}));
 document.querySelectorAll('[data-job]').forEach(b=>b.onclick=()=>action('job',{job:b.dataset.job}));
 document.querySelectorAll('[data-goal]').forEach(b=>b.onclick=()=>action('goal',{goal:b.dataset.goal}));
 $("zoom-level").textContent=Math.round(scene.zoom*100)+' %';
}
function draw(){if(world)scene.render({world,player,people,state,selected,path,guide:guides()});}
function moveActor(actor,route,dt){if(!route.length)return;const [x,y]=route[0],dx=x-actor.x,dy=y-actor.y,dist=Math.hypot(dx,dy),step=dt*4;if(dist<=step){actor.x=x;actor.y=y;route.shift();if(actor===player&&!route.length){scheduleSave();render();}}else{actor.x+=dx/dist*step;actor.y+=dy/dist*step;actor.dir=Math.abs(dx)>Math.abs(dy)?(dx>0?1:3):(dy>0?2:0);}actor.walk+=dt;}
function stepMove(dx,dy){const x=Math.round(player.x)+dx,y=Math.round(player.y)+dy;if(canWalk(x,y)){path=[[x,y]];selected=nearest()?.id||selected;}}
function animate(time){const dt=Math.min(.05,(time-lastTime)/1000||0);lastTime=time;if(world){if(!path.length&&keys.size){if(keys.has("ArrowUp")||keys.has("z")||keys.has("w"))stepMove(0,-1);else if(keys.has("ArrowDown")||keys.has("s"))stepMove(0,1);else if(keys.has("ArrowLeft")||keys.has("q")||keys.has("a"))stepMove(-1,0);else if(keys.has("ArrowRight")||keys.has("d"))stepMove(1,0);}moveActor(player,path,dt);if(!reduced&&!paused)for(const p of people){if(!p.path.length&&time>p.next){p.destination=(p.destination+1)%world.places.buildings.length;p.path=findPath(p.x,p.y,...world.places.buildings[p.destination].door);p.next=time+7000+p.destination*500;}moveActor(p,p.path,dt*.45);}draw();const near=nearest();$("interact").hidden=!near;$("interact").textContent=near?.id==="townhall"?"Parler à Jeanne":near?`Découvrir ${near.name}`:"";}requestAnimationFrame(animate);}

function pointerPosition(e){const r=canvas.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
function pick(e){
 if(!world)return;const m=pointerPosition(e);
 for(const g of guides()){const b=building(g.id),pin=scene.screen(b.x+b.w/2,b.y+b.h/2,b.kind==='townhall'?127:110);if(Math.hypot(m.x-pin.x,m.y-pin.y)<22*scene.scale){go(b.id);return;}}
 // Check the projected roof before the ground: tall buildings cover other tiles.
 const candidates=world.places.buildings.map(b=>({b,depth:scene.project(b.x+b.w/2,b.y+b.h).y})).sort((a,b)=>b.depth-a.depth);
 for(const {b} of candidates){const corners=[scene.screen(b.x-.4,b.y-.4,75),scene.screen(b.x+b.w+.4,b.y-.4,75),scene.screen(b.x+b.w+.4,b.y+b.h+.4),scene.screen(b.x-.4,b.y+b.h+.4)];
  if(pointInPolygon(m,corners)){go(b.id);return;}
 }
 const p=scene.worldAt(m.x,m.y),x=Math.floor(p.x),y=Math.floor(p.y);
 if(canWalk(x,y)){path=findPath(player.x,player.y,x,y);scene.follow=true;canvas.focus({preventScroll:true});}
}
function pointInPolygon(p,points){let inside=false;for(let i=0,j=points.length-1;i<points.length;j=i++){const a=points[i],b=points[j];if((a.y>p.y)!==(b.y>p.y)&&p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x)inside=!inside;}return inside;}
const pointers=new Map();let dragDistance=0,pinchDistance=0,suppressClick=false;
canvas.addEventListener('pointerdown',e=>{
 canvas.setPointerCapture(e.pointerId);const p=pointerPosition(e);pointers.set(e.pointerId,p);
 dragDistance=0;
 if(pointers.size===2){const [a,b]=[...pointers.values()];pinchDistance=Math.hypot(a.x-b.x,a.y-b.y);suppressClick=true;}
});
canvas.addEventListener('pointermove',e=>{
 if(!pointers.has(e.pointerId))return;const old=pointers.get(e.pointerId),p=pointerPosition(e);pointers.set(e.pointerId,p);
 if(pointers.size>=2){const [a,b]=[...pointers.values()],d=Math.hypot(a.x-b.x,a.y-b.y);if(pinchDistance>0)scene.zoomBy(d/pinchDistance,(a.x+b.x)/2,(a.y+b.y)/2);pinchDistance=d;suppressClick=true;renderZoom();}
 else{const dx=p.x-old.x,dy=p.y-old.y;dragDistance+=Math.hypot(dx,dy);if(dragDistance>5){scene.pan(dx,dy);suppressClick=true;}}
});
function finishPointer(e){pointers.delete(e.pointerId);if(pointers.size<2)pinchDistance=0;if(pointers.size===0){if(e.type!=='pointercancel'&&!suppressClick&&dragDistance<6)pick(e);suppressClick=false;dragDistance=0;}}
canvas.addEventListener('pointerup',finishPointer);canvas.addEventListener('pointercancel',finishPointer);
canvas.addEventListener('wheel',e=>{e.preventDefault();const p=pointerPosition(e);scene.zoomBy(Math.exp(-Math.max(-100,Math.min(100,e.deltaY))*.0035),p.x,p.y);renderZoom();},{passive:false});
function renderZoom(){$('zoom-level').textContent=Math.round(scene.zoom*100)+' %';}
$('zoom-in').onclick=()=>{scene.zoomBy(1.2);renderZoom();};
$('zoom-out').onclick=()=>{scene.zoomBy(1/1.2);renderZoom();};
$('overview').onclick=()=>{scene.overview();renderZoom();};
$('follow').onclick=()=>{scene.follow=true;scene.focus(player.x,player.y);};
window.addEventListener('resize',()=>scene.resize());
canvas.addEventListener("keydown",(e)=>{const key=e.key.length===1?e.key.toLowerCase():e.key;if(["ArrowUp","ArrowDown","ArrowLeft","ArrowRight","z","q","s","d","w","a"].includes(key)){e.preventDefault();keys.add(key);}if(key==="+"||key==="="){e.preventDefault();scene.zoomBy(1.2);renderZoom();}if(key==="-"){e.preventDefault();scene.zoomBy(1/1.2);renderZoom();}if(key==="0"){e.preventDefault();scene.overview();renderZoom();}if(key==="e"||key==="Enter"){e.preventDefault();const b=nearest();if(b){selected=b.id;render();}}});
window.addEventListener("keyup",e=>keys.delete(e.key.length===1?e.key.toLowerCase():e.key));window.addEventListener("blur",()=>keys.clear());
$("interact").onclick=()=>{const b=nearest();if(b){selected=b.id;render();}};
document.querySelectorAll("[data-place]").forEach(b=>b.onclick=()=>go(b.dataset.place));document.querySelectorAll("[data-move]").forEach(b=>b.onclick=()=>stepMove(...b.dataset.move.split(",").map(Number)));
$("advance").onclick=()=>action("advance");$("pause").onclick=()=>{paused=!paused;nextDay=Date.now()+60000;render();};
$("backup").onclick=async()=>{try{const data=await api("/api/backup"),url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download="city-ma-sauvegarde.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){toast(e.message);}};
document.addEventListener("visibilitychange",()=>{nextDay=Date.now()+60000;if(document.hidden){keys.clear();savePosition();}});
setInterval(()=>{if(!document.hidden&&!paused&&!busy&&state?.player.job&&Date.now()>=nextDay)action("advance");},1000);
(async()=>{try{world=await api("/api/world");world.places.blocked.forEach(([x,y])=>blocked.add(`${x},${y}`));people=world.places.people.map((p,i)=>({...p,x:p.start[0],y:p.start[1],dir:2,walk:0,path:[],destination:i%7,next:4000+i*900}));try{state=await api("/api/me");player.x=state.player.position[0];player.y=state.player.position[1];}catch(e){if(e.message!=="Installe-toi pour retrouver ton carnet")throw e;}render();requestAnimationFrame(animate);}catch(e){$("panel").innerHTML=`<div class="error-note">${escape(e.message)} Recharge la page quand la ville est disponible.</div>`;}})();
