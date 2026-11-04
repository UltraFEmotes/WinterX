import java.io.File;
public class WelcomeCheck {
    public static void main(String[] args) throws Exception {
        var activity = new com.guille.spring.LauncherActivity();
        Class<?> hooks = Class.forName("ruby.RubyHooks");
        var show = hooks.getMethod("showWelcome", com.guille.spring.LauncherActivity.class);
        show.invoke(null, activity);
        show.invoke(null, activity);
        if (x1.J.INSTANCE.calls != 1) throw new AssertionError("Welcome should show exactly once");
        if (!"WinterX".equals(x1.J.INSTANCE.title)) throw new AssertionError("Wrong title");
        String expected = "Welcome to WinterX, this project is still in beta, feel free to give suggestions and bug reports from the GitHub";
        if (!expected.equals(x1.J.INSTANCE.body)) throw new AssertionError("Wrong message");
        if (!new File(System.getProperty("ruby.test.dir"), "ruby/welcome-shown-v1").isFile()) throw new AssertionError("No welcome receipt");
        hooks.getMethod("showTestAlert", com.guille.spring.LauncherActivity.class).invoke(null, activity);
        if (x1.J.INSTANCE.calls != 2 || !"Ruby Test".equals(x1.J.INSTANCE.title) ||
            !"This is a test alert from WinterX.".equals(x1.J.INSTANCE.body)) throw new AssertionError("Test alert mismatch");
        System.out.println("Welcome and test alerts passed");
    }
}
