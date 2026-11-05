"""Spring 0.8.1 cache eligibility and sparse folder backgrounds; no persisted/native-cell changes."""
RENDER = 'smali/I1/h0.1.smali'
GEOMETRY = 'smali/I1/j1.smali'
TILES = 'smali/A/o.smali'
LAYERS = 'smali/I1/Y.smali'
SCENE = 'smali/I1/T0.smali'
QUEUED = 'smali/I1/R0.smali'
PATHS = (TILES, LAYERS, SCENE, QUEUED)
K = '.method public static final k(LE1/q6;JLE1/i6;FILI1/d0;LE1/S1;LE1/l4;LA/o;LI1/I0;Ljava/util/Map;Ljava/util/concurrent/ConcurrentHashMap;Landroid/graphics/Paint;FLandroid/graphics/Canvas;)V'
FAST = '.method public static o(Landroid/graphics/Canvas;LE1/q6;LI1/I0;Ljava/util/Map;Ljava/util/Map;LA/o;Landroid/graphics/Bitmap;Landroid/graphics/Bitmap;FFFLI1/d0;FJFLI1/c0;I)Z'
UPPER = '.method public static B(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;LI1/X;LI1/Z;F)V'
LOWER = '.method public final x(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;Landroid/graphics/Bitmap;LI1/X;LI1/Z;F)V'
FOLDER = '.method public static p(LE1/q6;LE1/S1;)LI1/X;'


def apply(contents, method, replace_once):
    def prepend(signature, locals_count, body):
        anchor = signature + '\n    .locals ' + str(locals_count)
        return lambda text: replace_once(text, anchor, anchor + '\n' + body)

    def guard(signature, locals_count, policy, result):
        body = ('    invoke-static {}, Lwinterx/layout/RenderPolicy;->' + policy + '()Z\n'
                '    move-result v0\n    if-nez v0, :winterx_native_cache\n' + result + '\n'
                '    :winterx_native_cache')
        return prepend(signature, locals_count, body)

    # Resolve the complete native list before any row filtering or U1.a indexing.
    # FreeMe returns copies in the same list order; dock/folder members stay native.
    for path, signature, receiver, page in ((RENDER, UPPER, 'v0', 'v3'),
                                            (RENDER, LOWER, 'v3', 'v1'),
                                            (GEOMETRY, FOLDER, 'v0', 'v6')):
        old = '    invoke-virtual {' + receiver + ', ' + page + '}, LE1/q6;->d(I)Ljava/util/List;'
        new = '    invoke-static {' + receiver + '}, Lwinterx/layout/FreeMe;->folderEntries(LE1/q6;)Ljava/util/List;'
        contents[path] = method(contents[path], signature, lambda body, old=old, new=new: replace_once(body, old, new))

    contents[RENDER] = method(contents[RENDER], K, prepend(K, 33,
        '    move-object/from16 v0, p9\n'
        '    invoke-static {v0}, Lwinterx/layout/RenderPolicy;->tiles(LA/o;)LA/o;\n'
        '    move-result-object v0\n    move-object/16 p9, v0'))
    contents[RENDER] = method(contents[RENDER], FAST, guard(FAST, 33, 'tilesAllowed',
        '    const/4 v0, 0x0\n    return v0'))

    # Producer and consumer gates both matter: hooked drawing must never warm a
    # themed native tile/dock composite which can leak after removal/Safe Mode.
    for signature, locals_count, result in (
        ('.method public m(LE1/i6;LI1/I0;Ljava/util/Map;Landroid/graphics/Bitmap;Ljava/lang/String;Ljava/lang/String;ZZLjava/lang/String;)LI1/e0;', 22, '    const/4 v0, 0x0\n    return-object v0'),
        ('.method public i(LE1/i6;LI1/I0;LE1/q6;Ljava/util/Map;LZ1/l;)LC1/D1;', 16, '    const/4 v0, 0x0\n    return-object v0'),
        ('.method public v(LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;Landroid/graphics/Paint;)V', 19, '    return-void')):
        contents[TILES] = method(contents[TILES], signature, guard(signature, locals_count, 'tilesAllowed', result))

    scene = '.method public static o(LI1/T0;Landroid/graphics/Canvas;LE1/q6;LI1/I0;FFLI1/d0;LE1/S1;FFLjava/lang/Long;JFI)Z'
    def scene_tiles(body):
        anchor = '    iget-object v4, v0, LI1/T0;->Z:LA/o;'
        return replace_once(body, anchor, anchor + '\n'
            '    invoke-static {v4}, Lwinterx/layout/RenderPolicy;->tiles(LA/o;)LA/o;\n    move-result-object v4')
    # T0.o is a complete native renderer: suppress only its later tile source,
    # not the whole method or its dock/native fallback.
    contents[SCENE] = method(contents[SCENE], scene, scene_tiles)

    for signature, locals_count, result in (
        ('.method public final c(LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;Landroid/graphics/Bitmap;)Z', 17, '    const/4 v0, 0x0\n    return v0'),
        ('.method public static d(LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Landroid/graphics/Bitmap;)Ljava/util/List;', 19, '    const/4 v0, 0x0\n    return-object v0'),
        ('.method public final b(ILE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;Landroid/graphics/Bitmap;LI1/X;)V', 15, '    return-void')):
        contents[LAYERS] = method(contents[LAYERS], signature, guard(signature, locals_count, 'folderLayersAllowed', result))

    prewarm = '.method public final P(LE1/q6;)V'
    def prewarm_gate(body):
        anchor = '    :cond_0\n    invoke-virtual {p1}, LE1/q6;->b()I'
        return replace_once(body, anchor, '    :cond_0\n'
            '    invoke-static {}, Lwinterx/layout/RenderPolicy;->folderLayersAllowed()Z\n'
            '    move-result v0\n    if-nez v0, :winterx_folder_prewarm\n    return-void\n'
            '    :winterx_folder_prewarm\n    invoke-virtual {p1}, LE1/q6;->b()I')
    # Keep the existing open-folder G bookkeeping above :cond_0.
    contents[SCENE] = method(contents[SCENE], prewarm, prewarm_gate)
    def queued_gate(body):
        anchor = '    iput-boolean v2, v0, LI1/T0;->R:Z'
        return replace_once(body, anchor, anchor + '\n'
            '    invoke-static {}, Lwinterx/layout/RenderPolicy;->folderLayersAllowed()Z\n'
            '    move-result v2\n    if-nez v2, :winterx_queued_folder\n'
            '    const/4 v2, 0x0\n    iput-object v2, v0, LI1/T0;->Q:LE1/q6;\n    return-void\n'
            '    :winterx_queued_folder')
    contents[QUEUED] = method(contents[QUEUED], '.method public final run()V', queued_gate)
