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
      var mode = "wave";
      if (files.exists("winterx/ruby/animaper.mode")) mode = files.read("winterx/ruby/animaper.mode").trim();
      return { active:true, native:true, safeModeSupported:true,
        safeMode:files.exists("winterx/ruby/safe-mode.enabled"),
        settingsInstalled:files.exists("winterx/ruby/settings-test.enabled"),
        colorsInstalled:files.exists("winterx/ruby/ui-colors.enabled"),
        iconsInstalled:files.exists("winterx/ruby/free-icons.enabled"),
        animaperInstalled:files.exists("winterx/ruby/animaper.enabled"), animaperMode:mode };
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
    UIAlertView.show({title:"Applied",message:marker === "animaper.enabled" ? "Animaper has been updated. Return Home and swipe between pages." : "Safe Mode has been updated. Return Home to see the change.",buttons:["OK"]});
  } catch (e) {
    try { if (previouslyEnabled && !files.exists(target)) files.write(target,"1"); else if (!previouslyEnabled && files.exists(target)) files.remove(target); } catch (ignored) {}
    UIAlertView.show({title:"Could not apply",message:String(e),buttons:["OK"]});
  }
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
    message: enable ? "Tweaks will be disabled until you leave Safe Mode." : "Installed tweaks will be enabled again.",
    buttons: ["Cancel", enable ? "Enter" : "Leave"] }, function (index) {
      if (index === 1) request("set_safe_mode", enable);
    });
}
function packageRequest(action, values) {
  var live = liveStatus();
  if (action === "set_animaper_mode" && live && live.native) {
    try {
      var modes = ["wave", "cascade", "bounce", "orbit", "ripple", "columns", "fan", "zigzag"];
      if (!values || modes.indexOf(values.mode) < 0) throw new Error("Unknown animation");
      files.write("winterx/ruby/animaper.mode", values.mode);
      UIAlertView.show({title:"Animaper",message:"Animation changed to " + values.mode + ".",buttons:["OK"]});
    } catch (e) { UIAlertView.show({title:"Could not apply",message:String(e),buttons:["OK"]}); }
    return;
  }
  if (!live) {
    UIAlertView.show({ title: "Jailbreak Required", message: "Start the Ruby bridge and jailbreak Spring first.", buttons: ["OK"] });
    return;
  }
  if (!bridgeStatus()) {
    UIAlertView.show({ title:"Bridge Needed", message:"Repository operations are still being moved into Spring.", buttons:["OK"] });
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
    if (action === "queue_app_install" || action === "queue_app_remove" || action === "set_animaper_mode") {
      var started = Date.now();
      var timer = setInterval(function () {
        var result = operation();
        if (result && !result.pending) {
          clearInterval(timer);
          UIAlertView.show({ title: result.ok ? "Request Queued" : "Could not queue", message: String(result.message || "Operation failed."), buttons: ["OK"] });
        } else if (Date.now() - started > 15000) {
          clearInterval(timer);
          UIAlertView.show({ title: "Bridge Unavailable", message: "Check that the Ruby Bridge is running.", buttons: ["OK"] });
        }
      }, 500);
    }
    if (action === "install_package" || action === "remove_package") UIAlertView.show({ title: "Applying Package", message: "Spring may respring. Open Ruby again after it starts.", buttons: ["OK"] });
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
function packageDetail(item, installedOnly) {
  var isExplorer = item.hook === "app.iexplored" && item.id === "me.weirdmm.iexplored";
  var isAnimaper = item.hook === "tweak.animaper" && item.id === "me.weirdmm.animaper";
  var native = liveStatus();
  var appId = "com.winterx.iexplored", state = appPackageState();
  var appPending = isExplorer && !!state.pending[appId];
  var installed = isExplorer ? !!state.installed[appId] : isAnimaper && native && native.native ? native.animaperInstalled : (installedOnly || !!item.installedSha256);
  var canUpdate = !isExplorer && !isAnimaper && !installedOnly && installed && item.installedSha256 !== item.sha256;
  var actionRows = [];
  if (appPending) actionRows.push({title:"Waiting for Spring installer",selectable:false});
  else if (isAnimaper && !installed && native && native.native) actionRows.push({title:"Install",accessory:"disclosure",onSelect:function () { nativeToggle("animaper.enabled", true); }});
  else if (isExplorer && !installed) actionRows.push({title:"Install",accessory:"disclosure",onSelect:function () {
    UIAlertView.show({title:"Install IExplored?",message:"Spring will install the app without restarting. Reopen the app if it was already running.",buttons:["Cancel","Queue"]},function(index){
      if (index === 1) packageRequest("queue_app_install", {appId:appId});
    });
  }});
  else if (!isExplorer && (!installed || canUpdate)) actionRows.push({ title: canUpdate ? "Update" : "Install", accessory: "disclosure", onSelect: function () {
    packageRequest("install_package", { filename: item.filename });
  } });
  if (installed && !appPending) actionRows.push({ title: "Remove", accessory: "disclosure", onSelect: function () {
    UIAlertView.show({ title: "Remove Package?", message: isExplorer ? "Close Spring Launcher for at least 5 seconds to remove the app. Its data will be kept." : "Spring may respring to apply this change.", buttons: ["Cancel", "Remove"] }, function (index) {
      if (index === 1) {
        if (isAnimaper && native && native.native && !item.installedSha256) nativeToggle("animaper.enabled", false);
        else packageRequest(isExplorer ? "queue_app_remove" : "remove_package", isExplorer ? {appId:appId} : {packageId:item.id});
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
  if (item.hook === "tweak.animaper" && installed) {
    var live = liveStatus(), selected = live && live.animaperMode || "wave";
    sections.push({ header: "PAGE ANIMATION", rows: ["wave", "cascade", "bounce", "orbit", "ripple", "columns", "fan", "zigzag"].map(function (mode) {
      return { title: mode.charAt(0).toUpperCase() + mode.slice(1), accessory: mode === selected ? "checkmark" : "none", onSelect: function () {
        packageRequest("set_animaper_mode", { mode: mode });
      } };
    }) });
  }
  var page = new UITableViewController({ title: item.name, style: "grouped", sections: sections });
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
    { header: "LOCAL PACKAGES", footer: r && r.pending ? "Waiting for the Ruby bridge…" : r && !r.ok ? "Operation failed." : "Import or refresh packages.", rows: [
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
  var page = new UITableViewController({ title: title || "Repositories", style: "grouped", sections: [{ rows: items.length ? items.map(function (item) {
    var app = item.hook === "app.iexplored" ? appPackageState() : null;
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
  catalogue.sections = [{ rows: [{ title: "Local Packages", accessory: "disclosure", onSelect: function () { refreshLocal(); catalogueNav.push(localPackages); packageRequest("scan_packages"); } }] }, { header: "TEST TWEAKS", footer: "Changes require a respring.", rows: tweaks.map(function (item) {
    return { title: item.name, subtitle: status(item), accessory: "disclosure", onSelect: function () { detail(item); } };
  }) }, { header: "WINTERX TWEAKS", rows: [
    { title:"Animaper", subtitle: live && live.animaperInstalled ? (live.safeMode ? "Installed — Safe Mode" : "Installed") : "Eight page swipe animations", accessory:"disclosure", onSelect:function () {
      packageDetail({id:"me.weirdmm.animaper",hook:"tweak.animaper",name:"Animaper",version:"0.1.0",author:"WeirdMM",description:"Animate Home screen page swipes with eight effects.",previews:[]},false);
    }}
  ] }, { header: "REPOSITORIES", rows: [
    { title: "Sources", accessory: "disclosure", onSelect: function () { tabs.selectedIndex = 2; } },
    { title: "Browse Repositories", accessory: "disclosure", onSelect: function () { showRepositoryPackages(repositoryData().packages); } },
    { title: "Search", accessory: "disclosure", onSelect: function () { tabs.selectedIndex = 3; } }
  ] }];
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
setInterval(function () { refresh(); refreshLocal(); refreshSources(); }, 2000);
refresh();
UIApplication.run(tabs);
