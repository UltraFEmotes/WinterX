var current = storage.get("jailbreak.request.v1") || null;
var selectedVersion = storage.get("winterx.version.v1") || "0.8.1";
var screen = new UIViewController({ title: "WinterX", background: "#e4e5e8" });
screen.add(new UILabel({ frame: [20, 30, 280, 46], text: "WinterX", size: 25, bold: true, align: "center", color: "#1d467d" }));
screen.add(new UILabel({ frame: [30, 90, 260, 54], text: "Jailbreak Spring", size: 16, align: "center", lines: 2, color: "#444444" }));
var versionButton = screen.add(new UIButton({ frame: [55, 142, 210, 38], title: "Spring " + selectedVersion, onTap: selectVersion }));
var message = screen.add(new UILabel({ frame: [25, 185, 270, 80], text: "Start the Ruby bridge on your Mac, then tap Jailbreak.", size: 14, lines: 4, align: "center", color: "#555555" }));
var button = screen.add(new UIButton({ frame: [45, 280, 230, 44], title: "Jailbreak", onTap: jailbreak }));
screen.add(new UIButton({ frame: [85, 340, 150, 38], title: "Check Status", onTap: refresh }));
function refresh() {
  // The patched Spring runtime exposes this status without the Mac bridge.
  try {
    if (files.exists("winterx/status")) {
      button.enabled = false;
      message.text = "Successfully Jailbroken";
      return;
    }
  } catch (e) {}
  if (selectedVersion !== "0.8.1") {
    button.enabled = false;
    message.text = "Spring 0.9 Preview 1 support is being developed.";
    return;
  }
  if (!current) { button.enabled = true; message.text = "Start the Ruby bridge on your Mac, then tap Jailbreak."; return; }
  var result = "results/" + current + ".json";
  if (!files.exists(result)) { button.enabled = false; message.text = "Waiting for the Ruby bridge. Spring will restart during jailbreak."; return; }
  try {
    var reply = files.readJSON(result);
    if (reply.action !== "jailbreak") {
      button.enabled = true;
      message.text = "Please restart the Ruby bridge on your Mac and try again.";
      return;
    }
    if (!reply.ok) {
      button.enabled = true;
      message.text = "Jailbreak failed: " + reply.message;
      return;
    }
    button.enabled = false;
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
function selectVersion() {
  UIAlertView.show({ title: "Spring Version", message: "Choose the version installed in Mac.APK.",
    buttons: ["Cancel", "0.8.1", "0.9 Preview 1"] }, function (index) {
      if (index !== 1 && index !== 2) return;
      selectedVersion = index === 1 ? "0.8.1" : "0.9 Preview 1";
      storage.set("winterx.version.v1", selectedVersion);
      versionButton.title = "Spring " + selectedVersion;
      refresh();
    });
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
refresh();
UIApplication.run(new UINavigationController(screen, { barStyle: "black" }));
