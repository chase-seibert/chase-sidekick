"""Tests for Slack configuration loading."""
import os
import unittest
from unittest.mock import patch

from sidekick.config import get_slack_config


class TestGetSlackConfig(unittest.TestCase):
    """Tests for get_slack_config()."""

    @patch("sidekick.config._load_env_file")
    def test_returns_bot_token_from_env_file(self, mock_load_env):
        """Config returns bot_token when SLACK_BOT_TOKEN is in .env file."""
        mock_load_env.return_value = {"SLACK_BOT_TOKEN": "xoxb-test-token-123"}
        config = get_slack_config()
        self.assertEqual(config["bot_token"], "xoxb-test-token-123")
        self.assertIn("user_token", config)

    @patch("sidekick.config._load_env_file")
    def test_returns_bot_token_from_os_environ(self, mock_load_env):
        """Config falls back to os.environ when .env file has no token."""
        mock_load_env.return_value = {}
        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-env-token-456"}):
            config = get_slack_config()
            self.assertEqual(config["bot_token"], "xoxb-env-token-456")
            self.assertIn("user_token", config)

    @patch("sidekick.config._load_env_file")
    def test_returns_user_token_from_env_file(self, mock_load_env):
        """Config returns user_token when SLACK_USER_TOKEN is in .env file."""
        mock_load_env.return_value = {
            "SLACK_BOT_TOKEN": "xoxb-bot-123",
            "SLACK_USER_TOKEN": "xoxp-user-456"
        }
        config = get_slack_config()
        self.assertEqual(config["bot_token"], "xoxb-bot-123")
        self.assertEqual(config["user_token"], "xoxp-user-456")

    @patch("sidekick.config._load_env_file")
    def test_user_token_only_is_sufficient(self, mock_load_env):
        """Config works with only a user token (no bot token)."""
        mock_load_env.return_value = {"SLACK_USER_TOKEN": "xoxp-user-only"}
        with patch.dict(os.environ, {}, clear=True):
            config = get_slack_config()
            self.assertIsNone(config["bot_token"])
            self.assertEqual(config["user_token"], "xoxp-user-only")

    @patch("sidekick.config._load_env_file")
    def test_raises_when_token_missing(self, mock_load_env):
        """Config raises ValueError with actionable message when both tokens missing."""
        mock_load_env.return_value = {}
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                get_slack_config()
            self.assertIn("SLACK_BOT_TOKEN", str(ctx.exception))
            self.assertIn("api.slack.com", str(ctx.exception))

    @patch("sidekick.config._load_env_file")
    def test_env_file_takes_precedence_over_os_environ(self, mock_load_env):
        """Config prefers .env file value over os.environ."""
        mock_load_env.return_value = {"SLACK_BOT_TOKEN": "xoxb-from-file"}
        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-from-env"}):
            config = get_slack_config()
            self.assertEqual(config["bot_token"], "xoxb-from-file")


if __name__ == "__main__":
    unittest.main()
