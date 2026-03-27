import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from opencontext import __version__


class TestCliVersion(unittest.TestCase):
    expected_version_output = f"opencontext {__version__}\n"

    def setUp(self):
        self.project_root = Path(__file__).resolve().parents[1]

    def test_version_flag_prints_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "opencontext.cli", "--version"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, self.expected_version_output)
        self.assertEqual(result.stderr, "")

    def test_version_flag_succeeds_when_fastapi_and_uvicorn_imports_are_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sitecustomize = Path(temp_dir) / "sitecustomize.py"
            sitecustomize.write_text(
                """import builtins
_real_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if (
        name in {"fastapi", "uvicorn"}
        or name.startswith("fastapi.")
        or name.startswith("uvicorn.")
    ):
        raise ImportError(f"blocked import: {name}")
    return _real_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
""",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PYTHONPATH"] = temp_dir if "PYTHONPATH" not in env else (
                os.pathsep.join([temp_dir, env["PYTHONPATH"]])
            )

            result = subprocess.run(
                [sys.executable, "-m", "opencontext.cli", "--version"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                env=env,
                timeout=10,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, self.expected_version_output)
        self.assertEqual(result.stderr, "")
