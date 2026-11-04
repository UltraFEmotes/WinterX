const vm=require('vm'),fs=require('fs'),assert=require('assert');
const source=fs.readFileSync('RubyJailbreak/main.js','utf8');
const views=[];
function View(o){Object.assign(this,o);this.add=x=>{views.push(x);return x;};}
function Nav(root){this.root=root;}
let active=true;
const ctx={UIViewController:View,UILabel:View,UIButton:View,UINavigationController:Nav,UIApplication:{run(){}},
 files:{exists(p){return p==='winterx/status' && active;},readJSON(){throw Error('no bridge');}},
 storage:{get(){return null;},set(){},remove(){}},setInterval(){},Date,Math,Number,String,isFinite};
vm.runInNewContext(source,ctx);
assert(views.some(v=>v.text==='Successfully Jailbroken'));
const button=views.find(v=>v.title==='Jailbreak');assert.strictEqual(button.enabled,false);
active=false;ctx.refresh();assert.strictEqual(button.enabled,true);
assert(views.some(v=>(v.text||'').includes('Start the Ruby bridge')));
console.log('WinterX status works with no bridge and jailbreak button remains available when unpatched');
