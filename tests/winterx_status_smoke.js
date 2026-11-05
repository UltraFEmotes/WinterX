const vm=require('vm'),fs=require('fs'),assert=require('assert');
const source=fs.readFileSync('RubyJailbreak/main.js','utf8');
function launch(saved, active) {
 const views=[], writes={};
 function View(o){Object.assign(this,o);this.add=x=>{views.push(x);return x;};}
 function Nav(root){this.root=root;}
 const ctx={UIViewController:View,UILabel:View,UIButton:View,UINavigationController:Nav,UIApplication:{run(){}},
  UIAlertView:{show(){throw Error('Unexpected version picker or alert');}},
  files:{exists(p){return p==='winterx/status' && ctx.active;},readJSON(){throw Error('no bridge');},writeJSON(p,v){writes[p]=v;}},
  storage:{get(k){return saved[k];},set(k,v){saved[k]=v;},remove(k){delete saved[k];}},setInterval(){},Date,Math,Number,String,isFinite,active};
 vm.runInNewContext(source,ctx);
 return {ctx,views,writes,saved};
}
const live=launch({},true);
assert(live.views.some(v=>v.text==='Successfully Jailbroken'));
const button=live.views.find(v=>v.title==='Jailbreak');assert.strictEqual(button.enabled,false);
live.ctx.active=false;live.ctx.refresh();assert.strictEqual(button.enabled,true);
assert(live.views.some(v=>(v.text||'').includes('start the Ruby bridge')));
assert(live.views.some(v=>(v.text||'').includes('Rooted Android')));
for (const version of [undefined,'0.8.1','0.9 Preview 1','0.9','unknown']) {
 const saved={'winterx.version.v1':version};
 if(version && version!=='0.8.1')saved['jailbreak.request.v1']='old-preview-request';
 const app=launch(saved,false);
 assert.strictEqual(app.saved['winterx.version.v1'],'0.8.1');
 assert.strictEqual(app.ctx.selectVersion,undefined);
 assert(app.views.some(v=>v.text==='Supports Spring 0.8.1'));
 assert(!app.views.some(v=>(v.title||v.text||'').includes('0.9')));
 assert(!app.views.some(v=>v.title==='Spring 0.8.1'));
 const jailbreak=app.views.find(v=>v.title==='Jailbreak');
 assert.strictEqual(jailbreak.enabled,true);
 jailbreak.onTap();
 const request=Object.values(app.writes)[0];
 assert.strictEqual(request.action,'jailbreak');
 assert.strictEqual(request.version,'0.8.1');
}
const manifest=JSON.parse(fs.readFileSync('RubyJailbreak/app.json','utf8'));
assert.strictEqual(manifest.version,'0.7');assert.strictEqual(manifest.build,7);
assert(manifest.description.includes('Android 10 ARM64 emulator'));
assert(manifest.description.includes('original installed Spring APK'));
assert(manifest.description.includes('https://github.com/UltraFEmotes/WinterX'));
console.log('WinterX: bridgeless status, 0.8.1-only UI, saved-preview migration, request version and description passed');
