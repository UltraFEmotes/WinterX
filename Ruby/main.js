// Ruby is available only while WinterX's trusted runtime is active.
if (!files.exists("winterx/")) throw new Error("WinterX is not active");
var tweaks = [
  { id: "settings", name: "Settings Button Test", description: "Adds a Ruby test button to Spring's Settings app." },
  { id: "icons", name: "Free Icon Placement Test", description: "Move home-screen icons freely on each page." },
  { id: "colors", name: "UI Color Test", description: "Recolors shared navigation bars red." }
];
var pending = storage.get("ruby.operation.v2") || null;
var home = new UITableViewController({ title: "Ruby", style: "grouped" });
var catalogue = new UITableViewController({ title: "Packages", style: "grouped" });
var localPackages = new UITableViewController({ title: "Local Packages", style: "grouped" });
var homeNav = new UINavigationController(home, { barStyle: "black" });
var catalogueNav = new UINavigationController(catalogue, { barStyle: "black" });
var tabs, sourcesNav, searchNav;
var refreshSources = function () {};
var refreshPackageDetail = function () {};
function activeNav() {
  if (tabs && tabs.selectedIndex === 2) return sourcesNav;
  if (tabs && tabs.selectedIndex === 3) return searchNav;
  return catalogueNav;
}
function bridgeStatus() {
  try {
    var live = files.readJSON("live.json"), age = Date.now() - Number(live.observedAt);
    if (isFinite(age) && age >= -5000 && age <= 10000 && live.active === true) return live;
  } catch (e) {}
  return null;
}
function liveStatus() {
  try {
    if (files.exists("winterx/ruby/boot-ok-v1")) {
      var capabilities = files.exists("winterx/ruby/capabilities-v1.json") ? files.readJSON("winterx/ruby/capabilities-v1.json") : {};
      var codeRuntime = capabilities.nativePackages === true && capabilities.nativeApi === "winterx-native-hooks-v1";
      if (codeRuntime) return { active:true, native:true, safeModeSupported:true, nativePackagesSupported:true,
        packageManager:capabilities.packageManager === "winterx-pm-v1",
        safeMode:files.exists("winterx/ruby/safe-mode.enabled") };
      var mode = "wave";
      if (files.exists("winterx/ruby/animaper.mode")) mode = files.read("winterx/ruby/animaper.mode").trim();
      return { active:true, native:true, safeModeSupported:true,
        nativePackagesSupported:codeRuntime,
        safeMode:files.exists("winterx/ruby/safe-mode.enabled"),
        settingsInstalled:files.exists("winterx/ruby/settings-test.enabled"),
        colorsInstalled:files.exists("winterx/ruby/ui-colors.enabled"),
        iconsInstalled:files.exists("winterx/ruby/free-icons.enabled"),
        animaperInstalled:files.exists("winterx/ruby/animaper.enabled"), animaperMode:mode,
        animaperBarrelSupported:capabilities.abi === "winterx-capabilities-v1" && capabilities.animaperBarrel === true };
    }
  } catch (e) {}
  return bridgeStatus();
}
function nativeToggle(marker, enabled) {
  var target = "winterx/ruby/" + marker;
  var previouslyEnabled = files.exists(target);
  try {
    if (enabled) files.write(target, "1"); else if (previouslyEnabled) files.remove(target);
    refresh();
    var live = liveStatus();
    UIAlertView.show({title:"Applied",message:marker === "animaper.enabled" ? "Animaper has been updated. Return Home and swipe between pages." : live && live.nativePackagesSupported && !enabled ? "Safe Mode is off. Fully close and reopen Spring through WinterX to load your installed tweaks." : "Safe Mode has been updated. Return Home to see the change.",buttons:["OK"]});
  } catch (e) {
    try { if (previouslyEnabled && !files.exists(target)) files.write(target,"1"); else if (!previouslyEnabled && files.exists(target)) files.remove(target); } catch (ignored) {}
    UIAlertView.show({title:"Could not apply",message:String(e),buttons:["OK"]});
  }
}

// Cydia-style console: replaces the whole screen while a package is applied, so it
// cannot be left until the bridge answers; "Return to Ruby" appears only when done.
var console_ = null;
function openConsole(id, verb, name) {
  var height = UIScreen.height - 64;
  var vc = new UIViewController({ title: verb === "Removing" ? "Removing" : "Installing", background: "#000000" });
  var heading = vc.add(new UILabel({ frame: [12, 10, 296, 22], text: verb + " " + name, size: 17, bold: true, color: "#ffffff" }));
  var text = vc.add(new UITextView({ frame: [8, 38, 304, height - 110], text: "", editable: false, size: 13, color: "#d8d8d8", background: "#000000" }));
  var spinner = vc.add(new UIActivityIndicatorView({ frame: [0, height - 64, 320, 44], style: "whiteLarge", animating: true }));
  var done = vc.add(new UIButton({ frame: [20, height - 62, 280, 44], title: "Return to Ruby", hidden: true, onTap: closeConsole }));
  console_ = { id: id, lines: [], started: Date.now(), text: text, heading: heading, spinner: spinner, done: done, finished: false };
  consoleLine("Preparing " + name + "…");
  var direct = (liveStatus() || {}).packageManager === true;
  consoleLine(direct ? "Sent the request to WinterX" : "Sent the request to the WinterX bridge");
  console_.waiting = direct ? "Working… " : "Waiting for the bridge… ";
  console_.timer = setInterval(function () {
    if (!console_ || console_.finished) return;
    finishOperation();
    if (console_ && !console_.finished) console_.text.text = console_.lines.concat([console_.waiting + Math.round((Date.now() - console_.started) / 1000) + "s"]).join("\n");
  }, 500);
  UIApplication.run(new UINavigationController(vc, { barStyle: "black" }));
}
function consoleLine(line) {
  console_.lines.push(line);
  console_.text.text = console_.lines.join("\n");
}
function finishConsole(result) {
  var seconds = Math.round((Date.now() - console_.started) / 1000);
  (Array.isArray(result.log) ? result.log : []).forEach(function (line) { consoleLine(String(line)); });
  consoleLine(result.ok ? "Done in " + seconds + "s." : "Failed after " + seconds + "s.");
  consoleLine("");
  consoleLine(String(result.message || (result.ok ? "Package operation completed." : "Check the Ruby bridge and try again.")));
  console_.finished = true;
  clearInterval(console_.timer);
  console_.spinner.stopAnimating();
  console_.done.hidden = false;
}
function closeConsole() {
  if (console_) clearInterval(console_.timer);
  console_ = null;
  refresh();
  UIApplication.run(tabs);
}

function operation() {
  if (!pending) return null;
  try {
    var path = "results/" + pending.id + ".json";
    if (!files.exists(path)) return { pending: true };
    var result = files.readJSON(path);
    if (result.action !== pending.action) return { ok: false, message: "Restart the Ruby bridge and try again." };
    return result;
  } catch (e) { return { ok: false, message: "Could not read the bridge response." }; }
}
function finishOperation() {
  if (!pending || pending.notified) return;
  var result = operation();
  if (!result || result.pending) return;
  pending.notified = true;
  storage.set("ruby.operation.v2", pending);
  refreshPackageDetail();
  if (console_ && console_.id === pending.id) { finishConsole(result); return; }
  if (!result.ok || pending.action === "install_package" || pending.action === "remove_package" || pending.action === "queue_app_install" || pending.action === "queue_app_remove" || pending.action === "set_animaper_mode") {
    UIAlertView.show({ title: result.ok ? (result.restartRequired ? "Reopen Spring" : "Completed") : "Could Not Complete", message: String(result.message || (result.ok ? "Package operation completed." : "Check the Ruby bridge and try again.")), buttons: ["OK"] });
  }
}
function status(item) {
  var r = operation(), live = liveStatus();
  if (r && r.pending) return "Respringing…";
  if (item.id === "settings" && live && live.settingsInstalled === true) return live.safeMode ? "Installed — Safe Mode" : "Installed";
  if (item.id === "icons") {
    if (live && live.iconsInstalled === true) return live.safeMode ? "Installed — Safe Mode" : "Installed";
    if (r && !r.ok) return "Operation failed";
    return live ? "Available" : "Jailbreak required";
  }
  if (item.id === "colors") {
    if (live && live.colorsInstalled === true) return live.safeMode ? "Installed — Safe Mode" : "Installed";
    if (r && !r.ok) return "Operation failed";
    return live ? "Available" : "Jailbreak required";
  }
  if (r && !r.ok) return "Operation failed";
  return live ? "Available" : "Jailbreak required";
}
function request(action, enabled) {
  var live = liveStatus();
  if (!live) {
    UIAlertView.show({ title: "Jailbreak Required", message: "Start the Ruby bridge and jailbreak Spring first.", buttons: ["OK"] });
    return;
  }
  if (action === "set_safe_mode" && live.native) {
    nativeToggle("safe-mode.enabled", enabled);
    return;
  }
  if (!bridgeStatus()) {
    UIAlertView.show({ title:"Bridge Needed", message:"This development feature still uses the Ruby bridge.", buttons:["OK"] });
    return;
  }
  if (action !== "enable_settings" && !live.safeModeSupported) {
    UIAlertView.show({ title: "WinterX Update Required", message: "Restart the Ruby bridge and jailbreak again with the new WinterX build.", buttons: ["OK"] });
    return;
  }
  var old = operation();
  if (old && old.pending) return;
  var id = String(Date.now()) + "-" + String(Math.floor(Math.random() * 1000000000));
  try {
    pending = { id: id, action: action };
    storage.set("ruby.operation.v2", pending);
    var record = { id: id, action: action };
    if (action === "set_safe_mode") record.enabled = enabled;
    files.writeJSON("requests/" + id + ".json", record);
    refresh();
    UIAlertView.show({ title: "Respringing", message: "Spring will restart. Open Ruby after it starts to check the result.", buttons: ["OK"] });
  } catch (e) {
    pending = null;
    storage.remove("ruby.operation.v2");
    UIAlertView.show({ title: "Could not start", message: String(e), buttons: ["OK"] });
  }
}
function changeSafeMode() {
  var live = liveStatus();
  if (!live || !live.safeModeSupported) { request("set_safe_mode", true); return; }
  var enable = !live.safeMode;
  UIAlertView.show({ title: enable ? "Enter Safe Mode?" : "Leave Safe Mode?",
    message: enable ? "Tweaks will be disabled until you leave Safe Mode." : live.nativePackagesSupported ? "Fully close and reopen Spring through WinterX after leaving Safe Mode to load installed tweaks." : "Installed tweaks will be enabled again.",
    buttons: ["Cancel", enable ? "Enter" : "Leave"] }, function (index) {
      if (index === 1) request("set_safe_mode", enable);
    });
}
function packageRequest(action, values, name) {
  var live = liveStatus();
  if (action === "set_animaper_mode" && live && live.native && !live.nativePackagesSupported) {
    try {
      var modes = ["wave", "cascade", "bounce", "orbit", "ripple", "columns", "fan", "zigzag", "barrel"];
      if (!values || modes.indexOf(values.mode) < 0) throw new Error("Unknown animation");
      if (values.mode === "barrel" && !live.animaperBarrelSupported) throw new Error("Barrel requires the updated native rendering engine.");
      files.write("winterx/ruby/animaper.mode", values.mode);
      UIAlertView.show({title:"Animaper",message:"Animation changed to " + values.mode + ".",buttons:["OK"]});
    } catch (e) { UIAlertView.show({title:"Could not apply",message:String(e),buttons:["OK"]}); }
    return;
  }
  if (!live) {
    UIAlertView.show({ title: "Jailbreak Required", message: "Start the Ruby bridge and jailbreak Spring first.", buttons: ["OK"] });
    return;
  }
  // A core with its own package manager installs, removes and scans without the bridge; sources still need it.
  var inCore = live.packageManager === true && (action === "install_package" || action === "remove_package" || action === "scan_packages");
  if (!inCore && !bridgeStatus()) {
    UIAlertView.show({ title:"Bridge Needed", message:"Keep the Ruby bridge connected to refresh or change sources.", buttons:["OK"] });
    return;
  }
  var previous = operation();
  if (previous && previous.pending) return;
  var id = String(Date.now()) + "-" + String(Math.floor(Math.random() * 1000000000));
  var record = { id: id, action: action };
  if (values) for (var key in values) record[key] = values[key];
  try {
    pending = { id: id, action: action };
    storage.set("ruby.operation.v2", pending);
    files.writeJSON("requests/" + id + ".json", record);
    if (action === "install_package" || action === "remove_package") openConsole(id, action === "remove_package" ? "Removing" : "Installing", name || "package");
  } catch (e) {
    pending = null;
    storage.remove("ruby.operation.v2");
    UIAlertView.show({ title: "Could not start", message: String(e), buttons: ["OK"] });
  }
}
function packageData() {
  try { return files.readJSON("packages.json"); }
  catch (e) { return { available: [], installed: [] }; }
}
function packageWithStatus(item, installed) {
  var value = Object.assign({}, item);
  installed = installed || packageData().installed || [];
  var record = installed.filter(function (entry) { return entry.id === item.id; })[0];
  if (record) {
    value.installedSha256 = record.sha256;
    value.installedVersion = record.version;
  } else if (item.runtime === "java") {
    value.installedSha256 = null;
    value.installedVersion = null;
  }
  return value;
}
function newerVersion(a, b) {
  var x = String(a || "0").split(/[-+]/)[0].split("."), y = String(b || "0").split(/[-+]/)[0].split(".");
  for (var i = 0; i < Math.max(x.length, y.length); i++) {
    var d = (parseInt(x[i], 10) || 0) - (parseInt(y[i], 10) || 0);
    if (d) return d > 0;
  }
  return false;
}
function codePackages() {
  var data = packageData(), byId = {};
  // Imported files first, then sources: a source's current entry replaces an old download of the same version,
  // while a newer manually imported build still wins.
  (data.available || []).concat(repositoryData().packages || []).forEach(function (item) {
    if (item.type !== "tweak") return;
    var current = byId[item.id];
    if (!current || !newerVersion(current.version, item.version)) byId[item.id] = item;
  });
  (data.installed || []).forEach(function (item) {
    if (item.type === "tweak" && !byId[item.id]) byId[item.id] = item;
  });
  return Object.keys(byId).map(function (id) { return packageWithStatus(byId[id], data.installed || []); }).sort(function (a, b) { return a.name.localeCompare(b.name); });
}
function importPackage() {
  files.import({ types: ["*/*"], multiple: false, to: "imports/" }, function (paths, error) {
    if (error) { UIAlertView.show({ title: "Import Failed", message: String(error), buttons: ["OK"] }); return; }
    if (paths && paths.length) packageRequest("scan_packages");
  });
}
function previewPackage(path) {
  var screen = new UIViewController({ title: "Preview", background: "#000000" });
  screen.add(new UIImageView({ frame: [0, 0, 320, 420], image: "files/" + path, contentMode: "scaleAspectFit" }));
  activeNav().push(screen);
}
function appPackageState() {
  try { return files.readJSON("app-packages.json"); }
  catch (e) { return { installed: {}, pending: {} }; }
}
function packageDetail(selectedItem, installedOnly) {
  var page = new UITableViewController({ title: selectedItem.name, style: "grouped" });
  function update() {
  var item = packageWithStatus(selectedItem);
  var isExplorer = item.hook === "app.iexplored" && item.id === "me.weirdmm.iexplored";
  var isAnimaper = item.hook === "tweak.animaper" && item.id === "me.weirdmm.animaper";
  var native = liveStatus();
  var appId = "com.winterx.iexplored", state = isExplorer ? appPackageState() : { installed:{}, pending:{} };
  var appPending = isExplorer && !!state.pending[appId];
  var installed = isExplorer ? !!state.installed[appId] : isAnimaper && native && native.native && !native.nativePackagesSupported ? native.animaperInstalled : (item.runtime === "java" ? !!item.installedSha256 : installedOnly || !!item.installedSha256);
  var canUpdate = !isExplorer && !isAnimaper && !installedOnly && installed && item.installedSha256 !== item.sha256;
  var blockedLegacy = native && native.nativePackagesSupported && !!item.hook;
  var needsCore = item.runtime === "java" && !(native && native.nativePackagesSupported);
  var actionRows = [];
  if (blockedLegacy) actionRows.push({title:"Use the source-backed code package",selectable:false});
  else if (needsCore) actionRows.push({title:"Native-code runtime required",selectable:false});
  else if (appPending) actionRows.push({title:"Waiting for Spring installer",selectable:false});
  else if (isAnimaper && !installed && native && native.native) actionRows.push({title:"Install",accessory:"disclosure",onSelect:function () { nativeToggle("animaper.enabled", true); }});
  else if (isExplorer && !installed) actionRows.push({title:"Install",accessory:"disclosure",onSelect:function () {
    UIAlertView.show({title:"Install IExplored?",message:"Spring will install the app without restarting. Reopen the app if it was already running.",buttons:["Cancel","Queue"]},function(index){
      if (index === 1) packageRequest("queue_app_install", {appId:appId});
    });
  }});
  else if (!isExplorer && (!installed || canUpdate)) actionRows.push({ title: canUpdate ? "Update" : "Install", accessory: "disclosure", onSelect: function () {
    packageRequest("install_package", { filename: item.filename }, item.name);
  } });
  if (installed && !appPending && !blockedLegacy && !needsCore) actionRows.push({ title: "Remove", accessory: "disclosure", onSelect: function () {
    UIAlertView.show({ title: "Remove Package?", message: isExplorer ? "Close Spring Launcher for at least 5 seconds to remove the app. Its data will be kept." : item.type === "tweak" ? "Disable this package and remove its installed record? Your saved preferences and layouts will be kept." : "Remove this package through the Ruby bridge?", buttons: ["Cancel", "Remove"] }, function (index) {
      if (index === 1) {
        if (isAnimaper && native && native.native && !item.installedSha256) nativeToggle("animaper.enabled", false);
        else packageRequest(isExplorer ? "queue_app_remove" : "remove_package", isExplorer ? {appId:appId} : {packageId:item.id}, item.name);
      }
    });
  } });
  var previews = (item.previews || []).map(function (path, index) {
    return { title: "Preview " + (index + 1), accessory: "disclosure", onSelect: function () { previewPackage((installedOnly ? "package-registry/" : "") + path); } };
  });
  var sections = [
    { header: "ABOUT", rows: [
      { title: item.name, subtitle: "Version " + item.version + " · " + item.author, selectable: false },
      { title: "Identifier", detail: item.id, selectable: false },
      { title: "Description", accessory: "disclosure", onSelect: function () { UIAlertView.show({ title: item.name, message: item.description, buttons: ["OK"] }); } }
    ] },
    { header: "ACTIONS", rows: actionRows },
    { header: "SCREENSHOTS", rows: previews.length ? previews : [{ title: "No previews", selectable: false }] }
  ];
  if (item.type === "tweak") {
    sections[0].rows.push({ title:"Code", detail:item.runtime === "java" ? "Java / Android DEX" : "JavaScript", selectable:false });
    if (item.runtime === "java") sections[0].rows.push({ title:"Preferences", detail:"Spring Settings → WINTERX TWEAKS", selectable:false });
    var source = item.sourceCode || item.source;
    if (typeof source === "string" && /^https:\/\//.test(source)) sections[0].rows.push({ title:"Source Code", accessory:"disclosure", onSelect:function () {
      try { UIApplication.openURL(source); } catch (e) { UIAlertView.show({title:"Source Code",message:source,buttons:["OK"]}); }
    }});
  }
  if (item.hook === "tweak.animaper" && installed && !blockedLegacy) {
    var live = liveStatus(), selected = live && live.animaperMode || "wave";
    sections.push({ header: "PAGE ANIMATION", rows: ["wave", "cascade", "bounce", "orbit", "ripple", "columns", "fan", "zigzag", "barrel"].filter(function (mode) {
      return mode !== "barrel" || live && live.animaperBarrelSupported;
    }).map(function (mode) {
      return { title: mode.charAt(0).toUpperCase() + mode.slice(1), accessory: mode === selected ? "checkmark" : "none", onSelect: function () {
        packageRequest("set_animaper_mode", { mode: mode });
      } };
    }) });
  }
  page.sections = sections;
  }
  page.onAppear = update;
  refreshPackageDetail = update;
  update();
  activeNav().push(page);
}
function refreshLocal() {
  var data = packageData(), r = operation();
  var available = data.available || [], installed = data.installed || [];
  var installedRows = installed.map(function (item) {
    return { title: item.name, subtitle: "Version " + item.version, image: item.icon ? "files/package-registry/" + item.icon : undefined,
      accessory: "disclosure", onSelect: function () { packageDetail(item, true); } };
  });
  var availableRows = available.map(function (item) {
    return { title: item.name, subtitle: item.installedSha256 ? (item.installedSha256 === item.sha256 ? "Installed" : "Update available") : item.description,
      image: item.icon ? "files/" + item.icon : undefined, accessory: "disclosure", onSelect: function () { packageDetail(item, false); } };
  });
  localPackages.sections = [
    { header: "LOCAL PACKAGES", footer: r && r.pending ? "Working…" : r && !r.ok ? "Operation failed." : "Import or refresh packages.", rows: [
      { title: "Import Package…", accessory: "disclosure", onSelect: importPackage },
      { title: "Refresh", accessory: "disclosure", onSelect: function () { packageRequest("scan_packages"); } }
    ] },
    { header: "INSTALLED", rows: installedRows.length ? installedRows : [{ title: "No packages installed", selectable: false }] },
    { header: "IMPORTED", rows: availableRows.length ? availableRows : [{ title: "No packages imported", selectable: false }] }
  ];
}

function repositoryData() {
  try { return files.readJSON("repository-catalogue.json"); }
  catch (e) { return { sources: [], packages: [] }; }
}
function addRepository() {
  var page = new UIViewController({ title: "Add Source", background: "#d8dde6" });
  page.add(new UILabel({ frame: [20, 35, 280, 55], text: "Enter the HTTPS URL of a Ruby repository index.", size: 15, lines: 2, color: "#333333" }));
  var field = page.add(new UITextField({ frame: [20, 105, 280, 36], placeholder: "https://example.com/repo.json", text: "" }));
  page.add(new UIButton({ frame: [45, 165, 230, 44], title: "Add Source", onTap: function () {
    if (!/^https:\/\//i.test(field.text || "")) { UIAlertView.show({ title: "Invalid Source", message: "Enter an HTTPS repository URL.", buttons: ["OK"] }); return; }
    packageRequest("add_repository", { url: field.text });
    UIAlertView.show({ title: "Adding Source", message: "Ruby is loading the repository. Return to Sources to see the result.", buttons: ["OK"] });
  } }));
  activeNav().push(page);
}
function makeSources() {
  var page = new UITableViewController({ title: "Sources", style: "grouped" });
  function updateSources() {
    var data = repositoryData();
    page.sections = [ { rows: [
      { title: "Add Source…", accessory: "disclosure", onSelect: addRepository },
      { title: "Refresh Sources", accessory: "disclosure", onSelect: function () { packageRequest("refresh_repositories"); } }
    ] }, { header: "SOURCES", rows: data.sources.length ? data.sources.map(function (source) {
      return { title: source.name, subtitle: source.error || (source.builtIn ? "Built-in source" : source.url), accessory: "disclosure", onSelect: function () {
        if (source.builtIn) {
          if (source.error) { UIAlertView.show({ title: source.name, message: source.error, buttons: ["OK"] }); return; }
          showRepositoryPackages(repositoryData().packages.filter(function (item) { return item.source === source.url; }), source.name);
          return;
        }
        UIAlertView.show({ title: source.name, message: source.error || source.url, buttons: ["Cancel", "Browse", "Remove"] }, function (index) {
          if (index === 1) showRepositoryPackages(repositoryData().packages.filter(function (item) { return item.source === source.url; }), source.name);
          if (index === 2) packageRequest("remove_repository", { url: source.url });
        });
      } };
    }) : [{ title: "No sources added", selectable: false }] } ];
  }
  refreshSources = updateSources;
  page.onAppear = function () {
    updateSources();
    if (!files.exists("repository-catalogue.json") && liveStatus()) packageRequest("refresh_repositories");
  };
  updateSources(); return page;
}
function showSources() { activeNav().push(makeSources()); }
function makeSearch() {
  var page = new UIViewController({ title: "Search", background: "#d8dde6" });
  page.add(new UILabel({ frame: [20, 24, 280, 32], text: "Search repository packages", size: 16, color: "#333333" }));
  var field = page.add(new UITextField({ frame: [20, 65, 280, 36], placeholder: "Name, author, or description", text: "" }));
  page.add(new UIButton({ frame: [45, 120, 230, 44], title: "Search", onTap: function () {
    var query = String(field.text || "").toLowerCase();
    var matches = repositoryData().packages.filter(function (item) {
      return (item.name + " " + item.author + " " + item.description + " " + item.id).toLowerCase().indexOf(query) >= 0;
    });
    showRepositoryPackages(matches, "Search Results");
  } }));
  return page;
}
function showSearch() { activeNav().push(makeSearch()); }
function showRepositoryPackages(items, title) {
  var installed = packageData().installed || [];
  var page = new UITableViewController({ title: title || "Repositories", style: "grouped", sections: [{ rows: items.length ? items.map(function (item) {
    var app = item.hook === "app.iexplored" ? appPackageState() : null;
    item = packageWithStatus(item, installed);
    var description = app && app.pending["com.winterx.iexplored"] ? "Restart needed" :
      app && app.installed["com.winterx.iexplored"] ? "Installed" :
      item.installedSha256 ? (item.installedSha256 === item.sha256 ? "Installed" : "Update available") : item.description;
    return { title: item.name, subtitle: description,
      image: item.icon ? "files/" + item.icon : undefined, accessory: "disclosure", onSelect: function () { packageDetail(item, false); } };
  }) : [{ title: "No packages found", selectable: false }] }] });
  activeNav().push(page);
}
function showAbout() {
  var page = new UIViewController({ title: "About Ruby", background: "#d8dde6" });
  page.add(new UILabel({ frame: [24, 32, 272, 45], text: "About Ruby", size: 22, bold: true, align: "center", color: "#344863" }));
  page.add(new UILabel({ frame: [25, 95, 270, 190], text: "WinterX and Ruby are fun fan-made projects for Spring, created by WeirdMM. Thanks for trying them and sharing your ideas!", size: 16, lines: 8, align: "center", color: "#333333" }));
  homeNav.push(page);
}
function joinDiscord() {
  try {
    UIApplication.openURL("https://discord.gg/4JTe27ZRNd");
  } catch (e) {
    UIAlertView.show({ title: "Could not open Discord", message: "Open https://discord.gg/4JTe27ZRNd in your browser. " + String(e), buttons: ["OK"] });
  }
}

function refresh() {
  var live = liveStatus();
  home.sections = [
    { header: "WELCOME TO RUBY", footer: "Packages and tweaks for Spring.", rows: [
      { title: "Ruby", subtitle: "The package manager for Spring", selectable: false },
      { title: "Browse Packages", accessory: "disclosure", onSelect: function () { tabs.selectedIndex = 1; } },
      { title: "About Ruby", accessory: "disclosure", onSelect: showAbout },
      { title: "Join our Discord", accessory: "disclosure", onSelect: joinDiscord }
    ] },
    { header: "WINTERX", footer: "Temporarily disable tweaks.", rows: [
      { title: "Safe Mode", detail: live && live.safeModeSupported ? (live.safeMode ? "On" : "Off") : "Unavailable", accessory: "disclosure", onSelect: changeSafeMode }
    ] }
  ];
  var localSection = { rows: [{ title: "Local Packages", accessory: "disclosure", onSelect: function () { refreshLocal(); catalogueNav.push(localPackages); packageRequest("scan_packages"); } }] };
  var repositoriesSection = { header: "REPOSITORIES", rows: [
    { title: "Sources", accessory: "disclosure", onSelect: function () { tabs.selectedIndex = 2; } },
    { title: "Browse Repositories", accessory: "disclosure", onSelect: function () { showRepositoryPackages(repositoryData().packages); } },
    { title: "Search", accessory: "disclosure", onSelect: function () { tabs.selectedIndex = 3; } }
  ] };
  if (live && live.nativePackagesSupported) {
    var packages = codePackages();
    catalogue.sections = [localSection, { header:"WINTERX TWEAKS", footer:"Install code packages through Ruby. Open Spring Settings → WINTERX TWEAKS after reopening Spring.", rows:packages.length ? packages.map(function (item) {
      return { title:item.name, subtitle:item.installedSha256 ? (item.installedSha256 === item.sha256 ? "Installed" : "Update available") : item.description, accessory:"disclosure", onSelect:function () { packageDetail(item, !item.filename); } };
    }) : [{ title:"Refresh Sources", subtitle:"Browse available code packages", accessory:"disclosure", onSelect:function () { packageRequest("refresh_repositories"); } }] }, repositoriesSection];
    return;
  }
  catalogue.sections = [localSection, { header: "TEST TWEAKS", footer: "Changes require a respring.", rows: tweaks.map(function (item) {
    return { title: item.name, subtitle: status(item), accessory: "disclosure", onSelect: function () { detail(item); } };
  }) }, { header: "WINTERX TWEAKS", rows: [
    { title:"Animaper", subtitle: live && live.animaperInstalled ? (live.safeMode ? "Installed — Safe Mode" : "Installed") : "Nine page swipe animations", accessory:"disclosure", onSelect:function () {
      packageDetail({id:"me.weirdmm.animaper",hook:"tweak.animaper",name:"Animaper",version:"0.1.0",author:"WeirdMM",description:"Animate Home screen page swipes with nine effects, including Barrel.",previews:[]},false);
    }}
  ] }, repositoriesSection];
}
function detail(item) {
  var page = new UITableViewController({ title: item.name, style: "grouped" });
  function update() {
    var r = operation(), live = liveStatus();
    var installed = live && ((item.id === "settings" && live.settingsInstalled === true) || (item.id === "colors" && live.colorsInstalled === true) || (item.id === "icons" && live.iconsInstalled === true));
    var info = r && r.pending ? "Spring is respringing. Open Ruby after it starts."
      : r && !r.ok ? String(r.message || "Operation failed. Try again.")
      : item.id === "icons" ? "Touch and hold an icon, then drag it to an empty spot on the same page. Folder creation is disabled while this test is installed; dock and cross-page moves use Spring's normal behavior."
      : item.id === "colors" ? "Recolors Spring's shared navigation bars red while preserving their iOS-style gradients. Some apps use their own bar artwork."
      : installed ? "Open Spring's Settings app and tap Ruby Test." : "Installs a Ruby Test row in Spring's Settings app.";
    var rows = [{ title: status(item), selectable: false }];
    if (!(r && r.pending)) {
      rows.push({ title: installed ? "Remove" : "Install", accessory: "disclosure", onSelect: function () {
        if (!installed) { request(item.id === "colors" ? "enable_colors" : item.id === "icons" ? "enable_icons" : "enable_settings"); return; }
        UIAlertView.show({ title: "Remove " + item.name + "?", message: "Spring will respring to apply this change.", buttons: ["Cancel", "Remove"] }, function (index) {
          if (index === 1) request(item.id === "colors" ? "disable_colors" : item.id === "icons" ? "disable_icons" : "disable_settings");
        });
      } });
    }
    page.sections = [
      { header: "ABOUT", rows: [{ title: item.name, subtitle: item.description, selectable: false }] },
      { header: "STATUS", rows: rows.concat([{ title: "Details", accessory: "disclosure", onSelect: function () { UIAlertView.show({ title: item.name, message: info, buttons: ["OK"] }); } }]) },
      { header: "REQUIRES", rows: [{ title: "Respring", detail: "After changes", selectable: false }] }
    ];
  }
  page.onAppear = update;
  update();
  activeNav().push(page);
}
catalogue.onAppear = refresh;
home.onAppear = refresh;
homeNav.tabTitle = "Ruby"; homeNav.tabIcon = "assets/home.png";
catalogueNav.tabTitle = "Packages"; catalogueNav.tabIcon = "assets/packages.png";
sourcesNav = new UINavigationController(makeSources(), { barStyle: "black" });
searchNav = new UINavigationController(makeSearch(), { barStyle: "black" });
sourcesNav.tabTitle = "Sources"; sourcesNav.tabIcon = "assets/sources.png";
searchNav.tabTitle = "Search"; searchNav.tabIcon = "assets/search.png";
tabs = new UITabBarController([homeNav, catalogueNav, sourcesNav, searchNav]);
setInterval(function () { finishOperation(); refresh(); refreshLocal(); refreshSources(); }, 2000);
refresh();
UIApplication.run(tabs);
