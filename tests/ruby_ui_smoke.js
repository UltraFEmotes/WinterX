const vm = require('vm');
const fs = require('fs');
const assert = require('assert');
const records = {};
const data = {
  'live.json': { active: true, safeModeSupported: true, safeMode: false, settingsInstalled: false, observedAt: Date.now() },
  'packages.json': { available: [{ id: 'me.test.settings', name: 'Test', description: 'Example', author: 'A', version: '1.0', filename: 'test.springys', sha256: 'abc', installedSha256: null, previews: [] }], installed: [] }
};
const views = [];
function Table(options) { Object.assign(this, options); views.push(this); }
function Nav(root) { this.root = root; this.push = x => { this.last = x; }; }
function View(options) { Object.assign(this, options); this.children = []; this.add = x => { this.children.push(x); return x; }; views.push(this); }
const context = {
  UITableViewController: Table, UINavigationController: Nav, UIViewController: View,
  UIImageView: View, UILabel: View, UITextField: View, UIButton: View, UITabBarController: function (controllers) { this.controllers = controllers; this.selectedIndex = 0; }, UIApplication: { run() {} },
  UIAlertView: { show(options, callback) { if (callback) callback(1); } },
  storage: { get(k) { return records[k]; }, set(k,v) { records[k] = v; }, remove(k) { delete records[k]; } },
  files: { exists(p) { return p === "winterx/" || p in data; }, readJSON(p) { if (!(p in data)) throw Error('missing'); return data[p]; },
    writeJSON(p,v) { data[p] = v; }, write(p,v) { data[p]=v; }, read(p) { return data[p]; }, remove(p) { delete data[p]; }, import(options, callback) { callback(['imports/test.springys'], null); } },
  setInterval() {}, clearInterval() {}, Date, Math, Number, String, isFinite
};
const unpatched = Object.assign({}, context, {files:Object.assign({}, context.files, {exists(){return false;}})});
assert.throws(() => vm.runInNewContext(fs.readFileSync('Ruby/main.js','utf8'), unpatched), /WinterX is not active/);
vm.runInNewContext(fs.readFileSync('Ruby/main.js', 'utf8'), context);
const catalogue = views.find(x => x.title === 'Packages');
const local = views.find(x => x.title === 'Local Packages');
catalogue.sections[0].rows[0].onSelect();
let req = Object.values(data).find(x => x && x.action === 'scan_packages');
assert(req && req.id);
data['results/' + req.id + '.json'] = {ok: true, action: 'scan_packages'};
context.refreshLocal();
local.sections[2].rows[0].onSelect();
const detail = views.find(x => x.title === 'Test');
assert(detail);
detail.sections[1].rows[0].onSelect();
req = Object.values(data).find(x => x && x.action === 'install_package');
assert(req && req.filename === 'test.springys');
console.log('Ruby local package navigation and install request passed');
data['live.json'].settingsInstalled = true;
data['live.json'].colorsInstalled = false;
data['results/' + req.id + '.json'] = {ok: true, action: 'install_package'};
context.refresh();
const colorRow = catalogue.sections[1].rows.find(row => row.title === 'UI Color Test');
assert.strictEqual(colorRow.subtitle, 'Available');
colorRow.onSelect();
const colorPage = views.find(x => x.title === 'UI Color Test');
assert(colorPage.sections[1].rows.some(row => row.title === 'Details'));
colorPage.sections[1].rows[1].onSelect();
assert(Object.values(data).some(x => x && x.action === 'enable_colors'));
console.log('Ruby color status and install request passed');
req = Object.values(data).find(x => x && x.action === 'enable_colors');
data['results/' + req.id + '.json'] = {ok: true, action: 'enable_colors'};
context.refresh();
const iconRow = catalogue.sections[1].rows.find(row => row.title === 'Free Icon Placement Test');
assert.strictEqual(iconRow.subtitle, 'Available');
iconRow.onSelect();
const iconPage = views.find(x => x.title === 'Free Icon Placement Test');
assert(iconPage.sections[1].rows.some(row => row.title === 'Details'));
iconPage.sections[1].rows[1].onSelect();
assert(Object.values(data).some(x => x && x.action === 'enable_icons'));
console.log('Ruby free icon install request passed');
context.UITextField = function (opts) { Object.assign(this, opts); return this; };
context.UILabel = function (opts) { Object.assign(this, opts); return this; };
context.UIButton = function (opts) { Object.assign(this, opts); return this; };
data['repository-catalogue.json'] = { sources: [{name:'Example Repo',url:'https://example.org/index.json',error:null}], packages: [{id:'me.test.repo',name:'Example Tweak',author:'WeirdMM',description:'A test tweak',version:'1.0',filename:'repo.springys',sha256:'abc',previews:[]}] };
context.refresh();
context.showSources();
const sources = views.filter(x => x.title === 'Sources').pop();
assert(sources && sources.sections[1].rows[0].title === 'Example Repo');
catalogue.sections[3].rows[1].onSelect();
const browse = views.find(x => x.title === 'Repositories');
assert(browse.sections[0].rows[0].title === 'Example Tweak');
browse.sections[0].rows[0].onSelect();
assert(views.some(x => x.title === 'Example Tweak'));
context.showAbout();
assert(views.some(x => x.title === 'About Ruby' && x.children.some(child => (child.text || '').includes('WeirdMM') && child.lines > 1)));
assert.deepStrictEqual(Array.from(context.tabs.controllers, x => x.tabTitle), ['Ruby', 'Packages', 'Sources', 'Search']);
console.log('Ruby sources, repository browsing, package details and About passed');
// The app package must report a pending restart before it is marked installed.
let lastRequest = Object.values(data).filter(x => x && x.action === 'enable_icons').pop();
data['results/' + lastRequest.id + '.json'] = {ok:true,action:'enable_icons'};
data['app-packages.json'] = {installed:{},pending:{}};
const explorer = {id:'me.weirdmm.iexplored',hook:'app.iexplored',name:'IExplored',author:'WeirdMM',version:'0.2.0',description:'File manager',previews:[]};
context.packageDetail(explorer,false);
let explorerPage=views.filter(x=>x.title==='IExplored').pop();
explorerPage.sections[1].rows[0].onSelect();
assert(Object.values(data).some(x=>x && x.action==='queue_app_install' && x.appId==='com.winterx.iexplored'));
data['app-packages.json'].pending['com.winterx.iexplored']={action:'install'};
context.packageDetail(explorer,false);
explorerPage=views.filter(x=>x.title==='IExplored').pop();
assert.strictEqual(explorerPage.sections[1].rows[0].title,'Waiting for Spring installer');
console.log('IExplored package install and pending states passed');
const animaper={id:'me.weirdmm.animaper',hook:'tweak.animaper',name:'Animaper',version:'0.1.0',author:'WeirdMM',description:'Page effects',sha256:'effect',installedSha256:'effect',previews:[]};
context.packageDetail(animaper,false);
const effectPage=views.filter(x=>x.title==='Animaper').pop();
assert.strictEqual(effectPage.sections[3].rows.length,8);
assert(effectPage.sections[3].rows.some(x=>x.title==='Wave'));
assert(effectPage.sections[3].rows.some(x=>x.title==='Zigzag'));
console.log('Animaper effect selection contains eight options');

// Trusted runtime operations work even without a live bridge.
data['winterx/ruby/boot-ok-v1']='1';
delete data['live.json'];
context.request('set_safe_mode',true);
assert.strictEqual(data['winterx/ruby/safe-mode.enabled'],'1');
assert.strictEqual(data['winterx/ruby/respring.request'],undefined);
context.nativeToggle('animaper.enabled',true);
assert.strictEqual(data['winterx/ruby/animaper.enabled'],'1');
context.packageRequest('set_animaper_mode',{mode:'orbit'});
assert.strictEqual(data['winterx/ruby/animaper.mode'],'orbit');
console.log('Safe Mode and Animaper controls work without the bridge');
