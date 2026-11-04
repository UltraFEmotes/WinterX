"""Opt-in SnowyHome renderer hooks. No geometry/app model/cache mutation; validate before writing."""
RENDER = 'smali/I1/h0.1.smali'
ICON = '.method public static c(LE1/a;LE1/q6;LI1/I0;Ljava/util/Map;)Landroid/graphics/Bitmap;'
LABEL = '.method public static G(Landroid/graphics/Canvas;LI1/I0;LE1/i6;Ljava/lang/String;IIZ)V'
DRAW = '.method public static E(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/i6;LI1/I0;Ljava/util/Map;Landroid/graphics/Bitmap;Ljava/lang/String;IIZZLI1/Z;Ljava/lang/String;)V'
EDIT = '.method public final winterxStockR(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;LA/o;LE1/G1;ZF)V'


def apply(contents, method, replace_once):
    text = contents[RENDER]
    # c() resolves icons in home/dock/edit/folder paths with the actual app ID.
    stock = ICON.replace(' c(', ' winterxStockIcon(')
    text = replace_once(text, ICON, stock)
    text += ('\n' + ICON + '\n    .locals 1\n'
             '    invoke-static/range {p0 .. p3}, LI1/h0;->winterxStockIcon(LE1/a;LE1/q6;LI1/I0;Ljava/util/Map;)Landroid/graphics/Bitmap;\n'
             '    move-result-object v0\n'
             '    invoke-static {p0, v0}, Lwinterx/snowy/SnowyHome;->icon(LE1/a;Landroid/graphics/Bitmap;)Landroid/graphics/Bitmap;\n'
             '    move-result-object v0\n    return-object v0\n.end method\n')
    def labels(body):
        anchor = LABEL + '\n    .locals 22'
        return replace_once(body, anchor, anchor + '\n'
            '    invoke-static {}, Lwinterx/snowy/SnowyHome;->hiddenLabels()Z\n'
            '    move-result v0\n    if-eqz v0, :winterx_snowy_labels\n'
            '    return-void\n    :winterx_snowy_labels')
    text = method(text, LABEL, labels)
    def artwork(body):
        anchor = DRAW + '\n    .locals 18'
        return replace_once(body, anchor, anchor + '\n'
            '    move-object/from16 v0, p4\n'
            '    invoke-static {v0}, Lwinterx/snowy/SnowyHome;->artwork(Ljava/util/Map;)Ljava/util/Map;\n'
            '    move-result-object v0\n    move-object/16 p4, v0')
    text = method(text, DRAW, artwork)
    def cache(body):
        anchor = EDIT + '\n    .locals 36'
        return replace_once(body, anchor, anchor + '\n'
            '    invoke-static {}, Lwinterx/snowy/SnowyHome;->enabled()Z\n'
            '    move-result v0\n    if-eqz v0, :winterx_snowy_stock_cache\n'
            '    const/4 v0, 0x0\n    move-object/16 p7, v0\n'
            '    :winterx_snowy_stock_cache')
    # Precomposed e0 artwork includes labels/badges. Bypass, never mutate or clear it.
    text = method(text, EDIT, cache)
    contents[RENDER] = text
