"""Hand-ported WinterX insertions for Spring 0.9 Preview 1: the ones whose 0.8.1 anchors can't be found automatically.

Each one names what it replaces (matched against port.py's survey) and was checked against 0.9's code by hand: the
registers it reads hold the same values as in 0.8.1, and any scratch register it writes is dead at that point
(tools/smali_live.py). port.py runs these after the automatic port.
"""
import re

import settings_test as st

HANDLED = {}                                   # failure text -> why it's handled


def handles(*needles):
    def register(function):
        for needle in needles: HANDLED[needle] = function.__name__
        FIXES.append(function)
        return function
    return register


FIXES = []
ALWAYS = set()                                 # corrections: automatic ports that apply but read the wrong registers


def corrects(function):
    """A fix for an insertion the automatic port places but can't get right (0.9 reshuffled its registers)."""
    FIXES.append(function); ALWAYS.add(function.__name__)
    return function


def body(port, cls, line):
    """(path, text, start, end) of one method in a 0.9 class, by its exact .method line."""
    path = port.files[cls]; text = path.read_text()
    if text.count(line + '\n') != 1: raise ValueError('0.9 method not found: ' + cls + ' ' + line)
    start = text.index(line + '\n'); end = text.index('.end method', start)
    return path, text, start, end


def edit(port, cls, line, change):
    path, text, start, end = body(port, cls, line)
    path.write_text(text[:start] + change(text[start:end]) + text[end:])


def once(text, old, new):
    if text.count(old) != 1: raise ValueError('expected one anchor, found %d: %s' % (text.count(old), old[:120]))
    return text.replace(old, new, 1)


def after_locals(code):
    """Insert code right after a method's .locals line."""
    def change(method):
        m = re.search(r'\n    \.locals \d+\n', method)
        return method[:m.end()] + code + '\n' + method[m.end():]
    return change


@handles('Expected one method: .method public constructor <init>(Lcom/guille/spring/LauncherActivity;Lr1/x0;')
def inbox(port):
    """J1/y (0.9 F1/O, the .sapp manager) constructor: start WinterX's inbox watcher. Its lambda parameter types differ."""
    edit(port, 'F1/O', '.method public constructor <init>(Lcom/guille/spring/LauncherActivity;Lr1/s0;Lr1/s0;LF1/j;Lr1/A;Lr1/s0;)V',
         lambda m: once(m, '    return-void', '    invoke-static {p0}, Lwinterx/runtime/InboxMonitor;->start(LF1/O;)V\n    return-void'))


@handles('Settings tap routing: anchor not found')
def settings_taps(port):
    """x1/i1.b4 (0.9 r1/E1.R4): route WinterX Settings rows. 0.8.1 v9 (row) / v5 (page state) are v8 / v4 here;
    v0 and v10 (scratch) are dead at :cond_34, as they were at 0.8.1's :cond_32."""
    patch = port.text(st.TAP_PATCH).replace(':cond_32', ':cond_34')
    patch = re.sub(r'\bv9\b', 'v8', re.sub(r'\bv5\b', 'v4', patch))
    anchor = '    :cond_34\n    sget-object v0, Ly1/j5;->a:Ljava/util/List;'
    def change(m):
        plain = re.sub(r'\n    \.line \d+', '', m)
        return once(plain, anchor, patch)
    edit(port, 'r1/E1', '.method public final R4(FF)Z', change)


@handles('Ruby delete guard: anchor not found')
def delete_guard(port):
    """x1/i1.d0 (0.9 r1/E1.m0): Spring's "can this app be deleted" check refuses Ruby. p0 is the app key."""
    guard = st.DELETE_PATCH[len(st.DELETE_MARKER):].lstrip('\n')
    edit(port, 'r1/E1', '.method public static m0(Ljava/lang/String;)Z', after_locals(guard))


@handles('Expected one method: .method public final d(Landroid/graphics/Canvas;Ly1/c7;LE1/e1;LE1/Q1;Ljava/util/Map;ZZ)V')
def status_bar(port):
    """I1/k0.d (0.9 E1/r0.d, now static with two more parameters): draw Safe Mode's label before every return.
    The Canvas is p0 here (p1 in 0.8.1's instance method)."""
    edit(port, 'E1/r0', '.method public static d(Landroid/graphics/Canvas;Ly1/c7;LE1/e1;LE1/Q1;Ljava/util/Map;ZZLjava/lang/Float;I)V',
         lambda m: m.replace('    return-void', '    move-object/from16 v0, p0\n'
                             '    invoke-static {v0}, Lwinterx/safe/SafeAppearance;->status(Landroid/graphics/Canvas;)V\n    return-void'))


@handles('Settings root row: anchor not found', 'iOS 6 Settings root row: anchor not found')
def ruby_test_rows(port):
    """Not ported on purpose: the legacy "Ruby Test" Settings row (only shown with ruby/settings-test.enabled, a
    developer marker from before tweaks were packages). WINTERX TWEAKS pages come from TweakSettings.decorate."""


@handles('Unexpected normal-home Barrel context registers')
def barrel_context(port):
    """I1/h0.k (0.9 E1/o0.l, its stock body now winterxStockK): tell Animaper which Home entry is drawn next.
    The entry is v3 right after its cast, as in 0.8.1; v4 (scratch) is dead there in both versions."""
    path = port.files['E1/o0']; text = path.read_text()
    line = re.search(r'^\.method [^\n]* winterxStockK\([^\n]*$', text, re.M).group(0)
    edit(port, 'E1/o0', line, lambda m: once(m, '    check-cast v3, LE1/i0;',
        '    check-cast v3, LE1/i0;\n    move-object/from16 v4, p0\n'
        '    invoke-static {v4, v3}, Lwinterx/animaper/Animaper;->context(Ly1/c7;LE1/i0;)V'))


@handles('Unexpected folder-content icon lookup')
def snowy_folder_icons(port):
    """I1/h0.C (0.9 E1/o0.D): open-folder icons go through the icon resolver (SnowyHome's icon packs). Same registers
    and parameters as 0.8.1: v1 the app, p3/p4/p5 the state, renderer and bitmap map; v4/v6/v11 are overwritten next."""
    def change(m):
        plain = re.sub(r'\n    \.line \d+', '', m)
        pattern = (r'    iget-object v4, v1, Ly1/a;->c:Ljava/lang/String;\n(?:\s*\n)*    move-object/from16 v11, p5\n(?:\s*\n)*'
                   r'    invoke-virtual \{v11, v4\}, Ljava/util/concurrent/ConcurrentHashMap;->get\(Ljava/lang/Object;\)Ljava/lang/Object;')
        out, n = re.subn(pattern, '    move-object/from16 v4, p3\n    move-object/from16 v6, p4\n    move-object/from16 v11, p5\n'
            '    invoke-static {v1, v4, v6, v11}, LE1/o0;->d(Ly1/a;Ly1/c7;LE1/e1;Ljava/util/Map;)Landroid/graphics/Bitmap;', plain)
        if n != 1: raise ValueError('folder icon lookup: %d' % n)
        return out
    edit(port, 'E1/o0', '.method public final D(Landroid/graphics/Canvas;Landroid/graphics/Paint;Ly1/c7;LE1/e1;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;Landroid/graphics/Bitmap;LE1/d0;I)V', change)


@handles('Expected one method: .method public final winterxStockR(', 'anchor not found (0 flexible matches): .method public final winterxStockR(')
def snowy_edit_cache(port):
    """I1/h0.r (0.9 E1/o0.s): with SnowyHome on, skip the precomposed edit-mode tile cache (p7, same slot in 0.9).
    With DockIn applied this goes in its winterxStockR (the stock body, .locals 40 here, 36 in 0.8.1); without DockIn,
    in the method itself. winterxStockR is still written in 0.8.1 types at this point, so it's found by name."""
    path = port.files['E1/o0']; text = path.read_text()
    found = re.findall(r'^\.method public final winterxStockR\(.*$', text, re.M)
    line = found[0] if len(found) == 1 else '.method public final s(Landroid/graphics/Canvas;Landroid/graphics/Paint;Ly1/c7;LE1/e1;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;LD/a;Ly1/C1;ZF)V'
    edit(port, 'E1/o0', line,
         after_locals('    invoke-static {}, Lwinterx/snowy/SnowyHome;->enabled()Z\n'
                      '    move-result v0\n    if-eqz v0, :winterx_snowy_stock_cache\n'
                      '    const/4 v0, 0x0\n    move-object/16 p7, v0\n    :winterx_snowy_stock_cache'))


@handles("replace_once in I1/T0: anchor not found (0 flexible matches): :cond_0")
def folder_prewarm(port):
    """I1/T0.P (0.9 E1/r1.W): don't warm folder layers while a tweak draws them. v0 is 'this' in 0.9, so the gate uses
    v1, which is dead at :cond_0."""
    edit(port, 'E1/r1', '.method public final W(Ly1/c7;)V', lambda m: once(re.sub(r'\n    \.line \d+', '', m),
        '    :cond_0\n    invoke-virtual/range {p1 .. p1}, Ly1/c7;->c()I',
        '    :cond_0\n    invoke-static {}, Lwinterx/layout/RenderPolicy;->folderLayersAllowed()Z\n'
        '    move-result v1\n    if-nez v1, :winterx_folder_prewarm\n    return-void\n'
        '    :winterx_folder_prewarm\n    invoke-virtual/range {p1 .. p1}, Ly1/c7;->c()I'))


@handles("replace_once in G1/l: anchor not found", "replace_once in I1/y: anchor not found")
def messages_buttons(port):
    """G1/l.a and I1/y.l (0.9 A1/n.a, E1/D.l): Message+ decorates the first navigation button each builds. The button
    is the same register as in 0.8.1 (v1, v5); 0.9's constructor takes one more argument."""
    ctor = 'Ly1/N0;-><init>(Ljava/lang/String;Ljava/lang/String;Ly1/M0;ZLjava/lang/Float;FLjava/lang/String;ZI)V'
    for cls, line, rng, reg in (('A1/n', '.method public final a(ILy1/q3;)Ly1/r3;', '{v7 .. v16}', 'v1'),
                                ('E1/D', '.method public static l(Ly1/R2;)Ly1/w2;', '{v13 .. v22}', 'v5')):
        call = '    invoke-direct/range ' + rng + ', ' + ctor
        def change(m, call=call, reg=reg):
            first = m.index(call)
            return m[:first + len(call)] + ('\n    invoke-static {%s}, Lwinterx/messages/MessagePlus;->button(Ly1/N0;)Ly1/N0;\n'
                                             '    move-result-object %s' % (reg, reg)) + m[first + len(call):]
        edit(port, cls, line, change)


@handles('ColoredBar dispatcher anchor missing')
def coloredbar(port):
    """ColoredBar's three patches, as coloredbar.py does them, on 0.9's counterparts: I1/T0.g and .m (E1/r1.g and .p;
    app id still p4), the Settings loader I1/S0.get (E1/q1.get) and the App Store renderer I1/N0.d (E1/h1.a, 78 locals)."""
    counts = {}
    for name in ('g(Landroid/graphics/Canvas;Ly1/c7;LE1/e1;Ljava/lang/String;J)V', 'p(Landroid/graphics/Canvas;Ly1/c7;LE1/e1;Ljava/lang/String;JZ)V'):
        def change(m, name=name):
            local = re.search(r'    \.locals (\d+)', m); count = int(local.group(1))
            m = m.replace(local.group(0), '    .locals ' + str(count + 2) + '\n    move-object/16 v' + str(count + 1) + ', p4\n'
                          '    invoke-static/range {p2 .. p2}, Lwinterx/coloredbar/ColoredBar;->observe(Ly1/c7;)V', 1)
            def wrap(match):
                r = match.group(1); a, b = 'v' + str(count), 'v' + str(count + 1)
                return (match.group(0) + '\n    move-object/16 %s, %s\n    invoke-static/range {%s .. %s}, Lwinterx/appearance/RubyAppearance;->assets(Ljava/util/Map;Ljava/lang/String;)Ljava/util/Map;'
                        '\n    move-result-object %s\n    move-object/16 %s, %s\n    invoke-static/range {%s .. %s}, Lwinterx/coloredbar/ColoredBar;->assets(Ljava/util/Map;Ljava/lang/String;)Ljava/util/Map;'
                        '\n    move-result-object %s') % (a, r, a, b, r, a, r, a, b, r)
            m, n = re.subn(r'^    iget-object (v\d+), (v\d+|p0), LE1/r1;->\w+:Ljava/util/Map;$', wrap, m, flags=re.M)
            if n == 0: raise ValueError('ColoredBar: no artwork maps in E1/r1.' + name[0])
            counts[name[0]] = n
            return m
        edit(port, 'E1/r1', '.method public final ' + name, change)
    def settings(m):
        m = once(m, '    .locals 2', '    .locals 4\n    move-object v2, p1')
        out, n = re.subn(r'^    return-object (v1|p1)$', lambda r: ('    move-object v3, ' + r.group(1) +
            '\n    invoke-static {v2, v3}, Lwinterx/coloredbar/ColoredBar;->settingsAsset(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;'
            '\n    move-result-object ' + r.group(1) + '\n' + r.group(0)), m, flags=re.M)
        if n != 2: raise ValueError('ColoredBar Settings loader returns: %d' % n)
        return out
    edit(port, 'E1/q1', '.method public final get(Ljava/lang/Object;)Ljava/lang/Object;', settings)
    def appstore(m):
        m = once(m, '    .locals 78', '    .locals 80\n    const-string v79, "appstore"')
        anchor = '    iget-object v8, v2, LE1/r1;->p:Ljava/util/Map;'
        return once(m, anchor, anchor + '\n    move-object/16 v78, v8\n'
                    '    invoke-static/range {v78 .. v79}, Lwinterx/coloredbar/ColoredBar;->assets(Ljava/util/Map;Ljava/lang/String;)Ljava/util/Map;\n'
                    '    move-result-object v8')
    edit(port, 'E1/h1', '.method public final a(Ljava/lang/Object;)Ljava/lang/Object;', appstore)
    port.failures.append({'class': 'port09.coloredbar', 'method': '', 'error': 'info: ColoredBar artwork maps wrapped: %s (0.8.1: g 14, m 18)' % counts})


@handles('Unexpected app-launch size anchors')
def dockin_launch(port):
    """DockIn's launch size, x1/i1.S2 / R2 / N (0.9 r1/E1.E3 / D3 / R): the zoom starts from DockIn's icon size instead
    of the stock one. Host and app registers are the same as 0.8.1; R reads the size from v3 (v2 in 0.8.1), and D3
    has two launch paths, not three (0.9 dropped the x1/K.x special case)."""
    def launch(anchor, host, app, dest, count):
        def change(m):
            if m.count(anchor) != count: raise ValueError('app-launch size: %d x %s' % (m.count(anchor), anchor.strip()))
            return m.replace(anchor, '    invoke-static {' + host + ', ' + app + '}, Lwinterx/layout/DockIn;->launchSize(Lr1/E1;Ljava/lang/String;)I\n'
                             '    move-result ' + dest)
        return change
    edit(port, 'r1/E1', '.method public static E3(Lr1/E1;Ly1/a;IIZZI)V', launch('    iget v13, v2, Ly1/U6;->e:I', 'v0', 'v14', 'v13', 1))
    edit(port, 'r1/E1', '.method public final D3(Ly1/A0;Ly1/a;)V', launch('    iget v15, v5, Ly1/U6;->e:I', 'v7', 'v4', 'v15', 2))
    edit(port, 'r1/E1', '.method public final R(Ljava/lang/String;Z)Z', launch('    iget v8, v3, Ly1/U6;->e:I', 'v0', 'v14', 'v8', 1))


def inserted(port, cls, name):
    """The one method called name in a 0.9 class; methods WinterX inserts are still in 0.8.1 types here."""
    found = re.findall(r'^\.method (?:[a-z-]+ )*' + re.escape(name) + r'\(.*$', port.files[cls].read_text(), re.M)
    if len(found) != 1: raise ValueError('%s.%s: %d methods' % (cls, name, len(found)))
    return found[0]


@corrects
def dockin_legacy(port):
    """DockIn's legacy dock icons, I1/j1.e (0.9 l2/d.w, DockIn's winterxStockE): 0.9 moved the Canvas to v10 and the
    grid to v12 (v9 / v11 in 0.8.1; v9 is p7 and v11 the Paint here), and already declares .locals 31, so v30 isn't
    free; DockIn's icon state goes in a new v31."""
    def change(m):
        m = once(m, '    .locals 31\n', '    .locals 32\n')
        m, n = re.subn(r'    invoke-static \{v9, v11, v3, v4, v2\}, (Lwinterx/layout/DockIn;->beginLegacy\([^\n]*)\n(\s*)move-result v30\n',
                       r'    invoke-static {v10, v12, v3, v4, v2}, \1\n\2move-result v31\n', m)
        if n != 1: raise ValueError('DockIn beginLegacy: %d' % n)
        return once(m, '    move/from16 v1, v30\n    invoke-static {v0, v1}, Lwinterx/layout/DockIn;->endIcon(',
                    '    move/from16 v1, v31\n    invoke-static {v0, v1}, Lwinterx/layout/DockIn;->endIcon(')
    edit(port, 'l2/d', inserted(port, 'l2/d', 'winterxStockE'), change)


@corrects
def dockin_motion_frame(port):
    """DockMotion's frame, x1/i1.a0 (0.9 r1/E1.j0): 0.8.1 has the frame time in v14:v15 there; 0.9 keeps it in
    v124:v125 (its v8:v9 copy is reused before this point). v14 and v15 are dead after the dock frame is built."""
    def change(m):
        return once(m, '    move-object/from16 v2, p0\n    invoke-static {v2, v0, v14, v15}, Lwinterx/layout/DockMotion;->frame(',
                    '    move-object/from16 v2, p0\n    move-wide/from16 v14, v124\n    invoke-static {v2, v0, v14, v15}, Lwinterx/layout/DockMotion;->frame(')
    edit(port, 'r1/E1', '.method public final j0()Ly1/c7;', change)


def apply(port):
    """Run the fixes whose failure the automatic port reported, so one doesn't land twice when the anchor did port
    (e.g. SnowyHome's edit cache: in DockIn's winterxStockR when DockIn is applied, in the method itself otherwise)."""
    done = []
    reported = {name for needle, name in HANDLED.items()
                if any(needle in f['error'] or needle in f['method'] for f in port.failures)}
    for fix in FIXES:
        if fix.__name__ not in reported and fix.__name__ not in ALWAYS: continue
        try: fix(port); done.append(fix.__name__)
        except Exception as failure:
            if not port.survey: raise
            port.failures.append({'class': 'port09.' + fix.__name__, 'method': '', 'error': str(failure)[:300]})
    return done
