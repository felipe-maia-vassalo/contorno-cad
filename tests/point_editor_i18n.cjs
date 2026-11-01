// Executes the real component script against a small DOM/canvas test harness.
// This is a protocol/state regression test, not a browser screenshot test.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../contorno_cad/components/point_editor/index.html'),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
let render;const events=[];
const drawing=new Proxy({}, {get(){return ()=>{}},set(){return true}});
const elements={};
for(const name of ['canvas','status','help','action','remove','clear','apply'])elements[name]={textContent:'',value:'select'};
elements.action.options=['select','add','calibrate'].map(value=>({value,textContent:''}));
elements.canvas.getContext=()=>drawing;
elements.canvas.getBoundingClientRect=()=>({left:0,top:0,width:900,height:600});
elements.canvas.setPointerCapture=()=>{};
class Picture {constructor(){this.width=900;this.height=600;this._src=''}get src(){return this._src}set src(value){this._src=value;this.onload()}}
const document={documentElement:{lang:'pt-BR'},getElementById:name=>elements[name]};
const context=vm.createContext({document,Image:Picture,window:{addEventListener:(_,cb)=>render=cb},parent:{postMessage:v=>events.push(v)},structuredClone,Date,Math});
vm.runInContext(script,context);
const args={image:'data:image/png;base64,test',points:[{x:10,y:20,kind:'line'},{x:40,y:80,kind:'spline'}],calibration:[[0,0],[0,100]],revision:1,language:'pt'};
render({data:{type:'streamlit:render',args}});
assert.equal(elements.apply.textContent,'Aplicar pontos à etapa');
// Make a pending edit; a language render must not replace it with old arguments.
elements.action.value='add';elements.canvas.onpointerdown({clientX:100,clientY:120,pointerId:1});
render({data:{type:'streamlit:render',args:{...args,language:'en'}}});
assert.equal(document.documentElement.lang,'en');
assert.equal(elements.apply.textContent,'Apply points to step');
assert.equal(elements.action.options[2].textContent,'Mark two calibration points');
assert.match(elements.status.textContent,/3 profile points/);
elements.apply.onclick();
let value=events.filter(x=>x.type==='streamlit:setComponentValue').at(-1).value;
assert.equal(value.points.length,3);assert.equal(value.points[2].x,100);assert.equal(value.calibration.length,2);
render({data:{type:'streamlit:render',args:{...args,language:'pt'}}});
assert.equal(elements.apply.textContent,'Aplicar pontos à etapa');assert.match(elements.status.textContent,/3 pontos no perfil/);
render({data:{type:'streamlit:render',args:{...args,revision:2,language:'en'}}});
assert.match(elements.status.textContent,/2 profile points/);
console.log('Point editor PT/EN labels and pending-edit preservation: passed');
