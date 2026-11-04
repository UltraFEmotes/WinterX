"""Version-specific experimental dock hooks. All anchors validate before any files are written."""
import re

DOCK_RENDER = 'smali/I1/j1.smali'
MODEL = 'smali/E1/t.1.smali'


def apply(contents, method, replace_once):
    spring = 'smali/x1.1/i1.1.smali'
    renderer = 'smali/I1/h0.1.smali'

    def dock_location(m):
        anchor = '.method public final f0(I)LM1/b;\n    .locals 4'
        body = ('\n    invoke-static {p0}, Lwinterx/layout/DockIn;->geometry(Lx1/i1;)Z\n'
                '    move-result v0\n    if-eqz v0, :winterx_stock_dock_location\n'
                '    iget-object v0, p0, Lx1/i1;->e:LE1/i6;\n'
                '    iget-object v1, p0, Lx1/i1;->M1:Ljava/util/List;\n'
                '    invoke-interface {v1}, Ljava/util/List;->size()I\n    move-result v1\n'
                '    invoke-static {v0, p1, v1}, Lwinterx/layout/DockIn;->location(LE1/i6;II)LM1/b;\n'
                '    move-result-object v0\n    return-object v0\n    :winterx_stock_dock_location')
        return replace_once(m, anchor, anchor + body)
    contents[spring] = method(contents[spring], '.method public final f0(I)LM1/b;', dock_location)

    def dock_touch(m):
        anchor = '    :cond_5\n'
        body = ('    invoke-static {p0}, Lwinterx/layout/DockIn;->geometry(Lx1/i1;)Z\n'
                '    move-result v0\n    if-eqz v0, :winterx_stock_dock_touch\n'
                '    invoke-static {p0, p1, p2}, Lwinterx/layout/DockIn;->hit(Lx1/i1;FF)LE1/A0;\n'
                '    move-result-object v0\n    return-object v0\n    :winterx_stock_dock_touch\n')
        return replace_once(m, anchor, anchor + body)
    contents[spring] = method(contents[spring], '.method public final o1(FF)LE1/A0;', dock_touch)

    def dock_delete(m):
        anchor = '    :cond_1\n'
        body = ('    invoke-static {p0}, Lwinterx/layout/DockIn;->geometry(Lx1/i1;)Z\n'
                '    move-result v0\n    if-eqz v0, :winterx_stock_dock_delete\n'
                '    invoke-static {p0, p1, p2}, Lwinterx/layout/DockIn;->deleteHit(Lx1/i1;FF)Ljava/lang/String;\n'
                '    move-result-object v0\n    return-object v0\n    :winterx_stock_dock_delete\n')
        return replace_once(m, anchor, anchor + body)
    contents[spring] = method(contents[spring], '.method public final I(FF)Ljava/lang/String;', dock_delete)

    def normalize(m):
        return replace_once(m, '    const/4 v5, 0x4',
            '    invoke-static {v2}, Lwinterx/layout/DockIn;->normalizeCapacity(Ljava/util/List;)I\n    move-result v5')
    contents[MODEL] = method(contents[MODEL], '.method public static R(LE1/i2;LE1/i2;Ljava/util/LinkedHashMap;I)LE1/i2;', normalize)

    def reorder(m):
        return replace_once(m, '    const/4 v5, 0x4',
            '    invoke-static {v7}, Lwinterx/layout/DockIn;->editCapacity(LE1/O1;)I\n    move-result v5')
    contents[spring] = method(contents[spring], '.method public final a6(J)Z', reorder)

    def legacy(m):
        m = replace_once(m, '    .locals 30', '    .locals 31')
        anchor = '    iget v0, v7, LE1/i6;->j:I'
        begin = ('    invoke-static {v9, v11, v3, v4, v2}, Lwinterx/layout/DockIn;->beginLegacy(Landroid/graphics/Canvas;LE1/q6;III)I\n'
                 '    move-result v30\n')
        m = replace_once(m, anchor, begin + anchor)
        anchor = '    :goto_b\n'
        end = ('    move-object/from16 v0, p0\n    move/from16 v1, v30\n'
               '    invoke-static {v0, v1}, Lwinterx/layout/DockIn;->endIcon(Landroid/graphics/Canvas;I)V\n')
        return replace_once(m, anchor, anchor + end)
    signature = '.method public static e(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/q6;Ljava/util/concurrent/ConcurrentHashMap;Landroid/graphics/Bitmap;Ljava/util/Map;LI1/I0;Ljava/util/Map;)V'
    contents[DOCK_RENDER] = method(contents[DOCK_RENDER], signature, legacy)

    def native(m):
        m = replace_once(m, '    .locals 30', '    .locals 34')
        begin = ('    move-object/from16 v30, p0\n    move-object/from16 v31, p2\n'
                 '    add-int/lit8 v32, v20, -0x1\n'
                 '    invoke-static/range {v30 .. v32}, Lwinterx/layout/DockIn;->beginNative(Landroid/graphics/Canvas;LE1/q6;I)I\n'
                 '    move-result v33\n')
        end = ('\n    move/from16 v31, v33\n'
               '    invoke-static/range {v30 .. v31}, Lwinterx/layout/DockIn;->endIcon(Landroid/graphics/Canvas;I)V')
        for sig in (
            '    invoke-static/range {v0 .. v6}, LI1/h0;->L(Landroid/graphics/Canvas;Landroid/graphics/Paint;Ljava/util/Map;Landroid/graphics/Bitmap;IIF)V',
            '    invoke-static/range {v0 .. v12}, LI1/h0;->E(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/i6;LI1/I0;Ljava/util/Map;Landroid/graphics/Bitmap;Ljava/lang/String;IIZZLI1/Z;Ljava/lang/String;)V'):
            m = replace_once(m, sig, begin + sig + end)
        return m
    signature = '.method public static p(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/q6;LI1/I0;Ljava/util/Map;Ljava/util/Map;FFF)V'
    contents[renderer] = method(contents[renderer], signature, native)
