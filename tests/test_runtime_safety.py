import json
import os
import tempfile
import time
import unittest
from pathlib import Path

import health_monitor as health
import lms_blog_bot as bot


class RuntimeSafetyTests(unittest.TestCase):
    def test_trim_processed_keeps_recent_numeric_ids(self):
        result = bot._trim_processed_ids(
            [str(i) for i in range(100)],
            limit=10,
        )
        self.assertEqual(result, [str(i) for i in range(90, 100)])

    def test_save_processed_atomic_and_bounded(self):
        original = bot.STATE_PATH
        with tempfile.TemporaryDirectory() as tmp:
            bot.STATE_PATH = Path(tmp) / "processed.json"
            try:
                bot.save_processed(
                    {str(i) for i in range(50010)},
                    "user:1",
                )
                data = json.loads(bot.STATE_PATH.read_text(encoding="utf-8"))
                ids = data["accounts"]["user:1"]
                self.assertEqual(len(ids), 50000)
                self.assertEqual(ids[0], "10")
                self.assertEqual(ids[-1], "50009")
                self.assertFalse((Path(tmp) / "processed.json.tmp").exists())
            finally:
                bot.STATE_PATH = original

    def test_health_write_is_atomic(self):
        original = health.HEALTH_PATH
        with tempfile.TemporaryDirectory() as tmp:
            health.HEALTH_PATH = Path(tmp) / "bot_health.json"
            try:
                for i in range(20):
                    health.write_health("running", sequence=i)
                data = json.loads(
                    health.HEALTH_PATH.read_text(encoding="utf-8")
                )
                self.assertEqual(data["sequence"], 19)
                self.assertFalse((Path(tmp) / "bot_health.json.tmp").exists())
            finally:
                health.HEALTH_PATH = original

    def test_log_cleanup_bounds_archive_count(self):
        original_dir = bot.LOG_DIR
        with tempfile.TemporaryDirectory() as tmp:
            bot.LOG_DIR = Path(tmp)
            try:
                for i in range(40):
                    path = bot.LOG_DIR / f"bot-{i:02d}.log"
                    path.write_text("x", encoding="utf-8")
                old = time.time() - 40 * 86400
                for i in range(5):
                    os.utime(bot.LOG_DIR / f"bot-{i:02d}.log", (old, old))

                removed = bot.cleanup_old_logs(30, 30)
                remaining = list(bot.LOG_DIR.glob("bot-*.log"))
                self.assertEqual(removed, 10)
                self.assertEqual(len(remaining), 30)
                cutoff = time.time() - 30 * 86400
                self.assertFalse(any(p.stat().st_mtime < cutoff for p in remaining))
            finally:
                bot.LOG_DIR = original_dir


    def test_attachment_cleanup_removes_old_files_and_empty_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "attachments"
            nested = root / "123" / "nested"
            nested.mkdir(parents=True)
            old_file = nested / "old.txt"
            old_file.write_text("x", encoding="utf-8")
            old = time.time() - 48 * 3600
            os.utime(old_file, (old, old))

            removed = health.cleanup_old_attachments(root, 24)

            self.assertEqual(removed, 1)
            self.assertFalse(old_file.exists())
            self.assertFalse(nested.exists())
            self.assertFalse((root / "123").exists())


if __name__ == "__main__":
    unittest.main()
