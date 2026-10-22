"""Packaging metadata regression; run with python tests/test_setup_metadata.py."""
import ast
import builtins
import importlib.metadata as metadata
from pathlib import Path
import runpy
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

import setuptools


class SetupMetadataTest(unittest.TestCase):
    def test_opencv_selection_keeps_names_order_and_constraints(self):
        cases = [
            ({}, False, "opencv-python-headless"),
            ({"opencv-python": "4.10.0.84"}, True, "opencv-python"),
            ({"opencv-python": "4.8.0.76"}, True, "opencv-python"),
            ({"opencv-contrib-python": "4.10.0.84"}, True, "opencv-contrib-python"),
            ({"opencv-python-headless": "4.10.0.84"}, True, "opencv-python-headless"),
            ({"opencv-python": "4.10.0.84", "opencv-contrib-python": "4.10.0.84"}, True, "opencv-python"),
            ({"opencv-contrib-python": "4.10.0.84", "opencv-contrib-python-headless": "4.10.0.84"}, True, "opencv-contrib-python"),
            ({}, True, None),
        ]
        source = Path(__file__).resolve().parents[1] / "setup.py"
        ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        real_import = builtins.__import__
        for installed, cv2_available, expected in cases:
            with self.subTest(installed=installed, cv2_available=cv2_available):
                with tempfile.TemporaryDirectory() as temporary:
                    distributions = {}
                    for name, version in installed.items():
                        path = Path(temporary) / (name.replace("-", "_") + "-" + version + ".dist-info")
                        path.mkdir()
                        (path / "METADATA").write_text("Metadata-Version: 2.1\nName: " + name + "\nVersion: " + version + "\n", encoding="utf-8")
                        distributions[name] = metadata.Distribution.at(path)
                    def lookup(name):
                        self.assertFalse(any(char in name for char in "!<>= "))
                        if name not in distributions:
                            raise metadata.PackageNotFoundError(name)
                        return distributions[name]
                    def importing(name, *args, **kwargs):
                        if name == "cv2" and not cv2_available:
                            raise ImportError("controlled absent cv2")
                        return real_import(name, *args, **kwargs)
                    with patch.dict(sys.modules, {"cv2": ModuleType("cv2")}), patch("builtins.__import__", importing), patch("importlib.metadata.distribution", side_effect=lookup), patch.object(setuptools, "setup") as setup:
                        runpy.run_path(str(source), run_name="__packaging_test__")
                    requirements = setup.call_args.kwargs["install_requires"]
                    actual = [r for r in requirements if r.startswith("opencv-")]
                    self.assertEqual(actual, [expected + ">=4.9.0.80"] if expected else [])
                    self.assertIn("albucore==0.0.28", requirements)


if __name__ == "__main__":
    unittest.main(verbosity=2)