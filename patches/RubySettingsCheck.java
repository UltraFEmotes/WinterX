import java.util.List;
public class RubySettingsCheck {
  public static void main(String[] args) throws Exception {
    Class<?> settings = Class.forName("E1.Z3");
    Object root = settings.getField("c").get(null);
    List<?> sections = (List<?>) root.getClass().getField("c").get(root);
    for (Object section : sections) {
      List<?> rows = (List<?>) section.getClass().getField("c").get(section);
      for (Object row : rows) {
        Object id = row.getClass().getField("a").get(row);
        if ("ruby-test".equals(id)) {
          System.out.println("Found Ruby Settings row: " + row.getClass().getField("b").get(row));
          return;
        }
      }
    }
    throw new AssertionError("Ruby Settings row not found");
  }
}
