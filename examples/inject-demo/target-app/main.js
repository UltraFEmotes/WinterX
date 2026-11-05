// A plain app. It knows nothing about tweaks: Inject Demo's script changes it from outside.
var screen = new UIViewController({ title: "Inject Target", background: "#ffffff" });
screen.add(new UILabel({ frame: [20, 40, 280, 60], text: "This app's own code set the title to \"Inject Target\".", lines: 2, size: 15 }));
UIApplication.run(new UINavigationController(screen));
