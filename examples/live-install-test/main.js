// Live Install Test: a Spring app. See docs/api.md for the API.
var list = new UITableViewController({
  title: "Live Install Test",
  style: "grouped",
  sections: [
    { header: "Hello", rows: [{ title: "Tap me", accessory: "disclosure" }] }
  ],
  didSelect: function (section, row) {
    UIAlertView.show({ title: "Live Install Test", message: "Hello from Spring.", buttons: ["OK"] });
  }
});
UIApplication.run(new UINavigationController(list));
