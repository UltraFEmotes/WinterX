package winterx.animaper;
import java.util.HashSet;
import java.util.Set;
import java.util.Arrays;
public class EffectsCheck {
  public static void main(String[] args) {
    String[] modes={"wave","cascade","bounce","orbit","ripple","columns","fan","zigzag"};
    Set<String> results=new HashSet<>();
    for (String mode:modes) {
      if (!Arrays.equals(Effects.offset(mode,0,1,2,640,114),new int[]{0,0})) throw new AssertionError(mode+" moved a settled icon");
      if (!Arrays.equals(Effects.offset(mode,1,1,2,640,114),new int[]{0,0})) throw new AssertionError(mode+" moved an offscreen page");
      int[] value=Effects.offset(mode,.45f,1,2,640,114);
      if (value[0]==0 && value[1]==0) throw new AssertionError(mode+" did not animate");
      results.add(Arrays.toString(value));
    }
    if (results.size()!=modes.length) throw new AssertionError("Effects are not distinct");
    System.out.println("Eight distinct settled-safe Animaper effects passed");
  }
}
