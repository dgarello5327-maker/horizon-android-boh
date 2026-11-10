import importlib.util
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("android_native_build.py")
SPEC = importlib.util.spec_from_file_location("android_native_build", SCRIPT)
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class NativeBundleTests(unittest.TestCase):
    def make_bundle(self, path, extra=(), manifest_overrides=None):
        manifest = {
            "schema": 1,
            "id": "sample_mod",
            "version": "1.0.0",
            "game": json.loads((BUILD.ROOT / "research-lock.json").read_text())["minecraft"]["version"],
            "horizon": "a" * 40,
            "mixins": "b" * 40,
        }
        manifest.update(manifest_overrides or {})
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("horizon-native.json", json.dumps(manifest))
            archive.writestr(
                "mixins/sample_mod/horizon-mixin.toml",
                '[mod]\nid = "sample_mod"\nversion = "1.0.0"\n',
            )
            archive.writestr("mixins/sample_mod/src/lib.rs", "// test")
            for name, data, mode in extra:
                info = zipfile.ZipInfo(name)
                if mode is not None:
                    info.external_attr = mode << 16
                archive.writestr(info, data)

    def test_valid_bundle_is_extracted(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, target = Path(temp) / "mod.hnmod", Path(temp) / "out"
            self.make_bundle(archive)
            self.assertEqual(
                BUILD.unpack(archive, target),
                ("sample_mod", "a" * 40, "b" * 40),
            )
            self.assertTrue((target / "mixins/sample_mod/src/lib.rs").is_file())

    def test_rejects_path_traversal_before_extracting(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, target = Path(temp) / "mod.hnmod", Path(temp) / "out"
            self.make_bundle(archive, [("../escape.txt", "bad", None)])
            with self.assertRaises(ValueError):
                BUILD.unpack(archive, target)
            self.assertFalse((Path(temp) / "escape.txt").exists())

    def test_rejects_symlink_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, target = Path(temp) / "mod.hnmod", Path(temp) / "out"
            self.make_bundle(archive, [("mixins/sample_mod/link", "target", stat.S_IFLNK | 0o777)])
            with self.assertRaises(ValueError):
                BUILD.unpack(archive, target)

    def test_rejects_other_minecraft_versions(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, target = Path(temp) / "mod.hnmod", Path(temp) / "out"
            self.make_bundle(archive, manifest_overrides={"game": "1.20.1"})
            with self.assertRaises(ValueError):
                BUILD.unpack(archive, target)


if __name__ == "__main__":
    unittest.main()
