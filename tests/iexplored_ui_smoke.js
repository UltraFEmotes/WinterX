const vm = require('vm'), fs = require('fs'), assert = require('assert');
const source=fs.readFileSync('IExplored/main.js','utf8');
const screens=[], remembered={};
function Table(o) { Object.assign(this,o); screens.push(this); }
function View(o) { Object.assign(this,o); this.add=x=>x; screens.push(this); }
function Nav(root) { this.root=root; this.push=x=>{this.top=x;}; this.pop=()=>{}; }
function context(active) {
  return {UITableViewController:Table,UIViewController:View,UINavigationController:Nav,UITextView:View,UIButton:View,
    UIApplication:{run(){}}, UIAlertView:{show(){}},
    files:{exists(p){return active && p==='winterx/';},list(p){assert.strictEqual(p,'winterx/');return ['notes/'];},stat(){return {size:0};}},
    storage:{get(k){return remembered[k];},set(k,v){remembered[k]=v;},remove(k){delete remembered[k];}},
    setTimeout(fn){fn();},Date,Math,String};
}
assert.throws(()=>vm.runInNewContext(source,context(false)),/WinterX is not active/);
const active=context(true); vm.runInNewContext(source,active);
assert.strictEqual(active.root.sections[1].rows[0].title,'notes');
active.root.sections[1].rows[0].onSelect();
const page=screens.find(x=>x.title==='notes');
assert(page.sections[0].rows.some(x=>x.title==='Open Folder'));
assert(page.sections[0].rows.some(x=>x.title==='Move to Trash'));
console.log('IExplored closes unjailbroken and browses directly when authorized');
