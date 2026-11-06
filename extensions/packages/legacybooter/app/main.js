// LegacyBooter draws iPhone OS 1 over this app while it's open; the app itself is only a black screen behind it.
var screen = new UIViewController({ title: "iPhone OS 1", background: "#000000" });
UIApplication.run(screen);
