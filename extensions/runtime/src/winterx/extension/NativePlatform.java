package winterx.extension;

/** Read-only adapters for Spring 0.8.1 native models, shared with community authors. */
public final class NativePlatform {
    private NativePlatform() {}
    public static E1.i6 editProfile(E1.O1 edit) {
        try {
            if (edit == null || !(edit.d instanceof x1.P0)) return null;
            java.lang.reflect.Field field = x1.P0.class.getDeclaredField("w"); field.setAccessible(true);
            x1.i1 controller = (x1.i1)field.get(edit.d); return controller == null ? null : controller.e;
        } catch (Exception unavailable) { return null; }
    }
    public static String appId(Object model) { return model instanceof E1.a ? ((E1.a)model).a : null; }
    public static int screenWidth(Object profile) { return profile instanceof E1.i6 ? ((E1.i6)profile).b : 0; }
    public static int screenHeight(Object profile) { return profile instanceof E1.i6 ? ((E1.i6)profile).c : 0; }
}
