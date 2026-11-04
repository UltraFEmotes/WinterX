public class BootCheck {
    public static void main(String[] args) throws Exception {
        var activity = new android.app.Activity();
        var hook = Class.forName("ruby.RubyHooks").getMethod("showBoot", android.app.Activity.class);
        hook.invoke(null, activity);
        var text = (android.widget.TextView) activity.last;
        if (!"WinterX\nby WeirdMM".equals(text.text) || text.textColor != -1 || text.gravity != 17)
            throw new AssertionError("Boot screen content is wrong");
        if (text.background != 0xff000000 || android.view.View.pending == null)
            throw new AssertionError("Boot screen appearance or timer is wrong");
        android.view.View.pending.run();
        if (!activity.root.removed) throw new AssertionError("Boot screen was not removed");
        var rejected = new android.app.Activity();
        android.view.View.acceptPost = false;
        hook.invoke(null, rejected);
        if (!rejected.root.removed) throw new AssertionError("Failed timer left the boot screen stuck");
        System.out.println("Boot screen content, timed removal and timer failure cleanup passed");
    }
}
