public class RubyProtectionCheck {
 public static void main(String[] args) throws Exception {
  Class<?> type=Class.forName("x1.i1");
  var m=type.getMethod("d0",String.class);
  if ((Boolean)m.invoke(null,"sapp:com.ruby.manager")) throw new AssertionError("Ruby is deletable");
  if (!(Boolean)m.invoke(null,"sapp:com.example.other")) throw new AssertionError("Other apps blocked");
  System.out.println("Ruby is protected; another Spring app remains deletable");
 }
}
