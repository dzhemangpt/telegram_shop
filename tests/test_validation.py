import os
import unittest
from unittest.mock import patch

from app.config import Settings
from app.validation import normalize_phone, valid_email, valid_name


class ValidationTests(unittest.TestCase):
    def test_name(self):
        for text in (None, "", "  ", "x" * 26, "/shop"):
            with self.subTest(text=text):
                self.assertFalse(valid_name(text))
        self.assertTrue(valid_name(" Анна "))

    def test_phone_normalization(self):
        for text in ("+79991234567", "89991234567", " +79991234567 "):
            with self.subTest(text=text):
                self.assertEqual(normalize_phone(text), "+79991234567")

    def test_invalid_phone(self):
        for text in (None, "", "+7999", "79991234567", "+7１２３４５６７８９０", "hello"):
            with self.subTest(text=text):
                self.assertIsNone(normalize_phone(text))

    def test_email(self):
        for text in ("buyer@example.com", " first.last+shop@sub.example.org "):
            with self.subTest(text=text):
                self.assertTrue(valid_email(text))
        for text in (
            None,
            "",
            "a@b",
            ".a@example.com",
            "a..b@example.com",
            "a@-example.com",
            "a@example-.com",
            "a@@example.com",
            "a @example.com",
            "a" * 45 + "@example.com",
        ):
            with self.subTest(text=text):
                self.assertFalse(valid_email(text))

    def test_settings_validation(self):
        for env in (
            {},
            {"BOT_TOKEN": "test"},
            {"BOT_TOKEN": "test", "ADMIN_CHAT_ID": "0"},
            {"BOT_TOKEN": "test", "ADMIN_CHAT_ID": "abc"},
        ):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError):
                    Settings.from_env()

    def test_group_chat_id_is_allowed(self):
        with patch.dict(
            os.environ, {"BOT_TOKEN": " test ", "ADMIN_CHAT_ID": "-100123"}, clear=True
        ):
            self.assertEqual(Settings.from_env(), Settings("test", -100123))
