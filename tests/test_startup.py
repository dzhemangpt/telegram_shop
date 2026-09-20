import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class StartupTests(unittest.TestCase):
    def test_fresh_demo_database_can_be_seeded_twice_without_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "demo.db"
            env = {
                key: value
                for key, value in os.environ.items()
                if key not in {"BOT_TOKEN", "ADMIN_CHAT_ID"}
            }
            env["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
            env["PYTHONIOENCODING"] = "utf-8"
            for expected in ("Демокаталог создан", "Изменений нет"):
                result = subprocess.run(
                    [sys.executable, "-m", "app.seed"],
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)
            result = subprocess.run(
                [sys.executable, "run.py"],
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Set BOT_TOKEN", result.stderr)

    def test_import_does_not_create_database_or_require_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "unused.db"
            env = {
                key: value
                for key, value in os.environ.items()
                if key not in {"BOT_TOKEN", "ADMIN_CHAT_ID"}
            }
            env["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
            result = subprocess.run(
                [sys.executable, "-c", "import run"],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(path.exists())
