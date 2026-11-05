"""Optional normal-home Barrel contexts and exception-safe per-icon Canvas transforms."""
import re
from patch_rendering import K
from patch_snowy import DRAW

RENDER = 'smali/I1/h0.1.smali'


def wrapper(text, signature, stock, before, after, replace_once):
    name = signature.split('(')[0].rsplit(' ', 1)[1]
    descriptor = signature[signature.index('('):]
    last = 15 if name == 'k' else 12
    renamed = signature.replace(' ' + name + '(', ' ' + stock + '(')
    body = (signature + '\n    .locals 5\n' + before + '\n    move-result-object v0\n'
            if name == 'k' else signature + '\n    .locals 2\n' + before + '\n    move-result v0\n')
    body += ('    :winterx_animaper_try\n    invoke-static/range {p0 .. p' + str(last) + '}, LI1/h0;->' + stock + descriptor + '\n'
             '    :winterx_animaper_end\n' + after + '\n    return-void\n'
             '    .catchall {:winterx_animaper_try .. :winterx_animaper_end} :winterx_animaper_failure\n'
             '    :winterx_animaper_failure\n    move-exception v1\n' + after + '\n    throw v1\n.end method\n')
    return replace_once(text, signature, renamed) + '\n' + body


def apply(contents, method, replace_once):
    def context(body):
        replace_once(body, K + '\n    .locals 33', K + '\n    .locals 33')
        anchor = '    check-cast v3, LI1/b0;'
        following = r'\n(?:[ \t]*\n|[ \t]*\.line [0-9]+\n)*[ \t]*iget v9, v3, LI1/b0;->b:I'
        if len(re.findall(re.escape(anchor) + following, body)) != 1:
            raise ValueError('Unexpected normal-home Barrel context registers')
        return replace_once(body, anchor, anchor + '\n    move-object/from16 v4, p0\n'
            '    invoke-static {v4, v3}, Lwinterx/animaper/Animaper;->context(LE1/q6;LI1/b0;)V')
    text = method(contents[RENDER], K, context)
    text = method(text, DRAW, lambda body: replace_once(body, DRAW + '\n    .locals 18', DRAW + '\n    .locals 18'))
    text = wrapper(text, K, 'winterxStockK',
        '    move-object/from16 v0, p15\n    move-wide/from16 v1, p1\n'
        '    move-object/from16 v3, p7\n    move-object/from16 v4, p8\n'
        '    invoke-static/range {v0 .. v4}, Lwinterx/animaper/Animaper;->beginFrame(Landroid/graphics/Canvas;JLE1/S1;LE1/l4;)Ljava/lang/Object;',
        '    invoke-static {v0}, Lwinterx/animaper/Animaper;->endFrame(Ljava/lang/Object;)V', replace_once)
    text = wrapper(text, DRAW, 'winterxStockArtwork',
        '    invoke-static {p0, p2, p7, p8}, Lwinterx/animaper/Animaper;->beginIcon(Landroid/graphics/Canvas;LE1/i6;II)I',
        '    invoke-static {p0, v0}, Lwinterx/animaper/Animaper;->endIcon(Landroid/graphics/Canvas;I)V', replace_once)
    contents[RENDER] = text
