"""Tests for Slack client."""
import io
import json
import unittest
from unittest.mock import patch, MagicMock

from sidekick.clients.slack import SlackClient


class TestSlackClientInit(unittest.TestCase):
    """Tests for SlackClient initialization."""

    def test_stores_bot_token(self):
        client = SlackClient(bot_token="xoxb-test-123")
        self.assertEqual(client.bot_token, "xoxb-test-123")

    def test_default_timeout(self):
        client = SlackClient(bot_token="xoxb-test-123")
        self.assertEqual(client.timeout, 30)

    def test_custom_timeout(self):
        client = SlackClient(bot_token="xoxb-test-123", timeout=60)
        self.assertEqual(client.timeout, 60)

    def test_api_call_count_starts_at_zero(self):
        client = SlackClient(bot_token="xoxb-test-123")
        self.assertEqual(client.api_call_count, 0)


class TestSlackClientAuth(unittest.TestCase):
    """Tests for authentication headers."""

    def test_bearer_token_format(self):
        client = SlackClient(bot_token="xoxb-test-token-456")
        headers = client._get_auth_headers()
        self.assertEqual(headers["Authorization"], "Bearer xoxb-test-token-456")

    def test_content_type_json(self):
        client = SlackClient(bot_token="xoxb-test-123")
        headers = client._get_auth_headers()
        self.assertIn("application/json", headers["Content-Type"])

    def test_accept_json(self):
        client = SlackClient(bot_token="xoxb-test-123")
        headers = client._get_auth_headers()
        self.assertEqual(headers["Accept"], "application/json")


def _mock_urlopen_response(body_dict, status=200):
    """Create a mock urllib response with JSON body."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(body_dict).encode()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


class TestSlackClientRequest(unittest.TestCase):
    """Tests for _request method."""

    def setUp(self):
        self.client = SlackClient(bot_token="xoxb-test-123")

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_success_returns_response(self, mock_urlopen):
        """Successful API call returns parsed response dict."""
        mock_urlopen.return_value = _mock_urlopen_response({
            "ok": True,
            "channels": [{"id": "C123", "name": "general"}]
        })
        result = self.client._request("GET", "conversations.list")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["channels"]), 1)

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_increments_api_call_count(self, mock_urlopen):
        """Each successful request increments api_call_count."""
        mock_urlopen.return_value = _mock_urlopen_response({"ok": True})
        self.client._request("GET", "conversations.list")
        self.client._request("GET", "conversations.list")
        self.assertEqual(self.client.api_call_count, 2)

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_slack_error_raises_value_error(self, mock_urlopen):
        """Slack ok=false response raises ValueError."""
        mock_urlopen.return_value = _mock_urlopen_response({
            "ok": False,
            "error": "channel_not_found"
        })
        with self.assertRaises(ValueError) as ctx:
            self.client._request("GET", "conversations.info")
        self.assertIn("channel_not_found", str(ctx.exception))

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_auth_error_has_actionable_message(self, mock_urlopen):
        """Auth errors include link to get new token."""
        mock_urlopen.return_value = _mock_urlopen_response({
            "ok": False,
            "error": "invalid_auth"
        })
        with self.assertRaises(ValueError) as ctx:
            self.client._request("GET", "conversations.list")
        self.assertIn("api.slack.com", str(ctx.exception))

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_missing_scope_error(self, mock_urlopen):
        """Missing scope error includes which scope is needed."""
        mock_urlopen.return_value = _mock_urlopen_response({
            "ok": False,
            "error": "missing_scope",
            "needed": "channels:read"
        })
        with self.assertRaises(ValueError) as ctx:
            self.client._request("GET", "conversations.list")
        self.assertIn("channels:read", str(ctx.exception))

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_ratelimited_in_body_raises_runtime_error(self, mock_urlopen):
        """Slack ratelimited in body raises RuntimeError."""
        mock_urlopen.return_value = _mock_urlopen_response({
            "ok": False,
            "error": "ratelimited"
        })
        with self.assertRaises(RuntimeError):
            self.client._request("GET", "conversations.list")

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_http_429_raises_runtime_error(self, mock_urlopen):
        """HTTP 429 rate limit raises RuntimeError with retry info."""
        import urllib.error
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.fp = mock_response
        mock_response.headers = {"Retry-After": "30"}
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://slack.com/api/test",
            code=429,
            msg="Too Many Requests",
            hdrs=mock_response.headers,
            fp=mock_response
        )
        with self.assertRaises(RuntimeError) as ctx:
            self.client._request("GET", "test")
        self.assertIn("429", str(ctx.exception))

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_http_401_raises_value_error(self, mock_urlopen):
        """HTTP 401 raises ValueError with auth guidance."""
        import urllib.error
        mock_response = MagicMock()
        mock_response.read.return_value = b"unauthorized"
        mock_response.fp = mock_response
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://slack.com/api/test",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=mock_response
        )
        with self.assertRaises(ValueError) as ctx:
            self.client._request("GET", "test")
        self.assertIn("authentication failed", str(ctx.exception).lower())

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_http_500_raises_runtime_error(self, mock_urlopen):
        """HTTP 500 raises RuntimeError."""
        import urllib.error
        mock_response = MagicMock()
        mock_response.read.return_value = b"internal server error"
        mock_response.fp = mock_response
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://slack.com/api/test",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=mock_response
        )
        with self.assertRaises(RuntimeError):
            self.client._request("GET", "test")

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_network_error_raises_connection_error(self, mock_urlopen):
        """Network failure raises ConnectionError."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        with self.assertRaises(ConnectionError):
            self.client._request("GET", "test")

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_builds_url_with_params(self, mock_urlopen):
        """GET params are encoded in the URL."""
        mock_urlopen.return_value = _mock_urlopen_response({"ok": True})
        self.client._request("GET", "conversations.list", params={"limit": "10"})
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        self.assertIn("limit=10", req.full_url)

    @patch("sidekick.clients.slack.urllib.request.urlopen")
    def test_sends_json_body_for_post(self, mock_urlopen):
        """POST sends JSON-encoded body."""
        mock_urlopen.return_value = _mock_urlopen_response({"ok": True})
        self.client._request("POST", "chat.postMessage",
                             json_data={"channel": "C123", "text": "hello"})
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode())
        self.assertEqual(body["channel"], "C123")
        self.assertEqual(body["text"], "hello")


class TestSlackClientPagination(unittest.TestCase):
    """Tests for cursor-based pagination."""

    def setUp(self):
        self.client = SlackClient(bot_token="xoxb-test-123")

    @patch.object(SlackClient, "_request")
    def test_single_page(self, mock_request):
        """Returns items from a single page when no next_cursor."""
        mock_request.return_value = {
            "ok": True,
            "channels": [{"id": "C1"}, {"id": "C2"}],
            "response_metadata": {"next_cursor": ""}
        }
        result = self.client._paginate("conversations.list", "channels")
        self.assertEqual(len(result), 2)
        mock_request.assert_called_once()

    @patch.object(SlackClient, "_request")
    def test_multiple_pages(self, mock_request):
        """Collects items across multiple pages."""
        mock_request.side_effect = [
            {
                "ok": True,
                "channels": [{"id": "C1"}, {"id": "C2"}],
                "response_metadata": {"next_cursor": "cursor_page2"}
            },
            {
                "ok": True,
                "channels": [{"id": "C3"}],
                "response_metadata": {"next_cursor": ""}
            }
        ]
        result = self.client._paginate("conversations.list", "channels")
        self.assertEqual(len(result), 3)
        self.assertEqual(mock_request.call_count, 2)

    @patch.object(SlackClient, "_request")
    def test_respects_limit(self, mock_request):
        """Stops collecting when limit is reached."""
        mock_request.side_effect = [
            {
                "ok": True,
                "channels": [{"id": f"C{i}"} for i in range(200)],
                "response_metadata": {"next_cursor": "more"}
            },
            {
                "ok": True,
                "channels": [{"id": f"C{i}"} for i in range(200, 400)],
                "response_metadata": {"next_cursor": ""}
            }
        ]
        result = self.client._paginate("conversations.list", "channels", limit=250)
        self.assertEqual(len(result), 250)

    @patch.object(SlackClient, "_request")
    def test_passes_params(self, mock_request):
        """Additional params are forwarded to _request."""
        mock_request.return_value = {
            "ok": True,
            "channels": [],
            "response_metadata": {"next_cursor": ""}
        }
        self.client._paginate("conversations.list", "channels",
                              params={"types": "public_channel"})
        call_params = mock_request.call_args[1]["params"]
        self.assertEqual(call_params["types"], "public_channel")


class TestSlackClientReadMethods(unittest.TestCase):
    """Tests for read API methods."""

    def setUp(self):
        self.client = SlackClient(bot_token="xoxb-test-123")

    @patch.object(SlackClient, "_paginate")
    def test_list_channels_calls_paginate(self, mock_paginate):
        """list_channels delegates to _paginate with correct args."""
        mock_paginate.return_value = [{"id": "C1", "name": "general"}]
        result = self.client.list_channels()
        mock_paginate.assert_called_once_with(
            "conversations.list",
            "channels",
            params={"types": "public_channel,private_channel"},
            limit=200
        )
        self.assertEqual(len(result), 1)

    @patch.object(SlackClient, "_paginate")
    def test_list_channels_custom_types(self, mock_paginate):
        """list_channels passes custom types parameter."""
        mock_paginate.return_value = []
        self.client.list_channels(types="im", limit=50)
        mock_paginate.assert_called_once_with(
            "conversations.list",
            "channels",
            params={"types": "im"},
            limit=50
        )

    @patch.object(SlackClient, "_request")
    def test_get_channel_info(self, mock_request):
        """get_channel_info returns channel dict."""
        mock_request.return_value = {
            "ok": True,
            "channel": {"id": "C123", "name": "general", "num_members": 42}
        }
        result = self.client.get_channel_info("C123")
        self.assertEqual(result["name"], "general")
        mock_request.assert_called_once_with(
            "GET", "conversations.info", params={"channel": "C123"}
        )

    def test_get_channel_info_empty_id_raises(self):
        """get_channel_info raises ValueError for empty channel_id."""
        with self.assertRaises(ValueError):
            self.client.get_channel_info("")

    @patch.object(SlackClient, "_paginate")
    def test_get_channel_history(self, mock_paginate):
        """get_channel_history calls paginate with channel param."""
        mock_paginate.return_value = [{"ts": "123", "text": "hello"}]
        result = self.client.get_channel_history("C123", limit=50)
        mock_paginate.assert_called_once_with(
            "conversations.history",
            "messages",
            params={"channel": "C123"},
            limit=50
        )

    @patch.object(SlackClient, "_paginate")
    def test_get_channel_history_with_time_range(self, mock_paginate):
        """get_channel_history passes oldest and latest params."""
        mock_paginate.return_value = []
        self.client.get_channel_history("C123", oldest="1000", latest="2000")
        call_params = mock_paginate.call_args[1]["params"]
        self.assertEqual(call_params["oldest"], "1000")
        self.assertEqual(call_params["latest"], "2000")

    def test_get_channel_history_empty_id_raises(self):
        """get_channel_history raises ValueError for empty channel_id."""
        with self.assertRaises(ValueError):
            self.client.get_channel_history("")

    @patch.object(SlackClient, "_paginate")
    def test_get_thread_replies(self, mock_paginate):
        """get_thread_replies calls paginate with channel and ts."""
        mock_paginate.return_value = [{"ts": "123", "text": "reply"}]
        self.client.get_thread_replies("C123", "1234567890.123456")
        mock_paginate.assert_called_once_with(
            "conversations.replies",
            "messages",
            params={"channel": "C123", "ts": "1234567890.123456"},
            limit=100
        )

    def test_get_thread_replies_empty_args_raises(self):
        """get_thread_replies raises ValueError for missing args."""
        with self.assertRaises(ValueError):
            self.client.get_thread_replies("", "123")
        with self.assertRaises(ValueError):
            self.client.get_thread_replies("C123", "")

    @patch.object(SlackClient, "_paginate")
    def test_get_users(self, mock_paginate):
        """get_users calls paginate for users.list."""
        mock_paginate.return_value = [{"id": "U1", "name": "alice"}]
        result = self.client.get_users()
        mock_paginate.assert_called_once_with(
            "users.list", "members", limit=200
        )
        self.assertEqual(len(result), 1)

    @patch.object(SlackClient, "_request")
    def test_get_user_info(self, mock_request):
        """get_user_info returns user dict."""
        mock_request.return_value = {
            "ok": True,
            "user": {"id": "U123", "name": "alice", "real_name": "Alice Smith"}
        }
        result = self.client.get_user_info("U123")
        self.assertEqual(result["name"], "alice")

    def test_get_user_info_empty_id_raises(self):
        """get_user_info raises ValueError for empty user_id."""
        with self.assertRaises(ValueError):
            self.client.get_user_info("")


class TestSlackClientWriteMethods(unittest.TestCase):
    """Tests for write API methods."""

    def setUp(self):
        self.client = SlackClient(bot_token="xoxb-test-123")

    @patch.object(SlackClient, "_request")
    def test_send_message(self, mock_request):
        """send_message posts to chat.postMessage with correct payload."""
        mock_request.return_value = {"ok": True, "ts": "123.456"}
        self.client.send_message("C123", "Hello world")
        mock_request.assert_called_once_with(
            "POST", "chat.postMessage",
            json_data={"channel": "C123", "text": "Hello world"}
        )

    @patch.object(SlackClient, "_request")
    def test_send_message_in_thread(self, mock_request):
        """send_message includes thread_ts when replying to a thread."""
        mock_request.return_value = {"ok": True, "ts": "123.789"}
        self.client.send_message("C123", "Reply", thread_ts="123.456")
        call_payload = mock_request.call_args[1]["json_data"]
        self.assertEqual(call_payload["thread_ts"], "123.456")

    def test_send_message_empty_channel_raises(self):
        """send_message raises ValueError for empty channel_id."""
        with self.assertRaises(ValueError):
            self.client.send_message("", "Hello")

    def test_send_message_empty_text_raises(self):
        """send_message raises ValueError for empty text."""
        with self.assertRaises(ValueError):
            self.client.send_message("C123", "")


class TestFormatChannel(unittest.TestCase):
    """Tests for _format_channel helper."""

    def test_basic_format(self):
        from sidekick.clients.slack import _format_channel
        channel = {"name": "general", "num_members": 42, "topic": {"value": ""}}
        result = _format_channel(channel)
        self.assertEqual(result, "#general (42 members)")

    def test_with_topic(self):
        from sidekick.clients.slack import _format_channel
        channel = {
            "name": "engineering",
            "num_members": 15,
            "topic": {"value": "Engineering discussion"}
        }
        result = _format_channel(channel)
        self.assertEqual(result, "#engineering (15 members) [Engineering discussion]")

    def test_missing_fields(self):
        from sidekick.clients.slack import _format_channel
        result = _format_channel({})
        self.assertEqual(result, "#unknown (? members)")


class TestFormatUser(unittest.TestCase):
    """Tests for _format_user helper."""

    def test_basic_format(self):
        from sidekick.clients.slack import _format_user
        user = {
            "name": "alice",
            "real_name": "Alice Smith",
            "profile": {"email": "alice@example.com"}
        }
        result = _format_user(user)
        self.assertEqual(result, "@alice (Alice Smith) [alice@example.com]")

    def test_without_email(self):
        from sidekick.clients.slack import _format_user
        user = {"name": "bob", "real_name": "Bob Jones", "profile": {}}
        result = _format_user(user)
        self.assertEqual(result, "@bob (Bob Jones)")

    def test_minimal_user(self):
        from sidekick.clients.slack import _format_user
        result = _format_user({"name": "charlie"})
        self.assertEqual(result, "@charlie")


class TestFormatMessage(unittest.TestCase):
    """Tests for _format_message helper."""

    def test_basic_format(self):
        from sidekick.clients.slack import _format_message
        msg = {"ts": "1705312200.000000", "user": "U123", "text": "Hello"}
        result = _format_message(msg)
        self.assertIn("U123", result)
        self.assertIn("Hello", result)
        self.assertIn("2024-01-15", result)

    def test_with_user_resolution(self):
        from sidekick.clients.slack import _format_message
        msg = {"ts": "1705312200.000000", "user": "U123", "text": "Hi"}
        users = {"U123": "alice"}
        result = _format_message(msg, users=users)
        self.assertIn("alice", result)
        self.assertNotIn("U123", result)

    def test_long_message_truncated(self):
        from sidekick.clients.slack import _format_message
        msg = {"ts": "1705312200.000000", "user": "U1", "text": "x" * 300}
        result = _format_message(msg)
        self.assertLessEqual(len(result), 300)
        self.assertTrue(result.endswith("..."))

    def test_multiline_collapsed(self):
        from sidekick.clients.slack import _format_message
        msg = {"ts": "1705312200.000000", "user": "U1", "text": "line1\nline2\nline3"}
        result = _format_message(msg)
        self.assertNotIn("\n", result)
        self.assertIn("line1 line2 line3", result)


class TestSlackCLI(unittest.TestCase):
    """Tests for CLI main() function."""

    @patch("sidekick.clients.slack.sys")
    def test_no_args_prints_help_and_exits(self, mock_sys):
        """CLI with no args prints usage and exits with code 1."""
        from sidekick.clients.slack import main
        mock_sys.argv = ["slack.py"]
        mock_sys.exit = MagicMock(side_effect=SystemExit(1))
        mock_sys.stderr = MagicMock()
        with self.assertRaises(SystemExit):
            main()
        mock_sys.exit.assert_called_with(1)

    @patch("sidekick.clients.slack.sys")
    @patch("sidekick.config.get_slack_config")
    def test_unknown_command_exits(self, mock_config, mock_sys):
        """CLI with unknown command exits with code 1."""
        from sidekick.clients.slack import main
        mock_config.return_value = {"bot_token": "xoxb-test"}
        mock_sys.argv = ["slack.py", "invalid-command"]
        mock_sys.exit = MagicMock(side_effect=SystemExit(1))
        mock_sys.stderr = MagicMock()
        with self.assertRaises(SystemExit):
            main()
        mock_sys.exit.assert_called_with(1)

    @patch("sidekick.clients.slack.sys")
    @patch("sidekick.config.get_slack_config")
    @patch.object(SlackClient, "list_channels")
    def test_list_channels_command(self, mock_list, mock_config, mock_sys):
        """CLI list-channels calls client and prints output."""
        mock_config.return_value = {"bot_token": "xoxb-test"}
        mock_sys.argv = ["slack.py", "list-channels"]
        mock_sys.exit = MagicMock()
        mock_sys.stderr = MagicMock()
        mock_list.return_value = [
            {"name": "general", "num_members": 10, "topic": {"value": ""}}
        ]
        from sidekick.clients.slack import main
        main()
        mock_list.assert_called_once()

    @patch("sidekick.clients.slack.sys")
    @patch("sidekick.config.get_slack_config")
    @patch.object(SlackClient, "get_channel_info")
    def test_channel_info_command(self, mock_info, mock_config, mock_sys):
        """CLI channel-info calls client with channel ID."""
        mock_config.return_value = {"bot_token": "xoxb-test"}
        mock_sys.argv = ["slack.py", "channel-info", "C123"]
        mock_sys.exit = MagicMock()
        mock_sys.stderr = MagicMock()
        mock_info.return_value = {
            "id": "C123", "name": "general",
            "num_members": 10, "topic": {"value": ""}, "purpose": {"value": ""}
        }
        from sidekick.clients.slack import main
        main()
        mock_info.assert_called_once_with("C123")

    @patch("sidekick.clients.slack.sys")
    @patch("sidekick.config.get_slack_config")
    @patch.object(SlackClient, "send_message")
    def test_send_message_command(self, mock_send, mock_config, mock_sys):
        """CLI send-message calls client with channel and text."""
        mock_config.return_value = {"bot_token": "xoxb-test"}
        mock_sys.argv = ["slack.py", "send-message", "C123", "Hello world"]
        mock_sys.exit = MagicMock()
        mock_sys.stderr = MagicMock()
        mock_send.return_value = {"ok": True, "ts": "123.456"}
        from sidekick.clients.slack import main
        main()
        mock_send.assert_called_once_with("C123", "Hello world")


if __name__ == "__main__":
    unittest.main()
