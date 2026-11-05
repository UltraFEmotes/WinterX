package me.example.winterx;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Collections;
import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

/** Community code: no official-tweak classes or private installer entry points. */
public final class HelloNative implements NativeTweak {
    private TweakContext context;
    private int count;

    public void start(TweakContext context) throws Exception {
        this.context = context;
        File saved = context.data("counter.txt");
        if (saved.isFile() && safe(saved) && saved.length() <= 16) {
            String value = new String(Files.readAllBytes(saved.toPath()), StandardCharsets.UTF_8).trim();
            if (value.matches("[0-9]{1,6}")) count = Integer.parseInt(value);
        }
    }

    public synchronized Object call(String point, Object[] args) throws Exception {
        if (!context.active()) return null;
        if ("settings.page".equals(point) && "main".equals(args[0])) {
            String rowId = "winterx-tw-r/" + context.id() + "/main/increment";
            V6 row = Z3.g(Z3.a, rowId, "Count: " + count + " — tap to add one", null, null, null, 0x18);
            W6 section = new W6("COMMUNITY CODE", null, null, null, Collections.singletonList(row));
            return new T6("winterx-tw-p/" + context.id(), "Hello Native", Collections.singletonList(section));
        }
        if ("settings.tap".equals(point) && args.length == 2 && "main".equals(args[0]) && "increment".equals(args[1])) {
            File saved = context.data("counter.txt");
            File directory = saved.getParentFile();
            if (!safe(directory) || !safe(saved) || !directory.isDirectory() && !directory.mkdirs())
                throw new IllegalStateException("Package data is unavailable");
            int next = count == 999999 ? 0 : count + 1;
            File temporary = File.createTempFile(".counter-", ".tmp", directory);
            try {
                try (FileOutputStream output = new FileOutputStream(temporary)) {
                    output.write((next + "\n").getBytes(StandardCharsets.UTF_8));
                    output.getFD().sync();
                }
                if (!context.active() || !safe(saved) || !temporary.renameTo(saved))
                    throw new IllegalStateException("Counter was not saved");
                count = next;
            } finally { temporary.delete(); }
        }
        return null;
    }

    private static boolean safe(File file) throws Exception {
        return !Files.isSymbolicLink(file.toPath()) && file.getCanonicalFile().equals(file.getAbsoluteFile());
    }
}
