package winterx.animaper;
import java.util.HashSet;
import java.util.Set;
import java.util.Arrays;
public class EffectsCheck {
  public static void main(String[] args) {
    String[] modes={"wave","cascade","bounce","orbit","ripple","columns","fan","zigzag","barrel"};
    Set<String> results=new HashSet<>();
    for (String mode:modes) {
      if (!Arrays.equals(Effects.offset(mode,0,1,2,640,114),new int[]{0,0})) throw new AssertionError(mode+" moved a settled icon");
      if (!Arrays.equals(Effects.offset(mode,1,1,2,640,114),new int[]{0,0})) throw new AssertionError(mode+" moved an offscreen page");
      int[] value=Effects.offset(mode,.45f,1,2,640,114);
      if (value[0]==0 && value[1]==0) throw new AssertionError(mode+" did not animate");
      results.add(Arrays.toString(value));
    }
    if (results.size()!=modes.length) throw new AssertionError("Effects are not distinct");
    for (float progress:new float[]{0f,1f,-1f,Float.NaN,Float.POSITIVE_INFINITY}) {
      Effects.Barrel value=Effects.barrel(progress,320,640);
      if (value.shiftX!=0 || value.scaleX!=1 || value.scaleY!=1) throw new AssertionError("invalid/settled Barrel transform");
    }
    for (float progress:new float[]{.1f,.45f,.8f}) for (float center:new float[]{40f,192f,344f,496f}) {
      Effects.Barrel value=Effects.barrel(progress,center,640), mirrored=Effects.barrel(-progress,640-center,640);
      if (!Float.isFinite(value.shiftX) || value.scaleX<=0 || value.scaleX>1 || value.scaleY<=0 || value.scaleY>1)
        throw new AssertionError("unbounded Barrel transform");
      if (Math.abs(value.shiftX+mirrored.shiftX)>.001f || Math.abs(value.scaleX-mirrored.scaleX)>.00001f || Math.abs(value.scaleY-mirrored.scaleY)>.00001f)
        throw new AssertionError("Barrel directions are not symmetric");
      if (value.scaleX==1 || value.scaleY==1) throw new AssertionError("Barrel is only a positional wave");
    }
    System.out.println("Nine distinct settled-safe Animaper effects and cylindrical Barrel projection passed");
  }
}
