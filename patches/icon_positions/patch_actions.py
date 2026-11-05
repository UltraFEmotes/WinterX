"""Explicit Spring 0.8.1 SSH action accessors; use native single-archive installer, never scan an inbox."""
LAUNCHER = 'smali/com/guille/spring/LauncherActivity.smali'
MANAGER = 'smali/J1/y.1.smali'
PACKAGE = 'smali/J1/P.smali'
PATHS = (LAUNCHER, PACKAGE)

GETTER = '''
.method public final winterxSappManager()LJ1/y;
    .locals 1
    iget-object v0, p0, Lcom/guille/spring/LauncherActivity;->sappApps:LJ1/y;
    return-object v0
.end method
'''
INSTALL = '''
.method public final winterxInstallArchive(Ljava/io/File;)Ljava/lang/String;
    .locals 3
    iget-object v0, p0, LJ1/y;->g:LJ1/P;
    new-instance v1, LJ1/x;
    const/4 v2, 0x2
    invoke-direct {v1, p0, v2}, LJ1/x;-><init>(LJ1/y;I)V
    invoke-virtual {v0, p1, v1}, LJ1/P;->b(Ljava/io/File;LJ1/x;)LJ1/N;
    move-result-object v0
    iget-object v0, v0, LJ1/N;->a:LH1/m0;
    iget-object v0, v0, LH1/m0;->a:Ljava/lang/String;
    invoke-virtual {p0}, LJ1/y;->g()V
    return-object v0
.end method
'''


def apply(contents, method, replace_once):
    launcher, manager, package = contents[LAUNCHER], contents[MANAGER], contents[PACKAGE]
    for anchor, text in (('.field private sappApps:LJ1/y;', launcher),
                         ('.field public final g:LJ1/P;', manager)):
        replace_once(text, anchor, anchor)
    signature = '.method public final b(Ljava/io/File;LJ1/x;)LJ1/N;'
    method(package, signature, lambda body: replace_once(body, signature + '\n    .locals 17', signature + '\n    .locals 17'))
    method(manager, '.method public final g()V', lambda body: body)
    if 'winterxSappManager(' in launcher or 'winterxInstallArchive(' in manager:
        raise ValueError('Spring SSH actions already patched')
    contents[LAUNCHER], contents[MANAGER] = launcher + GETTER, manager + INSTALL
