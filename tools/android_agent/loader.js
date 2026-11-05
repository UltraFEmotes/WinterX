import Java from 'frida-java-bridge';

// Process-local rooted loader. The installed APK, certificate and app data stay in place.
// It prepends locally built generic hook/core DEX files before Spring classes are loaded.
let configuration = null;
let appLoader = null;
let injecting = false;
let state = { phase: 'new', pid: Process.id, packagesInstalledByLoader: 0 };

function checkedConfiguration(value) {
  if (!value || value.package !== 'com.guille.spring' || !/^[0-9a-f]{32}$/.test(value.nonce) ||
      !/^\/data\/(?:user\/\d+|data)\/com\.guille\.spring\/files$/.test(value.filesRoot) ||
      !/^\/data\/app\/.+\/base\.apk$/.test(value.apkPath) || !Array.isArray(value.files) || value.files.length !== 2)
    throw new Error('Invalid explicit Spring runtime configuration');
  for (const file of value.files) {
    if (!file || typeof file.path !== 'string' || !file.path.startsWith(value.filesRoot + '/ruby/runtime/') ||
        file.path.includes('..') || !/^[0-9a-f]{64}$/.test(file.sha256)) throw new Error('Invalid pinned runtime DEX');
  }
  if (!Array.isArray(value.earlyClasses) || value.earlyClasses.length > 32 ||
      value.earlyClasses.some(name => typeof name !== 'string' || !/^[A-Za-z0-9_.$]+$/.test(name)))
    throw new Error('Invalid early class checks');
  return JSON.parse(JSON.stringify(value));
}

function hashFile(path) {
  const File = Java.use('java.io.File');
  const file = File.$new(path);
  if (!file.isFile() || !file.canRead() || file.getCanonicalPath().toString() !== path ||
      Number(file.length()) < 112 || Number(file.length()) > 32 * 1024 * 1024)
    throw new Error('Runtime DEX is not a bounded app-readable canonical file');
  const input = Java.use('java.io.FileInputStream').$new(file);
  const digest = Java.use('java.security.MessageDigest').getInstance('SHA-256');
  const buffer = Java.array('byte', Array(65536).fill(0));
  let total = 0;
  try {
    while (true) {
      const count = input.read(buffer);
      if (count < 0) break;
      total += count;
      if (total > 32 * 1024 * 1024) throw new Error('Runtime DEX grew while verifying');
      digest.update(buffer, 0, count);
    }
  } finally { input.close(); }
  return Array.from(digest.digest(), byte => (byte & 255).toString(16).padStart(2, '0')).join('');
}

function inject(loadedApk, loader) {
  if (injecting || state.phase === 'installed' || state.phase === 'failed') return loader;
  if (loadedApk.mPackageName.value.toString() !== configuration.package) return loader;
  injecting = true;
  let originalElements = null, elementsField = null, targetList = null;
  try {
    if (loadedApk.mAppDir.value.toString() !== configuration.apkPath) throw new Error('Installed APK path changed');
    const api = Java.use('android.os.Build$VERSION').SDK_INT.value;
    if (api < 26) throw new Error('Native code packages require Android API 26 or newer');
    const loaded = new Set(Java.enumerateLoadedClassesSync());
    if (configuration.earlyClasses.some(name => loaded.has(name))) throw new Error('Spring classes are already loaded; start through a fresh rooted launch');
    const checked = configuration.files.map(file => ({path: file.path, sha256: hashFile(file.path)}));
    if (checked.some((file, index) => file.sha256 !== configuration.files[index].sha256)) throw new Error('App-side runtime checksum mismatch');
    const BaseDex = Java.use('dalvik.system.BaseDexClassLoader');
    const pathListField = BaseDex.class.getDeclaredField('pathList'); pathListField.setAccessible(true);
    targetList = pathListField.get(loader);
    elementsField = targetList.getClass().getDeclaredField('dexElements'); elementsField.setAccessible(true);
    originalElements = elementsField.get(targetList);
    const overlay = Java.use('dalvik.system.DexClassLoader').$new(configuration.files.map(file => file.path).join(':'),
      configuration.filesRoot + '/ruby/runtime', null, loader);
    const extra = elementsField.get(pathListField.get(overlay));
    const arrays = Java.use('java.lang.reflect.Array');
    const extraLength = arrays.getLength(extra), originalLength = arrays.getLength(originalElements);
    const combined = arrays.newInstance(originalElements.getClass().getComponentType(), extraLength + originalLength);
    const system = Java.use('java.lang.System');
    system.arraycopy(extra, 0, combined, 0, extraLength);
    system.arraycopy(originalElements, 0, combined, extraLength, originalLength);
    elementsField.set(targetList, combined);
    appLoader = Java.retain(loader);
    const klass = loader.loadClass('winterx.extension.NativeRuntime');
    const abi = klass.getField('ABI').get(null).toString();
    if (abi !== 'winterx-native-hooks-v1') throw new Error('Loaded core ABI mismatch');
    state = {phase: 'installed', pid: Process.id, uid: Java.use('android.os.Process').myUid(), api,
      nonce: configuration.nonce, apkPath: configuration.apkPath, filesRoot: configuration.filesRoot,
      runtimeAbi: abi, dex: checked, packagesInstalledByLoader: 0};
    send({type: 'winterx-runtime', state});
  } catch (failure) {
    if (originalElements !== null && elementsField !== null) elementsField.set(targetList, originalElements);
    state = {...state, phase: 'failed', error: String(failure), nonce: configuration.nonce};
    send({type: 'winterx-runtime', state});
  } finally { injecting = false; }
  return loader;
}

rpc.exports = {
  observe(value) {
    if (configuration !== null) throw new Error('This observer is already configured');
    configuration = checkedConfiguration(value);
    Java.performNow(() => {
      const application = Java.use('android.app.ActivityThread').currentApplication();
      if (application === null || application.getPackageName().toString() !== configuration.package ||
          application.getApplicationInfo().sourceDir.value.toString() !== configuration.apkPath)
        throw new Error('Running app identity differs from the staged core');
      const loader = application.getClassLoader();
      const field = Java.use('dalvik.system.BaseDexClassLoader').class.getDeclaredField('pathList'); field.setAccessible(true);
      const list = field.get(loader), elementsField = list.getClass().getDeclaredField('dexElements'); elementsField.setAccessible(true);
      const elements = elementsField.get(list), arrays = Java.use('java.lang.reflect.Array');
      const names = [];
      for (let i = 0; i < arrays.getLength(elements); i++) {
        const element = arrays.get(elements, i), dexField = element.getClass().getDeclaredField('dexFile'); dexField.setAccessible(true);
        const dex = dexField.get(element);
        if (dex !== null) names.push(Java.cast(dex, Java.use('dalvik.system.DexFile')).getName().toString());
      }
      const checked = configuration.files.map(file => ({path:file.path,sha256:hashFile(file.path)}));
      if (checked.some((file, index) => file.sha256 !== configuration.files[index].sha256 || !names.includes(file.path)))
        throw new Error('Running class loader does not own the verified core DEX files');
      const abi = loader.loadClass('winterx.extension.NativeRuntime').getField('ABI').get(null).toString();
      if (abi !== 'winterx-native-hooks-v1') throw new Error('Running core ABI differs');
      appLoader = Java.retain(loader);
      state = {phase:'installed',pid:Process.id,uid:Java.use('android.os.Process').myUid(),api:Java.use('android.os.Build$VERSION').SDK_INT.value,
        nonce:configuration.nonce,apkPath:configuration.apkPath,filesRoot:configuration.filesRoot,runtimeAbi:abi,dex:checked,observedExistingCore:true};
    });
    return state;
  },
  arm(value) {
    if (configuration !== null) throw new Error('This process loader is already configured');
    configuration = checkedConfiguration(value);
    Java.performNow(() => {
      const getClassLoader = Java.use('android.app.LoadedApk').getClassLoader.overload();
      getClassLoader.implementation = function () { return inject(this, getClassLoader.call(this)); };
      state = {...state, phase: 'armed', nonce: configuration.nonce};
    });
    return state;
  },
  status() { return state; },
  inspect() {
    if (state.phase !== 'installed' || appLoader === null) return state;
    let report;
    Java.performNow(() => {
      const factory = Java.ClassFactory.get(appLoader);
      const runtime = factory.use('winterx.extension.NativeRuntime');
      const values = runtime.features(), features = [];
      for (let i = 0; i < values.size(); i++) features.push(Java.cast(values.get(i), Java.use('java.lang.String')).toString());
      const manifests = runtime.manifests(), loadedPackages = [];
      for (let i = 0; i < manifests.size(); i++) {
        const manifest = Java.cast(manifests.get(i), Java.use('org.json.JSONObject'));
        loadedPackages.push({id:manifest.getString('id').toString(),version:manifest.getString('version').toString(),
          entry:manifest.getString('entry').toString()});
      }
      report = {...state, nativePackageCount: loadedPackages.length, loadedPackages, features, safeMode:runtime.safeMode(),
        coreFilesRoot: runtime.files() === null ? null : runtime.files().getCanonicalPath().toString()};
      const activity = factory.use('winterx.tweaks.TweakHost').launcher();
      report.unlockedCore = activity !== null;
      if (activity !== null) {
        const controller = factory.use('com.guille.spring.LauncherActivity')['access$getController$p'](activity);
        report.developerMode = controller.K0();
        const manager = activity.winterxSappManager();
        report.sappManagerAvailable = manager !== null;
      }
    });
    return report;
  }
};
