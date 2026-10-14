/* Record native canvas geometry for QA and a faithful SVG drawing preview. */
const xml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
function color(value,property){if(/^#[0-9a-f]{8}$/i.test(value))return `${property}="${value.slice(0,7)}" ${property}-opacity="${parseInt(value.slice(7),16)/255}"`;return `${property}="${xml(value)}"`;}
class CanvasRecorder {
 constructor(operations){this.ops=operations;this.fillStyle='#000';this.strokeStyle='#000';this.font='13px sans-serif';this.textAlign='left';this.lineWidth=1;this.matrix=[1,0,0,1,0,0];this.path=[];}
 setTransform(...m){this.matrix=m;}
 point(x,y){const [a,b,c,d,e,f]=this.matrix;return [a*x+c*y+e,b*x+d*y+f];}
 beginPath(){this.path=[];}
 moveTo(x,y){this.path.push(['M',...this.point(x,y)]);}
 lineTo(x,y){this.path.push(['L',...this.point(x,y)]);}
 closePath(){this.path.push(['Z']);}
 ellipse(x,y,rx,ry,rotation,start,end){const [cx,cy]=this.point(x,y),m=this.matrix;this.path.push(['ellipse',cx,cy,rx*m[0],ry*m[3]]);}
 fill(){this.ops.push({type:'path',path:this.path.slice(),fill:this.fillStyle});}
 stroke(){this.ops.push({type:'path',path:this.path.slice(),stroke:this.strokeStyle,width:this.lineWidth*Math.abs(this.matrix[0])});}
 fillRect(x,y,w,h){const [px,py]=this.point(x,y);this.ops.push({type:'rect',x:px,y:py,w:w*this.matrix[0],h:h*this.matrix[3],fill:this.fillStyle});}
 fillText(text,x,y){const [px,py]=this.point(x,y),size=Number(this.font.match(/([\d.]+)px/)?.[1]||13)*Math.abs(this.matrix[0]);this.ops.push({type:'text',text,x:px,y:py,size,fill:this.fillStyle,align:this.textAlign,bold:this.font.includes('600')||this.font.includes('bold')});}
 measureText(text){return {width:text.length*Number(this.font.match(/([\d.]+)px/)?.[1]||13)*.52};}
}
function toSVG(ops,width,height){return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`+ops.map(op=>{
 if(op.type==='rect')return `<rect x="${op.x}" y="${op.y}" width="${Math.max(0,op.w)}" height="${Math.max(0,op.h)}" ${color(op.fill,'fill')}/>`;
 if(op.type==='text')return `<text x="${op.x}" y="${op.y}" ${color(op.fill,'fill')} font-family="Trebuchet MS,sans-serif" font-size="${op.size}" font-weight="${op.bold?600:400}" text-anchor="${op.align==='center'?'middle':'start'}">${xml(op.text)}</text>`;
 if(op.type==='path'){const style=(op.fill?color(op.fill,'fill'):'fill="none"')+(op.stroke?' '+color(op.stroke,'stroke')+` stroke-width="${op.width}" stroke-linecap="round" stroke-linejoin="round"`:'');
  if(op.path[0]?.[0]==='ellipse'){const [,cx,cy,rx,ry]=op.path[0];return `<ellipse cx="${cx}" cy="${cy}" rx="${Math.abs(rx)}" ry="${Math.abs(ry)}" ${style}/>`;}
  return `<path d="${op.path.map(p=>p.join(' ')).join(' ')}" ${style}/>`;
 }
 return '';
}).join('')+'</svg>';}
module.exports={CanvasRecorder,toSVG};
