#!/usr/bin/env python3
"""Relay Ruby's local package requests to Spring's Mac.APK inbox."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile
import time

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / 'SpringSDK-r10' / 'tools' / 'spring_pack.py'
DEFAULT_BASE = Path.home() / 'Library/Application Support/MacApk/com.guille.spring'
APP_ID = 'com.ruby.manager'
JAILBREAK_ID = 'com.ruby.jailbreak'
ID = re.compile(r'^[0-9]+-[0-9]+$')
class _SDK:
    """Only .sapp operations need the separately obtained Spring SDK, not tweak/file requests."""
    module = None

    def __getattr__(self, name):
        if self.module is None:
            if not SDK.is_file():
                raise RuntimeError('Spring SDK r10 is required for .sapp operations; see README.md')
            spec = importlib.util.spec_from_file_location('spring_pack', SDK)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.module = module
        return getattr(self.module, name)


pack = _SDK()


def locations(base):
    data = base / 'data/data/com.guille.spring_0.8.1/files/sapps-data' / APP_ID / 'files'
    inbox = base / 'sdcard/Android/data/com.guille.spring/files/sapps-inbox'
    return data, inbox


def jailbreak_data(base):
    return base / 'data/data/com.guille.spring_0.8.1/files/sapps-data' / JAILBREAK_ID / 'files'


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value), encoding='utf-8')
    os.replace(temp, path)


def same_content(a, b):
    def digest(path):
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        return h.digest()
    return a.stat().st_size == b.stat().st_size and digest(a) == digest(b)


def running_engine():
    """A receipt alone or another launcher alongside the overlay never proves capability."""
    if str(ROOT / 'patches') not in sys.path: sys.path.insert(0, str(ROOT / 'patches'))
    import macapk_controls
    import macapk_jailbreak
    import tweak_runtime
    return tweak_runtime.active_engine(macapk_jailbreak.STATE, lambda pid, apk, root:
        macapk_controls.spring_pids() == [pid] and macapk_controls.is_overlay_process(pid, apk, root))


def operation_engine():
    """Keep explicitly requested Safe Mode/legacy operations on the verified current engine."""
    apk = running_engine()
    import macapk_jailbreak
    if apk is not None:
        sha = macapk_jailbreak.digest(apk)
        if sha in (macapk_jailbreak.PATCH_SHA, macapk_jailbreak.LOCAL_ALPHA8_SHA, macapk_jailbreak.LOCAL_SNOWY_SHA,
                   macapk_jailbreak.BRIDGELESS_ALPHA4_SHA, macapk_jailbreak.BRIDGELESS_ALPHA2_SHA):
            return apk, sha
    # Existing verification in safe_mode refuses this fallback unless it really is running.
    return macapk_jailbreak.PATCHED, macapk_jailbreak.PATCH_SHA


def app_lifecycle(base, inbox):
    if str(ROOT / 'patches') not in sys.path:
        sys.path.insert(0, str(ROOT / 'patches'))
    import macapk_controls
    import macapk_jailbreak
    import sapp_lifecycle
    hot_install = False
    try:
        with zipfile.ZipFile(macapk_jailbreak.PATCHED) as apk:
            hot_install = b'winterx/runtime/InboxMonitor' in apk.read('classes.dex')
    except (OSError, KeyError, zipfile.BadZipFile):
        pass
    return sapp_lifecycle.Lifecycle(base / 'data/data/com.guille.spring_0.8.1/files', inbox,
        ROOT / '.ruby-state/app-packages', pack.check_zip, lambda: bool(macapk_controls.spring_pids()), hot_install)


def process(request, data, inbox, base=DEFAULT_BASE):
    if not ID.fullmatch(request.stem):
        return
    result = data / 'results' / (request.stem + '.json')
    if result.exists():
        return
    try:
        record = json.loads(request.read_text(encoding='utf-8'))
        if record.get('id') != request.stem:
            raise ValueError('Invalid request ID')
        if record.get('action') in ('queue_app_install', 'queue_app_remove'):
            if record.get('appId') != 'com.winterx.iexplored':
                raise ValueError('This WinterX version does not provide that app')
            lifecycle = app_lifecycle(base, inbox)
            if record['action'] == 'queue_app_install':
                with tempfile.TemporaryDirectory(prefix='winterx-sapp-') as directory:
                    archive = Path(directory) / 'IExplored.sapp'
                    pack.pack(str(ROOT / 'IExplored'), str(archive))
                    reply = lifecycle.queue_install(record['appId'], archive)
            else:
                reply = lifecycle.queue_remove(record['appId'])
            reply.update(ok=True, action=record['action'])
            atomic_json(result, reply)
            return
        if record.get('action') in ('scan_packages', 'install_package', 'remove_package', 'add_repository', 'remove_repository', 'refresh_repositories'):
            if str(ROOT / 'patches') not in sys.path:
                sys.path.insert(0, str(ROOT / 'patches'))
            import macapk_jailbreak
            import safe_mode
            import ruby_packages
            action = record['action']
            def apply_settings(enabled):
                apk, sha = operation_engine()
                return safe_mode.set_marker_and_respring(macapk_jailbreak.DATA, macapk_jailbreak.STATE,
                    apk, sha, enabled,
                    'settings-test.enabled', 'Settings test')
            def apply_extra(marker, label, enabled):
                apk, sha = operation_engine()
                if marker == 'ui-colors.enabled' and enabled:
                    import ruby_theme
                    ruby_theme.stage(macapk_jailbreak.DATA)
                return safe_mode.set_marker_and_respring(macapk_jailbreak.DATA, macapk_jailbreak.STATE,
                    apk, sha, enabled, marker, label)
            ruby_data = macapk_jailbreak.DATA / 'files/ruby'
            extra_hooks = {
                'test.colors': (ruby_data / 'ui-colors.enabled', lambda enabled: apply_extra('ui-colors.enabled', 'Color test', enabled)),
                'test.icons': (ruby_data / 'free-icons.enabled', lambda enabled: apply_extra('free-icons.enabled', 'Icon placement test', enabled)),
            }
            import animaper
            import tweak_runtime
            import macapk_controls
            engine = running_engine()
            if engine is not None and animaper.supported_by(engine):
                extra_hooks['tweak.animaper'] = (ruby_data / 'animaper.enabled', lambda enabled:
                    safe_mode.set_live_animaper(macapk_jailbreak.DATA, macapk_jailbreak.STATE, engine,
                        macapk_jailbreak.digest(engine), enabled))
            if engine is not None and tweak_runtime.coloredbar_supported_by(engine):
                extra_hooks['tweak.coloredbar'] = (ruby_data / 'coloredbar.enabled', lambda enabled:
                    safe_mode.set_live_tweak(macapk_jailbreak.DATA, macapk_jailbreak.STATE, engine,
                        macapk_jailbreak.digest(engine), enabled, 'coloredbar.enabled', 'ColoredBar'))
            if engine is not None and tweak_runtime.freeme_supported_by(engine):
                extra_hooks['tweak.freeme'] = (ruby_data / 'freeme.enabled', lambda enabled:
                    safe_mode.set_live_tweak(macapk_jailbreak.DATA, macapk_jailbreak.STATE, engine,
                        macapk_jailbreak.digest(engine), enabled, 'freeme.enabled', 'FreeMe'))
            if engine is not None and tweak_runtime.dockin_supported_by(engine):
                extra_hooks['tweak.dockin'] = (ruby_data / 'dockin.enabled', lambda enabled:
                    safe_mode.set_live_tweak(macapk_jailbreak.DATA, macapk_jailbreak.STATE, engine,
                        macapk_jailbreak.digest(engine), enabled, 'dockin.enabled', 'DockIn'))
            if engine is not None and tweak_runtime.snowyhome_supported_by(engine):
                extra_hooks['tweak.snowyhome'] = (ruby_data / 'snowyhome.enabled', lambda enabled:
                    safe_mode.set_live_tweak(macapk_jailbreak.DATA, macapk_jailbreak.STATE, engine,
                        macapk_jailbreak.digest(engine), enabled, 'snowyhome.enabled', 'SnowyHome'))
            if engine is not None and tweak_runtime.ssh_supported_by(engine):
                extra_hooks['tweak.ssh'] = (ruby_data / 'ssh.enabled', lambda enabled:
                    safe_mode.set_live_tweak(macapk_jailbreak.DATA, macapk_jailbreak.STATE, engine,
                        macapk_jailbreak.digest(engine), enabled, 'ssh.enabled', 'SSH'))
            if engine is not None and tweak_runtime.messageplus_supported_by(engine):
                extra_hooks['tweak.messageplus'] = (ruby_data / 'messageplus.enabled', lambda enabled:
                    safe_mode.set_live_tweak(macapk_jailbreak.DATA, macapk_jailbreak.STATE, engine,
                        macapk_jailbreak.digest(engine), enabled, 'messageplus.enabled', 'Message+'))
            packages = ruby_packages.Packages(data, ruby_data / 'settings-test.enabled', apply_settings,
                                              extra_hooks=extra_hooks,
                                              tweak_root=macapk_jailbreak.DATA / 'files' / 'winterx-tweaks',
                                              supported_tweaks=engine is not None and tweak_runtime.supported_by(engine),
                                              supported_capabilities=('home.read', 'home.grid') if engine is not None and tweak_runtime.home_supported_by(engine) else ())
            if action in ('add_repository', 'remove_repository', 'refresh_repositories'):
                import ruby_repositories
                repos = ruby_repositories.Repositories(data, packages, builtin_root=ROOT / 'builtin-repo')
                if action == 'add_repository':
                    repos.add(record.get('url', ''))
                elif action == 'remove_repository':
                    repos.remove(record.get('url', ''))
                else:
                    repos.refresh()
            elif action == 'install_package':
                installed_package = packages.install(record.get('filename'))
            elif action == 'remove_package':
                packages.uninstall(record.get('packageId'))
            scan = packages.scan()
            atomic_json(data / 'packages.json', scan)
            catalogue_path = data / 'repository-catalogue.json'
            if action in ('install_package', 'remove_package') and catalogue_path.exists():
                catalogue = json.loads(catalogue_path.read_text(encoding='utf-8'))
                installed = {item['id']: item for item in scan['installed']}
                for item in catalogue.get('packages', []):
                    record_installed = installed.get(item['id'], {})
                    item['installedVersion'] = record_installed.get('version')
                    item['installedSha256'] = record_installed.get('sha256')
                atomic_json(catalogue_path, catalogue)
            installed_code = action == 'install_package' and installed_package.get('type') == 'tweak'
            atomic_json(result, {'ok': True, 'action': action,
                'restartRequired': installed_code,
                'message': 'Tweak staged. Fully reopen Spring Launcher to load its code.' if installed_code else 'Package operation completed'})
            return
        if record.get('action') == 'set_animaper_mode':
            if str(ROOT / 'patches') not in sys.path: sys.path.insert(0, str(ROOT / 'patches'))
            import macapk_jailbreak
            import animaper
            if record.get('mode') == 'barrel':
                engine = running_engine()
                if engine is None or not animaper.barrel_supported_by(engine):
                    raise ValueError('Barrel requires the updated native rendering engine')
            reply = animaper.set_mode(macapk_jailbreak.DATA, record.get('mode'))
            reply['action'] = 'set_animaper_mode'
            atomic_json(result, reply)
            return
        if record.get('action') in ('set_safe_mode', 'disable_settings', 'enable_colors', 'disable_colors', 'enable_icons', 'disable_icons'):
            if str(ROOT / 'patches') not in sys.path:
                sys.path.insert(0, str(ROOT / 'patches'))
            import macapk_jailbreak
            import safe_mode
            apk, sha = operation_engine()
            action = record['action']
            package_hook = {'disable_settings': 'test.settings', 'disable_colors': 'test.colors',
                            'disable_icons': 'test.icons'}.get(action)
            if package_hook:
                import springys_registry
                registry = springys_registry.Registry(data / 'package-registry', lambda hooks, tweaks: None)
                if any(item.get('hook') == package_hook for item in registry.list().values()):
                    raise ValueError('Remove the installed .springys package using Local Packages first.')
            if action == 'set_safe_mode':
                if not isinstance(record.get('enabled'), bool):
                    raise ValueError('Safe Mode requires an on or off value')
                print('Changing Safe Mode; Spring will respring', flush=True)
                response = safe_mode.set_safe_mode(macapk_jailbreak.DATA, macapk_jailbreak.STATE,
                    apk, sha, record['enabled'])
            elif action == 'disable_settings':
                print('Removing Settings test; Spring will respring', flush=True)
                response = safe_mode.set_marker_and_respring(macapk_jailbreak.DATA, macapk_jailbreak.STATE,
                    apk, sha, False,
                    'settings-test.enabled', 'Settings test')
            elif action in ('enable_colors', 'disable_colors'):
                print('Changing color test; Spring will respring', flush=True)
                if action == 'enable_colors':
                    import ruby_theme
                    ruby_theme.stage(macapk_jailbreak.DATA)
                response = safe_mode.set_marker_and_respring(macapk_jailbreak.DATA, macapk_jailbreak.STATE,
                    apk, sha, action == 'enable_colors',
                    'ui-colors.enabled', 'Color test')
            else:
                print('Changing icon placement test; Spring will respring', flush=True)
                response = safe_mode.set_marker_and_respring(macapk_jailbreak.DATA, macapk_jailbreak.STATE,
                    apk, sha, action == 'enable_icons',
                    'free-icons.enabled', 'Icon placement test')
            response['action'] = action
            atomic_json(result, response)
            print(response['message'], flush=True)
            return
        if record.get('action') == 'enable_settings':
            if str(ROOT / 'patches') not in sys.path:
                sys.path.insert(0, str(ROOT / 'patches'))
            import macapk_jailbreak
            print('Installing Settings test; Spring will respring', flush=True)
            response = macapk_jailbreak.enable_settings_test()
            response['action'] = 'enable_settings'
            atomic_json(result, response)
            print(response['message'], flush=True)
            return
        relative = record.get('path')
        if not isinstance(relative, str) or not relative.startswith('imports/'):
            raise ValueError('Invalid package path')
        package = (data / relative).resolve(strict=True)
        imports = (data / 'imports').resolve(strict=True)
        if package.parent != imports or package.suffix.lower() != '.sapp' or not package.is_file():
            raise ValueError('Package must be a .sapp in Ruby imports')
        manifest = pack.check_zip(str(package))
        inbox.mkdir(parents=True, exist_ok=True)
        destination = inbox / ('ruby-' + request.stem + '.sapp')
        temporary = inbox / ('ruby-' + request.stem + '.pending')
        try:
            shutil.copyfile(package, temporary)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        atomic_json(result, {'ok': True, 'message': 'Sent to Spring inbox', 'package': manifest['id']})
        print('Queued {} ({})'.format(manifest['name'], manifest['id']), flush=True)
    except Exception as exc:
        atomic_json(result, {'ok': False, 'action': record.get('action', '') if isinstance(locals().get('record'), dict) else '', 'message': str(exc)[:250]})
        print('Failed {}: {}'.format(request.stem, exc), file=sys.stderr, flush=True)


def process_jailbreak(request, data, inbox):
    if not ID.fullmatch(request.stem):
        return
    result = data / 'results' / (request.stem + '.json')
    if result.exists():
        return
    try:
        record = json.loads(request.read_text(encoding='utf-8'))
        if record.get('id') != request.stem:
            raise ValueError('Invalid jailbreak request')
        if record.get('action') == 'jailbreak':
            if record.get('version', '0.8.1') != '0.8.1':
                raise ValueError('This WinterX build does not yet support the selected Spring version')
            # Import only when requested. This operation deliberately restarts
            # Spring; the user initiates it by tapping Jailbreak.
            if str(ROOT / 'patches') not in sys.path:
                sys.path.insert(0, str(ROOT / 'patches'))
            import macapk_jailbreak
            if (macapk_jailbreak.DATA / 'files/ruby/ui-colors.enabled').is_file():
                import ruby_theme
                ruby_theme.stage(macapk_jailbreak.DATA)
            print('Starting verified Spring jailbreak; Spring will respring', flush=True)
            response = macapk_jailbreak.run()
            response['action'] = 'jailbreak'
            atomic_json(result, response)
            print(response['message'], flush=True)
            return
        if record.get('action') != 'install_ruby':
            raise ValueError('Invalid jailbreak request')
        package = ROOT / 'Ruby.sapp'
        manifest = pack.check_zip(str(package))
        if manifest.get('id') != APP_ID:
            raise ValueError('Ruby.sapp has an unexpected app ID')
        inbox.mkdir(parents=True, exist_ok=True)
        # The app may be tapped repeatedly before Spring processes the first
        # request. Avoid filling the inbox with identical Ruby packages.
        existing = sorted(inbox.glob('ruby-setup-*.sapp'))
        if any(same_content(other, package) for other in existing if other.is_file()):
            atomic_json(result, {'ok': True, 'message': 'Ruby already waiting in Spring inbox'})
            print('Ruby is already waiting in Spring inbox', flush=True)
            return
        destination = inbox / ('ruby-setup-' + request.stem + '.sapp')
        temporary = inbox / ('ruby-setup-' + request.stem + '.pending')
        try:
            shutil.copyfile(package, temporary)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        atomic_json(result, {'ok': True, 'message': 'Ruby sent to Spring inbox'})
        print('Ruby setup sent to Spring inbox', flush=True)
    except Exception as exc:
        atomic_json(result, {'ok': False, 'action': 'jailbreak', 'message': str(exc)[:250]})
        print('Ruby setup failed: {}'.format(exc), file=sys.stderr, flush=True)


def update_live_status(data):
    active = False
    supported = False
    safe = False
    settings = False
    colors = False
    icons = False
    animaper_enabled = False
    animaper_mode = 'wave'
    barrel_supported = False
    try:
        apk = running_engine()
        if apk is not None:
            import macapk_jailbreak
            active = True
            import animaper
            barrel_supported = animaper.barrel_supported_by(apk)
            supported = macapk_jailbreak.digest(apk) in (macapk_jailbreak.PATCH_SHA, macapk_jailbreak.LOCAL_ALPHA8_SHA, macapk_jailbreak.LOCAL_SNOWY_SHA,
                macapk_jailbreak.BRIDGELESS_ALPHA4_SHA, macapk_jailbreak.BRIDGELESS_ALPHA2_SHA)
            ruby_data = macapk_jailbreak.DATA / 'files/ruby'
            safe = supported and (ruby_data / 'safe-mode.enabled').is_file()
            settings = active and (ruby_data / 'settings-test.enabled').is_file()
            colors = supported and (ruby_data / 'ui-colors.enabled').is_file()
            icons = supported and (ruby_data / 'free-icons.enabled').is_file()
            animaper_enabled = supported and (ruby_data / 'animaper.enabled').is_file()
            config = ruby_data / 'animaper.mode'
            if config.is_file() and config.stat().st_size <= 64: animaper_mode = config.read_text(encoding='utf-8').strip()
    except (OSError, ValueError, KeyError, TypeError):
        active = False
    atomic_json(data / 'live.json', {'active': active, 'safeModeSupported': supported, 'safeMode': safe,
                                     'settingsInstalled': settings, 'colorsInstalled': colors,
                                     'iconsInstalled': icons, 'animaperInstalled': animaper_enabled, 'animaperMode': animaper_mode,
                                     'animaperBarrelSupported': barrel_supported, 'observedAt': int(time.time() * 1000)})


def process_explorer(request, data, spring_files, trash):
    if not ID.fullmatch(request.stem):
        return
    result = data / 'results' / (request.stem + '.json')
    if result.exists():
        return
    try:
        record = json.loads(request.read_text(encoding='utf-8'))
        if record.get('id') != request.stem:
            raise ValueError('Invalid request ID')
        import iexplored
        explorer = iexplored.Explorer(spring_files, trash)
        action, path = record.get('action'), record.get('path', '')
        reply = {'ok': True, 'action': action}
        if action == 'list': reply['items'] = explorer.list(path)
        elif action == 'read': reply['text'] = explorer.read(path)
        elif action == 'write': explorer.write(path, record.get('text'))
        elif action == 'mkdir': explorer.mkdir(path)
        elif action == 'trash': reply['token'] = explorer.move_to_trash(path)
        elif action == 'restore': explorer.restore(record.get('token'))
        else: raise ValueError('Unsupported file operation')
    except Exception as exc:
        reply = {'ok': False, 'message': str(exc)[:250]}
    atomic_json(result, reply)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=DEFAULT_BASE, help='Mac.APK Spring data root')
    parser.add_argument('--once', action='store_true', help='Process pending requests and exit')
    args = parser.parse_args()
    data, inbox = locations(args.base)
    setup = jailbreak_data(args.base)
    spring_files = args.base / 'data/data/com.guille.spring_0.8.1/files'
    explorer_data = spring_files / 'sapps-data/com.winterx.iexplored/files'
    print('Ruby bridge watching package and jailbreak requests', flush=True)
    last_status = 0.0
    while True:
        for request in sorted((data / 'requests').glob('*.json')):
            process(request, data, inbox, args.base)
        for request in sorted((setup / 'requests').glob('*.json')):
            process_jailbreak(request, setup, inbox)
        for request in sorted((explorer_data / 'requests').glob('*.json')):
            process_explorer(request, explorer_data, spring_files, ROOT / '.ruby-state/iexplored-trash')
        # Finish app-package operations only after Spring's install has been
        # observed, or after a complete launcher shutdown for removal.
        if data.parent.exists() and time.monotonic() - last_status >= 3:
            lifecycle = app_lifecycle(args.base, inbox)
            try:
                state = lifecycle.reconcile()
                atomic_json(data / 'app-packages.json', state)
            except (OSError, ValueError, KeyError) as exc:
                print('App package recovery: {}'.format(exc), file=sys.stderr, flush=True)
        # Do not create an app-data directory before the app itself exists.
        if setup.exists() and time.monotonic() - last_status >= 3:
            update_live_status(setup)
            if data.parent.exists():
                update_live_status(data)
            last_status = time.monotonic()
        if args.once:
            break
        time.sleep(1)


if __name__ == '__main__':
    main()
