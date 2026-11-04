import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('engine_build', ROOT / 'patches/icon_positions/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class EngineBuildTests(unittest.TestCase):
    def test_decode_omits_assets_but_preserves_bytecode_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'stock.apk', Path(tmp) / 'decode.apk'
            names = ('AndroidManifest.xml', 'resources.arsc', 'classes.dex', 'classes2.dex')
            with zipfile.ZipFile(source, 'x') as archive:
                for name in names: archive.writestr(name, name.encode())
                archive.writestr('assets/private.bin', b'not needed for smali')
                archive.writestr('lib/arm64-v8a/native.so', b'not needed for smali')
            build.decode_input(source, output)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()), set(names))
                for name in names: self.assertEqual(archive.read(name), name.encode())

    def test_final_output_is_exclusive_and_survives_temporary_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'assembled.apk', Path(tmp) / 'engine.apk'
            source.write_bytes(b'original')
            output.write_bytes(b'user work')
            with self.assertRaises(FileExistsError): build.publish_output(source, output)
            self.assertEqual(output.read_bytes(), b'user work')
            output.unlink()
            build.publish_output(source, output)
            source.unlink()
            self.assertEqual(output.read_bytes(), b'original')


if __name__ == '__main__': unittest.main()
