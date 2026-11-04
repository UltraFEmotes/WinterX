const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const java = fs.readFileSync(path.join(root, 'patches/icon_positions/src/winterx/tweaks/TweakHost.java'), 'utf8');
const literals = java.split('static final String BOOTSTRAP =')[1].match(/"(?:\\.|[^"\\])*"/g);
const bootstrap = literals.map(literal => JSON.parse(literal)).join('');

function runtime() {
  let state = {};
  const data = new Map();
  const logs = [];
  const alerts = [];
  const context = vm.createContext({__host: {
    winterxLog(text) { logs.push(text); },
    winterxStateRead() { return JSON.stringify(state); },
    winterxStateWrite(text) { state = JSON.parse(text); },
    winterxDataRead(name) { return data.get(name) ?? null; },
    winterxDataWrite(name, value) { data.set(name, value); },
    winterxAlert(text) { alerts.push(JSON.parse(text)); return alerts.length; }
  }});
  vm.runInContext(bootstrap, context);
  return {context, logs, alerts, data, state: () => state};
}

(async function () {
  const first = runtime();
  const second = runtime();
  assert.equal(typeof first.context.__spring.settingsTap, 'function');
  assert.equal(typeof first.context.__spring.alert, 'function');
  vm.runInContext(fs.readFileSync(path.join(root, 'examples/code-tweak/tweak/main.js'), 'utf8'), first.context);
  first.context.__spring.settingsTap('main', 'hello');
  assert.equal(first.state().helloCount, 1);
  assert.match(first.alerts[0].message, /code from tweak\/main\.js/);
  first.context.__spring.alert(1, 0);
  await Promise.resolve();
  assert(first.logs.some(line => line === 'Alert button: 0'));
  first.context.__spring.settingsTap('more', 'save');
  assert.equal(first.data.get('example.txt'), 'Hello from my custom tweak!\n');
  assert.equal(second.state().helloCount, undefined);
  assert.equal(second.alerts.length, 0);
  assert.throws(() => first.context.WinterX.state.set([]), /State must be an object/);
  first.context.WinterX.on('settingsTap', () => { throw new Error('bad handler'); });
  assert.throws(() => first.context.__spring.settingsTap('main', 'unknown'), /bad handler/);
  console.log('Tweak bootstrap: __host binding, __spring methods, custom code, promises, storage and context isolation passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
