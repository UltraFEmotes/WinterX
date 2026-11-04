#!/usr/bin/env python3
"""Apply the Spring 0.8.1 Ruby Settings test to an apktool-decoded APK.

This is an experimental build-time patch. It never modifies an installed app.
"""
import argparse
import re
from pathlib import Path

ROOT_MARKER = '''    .line 27
    invoke-static {v10}, Lt/i;->K(Ljava/lang/Object;)Ljava/util/List;

    move-result-object v12'''
ROOT_PATCH = '''    .line 27
    # Ruby: add the test row only when its marker is present.
    move-object/16 v113, v10
    invoke-static {}, Lruby/RubyHooks;->settingsEnabled()Z
    move-result v10
    if-eqz v10, :ruby_default_rows
    move-object/from16 v10, v17
    const-string v11, "ruby-test"
    const-string v12, "Ruby Test"
    const-string v13, "ruby-test"
    const/4 v14, 0x0
    const/4 v15, 0x0
    const/16 v16, 0x8
    invoke-static/range {v10 .. v16}, LE1/Z3;->g(LE1/Z3;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;I)LE1/V6;
    move-result-object v11
    move-object/from16 v10, v113
    filled-new-array {v10, v11}, [LE1/V6;
    move-result-object v10
    invoke-static {v10}, LN1/q;->n0([Ljava/lang/Object;)Ljava/util/List;
    move-result-object v12
    goto :ruby_rows_done
    :ruby_default_rows
    move-object/from16 v10, v113
    invoke-static {v10}, Lt/i;->K(Ljava/lang/Object;)Ljava/util/List;
    move-result-object v12
    :ruby_rows_done'''
IOS6_ROOT_MARKER = '''    .line 271
    invoke-static {v12}, Lt/i;->K(Ljava/lang/Object;)Ljava/util/List;

    move-result-object v47'''
IOS6_ROOT_PATCH = '''    .line 271
    # iOS 6 has a separate root Settings model.
    move-object/16 v113, v12
    invoke-static {}, Lruby/RubyHooks;->settingsEnabled()Z
    move-result v12
    if-eqz v12, :ruby_ios6_default_rows
    move-object/from16 v45, v3
    const-string v46, "ruby-test"
    const-string v47, "Ruby Test"
    const-string v48, "ruby-test"
    const/16 v49, 0x0
    const/16 v50, 0x0
    const/16 v51, 0x8
    invoke-static/range {v45 .. v51}, LE1/Z3;->g(LE1/Z3;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;I)LE1/V6;
    move-result-object v14
    move-object/from16 v12, v113
    filled-new-array {v12, v14}, [LE1/V6;
    move-result-object v12
    invoke-static {v12}, LN1/q;->n0([Ljava/lang/Object;)Ljava/util/List;
    move-result-object v47
    goto :ruby_ios6_rows_done
    :ruby_ios6_default_rows
    move-object/from16 v12, v113
    invoke-static {v12}, Lt/i;->K(Ljava/lang/Object;)Ljava/util/List;
    move-result-object v47
    :ruby_ios6_rows_done'''
TAP_MARKER = '''    :cond_32
    sget-object v0, LE1/f5;->a:Ljava/util/List;'''
TAP_PATCH = '''    :cond_32
    # Route the WinterX test page and actions through Spring's own UI.
    iget-object v0, v9, LE1/V6;->a:Ljava/lang/String;
    const-string v10, "ruby-test"
    invoke-virtual {v10, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :ruby_check_alert
    const-string v10, "ruby-test-page"
    invoke-virtual {v1, v10, v5}, Lx1/i1;->t3(Ljava/lang/String;LE1/L6;)V
    const/4 v0, 0x1
    return v0
    :ruby_check_alert
    iget-object v0, v9, LE1/V6;->a:Ljava/lang/String;
    const-string v10, "ruby-action-alert"
    invoke-virtual {v10, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :ruby_check_close
    iget-object v0, v1, Lx1/i1;->a:Lcom/guille/spring/LauncherActivity;
    invoke-static {v0}, Lruby/RubyHooks;->showTestAlert(Lcom/guille/spring/LauncherActivity;)V
    const/4 v0, 0x1
    return v0
    :ruby_check_close
    iget-object v0, v9, LE1/V6;->a:Ljava/lang/String;
    const-string v10, "ruby-action-close"
    invoke-virtual {v10, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :animaper_check_entry
    iget-object v0, v1, Lx1/i1;->a:Lcom/guille/spring/LauncherActivity;
    invoke-virtual {v0}, Lcom/guille/spring/LauncherActivity;->winterxGoHome()V
    const/4 v0, 0x1
    return v0
    :animaper_check_entry
    iget-object v0, v9, LE1/V6;->a:Ljava/lang/String;
    const-string v10, "winterx-animaper"
    invoke-virtual {v10, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :animaper_check_mode
    const-string v10, "winterx-animaper-page"
    invoke-virtual {v1, v10, v5}, Lx1/i1;->t3(Ljava/lang/String;LE1/L6;)V
    const/4 v0, 0x1
    return v0
    :animaper_check_mode
    iget-object v0, v9, LE1/V6;->a:Ljava/lang/String;
    const-string v10, "winterx-animaper-mode-"
    invoke-virtual {v0, v10}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :ruby_test_continue
    iget-object v0, v9, LE1/V6;->a:Ljava/lang/String;
    invoke-static {v0}, Lwinterx/animaper/AnimaperSettings;->select(Ljava/lang/String;)V
    const/4 v0, 0x1
    return v0
    :ruby_test_continue
    sget-object v0, LE1/f5;->a:Ljava/util/List;'''

PAGE_HOOK = '''
    invoke-static/range {p1 .. p1}, Lruby/RubyHooks;->settingsPage(Ljava/lang/String;)LE1/T6;
    move-result-object v0
    if-eqz v0, :winterx_stock_page
    return-object v0
    :winterx_stock_page'''
HOME_WRAPPER = '''
.method public final winterxGoHome()V
    .locals 0
    invoke-direct {p0}, Lcom/guille/spring/LauncherActivity;->onHomePressed()V
    return-void
.end method
'''

DELETE_MARKER = '''.method public static d0(Ljava/lang/String;)Z
    .locals 3'''
DELETE_PATCH = DELETE_MARKER + '''
    # Ruby is a required component of the patched Spring session.
    const-string v0, "sapp:com.ruby.manager"
    invoke-virtual {v0, p0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :winterx_delete_original
    const/4 v0, 0x0
    return v0
    :winterx_delete_original'''

BOOT_MARKER = '''    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V'''
BOOT_PATCH = BOOT_MARKER + '''
    invoke-static/range {p0 .. p0}, Lruby/RubyHooks;->boot(Landroid/app/Activity;)V'''
CONTENT_CALL = '    invoke-virtual {p0, p1}, Landroid/app/Activity;->setContentView(Landroid/view/View;)V'
# Retained for the separate 0.9 preview research patch.
CONTENT_PATCH = CONTENT_CALL + '''
    invoke-static/range {p0 .. p0}, Lruby/RubyHooks;->showBoot(Landroid/app/Activity;)V'''

UNLOCK_START = '.method public final r0()V'
UNLOCK_CALL = '    invoke-virtual {p0}, Lx1/i1;->O1()V'
UNLOCK_PATCH = UNLOCK_CALL + '''
    iget-object v0, p0, Lx1/i1;->a:Lcom/guille/spring/LauncherActivity;
    invoke-static {v0}, Lruby/RubyHooks;->showWelcome(Lcom/guille/spring/LauncherActivity;)V'''

HOOKS = '''.class public final Lruby/RubyHooks;
.super Ljava/lang/Object;

.method public static boot(Landroid/app/Activity;)V
    .locals 3
    :try_start
    invoke-virtual {p0}, Landroid/app/Activity;->getFilesDir()Ljava/io/File;
    move-result-object v0
    new-instance v1, Ljava/io/File;
    const-string v2, "ruby"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->mkdirs()Z
    new-instance v0, Ljava/io/File;
    const-string v2, "boot-ok-v1"
    invoke-direct {v0, v1, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v0}, Ljava/io/File;->createNewFile()Z
    :try_end
    return-void
    .catch Ljava/lang/Exception; {:try_start .. :try_end} :failure
    :failure
    move-exception v0
    return-void
.end method

.method public static settingsEnabled()Z
    .locals 3
    :try_start
    invoke-static {}, Lruby/RubyHooks;->safeMode()Z
    move-result v0
    if-nez v0, :disabled
    invoke-static {}, Landroid/app/ActivityThread;->currentApplication()Landroid/app/Application;
    move-result-object v0
    if-eqz v0, :disabled
    invoke-virtual {v0}, Landroid/app/Application;->getFilesDir()Ljava/io/File;
    move-result-object v0
    new-instance v1, Ljava/io/File;
    const-string v2, "ruby/settings-test.enabled"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->isFile()Z
    move-result v0
    :try_end
    return v0
    .catch Ljava/lang/Exception; {:try_start .. :try_end} :failure
    :failure
    move-exception v0
    :disabled
    const/4 v0, 0x0
    return v0
.end method

.method public static safeMode()Z
    .locals 3
    :try_start
    invoke-static {}, Landroid/app/ActivityThread;->currentApplication()Landroid/app/Application;
    move-result-object v0
    if-eqz v0, :safe
    invoke-virtual {v0}, Landroid/app/Application;->getFilesDir()Ljava/io/File;
    move-result-object v0
    new-instance v1, Ljava/io/File;
    const-string v2, "ruby/safe-mode.enabled"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->isFile()Z
    move-result v0
    :try_end
    return v0
    .catch Ljava/lang/Exception; {:try_start .. :try_end} :failure
    :failure
    move-exception v0
    :safe
    const/4 v0, 0x1
    return v0
.end method

# Construct normal Spring Settings models, so styling and Back work naturally.
.method public static settingsPage(Ljava/lang/String;)LE1/T6;
    .locals 10
    const-string v0, "ruby-test-page"
    invoke-virtual {v0, p0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :missing
    invoke-static {}, Lruby/RubyHooks;->settingsEnabled()Z
    move-result v0
    if-eqz v0, :missing
    sget-object v0, LE1/Z3;->a:LE1/Z3;
    const-string v1, "ruby-action-alert"
    const-string v2, "Show Test Alert"
    const/4 v3, 0x0
    const/4 v4, 0x0
    const/4 v5, 0x0
    const/16 v6, 0x18
    invoke-static/range {v0 .. v6}, LE1/Z3;->g(LE1/Z3;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;I)LE1/V6;
    move-result-object v7
    const-string v1, "ruby-action-close"
    const-string v2, "Close Settings"
    invoke-static/range {v0 .. v6}, LE1/Z3;->g(LE1/Z3;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;I)LE1/V6;
    move-result-object v8
    filled-new-array {v7, v8}, [LE1/V6;
    move-result-object v0
    invoke-static {v0}, Ljava/util/Arrays;->asList([Ljava/lang/Object;)Ljava/util/List;
    move-result-object v5
    new-instance v0, LE1/W6;
    const-string v1, "TEST ACTIONS"
    const/4 v2, 0x0
    const/4 v3, 0x0
    const/4 v4, 0x0
    invoke-direct/range {v0 .. v5}, LE1/W6;-><init>(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/util/List;)V
    filled-new-array {v0}, [LE1/W6;
    move-result-object v0
    invoke-static {v0}, Ljava/util/Arrays;->asList([Ljava/lang/Object;)Ljava/util/List;
    move-result-object v2
    new-instance v0, LE1/T6;
    const-string v1, "ruby-test-page"
    const-string v3, "Ruby Test"
    invoke-direct {v0, v1, v3, v2}, LE1/T6;-><init>(Ljava/lang/String;Ljava/lang/String;Ljava/util/List;)V
    return-object v0
    :missing
    invoke-static {p0}, Lwinterx/animaper/AnimaperSettings;->page(Ljava/lang/String;)LE1/T6;
    move-result-object v0
    return-object v0
.end method

.method public static showTestAlert(Lcom/guille/spring/LauncherActivity;)V
    .locals 7
    invoke-static {p0}, Lcom/guille/spring/LauncherActivity;->access$alertView(Lcom/guille/spring/LauncherActivity;)Lx1/J;
    move-result-object v1
    if-eqz v1, :done
    const-string v2, "Ruby Test"
    const-string v3, "This is a test alert from WinterX."
    const-string v0, "OK"
    filled-new-array {v0}, [Ljava/lang/String;
    move-result-object v4
    const/4 v5, 0x0
    new-instance v6, Lruby/Noop;
    invoke-direct {v6}, Lruby/Noop;-><init>()V
    invoke-virtual/range {v1 .. v6}, Lx1/J;->n(Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;ILZ1/l;)Lx1/H;
    :done
    return-void
.end method

.method public static showWelcome(Lcom/guille/spring/LauncherActivity;)V
    .locals 8
    :try_start
    invoke-virtual {p0}, Landroid/app/Activity;->getFilesDir()Ljava/io/File;
    move-result-object v0
    new-instance v7, Ljava/io/File;
    const-string v1, "ruby/welcome-shown-v1"
    invoke-direct {v7, v0, v1}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v7}, Ljava/io/File;->isFile()Z
    move-result v0
    if-nez v0, :done
    invoke-static {p0}, Lcom/guille/spring/LauncherActivity;->access$alertView(Lcom/guille/spring/LauncherActivity;)Lx1/J;
    move-result-object v1
    if-eqz v1, :done
    const-string v2, "WinterX"
    const-string v3, "Welcome to WinterX, this project is still in beta, feel free to give suggestions and bug reports from the GitHub"
    const-string v0, "OK"
    filled-new-array {v0}, [Ljava/lang/String;
    move-result-object v4
    const/4 v5, 0x0
    new-instance v6, Lruby/Noop;
    invoke-direct {v6}, Lruby/Noop;-><init>()V
    invoke-virtual/range {v1 .. v6}, Lx1/J;->n(Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;ILZ1/l;)Lx1/H;
    invoke-virtual {v7}, Ljava/io/File;->createNewFile()Z
    :done
    :try_end
    return-void
    .catch Ljava/lang/Exception; {:try_start .. :try_end} :failure
    :failure
    move-exception v0
    return-void
.end method

.method public static openAsset(Landroid/content/res/AssetManager;Ljava/lang/String;)Ljava/io/InputStream;
    .locals 4
    :try_start
    invoke-static {}, Lruby/RubyHooks;->safeMode()Z
    move-result v0
    if-nez v0, :original
    const-string v0, "ios4/uikit/UINavigationBar"
    invoke-virtual {p1, v0}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result v0
    if-nez v0, :candidate
    const-string v0, "ios6/uikit/UINavigationBar"
    invoke-virtual {p1, v0}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :original
    :candidate
    const-string v0, ".."
    invoke-virtual {p1, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v0
    if-nez v0, :original
    const-string v0, ".png"
    invoke-virtual {p1, v0}, Ljava/lang/String;->endsWith(Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :original
    invoke-static {}, Landroid/app/ActivityThread;->currentApplication()Landroid/app/Application;
    move-result-object v0
    if-eqz v0, :original
    invoke-virtual {v0}, Landroid/app/Application;->getFilesDir()Ljava/io/File;
    move-result-object v0
    new-instance v1, Ljava/io/File;
    const-string v2, "ruby/ui-colors.enabled"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->isFile()Z
    move-result v2
    if-eqz v2, :original
    new-instance v1, Ljava/io/File;
    const-string v2, "ruby/theme"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    new-instance v0, Ljava/io/File;
    invoke-direct {v0, v1, p1}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v0}, Ljava/io/File;->isFile()Z
    move-result v1
    if-eqz v1, :original
    new-instance v1, Ljava/io/FileInputStream;
    invoke-direct {v1, v0}, Ljava/io/FileInputStream;-><init>(Ljava/io/File;)V
    :try_end
    return-object v1
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :failure
    :failure
    move-exception v0
    :original
    invoke-virtual {p0, p1}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;
    move-result-object v0
    return-object v0
.end method

.method public static showBoot(Landroid/app/Activity;)V
    .locals 6
    const/4 v1, 0x0
    :try_start
    new-instance v1, Landroid/widget/TextView;
    invoke-direct {v1, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V
    const-string v0, "WinterX\\nby WeirdMM"
    invoke-virtual {v1, v0}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V
    const/4 v0, -0x1
    invoke-virtual {v1, v0}, Landroid/widget/TextView;->setTextColor(I)V
    const/high16 v0, -0x1000000
    invoke-virtual {v1, v0}, Landroid/view/View;->setBackgroundColor(I)V
    const/16 v0, 0x11
    invoke-virtual {v1, v0}, Landroid/widget/TextView;->setGravity(I)V
    const/high16 v0, 0x41c00000
    invoke-virtual {v1, v0}, Landroid/widget/TextView;->setTextSize(F)V
    new-instance v2, Landroid/view/ViewGroup$LayoutParams;
    const/4 v0, -0x1
    invoke-direct {v2, v0, v0}, Landroid/view/ViewGroup$LayoutParams;-><init>(II)V
    new-instance v3, Lruby/BootDismiss;
    invoke-direct {v3, v1}, Lruby/BootDismiss;-><init>(Landroid/view/View;)V
    invoke-virtual {p0, v1, v2}, Landroid/app/Activity;->addContentView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V
    const-wide/16 v4, 0x9c4
    invoke-virtual {v1, v3, v4, v5}, Landroid/view/View;->postDelayed(Ljava/lang/Runnable;J)Z
    move-result v0
    if-nez v0, :done
    invoke-virtual {v3}, Lruby/BootDismiss;->run()V
    :done
    :try_end
    return-void
    .catch Ljava/lang/Exception; {:try_start .. :try_end} :failure
    :failure
    move-exception v0
    if-eqz v1, :failure_done
    :try_cleanup
    new-instance v2, Lruby/BootDismiss;
    invoke-direct {v2, v1}, Lruby/BootDismiss;-><init>(Landroid/view/View;)V
    invoke-virtual {v2}, Lruby/BootDismiss;->run()V
    :try_cleanup_end
    :failure_done
    return-void
    .catch Ljava/lang/Exception; {:try_cleanup .. :try_cleanup_end} :cleanup_failure
    :cleanup_failure
    move-exception v0
    return-void
.end method
'''

NOOP = '''.class public final Lruby/Noop;
.super Ljava/lang/Object;
.implements LZ1/l;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public final a(Ljava/lang/Object;)Ljava/lang/Object;
    .locals 1
    sget-object v0, LM1/h;->a:LM1/h;
    return-object v0
.end method
'''

BOOT_DISMISS = '''.class public final Lruby/BootDismiss;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;
.field private final view:Landroid/view/View;

.method public constructor <init>(Landroid/view/View;)V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    iput-object p1, p0, Lruby/BootDismiss;->view:Landroid/view/View;
    return-void
.end method

.method public final run()V
    .locals 2
    iget-object v0, p0, Lruby/BootDismiss;->view:Landroid/view/View;
    invoke-virtual {v0}, Landroid/view/View;->getParent()Landroid/view/ViewParent;
    move-result-object v1
    instance-of v0, v1, Landroid/view/ViewGroup;
    if-eqz v0, :done
    check-cast v1, Landroid/view/ViewGroup;
    iget-object v0, p0, Lruby/BootDismiss;->view:Landroid/view/View;
    invoke-virtual {v1, v0}, Landroid/view/ViewGroup;->removeView(Landroid/view/View;)V
    :done
    return-void
.end method
'''


def patched(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f'{path}: expected one patch location; found {text.count(old)}')
    return text.replace(old, new, 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('decoded', type=Path)
    a = p.parse_args()
    root = a.decoded / 'smali/E1/Z3.smali'
    tap = a.decoded / 'smali/x1.1/i1.1.smali'
    activity = a.decoded / 'smali/com/guille/spring/LauncherActivity.smali'
    hook = a.decoded / 'smali/ruby/RubyHooks.smali'
    noop = a.decoded / 'smali/ruby/Noop.smali'
    dismiss = a.decoded / 'smali/ruby/BootDismiss.smali'
    # Validate all patch locations before modifying files.
    page_files = [(a.decoded / 'smali/E1/B0.smali', '.method public a(Ljava/lang/String;)LE1/T6;\n    .locals 1'), (a.decoded / 'smali/E1/b4.1.smali', '.method public final a(Ljava/lang/String;)LE1/T6;\n    .locals 56')]
    page_changes = []
    for path, marker in page_files:
        content = patched(path, marker, marker + PAGE_HOOK)
        begin = content.index(marker)
        end = content.index('.end method', begin)
        method_text = content[begin:end]
        def decorate(match):
            register = match.group(1)
            return ('    invoke-static/range {' + register + ' .. ' + register + '}, Lwinterx/animaper/AnimaperSettings;->decorate(LE1/T6;)LE1/T6;\n'
                    '    move-result-object ' + register + '\n    return-object ' + register)
        method_text, count = re.subn(r'^    return-object ([vp]\d+)$', decorate, method_text, flags=re.M)
        if count < 2: raise ValueError('Settings page return hooks were not found')
        page_changes.append((path, content[:begin] + method_text + content[end:]))
    new_root = patched(root, ROOT_MARKER, ROOT_PATCH)
    if new_root.count(IOS6_ROOT_MARKER) != 1:
        raise ValueError('Expected exactly one iOS 6 Settings patch location')
    new_root = new_root.replace(IOS6_ROOT_MARKER, IOS6_ROOT_PATCH, 1)
    new_tap = patched(tap, TAP_MARKER, TAP_PATCH)
    if new_tap.count(DELETE_MARKER) != 1:
        raise ValueError('Expected exactly one app deletion check')
    new_tap = new_tap.replace(DELETE_MARKER, DELETE_PATCH, 1)
    start = new_tap.index(UNLOCK_START)
    end = new_tap.index('.end method', start)
    unlock = new_tap[start:end]
    if unlock.count(UNLOCK_CALL) != 1:
        raise ValueError('Expected exactly one unlock completion call')
    new_tap = new_tap[:start] + unlock.replace(UNLOCK_CALL, UNLOCK_PATCH, 1) + new_tap[end:]
    new_activity = patched(activity, BOOT_MARKER, BOOT_PATCH) + HOME_WRAPPER
    start = new_activity.index('.method public onCreate(Landroid/os/Bundle;)V')
    end = new_activity.index('.end method', start)
    oncreate = new_activity[start:end]
    if oncreate.count(CONTENT_CALL) != 3:
        raise ValueError('Expected three launcher content setup paths')
    # 0.8.1 uses replacement splash assets; an overlay here is covered by Spring.
    new_activity = new_activity[:start] + oncreate + new_activity[end:]
    if hook.exists() or noop.exists() or dismiss.exists():
        raise ValueError('Ruby hook already exists')
    for path, content in page_changes:
        path.write_text(content)
    root.write_text(new_root)
    tap.write_text(new_tap)
    activity.write_text(new_activity)
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(HOOKS)
    noop.write_text(NOOP)
    dismiss.write_text(BOOT_DISMISS)
    pattern = re.compile(r'invoke-virtual(/range)? (\{[^}]+\}), Landroid/content/res/AssetManager;->open\(Ljava/lang/String;\)Ljava/io/InputStream;')
    count = 0
    for path in (a.decoded / 'smali').rglob('*.smali'):
        if path == hook:
            continue
        text = path.read_text()
        text, n = pattern.subn(lambda m: 'invoke-static' + (m.group(1) or '') + ' ' + m.group(2) + ', Lruby/RubyHooks;->openAsset(Landroid/content/res/AssetManager;Ljava/lang/String;)Ljava/io/InputStream;', text)
        if n:
            path.write_text(text)
            count += n
    if count != 43:
        raise ValueError('Unexpected asset loader count: ' + str(count))
    print('Patched', count, 'asset loading calls')
    print('Applied experimental Settings test patch to decoded APK')


if __name__ == '__main__':
    main()
