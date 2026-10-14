/* Native illustrated scenery. World coordinates stay independent of the camera. */
"use strict";
class CityScene {
  constructor(canvas) {
    this.canvas=canvas;this.ctx=canvas.getContext("2d");this.width=1440;this.height=880;
    this.center={x:948,y:75};this.zoom=1.18;this.scale=1;this.follow=true;this.ratio=1;
    this.resize();if(this.width<620){this.zoom=2.1;this.scale=this.baseScale*this.zoom;}
  }
  project(x,y,z=0){return {x:32*x+12*y,y:-5*x+13*y-z};}
  unproject(x,y){return {x:(13*x-12*y)/476,y:(5*x+32*y)/476};}
  resize(){const r=this.canvas.getBoundingClientRect(),w=Math.max(1,r.width),h=Math.max(1,r.height);this.width=w;this.height=h;this.ratio=Math.min(2,window.devicePixelRatio||1);this.canvas.width=Math.round(w*this.ratio);this.canvas.height=Math.round(h*this.ratio);this.baseScale=Math.min(w/1810,h/730);this.scale=this.baseScale*this.zoom;}
  screen(x,y,z=0){const p=this.project(x,y,z);return {x:(p.x-this.center.x)*this.scale+this.width/2,y:(p.y-this.center.y)*this.scale+this.height/2};}
  worldAt(sx,sy){return this.unproject((sx-this.width/2)/this.scale+this.center.x,(sy-this.height/2)/this.scale+this.center.y);}
  zoomBy(factor,sx=this.width/2,sy=this.height/2){const before=this.worldAt(sx,sy);this.zoom=Math.max(.65,Math.min(3.2,this.zoom*factor));this.scale=this.baseScale*this.zoom;const after=this.worldAt(sx,sy),a=this.project(before.x,before.y),b=this.project(after.x,after.y);this.center.x+=a.x-b.x;this.center.y+=a.y-b.y;this.follow=false;this.clamp();return this.zoom;}
  pan(dx,dy){this.center.x-=dx/this.scale;this.center.y-=dy/this.scale;this.follow=false;this.clamp();}
  clamp(){this.center.x=Math.max(100,Math.min(1820,this.center.x));this.center.y=Math.max(-270,Math.min(500,this.center.y));}
  overview(){this.zoom=1;this.scale=this.baseScale;this.center=this.project(24,14);this.follow=false;}
  focus(x,y){this.center=this.project(x,y);this.center.y-=55;this.clamp();}
  track(p){if(!this.follow)return;const q=this.screen(p.x,p.y);if(q.x<170||q.x>this.width-340||q.y<130||q.y>this.height-130){this.focus(p.x,p.y);}}
  poly(points,fill,stroke=null,width=1){const c=this.ctx;c.beginPath();points.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.closePath();if(fill){c.fillStyle=fill;c.fill();}if(stroke){c.strokeStyle=stroke;c.lineWidth=width;c.stroke();}}
  line(points,color,width=1){const c=this.ctx;c.beginPath();points.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.strokeStyle=color;c.lineWidth=width;c.stroke();}
  oval(x,y,rx,ry,color){const c=this.ctx;c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fillStyle=color;c.fill();}
  box(x,y,w,h,color){const c=this.ctx;c.fillStyle=color;c.fillRect(x,y,w,h);}
  ground(x,y,w,h,color,stroke=null){this.poly([this.project(x,y),this.project(x+w,y),this.project(x+w,y+h),this.project(x,y+h)],color,stroke);}
  text(text,x,y,color="#3b5745",size=13){const c=this.ctx;c.font=`${size}px Candara, Trebuchet MS, sans-serif`;c.textAlign="center";c.fillStyle=color;c.fillText(text,x,y);}
  badge(text,x,y,color="#fcfdf2",ink="#3b5745",size=14){const c=this.ctx;c.font=`600 ${size}px Candara, Trebuchet MS, sans-serif`;const w=c.measureText(text).width+22;this.box(x-w/2,y-18,w,27,color);this.oval(x-w/2,y-4.5,6,13.5,color);this.oval(x+w/2,y-4.5,6,13.5,color);this.text(text,x,y+1,ink,size);}
  scenery(){
    this.ground(-8,-8,65,50,"#abc78f");
    for(let y=0;y<32;y+=2)for(let x=0;x<50;x+=2){const n=(x*31+y*17)%19,p=this.project(x+.25,y+.4);if(n<5)this.oval(p.x,p.y,31,13,n%2?"#a5c086":"#b1cb95");if(n===7){this.line([{x:p.x-4,y:p.y+4},{x:p.x-2,y:p.y-2},{x:p.x+1,y:p.y+2}],"#91b176",1.2);}}
    const paths=[[8,10,30,2],[7,18,31,2],[8,27,30,1.1],[21,10,3,18],[10,9,2,19],[32,9,2,19]];
    for(const r of paths){this.ground(r[0]-.13,r[1]-.13,r[2]+.26,r[3]+.26,"#bac59a");this.ground(...r,"#e1d6ba");}
    this.ground(18,14,10,5,"#d2cbb3");
    for(let x=18;x<28;x+=.7)for(let y=14;y<19;y+=.65)this.ground(x+.07,y+.07,.54,.45,(Math.round(x*10+y*10)%3)?"#d8d1bc":"#cdc7b0");
    for(let i=0;i<40;i++){const x=8+(i*3.79)%29,y=i%2?10.3:18.4;this.ground(x,y,.09,.12,"#c5bba1");}
    const p=this.project(42.5,22);this.oval(p.x,p.y,140,57,"#96b48e");this.oval(p.x,p.y-3,127,49,"#6f9fa8");this.oval(p.x-16,p.y-8,105,39,"#83afb5");this.oval(p.x-39,p.y-16,71,23,"#90babe");
    for(let i=0;i<8;i++){const q=this.project(40.5+i%3,20+i*.5);this.line([{x:q.x-10,y:q.y},{x:q.x+12,y:q.y-2}],"#b1ced0",1.5);}
    for(let i=0;i<8;i++){const q=this.project(39.7+i*.5,25);this.line([{x:q.x,y:q.y},{x:q.x-3,y:q.y-20-i%3*4}],"#749165",2);this.oval(q.x-3,q.y-20-i%3*4,2,6,"#9c8760");}
    this.ground(5.9,22,1.7,4.2,"#947f59");for(let y=22.2;y<26;y+=.55)for(let x=6.1;x<7.5;x+=.45){const q=this.project(x,y);this.oval(q.x,q.y-3,4,3,"#699252");this.oval(q.x+2,q.y-5,3,2,"#93ad6a");}
    for(const [x,y] of [[15,9],[37,9],[9,21],[30,21]]){this.ground(x,y,1.4,.8,"#7c9770");for(let i=0;i<7;i++){const q=this.project(x+.1+i*.19,y+.25);this.oval(q.x,q.y-5,3,3,i%2?"#d9b56d":"#c99ba6");}}
    for(const [x,y] of [[8.3,4.6],[31.3,4.6]]){this.ground(x,y,6.2,.28,"#91aa77");for(let i=0;i<15;i++){const q=this.project(x+i*.42,y,0);this.line([{x:q.x,y:q.y},{x:q.x,y:q.y-13}],"#d4d4b6",2);if(i<14){const n=this.project(x+(i+1)*.42,y,10);this.line([{x:q.x,y:q.y-10},n],"#e1ddc3",2);}}}
    for(let j=0;j<3;j++){this.ground(14.5+j*1.1,23,.75,2.8,"#a08861");for(let i=0;i<5;i++){const q=this.project(14.9+j*1.1,23.2+i*.5);this.oval(q.x,q.y-4,5,4,"#7b9d61");this.oval(q.x+2,q.y-6,3,3,j%2?"#d2af68":"#94b179");}}
    const duck=this.project(43.7,22.3);this.oval(duck.x,duck.y,9,3,"#b8d0c5");this.oval(duck.x,duck.y-4,6,4,"#e7e7d1");this.oval(duck.x+5,duck.y-9,3,3,"#e7e7d1");this.poly([{x:duck.x+7,y:duck.y-9},{x:duck.x+12,y:duck.y-8},{x:duck.x+7,y:duck.y-6}],"#c9ac68");
  }
  tree(x,y,size=1){const p=this.project(x,y),s=size;this.oval(p.x+15*s,p.y+6*s,32*s,12*s,"#5c83532b");this.line([{x:p.x,y:p.y},{x:p.x-2,y:p.y-48*s}],"#887659",8*s);this.line([{x:p.x,y:p.y-25*s},{x:p.x+13*s,y:p.y-48*s}],"#8f7c5b",4*s);this.oval(p.x,p.y-52*s,32*s,28*s,"#537a55");this.oval(p.x-18*s,p.y-53*s,22*s,24*s,"#648c5b");this.oval(p.x+17*s,p.y-64*s,24*s,23*s,"#729969");this.oval(p.x-6*s,p.y-74*s,23*s,21*s,"#7ca16d");this.oval(p.x-17*s,p.y-77*s,12*s,9*s,"#8aac7b");for(let i=0;i<8;i++)this.oval(p.x+(i*13%40-20)*s,p.y-(48+i*7%35)*s,2.5*s,1.5*s,"#aac28e55");}
  bush(x,y){const p=this.project(x,y);this.oval(p.x+5,p.y+3,24,9,"#68885833");this.oval(p.x,p.y-4,19,11,"#719463");this.oval(p.x-5,p.y-10,12,9,"#86a876");}
  wallWindow(x,y,z=21,blue=false){const p=this.project.bind(this),w=.42;this.poly([p(x,y,z+21),p(x+w,y,z+21),p(x+w,y,z),p(x,y,z)],"#7c9d9c","#ece3cd",2);this.line([p(x+w/2,y,z),p(x+w/2,y,z+21)],"#eadfc5",1.5);this.line([p(x,y,z+10),p(x+w,y,z+10)],"#eadfc5",1.5);for(const q of [x-.16,x+w+.03])this.poly([p(q,y,z+21),p(q+.12,y,z+21),p(q+.12,y,z),p(q,y,z)],blue?"#6d939a":"#8b9972");this.poly([p(x-.15,y+.05,z-1),p(x+w+.15,y+.05,z-1),p(x+w+.15,y+.24,z-1),p(x-.15,y+.24,z-1)],"#b89d7c");for(let i=0;i<5;i++){const q=p(x+i*.08,y+.2,z+2);this.oval(q.x,q.y,2,3,i%2?"#cc9b9e":"#94a066");}}
  building(b){
    const p=this.project.bind(this),x=b.x,y=b.y,w=b.w,h=b.h,z=b.kind==="townhall"?79:58;
    const A=p(x,y),B=p(x+w,y),C=p(x+w,y+h),D=p(x,y+h),a=p(x,y,z),bb=p(x+w,y,z),c=p(x+w,y+h,z),d=p(x,y+h,z);
    this.poly([{x:A.x+12,y:A.y+14},{x:B.x+25,y:B.y+15},{x:C.x+34,y:C.y+17},{x:D.x+23,y:D.y+15}],"#56774929");
    this.poly([A,D,d,a],b.kind==="house"?"#cbbf9b":"#c0b498","#b1a187",1);this.poly([D,C,c,d],b.kind==="house"?"#f0e5c9":"#e4d7b9","#c4b697",1);
    this.poly([a,d,p(x,y+h/2,z+32)],b.kind==="house"?"#cbbf9b":"#c0b498","#b1a187",1);
    this.line([D,C],"#b4a589",7);this.line([D,d],"#b9a88b",2);
    for(let j=0;j<4;j++){const q1=p(x,y+.4+j*.8,10),q2=p(x,y+.4+j*.8,25);this.line([q1,q2],"#b3a58a",1);}
    const mid=y+h/2,R1=p(x-.2,mid,z+32),R2=p(x+w+.2,mid,z+32),edgeFront=[p(x-.3,y+h+.23,z),p(x+w+.3,y+h+.23,z)];
    const roof=b.kind==="townhall"?"#6d8791":b.kind==="market"?"#8c9c70":b.kind==="house"&&b.id==="home_garden"?"#83999d":"#b77e69";
    this.poly([p(x-.3,y-.23,z),p(x+w+.3,y-.23,z),R2,R1],b.kind==="townhall"?"#91a5aa":"#cc9d84","#9d8c70",1);
    this.poly([R1,R2,...edgeFront.slice().reverse()],roof,"#8c8270",1.5);
    for(let t=.17;t<1;t+=.17){const q1={x:R1.x+(edgeFront[0].x-R1.x)*t,y:R1.y+(edgeFront[0].y-R1.y)*t},q2={x:R2.x+(edgeFront[1].x-R2.x)*t,y:R2.y+(edgeFront[1].y-R2.y)*t};this.line([q1,q2],"#53644b22",1.4);for(let i=0;i<w;i+=.45){const u=i/w;this.line([{x:q1.x+(q2.x-q1.x)*u,y:q1.y+(q2.y-q1.y)*u},{x:q1.x+(q2.x-q1.x)*u+3,y:q1.y+(q2.y-q1.y)*u+4}],"#edf1d52b",1);}}
    this.line([R1,R2],b.kind==="townhall"?"#a3b4b5":"#d9af94",4);this.line(edgeFront,"#6c6a5644",3);
    const chimney=p(x+.8,y+1,z+12);this.box(chimney.x,chimney.y-25,14,27,"#baad97");this.box(chimney.x+3,chimney.y-25,11,27,"#d6c8ac");this.box(chimney.x-2,chimney.y-27,19,5,"#969382");
    const doorX=Math.max(x+.6,Math.min(x+w-.6,b.door[0]+.2));
    this.poly([p(doorX,y+h,0),p(doorX+.55,y+h,0),p(doorX+.55,y+h,34),p(doorX,y+h,34)],"#85785e","#c4b593",2);
    const knob=p(doorX+.43,y+h+.02,15);this.oval(knob.x,knob.y,1.8,1.8,"#dfc680");this.ground(doorX-.14,y+h,.95,.65,"#d4c7a9","#c0b599");
    for(let i=.9;i<w-.4;i+=1.7)if(Math.abs(x+i-doorX)>.7)this.wallWindow(x+i,y+h+.025,20,b.id==="home_garden");
    if(b.kind==="townhall"){const q=p(x+w/2,y+h,57);this.oval(q.x,q.y,13,13,"#f0e5cc");this.oval(q.x,q.y,11,11,"#ebe9d6");this.line([{x:q.x,y:q.y},{x:q.x,y:q.y-7}],"#667f7c",2);this.line([{x:q.x,y:q.y},{x:q.x+6,y:q.y+3}],"#667f7c",2);const flag=p(x+w-.4,y+h,40);this.line([{x:flag.x,y:flag.y},{x:flag.x,y:flag.y-23}],"#898d73",2);this.poly([{x:flag.x,y:flag.y-23},{x:flag.x+17,y:flag.y-19},{x:flag.x,y:flag.y-13}],"#92a887");}
    if(b.kind==="market"||b.kind==="bakery"){for(let i=0;i<w*3;i++){const q=i/3;this.poly([p(x+q,y+h,44),p(x+q+.34,y+h,44),p(x+q+.34,y+h+.7,34),p(x+q,y+h+.7,34)],i%2?"#f4ead6":b.kind==="market"?"#8f9d74":"#bb8b72");}const s=p(x+w/2,y+h,48);this.badge(b.kind==="bakery"?"Le fournil":"Chez Nora",s.x,s.y-12,"#f1e9d5","#746f55",11);if(b.kind==="market"){for(let i=0;i<3;i++){const q=p(x+.5+i*1.2,y+h+.6);this.box(q.x-9,q.y-10,24,13,"#b6976e");for(let j=0;j<6;j++)this.oval(q.x-5+(j%3)*6,q.y-10-Math.floor(j/3)*4,3,3,i%2?"#c5a65e":"#a8b97a");}}}
    if(b.kind==="workshop"){for(let i=0;i<4;i++){const q=p(x+.7,y+h+.5,3+i*3);this.line([q,{x:q.x+34,y:q.y+9}],i%2?"#bc9a70":"#967b58",4);}const q=p(x+w-.4,y+h+.4);this.oval(q.x,q.y-10,11,11,"#908c73");this.oval(q.x,q.y-10,7,7,"#c9c5aa");}
    if(b.kind==="farm"){for(let i=0;i<4;i++){const q=p(x+w-.6,y+h+.8,0);this.box(q.x-8+i*3,q.y-12-i*2,3,14,"#8d8668");}const q=p(x+.4,y+h,48);this.badge("Les jardins",q.x+35,q.y-10,"#ece9cf","#6c825c",10);}
  }
  lamp(x,y){const p=this.project(x,y);this.oval(p.x+7,p.y+2,13,5,"#51764c20");this.line([{x:p.x,y:p.y},{x:p.x,y:p.y-49}],"#6a8072",3);this.box(p.x-5,p.y-58,10,12,"#ede4b9");this.line([{x:p.x-6,y:p.y-58},{x:p.x+6,y:p.y-58},{x:p.x+5,y:p.y-46},{x:p.x-5,y:p.y-46},{x:p.x-6,y:p.y-58}],"#6c8175",1.5);}
  bench(x,y){const p=this.project.bind(this);for(let i=0;i<3;i++)this.poly([p(x,y+i*.11,18),p(x+1.3,y+i*.11,18),p(x+1.3,y+i*.11+.08,18),p(x,y+i*.11+.08,18)],"#ad906c");for(let i=0;i<2;i++)this.line([p(x+i,y+.1,0),p(x+i,y+.1,28)],"#7e886f",3);this.line([p(x,y,28),p(x+1.3,y,28)],"#b19a76",6);}
  fountain(){const q=this.project(23.5,16.4);this.oval(q.x+10,q.y+8,36,17,"#536d572a");this.oval(q.x,q.y,33,17,"#a6b4a1");this.oval(q.x,q.y-5,31,15,"#d0d6c1");this.oval(q.x,q.y-6,25,10,"#87b2b8");this.box(q.x-5,q.y-35,10,28,"#a3b6ae");this.oval(q.x,q.y-33,17,6,"#bdcdc0");this.oval(q.x,q.y-35,14,4,"#8cb5bc");this.line([{x:q.x,y:q.y-47},{x:q.x,y:q.y-39}],"#a7d0d0",3);this.oval(q.x,q.y-49,3,4,"#c0dddd");}
  person(actor,player=false,label=""){const p=this.project(actor.x+.5,actor.y+.5),s=Math.sin(actor.walk*9)*2;this.oval(p.x+3,p.y+2,10,4,"#41654036");this.line([{x:p.x-3,y:p.y-8},{x:p.x-4-s,y:p.y-1}],"#526466",4);this.line([{x:p.x+3,y:p.y-8},{x:p.x+4+s,y:p.y-1}],"#526466",4);this.oval(p.x,p.y-15,8,9,player?"#dcb75e":actor.shirt);this.line([{x:p.x-7,y:p.y-18},{x:p.x-9,y:p.y-9+s}],"#e4bf98",3);this.line([{x:p.x+7,y:p.y-18},{x:p.x+9,y:p.y-9-s}],"#e4bf98",3);this.oval(p.x,p.y-29,6.5,7,"#e9c7a6");this.oval(p.x-1,p.y-33,7,4,"#7d6955");if(actor.dir!==0){this.oval(p.x-2,p.y-29,1,1,"#58645a");this.oval(p.x+3,p.y-29,1,1,"#58645a");}if(player){this.oval(p.x,p.y-37,11,3,"#eee1ac");this.box(p.x-6,p.y-43,12,7,"#e2cea1");this.oval(p.x,p.y-43,6,2,"#eee1ac");}if(label)this.badge(label,p.x,p.y-52,"#fcfdf0ed","#577054",12);}
  marker(b,label,active=false){const p=this.project(b.x+b.w/2,b.y+b.h/2,b.kind==="townhall"?127:110);this.oval(p.x+2,p.y+2,15,15,"#55734b22");this.oval(p.x,p.y,14,14,active?"#5c8965":"#fffdf1");this.poly([{x:p.x-5,y:p.y+10},{x:p.x+5,y:p.y+10},{x:p.x,y:p.y+21}],active?"#5c8965":"#fffdf1");this.text(label,p.x,p.y+5,active?"#fff":"#5a7f56",14);}
  render({world,player,people,state,selected,path,guide=[]}){
    this.resize();this.track(player);const c=this.ctx,r=this.ratio,s=this.scale;
    c.setTransform(r,0,0,r,0,0);this.box(0,0,this.width,this.height,"#abc78f");
    c.setTransform(r*s,0,0,r*s,(this.width/2-this.center.x*s)*r,(this.height/2-this.center.y*s)*r);c.lineJoin="round";c.lineCap="round";this.scenery();
    if(path.length){const pts=[this.project(player.x+.5,player.y+.5),...path.map(([x,y])=>this.project(x+.5,y+.5))];for(let i=1;i<pts.length;i++){this.oval(pts[i].x,pts[i].y,2.5,2.5,"#fcf9dd");}const end=pts[pts.length-1];this.oval(end.x,end.y,9,5,"#fffbe0");this.oval(end.x,end.y,5,3,"#90a77c");}
    const trees=[[3,4,1.3],[5,8,1.1],[3,13,1.2],[5,18,1.1],[3,25,1.3],[7,2,1.2],[16,3,1.2],[28,3,1.1],[39,3,1.25],[42,8,1.25],[44,13,1.15],[42,28,1.2],[18,24,1.1],[27,24,1.2],[3,28,1.15],[46,6,1.2],[40,16,.9],[16,21,.85]];
    const objects=[...world.places.buildings.map(b=>({depth:this.project(b.x+b.w/2,b.y+b.h).y,draw:()=>this.building(b)})),...trees.map(([x,y,s])=>({depth:this.project(x,y).y,draw:()=>this.tree(x,y,s)})),...people.map(p=>({depth:this.project(p.x+.5,p.y+.5).y,draw:()=>this.person(p,false,Math.hypot(p.x-player.x,p.y-player.y)<3?p.name:"")})),{depth:this.project(player.x+.5,player.y+.5).y,draw:()=>this.person(player,true)},...[ [16,11],[29,11],[17,20],[36,20] ].map(([x,y])=>({depth:this.project(x,y).y,draw:()=>this.lamp(x,y)})),{depth:this.project(23.5,16.4).y,draw:()=>this.fountain()},...[ [20,19.8],[27,14],[38,17] ].map(([x,y])=>({depth:this.project(x,y).y,draw:()=>this.bench(x,y)}))];
    objects.sort((a,b)=>a.depth-b.depth);objects.forEach(o=>o.draw());for(const [x,y] of [[15,10],[37,10],[29,22],[15,27]])this.bush(x,y);
    if(state?.player.completed_goals.includes("garden")){this.ground(5,23,2,2,"#9c8c67");for(let i=0;i<12;i++){const p=this.project(5.25+i%4*.4,23.25+Math.floor(i/4)*.6);this.line([{x:p.x,y:p.y},{x:p.x,y:p.y-9}],"#7a975b",1.5);this.oval(p.x,p.y-10,4,3,i%2?"#e3bb70":"#d69ca6");}}
    if(state?.player.completed_goals.includes("bench"))this.bench(26,17.2);
    for(const g of guide){const b=world.places.buildings.find(b=>b.id===g.id);if(b)this.marker(b,g.label,selected===b.id);}
    const chosen=world.places.buildings.find(b=>b.id===selected);if(chosen){const q=this.project(chosen.x+chosen.w/2,chosen.y,145);this.badge(chosen.name,q.x,q.y,"#fcfdf0ee","#516b54",13);}
    c.setTransform(r,0,0,r,0,0);
  }
}
window.CityScene=CityScene;
