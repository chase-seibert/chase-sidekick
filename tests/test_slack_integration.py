"""Integration tests for Slack client.

These tests require a real SLACK_BOT_TOKEN to be set in the environment
or .env file. They are automatically skipped when no token is available.

Run with:
    SLACK_BOT_TOKEN=xoxb-... python3 -m unittest tests/test_slack_integration.py -v
"""
import os
import unittest

# Check for token before importing (avoids config error on import)
HAS_TOKEN = bool(os.environ.get("SLACK_BOT_TOKEN"))


@unittest.skipUnless(HAS_TOKEN, "SLACK_BOT_TOKEN not set — skipping integration tests")
class TestSlackIntegration(unittest.TestCase):
    """Integration tests that hit the real Slack API."""

    @classmethod
    def setUpClass(cls):
        from sidekick.clients.slack import SlackClient
        cls.client = SlackClient(bot_token=os.environ["SLACK_BOT_TOKEN"])

    def test_list_channels_returns_results(self):
        """list_channels should return at least one channel."""
        channels = self.client.list_channels(limit=5)
        self.assertIsInstance(channels, list)
        self.assertGreater(len(channels), 0)
        # Each channel should have basic fields
        ch = channels[0]
        self.assertIn("id", ch)
        self.assertIn("name", ch)

    def test_get_channel_info(self):
        """get_channel_info should return details for a known channel."""
        channels = self.client.list_channels(limit=1)
        if not channels:
            self.skipTest("No channels available")
        channel_id = channels[0]["id"]
        info = self.client.get_channel_info(channel_id)
        self.assertIn("id", info)
        self.assertEqual(info["id"], channel_id)

    def test_get_channel_history(self):
        """get_channel_history should return messages."""
        channels = self.client.list_channels(limit=5)
        if not channels:
            self.skipTest("No channels available")
        # Try to find a channel with messages
        for ch in channels:
            messages = self.client.get_channel_history(ch["id"], limit=5)
            if messages:
                self.assertIsInstance(messages, list)
                msg = messages[0]
                self.assertIn("ts", msg)
                self.assertIn("text", msg)
                return
        self.skipTest("No channels with messages found")

    def test_get_users_returns_results(self):
        """get_users should return at least one user."""
        users = self.client.get_users(limit=5)
        self.assertIsInstance(users, list)
        self.assertGreater(len(users), 0)
        user = users[0]
        self.assertIn("id", user)
        self.assertIn("name", user)

    def test_get_user_info(self):
        """get_user_info should return details for a known user."""
        users = self.client.get_users(limit=1)
        if not users:
            self.skipTest("No users available")
        user_id = users[0]["id"]
        info = self.client.get_user_info(user_id)
        self.assertIn("id", info)
        self.assertEqual(info["id"], user_id)

    def test_invalid_channel_raises(self):
        """get_channel_info with bogus channel ID should raise ValueError."""
        with self.assertRaises(ValueError):
            self.client.get_channel_info("C000BOGUS000")


if __name__ == "__main__":
    unittest.main()
