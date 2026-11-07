"""Rootless WinterX: the binary-manifest editor, the package rename and the requires_root manifest field."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'patches'))
import axml
import native_package
import package_rename
import toolchain

SPRING = ROOT / 'Spring-0.8.1.apk'


class PackageRenameTests(unittest.TestCase):
    def test_only_the_bare_package_literal_changes(self):
        text = ('    const-string v0, "com.guille.spring"\n'
                '    const-string v1, "com.guille.spring.hle.HleLink"\n'
                '    const-string v2, "null cannot be cast to non-null type com.guille.spring.model.Yt6Flow.Results"\n'
                '    const-string v3, "com.guille.spring.CLOCK_FIRE"\n'
                '    const-string v4, "store/com.guille.spring@1"\n')
        out, renamed, unknown = package_rename.rename(text, 'com.winterx.spring')
        self.assertEqual((renamed, unknown), (1, []))
        self.assertIn('"com.winterx.spring"', out)
        self.assertIn('"com.guille.spring.hle.HleLink"', out)

    def test_an_unreviewed_literal_stops_the_build(self):
        _, _, unknown = package_rename.rename('    const-string v0, "com.guille.spring.newthing"\n', 'x.y')
        self.assertEqual(unknown, ['com.guille.spring.newthing'])


@unittest.skipUnless(SPRING.is_file(), 'needs Spring-0.8.1.apk')
class ManifestTests(unittest.TestCase):
    def setUp(self):
        with zipfile.ZipFile(SPRING) as apk: self.original = apk.read('AndroidManifest.xml')

    def dump(self, data):
        with tempfile.TemporaryDirectory() as folder:
            apk = Path(folder) / 'm.apk'
            with zipfile.ZipFile(apk, 'w') as out: out.writestr('AndroidManifest.xml', data)
            return subprocess.run([str(toolchain.build_tool('aapt2')), 'dump', 'xmltree', str(apk), '--file', 'AndroidManifest.xml'],
                                  capture_output=True, text=True, check=True).stdout

    def test_unchanged_round_trip(self):
        self.assertEqual(self.dump(axml.edit(self.original)), self.dump(self.original))

    def test_rename_and_debuggable(self):
        edited = self.dump(axml.edit(self.original, {'com.guille.spring': 'com.winterx.spring',
                                                     'com.guille.spring.sappcapture': 'com.winterx.spring.sappcapture'}, True))
        self.assertIn('package="com.winterx.spring"', edited)
        self.assertIn('authorities(0x01010018)="com.winterx.spring.sappcapture"', edited)
        self.assertIn('debuggable(0x0101000f)=true', edited)
        self.assertIn('"com.guille.spring.LauncherActivity"', edited)          # class names keep their package
        before = [l for l in self.dump(self.original).splitlines() if 'sappcapture' not in l and 'package=' not in l]
        after = [l for l in edited.splitlines() if 'sappcapture' not in l and 'package=' not in l and 'debuggable' not in l]
        self.assertEqual(before, after)


class PrebuiltRuntimeTests(unittest.TestCase):
    def test_shipped_runtime_matches_this_source(self):
        """Release check: after changing the runtime or a name map, rebuild the 0.9 core with --base and copy its
        runtime-<version>.dex/.json into extensions/prebuilt/, or 0.9-only users can't build."""
        sys.path.insert(0, str(ROOT / 'extensions'))
        import build
        for version in build.VERSIONS.values():
            self.assertIsNotNone(build.prebuilt_runtime(version), 'extensions/prebuilt is stale for Spring ' + version['name'])


class RootFieldTests(unittest.TestCase):
    def test_valid_and_invalid(self):
        native_package.root_fields({})
        native_package.root_fields({'requires_root': True, 'root_note': 'Reads other apps\' data'})
        for bad in ({'requires_root': 'yes'}, {'requires_root': 1}, {'root_note': ''}, {'root_note': 'x' * 161}, {'root_note': 3}):
            with self.assertRaises(ValueError): native_package.root_fields(bad)


if __name__ == '__main__': unittest.main()
