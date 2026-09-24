import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lms_blog_bot as bot


class FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector

    @property
    def first(self):
        return self

    def count(self):
        if self.selector == 'a[rel="next"]':
            return 1 if self.page.current_data().get("next") else 0
        return 0

    def get_attribute(self, name):
        if self.selector == 'a[rel="next"]' and name == "href":
            return self.page.current_data().get("next")
        return None

    def evaluate_all(self, script):
        if self.selector == 'a[href*="entryid="]':
            return list(self.page.current_data().get("entries", []))
        return []


class FakeBlogPage:
    def __init__(self, pages):
        self.pages = pages
        self.url = None

    def goto(self, url, **kwargs):
        if url not in self.pages:
            raise AssertionError(f"Unexpected URL: {url}")
        self.url = url

    def current_data(self):
        return self.pages[self.url]

    def locator(self, selector):
        return FakeLocator(self, selector)


class FakeEntryPage:
    def __init__(self):
        self.url = None

    def goto(self, url, **kwargs):
        self.url = url

def entry_url(eid):
    return f"https://example.test/blog/index.php?entryid={eid}"


class CoreBehaviorTests(unittest.TestCase):
    def test_pagination_skips_processed_first_page_and_reaches_backlog(self):
        base = "https://example.test/blog/index.php?userid=1"
        p2 = base + "&page=1"
        p3 = base + "&page=2"
        pages = {
            base: {
                "entries": [entry_url(i) for i in range(30, 20, -1)],
                "next": p2,
            },
            p2: {
                "entries": [entry_url(i) for i in range(20, 10, -1)],
                "next": p3,
            },
            p3: {
                "entries": [entry_url(i) for i in range(10, 0, -1)],
                "next": None,
            },
        }
        page = FakeBlogPage(pages)
        processed = {str(i) for i in range(21, 31)}

        entries, meta = bot.scan_blog_entries(
            page,
            base,
            limit=5,
            skip_ids=processed,
            max_pages=5,
        )

        self.assertEqual([eid for eid, _ in entries], ["20", "19", "18", "17", "16"])
        self.assertEqual(meta["pages_scanned"], 2)
        self.assertTrue(meta["hit_limit"])

    def test_scan_floor_stops_before_old_history(self):
        base = "https://example.test/blog/index.php?userid=1"
        p2 = base + "&page=1"
        p3 = base + "&page=2"
        pages = {
            base: {
                "entries": [entry_url(i) for i in range(30, 20, -1)],
                "next": p2,
            },
            p2: {
                "entries": [entry_url(i) for i in range(20, 10, -1)],
                "next": p3,
            },
            p3: {
                "entries": [entry_url(i) for i in range(10, 0, -1)],
                "next": None,
            },
        }
        page = FakeBlogPage(pages)

        entries, meta = bot.scan_blog_entries(
            page,
            base,
            limit=100,
            max_pages=10,
            ignore_through_entry_id="20",
        )

        self.assertEqual([eid for eid, _ in entries], [str(i) for i in range(30, 20, -1)])
        self.assertTrue(meta["hit_floor"])
        self.assertEqual(meta["pages_scanned"], 2)

    def test_processed_state_recovers_from_last_good_backup(self):
        original_state = bot.STATE_PATH
        original_backup = bot.STATE_BACKUP_PATH
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bot.STATE_PATH = root / "processed.json"
            bot.STATE_BACKUP_PATH = root / "processed.json.bak"
            try:
                bot.save_processed({"1"}, "user:1")
                bot.save_processed({"1", "2"}, "user:1")
                bot.STATE_PATH.write_text("{broken", encoding="utf-8")

                recovered = bot.load_processed("user:1")

                self.assertEqual(recovered, {"1"})
                restored = json.loads(bot.STATE_PATH.read_text(encoding="utf-8"))
                self.assertEqual(set(restored["accounts"]["user:1"]), {"1"})
            finally:
                bot.STATE_PATH = original_state
                bot.STATE_BACKUP_PATH = original_backup

    def test_pending_comment_round_trip_and_clear(self):
        original_pending = bot.PENDING_PATH
        original_backup = bot.PENDING_BACKUP_PATH
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bot.PENDING_PATH = root / "pending_comments.json"
            bot.PENDING_BACKUP_PATH = root / "pending_comments.json.bak"
            try:
                bot.save_pending_comment("user:1", "99", "answer text")
                item = bot.get_pending_comment("user:1", "99")
                self.assertEqual(item["answer"], "answer text")

                bot.clear_pending_comment("user:1", "99")
                self.assertIsNone(bot.get_pending_comment("user:1", "99"))
            finally:
                bot.PENDING_PATH = original_pending
                bot.PENDING_BACKUP_PATH = original_backup

    def test_pending_answer_is_reused_without_second_ai_call(self):
        page = FakeEntryPage()
        with (
            patch.object(bot, "logged_out", return_value=False),
            patch.object(
                bot,
                "get_pending_comment",
                return_value={"answer": "same answer"},
            ),
            patch.object(bot, "call_ai") as call_ai,
            patch.object(
                bot,
                "post_comment",
                return_value=(True, "verified"),
            ) as post_comment,
            patch.object(bot, "clear_pending_comment") as clear_pending,
        ):
            status = bot.process_entry(
                page,
                "99",
                entry_url(99),
                {},
                "user:1",
                "123",
            )

        self.assertEqual(status, "completed")
        call_ai.assert_not_called()
        post_comment.assert_called_once_with(
            page,
            "same answer",
            expected_user_id="123",
        )
        clear_pending.assert_not_called()

    def test_non_trigger_post_is_marked_ignored(self):
        page = FakeEntryPage()
        with (
            patch.object(bot, "logged_out", return_value=False),
            patch.object(bot, "get_pending_comment", return_value=None),
            patch.object(bot, "match_command", return_value=None),
        ):
            status = bot.process_entry(
                page,
                "100",
                entry_url(100),
                {},
                "user:1",
                "123",
            )
        self.assertEqual(status, "ignored")

    def test_config_example_is_valid(self):
        example = json.loads(
            (Path(__file__).resolve().parents[1] / "config.example.json")
            .read_text(encoding="utf-8")
        )
        self.assertIs(bot.validate_config(example), example)

    def test_config_rejects_invalid_deep_scan_value(self):
        cfg = {
            "lms_base_url": "https://example.test",
            "username": "u",
            "password": "p",
            "provider": "groq",
            "groq_api_key": "k",
            "deep_scan_max_pages": "not-a-number",
        }
        with self.assertRaisesRegex(RuntimeError, "deep_scan_max_pages"):
            bot.validate_config(cfg)

    def test_config_rejects_plain_http_by_default(self):
        cfg = {
            "lms_base_url": "http://example.test",
            "username": "u",
            "password": "p",
            "provider": "groq",
            "groq_api_key": "k",
        }
        with self.assertRaises(RuntimeError):
            bot.validate_config(cfg)

    def test_config_accepts_https(self):
        cfg = {
            "lms_base_url": "https://example.test",
            "username": "u",
            "password": "p",
            "provider": "groq",
            "groq_api_key": "k",
        }
        self.assertIs(bot.validate_config(cfg), cfg)

    def test_comment_normalization_collapses_whitespace(self):
        self.assertEqual(
            bot._normalize_comment_text("hello\n   world\t!"),
            "hello world !",
        )

    def test_corrupt_processed_without_backup_fails_closed(self):
        original_state = bot.STATE_PATH
        original_backup = bot.STATE_BACKUP_PATH
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bot.STATE_PATH = root / "processed.json"
            bot.STATE_BACKUP_PATH = root / "processed.json.bak"
            try:
                bot.STATE_PATH.write_text("{broken", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "state_corrupt"):
                    bot.load_processed("user:1")
            finally:
                bot.STATE_PATH = original_state
                bot.STATE_BACKUP_PATH = original_backup

    def test_account_meta_survives_processed_save(self):
        original_state = bot.STATE_PATH
        original_backup = bot.STATE_BACKUP_PATH
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bot.STATE_PATH = root / "processed.json"
            bot.STATE_BACKUP_PATH = root / "processed.json.bak"
            try:
                bot.save_processed({"1"}, "user:1")
                bot.update_account_meta(
                    "user:1",
                    ignore_through_entry_id="1",
                )
                bot.save_processed({"1", "2"}, "user:1")
                meta = bot.get_account_meta("user:1")
                data = json.loads(
                    bot.STATE_PATH.read_text(encoding="utf-8")
                )
                self.assertEqual(meta["ignore_through_entry_id"], "1")
                self.assertGreaterEqual(data["version"], 3)
            finally:
                bot.STATE_PATH = original_state
                bot.STATE_BACKUP_PATH = original_backup

    def test_prune_pending_removes_already_processed(self):
        original_pending = bot.PENDING_PATH
        original_backup = bot.PENDING_BACKUP_PATH
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bot.PENDING_PATH = root / "pending_comments.json"
            bot.PENDING_BACKUP_PATH = root / "pending_comments.json.bak"
            try:
                bot.save_pending_comment("user:1", "1", "done")
                bot.save_pending_comment("user:1", "2", "still pending")
                removed = bot.prune_pending_comments("user:1", {"1"})
                self.assertEqual(removed, 1)
                self.assertIsNone(bot.get_pending_comment("user:1", "1"))
                self.assertEqual(
                    bot.get_pending_comment("user:1", "2")["answer"],
                    "still pending",
                )
            finally:
                bot.PENDING_PATH = original_pending
                bot.PENDING_BACKUP_PATH = original_backup

    def test_permanent_ai_error_is_not_retried(self):
        cfg = {
            "provider": "groq",
            "retry_count": 5,
            "retry_delay_seconds": 0,
        }
        with patch.object(
            bot,
            "call_groq",
            side_effect=RuntimeError(
                "ai_permanent:AuthenticationError:bad key"
            ),
        ) as call_groq:
            with self.assertRaisesRegex(RuntimeError, "ai_permanent"):
                bot.call_ai("p", "s", cfg)
        call_groq.assert_called_once()


if __name__ == "__main__":
    unittest.main()
