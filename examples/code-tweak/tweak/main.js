WinterX.log("My independently packaged tweak has loaded.");

WinterX.on("settingsTap", function (page, row) {
  if (page === "main" && row === "hello") {
    var count = (WinterX.state.read("helloCount") || 0) + 1;
    WinterX.state.write("helloCount", count);
    WinterX.alert({
      title: "My Own Tweak",
      message: "This is code from tweak/main.js, not a preset WinterX hook.\nRuns: " + count,
      buttons: ["OK"]
    }).then(function (button) {
      WinterX.log("Alert button:", button);
    });
  } else if (page === "main" && row === "enabled") {
    var settings = WinterX.state.read("settings") || {};
    WinterX.log("My preference:", settings["main/enabled"]);
  } else if (page === "more" && row === "save") {
    WinterX.data.write("example.txt", "Hello from my custom tweak!\n");
    WinterX.alert({title: "Saved", message: WinterX.data.read("example.txt")});
  }
});
