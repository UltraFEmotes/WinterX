const vm=require('vm'),fs=require('fs'),assert=require('assert');
const source=fs.readFileSync('RubyJailbreak/main.js','utf8');
function launch(saved, active) {
 const views=[], writes={};
 // Like Spring's views, keep only known properties (a custom one such as version is dropped).
 const KEEP=['frame','text','title','size','bold','align','color','lines','background','onTap','enabled'];
 function View(o){for(const k of KEEP)if(k in o)this[k]=o[k];this.add=x=>{views.push(x);return x;};}
 function Nav(root){this.root=root;}
 const ctx={UIViewController:View,UILabel:View,UIButton:View,UINavigationController:Nav,UIApplication:{run(){}},
  UIAlertView:{show(){throw Error('Unexpected alert');}},
  files:{exists(p){return p==='winterx/status' && ctx.active || p in ctx.results;},readJSON(p){if(p in ctx.results)return ctx.results[p];throw Error('no bridge');},writeJSON(p,v){writes[p]=v;}},
  storage:{get(k){return saved[k];},set(k,v){saved[k]=v;},remove(k){delete saved[k];}},setInterval(){},Date,Math,Number,String,isFinite,active,results:{}};
 vm.runInNewContext(source,ctx);
 const pick=name=>views.find(v=>(v.title||'').endsWith(name));
 return {ctx,views,writes,saved,pick,message:()=>views.find(v=>(v.text||'').length>20&&v.lines===4).text,
         jailbreak:views.find(v=>v.title==='Jailbreak')};
}
// Status: bridgeless "jailbroken" receipt, and the setup text without it.
const live=launch({},true);
assert.strictEqual(live.message(),'Successfully Jailbroken');assert.strictEqual(live.jailbreak.enabled,false);
live.ctx.active=false;live.ctx.refresh();assert.strictEqual(live.jailbreak.enabled,true);
assert(live.message().includes('start the Ruby bridge')&&live.message().includes('Rooted Android'));
// Both versions are offered; 0.8.1 is the default and old or unknown saved choices fall back to it.
for (const version of [undefined,'0.8.1','0.9 Preview 1','0.9','unknown']) {
 const saved={'winterx.version.v1':version};
 if(version && version!=='0.8.1')saved['jailbreak.request.v1']='old-request';
 const app=launch(saved,false);
 assert.strictEqual(app.saved['winterx.version.v1'],'0.8.1');
 assert.strictEqual(app.saved['jailbreak.request.v1'],undefined);
 assert.strictEqual(app.pick('Spring 0.8.1').title,'✓ Spring 0.8.1');
 assert.strictEqual(app.pick('Spring 0.9 Preview 1').title,'Spring 0.9 Preview 1');
 app.jailbreak.onTap();
 const request=Object.values(app.writes)[0];
 assert.strictEqual(request.action,'jailbreak');assert.strictEqual(request.version,'0.8.1');
}
// Choosing 0.9 Preview 1 is remembered and sent; switching drops a pending request for the other version.
const pick=launch({'jailbreak.request.v1':'pending'},false);
pick.pick('Spring 0.9 Preview 1').onTap();
assert.strictEqual(pick.saved['winterx.version.v1'],'0.9-preview1');assert.strictEqual(pick.saved['jailbreak.request.v1'],undefined);
assert.strictEqual(pick.pick('Spring 0.9 Preview 1').title,'✓ Spring 0.9 Preview 1');
pick.jailbreak.onTap();
const request=Object.values(pick.writes)[0];assert.strictEqual(request.version,'0.9-preview1');
pick.ctx.results['results/'+request.id+'.json']={action:'jailbreak',ok:true,springVersion:'0.9-preview1'};pick.ctx.refresh();
assert.strictEqual(pick.saved['winterx.jailbroken.v1'],'0.9-preview1');
const again=launch({'winterx.version.v1':'0.9-preview1'},false);assert.strictEqual(again.pick('Spring 0.9 Preview 1').title,'✓ Spring 0.9 Preview 1');
// While jailbroken, choosing the other version offers a switch instead of locking Jailbreak.
const on=launch({'winterx.jailbroken.v1':'0.9-preview1','winterx.version.v1':'0.9-preview1'},true);
assert.strictEqual(on.jailbreak.enabled,false);
on.pick('Spring 0.8.1').onTap();assert.strictEqual(on.jailbreak.enabled,true);
assert.strictEqual(on.message(),'Spring 0.9 Preview 1 is jailbroken. Tap Jailbreak to switch to Spring 0.8.1.');
const unknown=launch({},true);assert.strictEqual(unknown.jailbreak.enabled,false);
unknown.pick('Spring 0.9 Preview 1').onTap();assert.strictEqual(unknown.jailbreak.enabled,true);
const manifest=JSON.parse(fs.readFileSync('RubyJailbreak/app.json','utf8'));
assert.strictEqual(manifest.version,'0.8');assert.strictEqual(manifest.build,9);
assert(manifest.description.includes('Spring 0.9 Preview 1'));
assert(manifest.description.includes('Android 10 ARM64 emulator'));
assert(manifest.description.includes('https://github.com/UltraFEmotes/WinterX'));
console.log('WinterX: status, version picker, saved choice, request version, switching and description passed');
