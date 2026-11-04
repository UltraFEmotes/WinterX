"""Opt-in, anchor-checked Messages-only settings and existing JPEG quality hooks."""
SPRING = 'smali/x1.1/i1.1.smali'
ACTIVITY = 'smali/com/guille/spring/LauncherActivity.smali'
MODEL = 'smali/G1/l.smali'
RENDER = 'smali/I1/y.1.smali'
PHOTO = 'smali/x1.1/w1.1.smali'
PATHS = (ACTIVITY, MODEL, RENDER, PHOTO)


def apply(contents, method, replace_once):
    for name, register, constructor, line, signature in (
        (MODEL, 'v1', '{v7 .. v15}', 18, '.method public final a(ILE1/k3;)LE1/l3;'),
        (RENDER, 'v5', '{v13 .. v21}', 44, '.method public static l(LE1/K2;)LE1/w2;'),
    ):
        def decorate(m, register=register, constructor=constructor, line=line):
            anchor = ('    .line ' + str(line) + '\n    invoke-direct/range ' + constructor + ', LE1/N0;-><init>'
                      '(Ljava/lang/String;Ljava/lang/String;LE1/M0;ZLjava/lang/Float;FLjava/lang/String;I)V')
            return replace_once(m, anchor, anchor + '\n'
                '    invoke-static {' + register + '}, Lwinterx/messages/MessagePlus;->button(LE1/N0;)LE1/N0;\n'
                '    move-result-object ' + register)
        contents[name] = method(contents[name], signature, decorate)
    for name, local_count, hook in (('u1', 34, 'press'), ('t1', 29, 'move'), ('v1', 33, 'release')):
        signature = '.method public final ' + name + '(FF)Z'
        anchor = signature + '\n    .locals ' + str(local_count)
        body = ('\n    invoke-static/range {p0 .. p2}, Lwinterx/messages/MessagePlus;->' + hook + '(Lx1/i1;FF)Z\n'
                '    move-result v0\n    if-eqz v0, :winterx_messages_native\n'
                '    return v0\n    :winterx_messages_native')
        contents[SPRING] = method(contents[SPRING], signature, lambda m, a=anchor, b=body: replace_once(m, a, a + b))
    signature = '.method private final onVirtualCancel()V'
    anchor = signature + '\n    .locals 42'
    contents[ACTIVITY] = method(contents[ACTIVITY], signature, lambda m: replace_once(m, anchor, anchor + '\n'
        '    invoke-static/range {p0 .. p0}, Lwinterx/messages/MessagePlus;->cancel(Lcom/guille/spring/LauncherActivity;)V'))
    signature = '.method public final a(Landroid/net/Uri;)Lx1/v1;'
    def photo(m):
        # w1 is used by messagesPhotoPicked/shootMessagesPhoto, not WhatsApp or screenshots.
        if '"msg-photo"' not in m or m.count('Bitmap;->compress(') != 1:
            raise ValueError('Unexpected Messages photo processor')
        anchor = '    invoke-virtual {v6, v3, v4, v2}, Landroid/graphics/Bitmap;->compress(Landroid/graphics/Bitmap$CompressFormat;ILjava/io/OutputStream;)Z'
        return replace_once(m, anchor, '    invoke-static {v4}, Lwinterx/messages/MessagePlus;->photoQuality(I)I\n'
            '    move-result v4\n' + anchor)
    contents[PHOTO] = method(contents[PHOTO], signature, photo)
