// Runs inside Inject Target after Spring's UIKit and before the app's own main.js,
// in the same JavaScript context. Wrap any UIKit class the app will use.
(function () {
  var Original = UIViewController;
  function SnowflakeController(options) {
    if (options && typeof options.title === "string") options.title = "❄ " + options.title;
    return new Original(options);
  }
  SnowflakeController.prototype = Original.prototype;
  UIViewController = SnowflakeController;
})();
