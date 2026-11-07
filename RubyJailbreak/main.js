var current = storage.get("jailbreak.request.v1") || null;
// Spring versions WinterX can jailbreak; the bridge starts the matching core.
var VERSIONS = [{ id: "0.8.1", name: "Spring 0.8.1" }, { id: "0.9-preview1", name: "Spring 0.9 Preview 1" }];
function known(id) { for (var i = 0; i < VERSIONS.length; i++) if (VERSIONS[i].id === id) return true; return false; }
var selectedVersion = storage.get("winterx.version.v1");
if (!known(selectedVersion)) {
  // Unknown or older saved choices (e.g. the "0.9 Preview 1" draft) start over on 0.8.1.
  if (selectedVersion) { current = null; storage.remove("jailbreak.request.v1"); }
  selectedVersion = "0.8.1";
}
storage.set("winterx.version.v1", selectedVersion);
var screen = new UIViewController({ title: "WinterX", background: "#e4e5e8" });
screen.add(new UILabel({ frame: [20, 30, 280, 46], text: "WinterX", size: 25, bold: true, align: "center", color: "#1d467d" }));
screen.add(new UILabel({ frame: [30, 90, 260, 54], text: "Jailbreak Spring", size: 16, align: "center", lines: 2, color: "#444444" }));
var chosen = false;                            // picked a version this session
function nameOf(id) { return VERSIONS.filter(function (v) { return v.id === id; })[0].name; }
var choices = [];
VERSIONS.forEach(function (version, i) {
  choices.push(screen.add(new UIButton({ frame: [45, 136 + i * 40, 230, 36], title: version.name,
    onTap: function () { chosen = true; selectVersion(version.id); } })));
});
function selectVersion(id) {
  if (!known(id)) return;
  if (id !== selectedVersion) { current = null; storage.remove("jailbreak.request.v1"); }
  selectedVersion = id;
  storage.set("winterx.version.v1", id);
  // Spring's views keep only their own properties, so buttons are matched to VERSIONS by position.
  choices.forEach(function (choice, i) { choice.title = (VERSIONS[i].id === id ? "\u2713 " : "") + VERSIONS[i].name; });
  refresh();
}
var setupMessage = "Mac.APK: tap Jailbreak. Rooted Android: launch Spring with the rooted WinterX bridge. No root: run Start WinterX Rootless on your computer.";
var message = screen.add(new UILabel({ frame: [25, 220, 270, 72], text: setupMessage, size: 14, lines: 4, align: "center", color: "#555555" }));
var button = screen.add(new UIButton({ frame: [45, 300, 230, 44], title: "Jailbreak", onTap: jailbreak }));
screen.add(new UIButton({ frame: [85, 356, 150, 38], title: "Check Status", onTap: refresh }));
function refresh() {
  // The active Spring runtime exposes this status on either supported workflow.
  try {
    if (files.exists("winterx/status")) {
      // This Spring is jailbroken; Jailbreak stays available to switch to the other version.
      var running = storage.get("winterx.jailbroken.v1");
      if (known(running) && running !== selectedVersion || !known(running) && chosen) {
        button.enabled = true;
        message.text = (known(running) ? nameOf(running) + " is jailbroken. " : "") + "Tap Jailbreak to switch to " + nameOf(selectedVersion) + ".";
      } else {
        button.enabled = false;
        message.text = "Successfully Jailbroken";
      }
      return;
    }
  } catch (e) {}
  if (!current) { button.enabled = true; message.text = setupMessage; return; }
  var result = "results/" + current + ".json";
  if (!files.exists(result)) { button.enabled = false; message.text = "Waiting for the Ruby bridge. Spring will restart during jailbreak."; return; }
  try {
    var reply = files.readJSON(result);
    if (reply.action !== "jailbreak") {
      button.enabled = true;
      message.text = "Please reconnect the Ruby bridge on your computer and try again.";
      return;
    }
    if (!reply.ok) {
      button.enabled = true;
      message.text = "Jailbreak failed: " + reply.message;
      return;
    }
    button.enabled = false;
    storage.set("winterx.jailbroken.v1", reply.springVersion || selectedVersion);
    if (!files.exists("live.json")) { message.text = "Checking jailbreak status with the Ruby bridge."; return; }
    var live = files.readJSON("live.json");
    var age = Date.now() - Number(live.observedAt);
    if (!isFinite(age) || age < -5000 || age > 10000) {
      message.text = "Reconnect the Ruby bridge to confirm jailbreak status.";
    } else if (live.active === true) {
      message.text = "Successfully Jailbroken";
    } else {
      button.enabled = true;
      message.text = "Jailbreak is not active. Open the original Spring and tap Jailbreak.";
    }
  } catch (e) { message.text = "Could not read the bridge response."; }
}
function jailbreak() {
  var id = String(Date.now()) + "-" + String(Math.floor(Math.random() * 1000000000));
  try {
    current = id;
    storage.set("jailbreak.request.v1", id);
    files.writeJSON("requests/" + id + ".json", { id: id, action: "jailbreak", version: selectedVersion });
    refresh();
  } catch (e) {
    current = null;
    storage.remove("jailbreak.request.v1");
    button.enabled = true;
    UIAlertView.show({ title: "Could not start", message: String(e), buttons: ["OK"] });
  }
}
screen.onAppear = refresh;
setInterval(refresh, 1000);
selectVersion(selectedVersion);
UIApplication.run(new UINavigationController(screen, { barStyle: "black" }));
