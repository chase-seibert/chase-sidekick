"""Slack API Client - single file implementation with CLI support."""

import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional


class SlackClient:
    """Slack API client using native Python stdlib."""

    BASE_URL = "https://slack.com/api"

    def __init__(self, bot_token: str, timeout: int = 30):
        """Initialize Slack client with bot token.

        Args:
            bot_token: Bot User OAuth Token (starts with xoxb-)
            timeout: Request timeout in seconds
        """
        self.bot_token = bot_token
        self.timeout = timeout
        self.api_call_count = 0

    def _get_auth_headers(self) -> dict:
        """Generate Bearer auth headers for Slack API."""
        return {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json"
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None
    ) -> dict:
        """Make HTTP request to Slack API.

        Slack returns HTTP 200 for most responses, including errors.
        The actual success/failure is in the response body's "ok" field.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API method name (e.g., conversations.list)
            params: URL query parameters (for GET requests)
            json_data: JSON body data (for POST requests)

        Returns:
            Parsed JSON response as dict (with "ok" field removed)

        Raises:
            ConnectionError: For network errors
            ValueError: For Slack API errors (ok=false) and HTTP 4xx
            RuntimeError: For HTTP 5xx and rate limiting
        """
        url = f"{self.BASE_URL}/{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = self._get_auth_headers()
        data = json.dumps(json_data).encode() if json_data else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                self.api_call_count += 1
                body = response.read().decode()
                result = json.loads(body)

                # Slack returns 200 even for errors — check "ok" field
                if not result.get("ok"):
                    error = result.get("error", "unknown_error")
                    if error == "not_authed" or error == "invalid_auth":
                        raise ValueError(
                            f"Slack authentication failed: {error}\n"
                            f"Your bot token may be invalid or expired.\n"
                            f"Get a new token at: https://api.slack.com/apps"
                        )
                    elif error == "missing_scope":
                        needed = result.get("needed", "unknown")
                        raise ValueError(
                            f"Slack missing scope: {needed}\n"
                            f"Add the scope at: https://api.slack.com/apps → OAuth & Permissions"
                        )
                    elif error == "ratelimited":
                        retry_after = result.get("headers", {}).get("Retry-After", "unknown")
                        raise RuntimeError(
                            f"Slack rate limited. Retry after {retry_after} seconds."
                        )
                    else:
                        raise ValueError(f"Slack API error: {error}")

                return result

        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            if e.code == 429:
                retry_after = e.headers.get("Retry-After", "unknown")
                raise RuntimeError(
                    f"Slack rate limited (HTTP 429). Retry after {retry_after} seconds."
                )
            elif e.code == 401 or e.code == 403:
                raise ValueError(
                    f"Slack authentication failed (HTTP {e.code}): {error_body}\n"
                    f"Your bot token may be invalid or expired.\n"
                    f"Get a new token at: https://api.slack.com/apps"
                )
            elif 400 <= e.code < 500:
                raise ValueError(f"Client error {e.code}: {error_body}")
            else:
                raise RuntimeError(f"Server error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Network error: {e.reason}")

    def _paginate(
        self,
        endpoint: str,
        response_key: str,
        params: Optional[dict] = None,
        limit: int = 200
    ) -> list:
        """Fetch all pages of a cursor-paginated Slack API endpoint.

        Args:
            endpoint: API method name (e.g., conversations.list)
            response_key: Key in response containing the items (e.g., "channels")
            params: Additional query parameters
            limit: Maximum total items to return

        Returns:
            List of items collected across all pages
        """
        all_items = []
        request_params = dict(params or {})
        page_size = min(limit, 200)
        request_params["limit"] = str(page_size)

        while True:
            result = self._request("GET", endpoint, params=request_params)
            items = result.get(response_key, [])
            all_items.extend(items)

            if len(all_items) >= limit:
                return all_items[:limit]

            # Check for next page
            cursor = result.get("response_metadata", {}).get("next_cursor", "")
            if not cursor:
                break
            request_params["cursor"] = cursor

        return all_items

    def list_channels(
        self,
        limit: int = 200,
        types: str = "public_channel,private_channel"
    ) -> list:
        """List channels the bot has access to.

        Args:
            limit: Maximum number of channels to return
            types: Comma-separated channel types
                   (public_channel, private_channel, mpim, im)

        Returns:
            List of channel dicts with keys like id, name, topic, num_members
        """
        return self._paginate(
            "conversations.list",
            "channels",
            params={"types": types},
            limit=limit
        )

    def get_channel_info(self, channel_id: str) -> dict:
        """Get detailed info about a channel.

        Args:
            channel_id: Channel ID (e.g., C09NU0MEGH1)

        Returns:
            Channel dict with id, name, topic, purpose, num_members, etc.

        Raises:
            ValueError: If channel_id is empty or channel not found
        """
        if not channel_id:
            raise ValueError("channel_id is required")
        result = self._request("GET", "conversations.info",
                               params={"channel": channel_id})
        return result.get("channel", {})

    def get_channel_history(
        self,
        channel_id: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None
    ) -> list:
        """Get messages from a channel.

        Args:
            channel_id: Channel ID
            limit: Maximum number of messages to return
            oldest: Only messages after this Unix timestamp
            latest: Only messages before this Unix timestamp

        Returns:
            List of message dicts with keys like ts, user, text, thread_ts
        """
        if not channel_id:
            raise ValueError("channel_id is required")
        params = {"channel": channel_id}
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        return self._paginate(
            "conversations.history",
            "messages",
            params=params,
            limit=limit
        )

    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        limit: int = 100
    ) -> list:
        """Get replies to a thread.

        Args:
            channel_id: Channel ID containing the thread
            thread_ts: Timestamp of the parent message

        Returns:
            List of message dicts (first item is the parent message)
        """
        if not channel_id or not thread_ts:
            raise ValueError("channel_id and thread_ts are required")
        params = {"channel": channel_id, "ts": thread_ts}
        return self._paginate(
            "conversations.replies",
            "messages",
            params=params,
            limit=limit
        )

    def get_users(self, limit: int = 200) -> list:
        """List all users in the workspace.

        Args:
            limit: Maximum number of users to return

        Returns:
            List of user dicts with keys like id, name, real_name, profile
        """
        return self._paginate("users.list", "members", limit=limit)

    def get_user_info(self, user_id: str) -> dict:
        """Get detailed info about a user.

        Args:
            user_id: User ID (e.g., U12345678)

        Returns:
            User dict with id, name, real_name, profile, etc.

        Raises:
            ValueError: If user_id is empty or user not found
        """
        if not user_id:
            raise ValueError("user_id is required")
        result = self._request("GET", "users.info",
                               params={"user": user_id})
        return result.get("user", {})

    def send_message(
        self,
        channel_id: str,
        text: str,
        thread_ts: Optional[str] = None
    ) -> dict:
        """Send a message to a channel.

        Args:
            channel_id: Channel ID to post to
            text: Message text
            thread_ts: Optional thread timestamp to reply in a thread

        Returns:
            Dict with ts (timestamp) of the posted message

        Raises:
            ValueError: If channel_id or text is empty
        """
        if not channel_id or not text:
            raise ValueError("channel_id and text are required")
        payload = {"channel": channel_id, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        return self._request("POST", "chat.postMessage", json_data=payload)


def _format_channel(channel: dict) -> str:
    """Format channel as one-line microformat.

    Example: #general (42 members) [Team announcements]
    """
    name = channel.get("name", "unknown")
    members = channel.get("num_members", "?")
    topic = channel.get("topic", {}).get("value", "")
    topic_str = f" [{topic}]" if topic else ""
    return f"#{name} ({members} members){topic_str}"


def _format_user(user: dict) -> str:
    """Format user as one-line microformat.

    Example: @alice (Alice Smith) [alice@example.com]
    """
    name = user.get("name", "unknown")
    real_name = user.get("real_name", "")
    email = user.get("profile", {}).get("email", "")
    parts = [f"@{name}"]
    if real_name:
        parts.append(f"({real_name})")
    if email:
        parts.append(f"[{email}]")
    return " ".join(parts)


def _format_message(msg: dict, users: Optional[dict] = None) -> str:
    """Format a message for display.

    Args:
        msg: Message dict from Slack API
        users: Optional dict mapping user_id -> display name for resolution

    Example: [2024-01-15 10:30] alice: Hello everyone
    """
    ts = msg.get("ts", "")
    user_id = msg.get("user", "")
    text = msg.get("text", "")

    # Format timestamp
    time_str = ""
    if ts:
        try:
            t = time.gmtime(float(ts))
            time_str = time.strftime("%Y-%m-%d %H:%M", t)
        except (ValueError, OverflowError):
            time_str = ts

    # Resolve user name
    if users and user_id in users:
        user_display = users[user_id]
    elif user_id:
        user_display = user_id
    else:
        user_display = msg.get("username", "unknown")

    # Truncate long messages for one-line display
    text_oneline = text.replace("\n", " ")
    if len(text_oneline) > 200:
        text_oneline = text_oneline[:197] + "..."

    return f"[{time_str}] {user_display}: {text_oneline}"


def main():
    """CLI entry point for Slack client.

    Usage:
        python3 -m sidekick.clients.slack list-channels
        python3 -m sidekick.clients.slack channel-info C09NU0MEGH1
        python3 -m sidekick.clients.slack history C09NU0MEGH1 [--limit 50]
        python3 -m sidekick.clients.slack thread C09NU0MEGH1 1234567890.123456
        python3 -m sidekick.clients.slack users
        python3 -m sidekick.clients.slack user-info U12345678
        python3 -m sidekick.clients.slack send-message C09NU0MEGH1 "Hello world"
    """
    from sidekick.config import get_slack_config

    if len(sys.argv) < 2:
        print("Usage: python3 -m sidekick.clients.slack <command> [args...]")
        print("\nCommands:")
        print("  list-channels")
        print("  channel-info <channel-id>")
        print("  history <channel-id> [--limit N]")
        print("  thread <channel-id> <thread-ts>")
        print("  users")
        print("  user-info <user-id>")
        print("  send-message <channel-id> <text>")
        sys.exit(1)

    try:
        start_time = time.time()

        config = get_slack_config()
        client = SlackClient(bot_token=config["bot_token"])

        command = sys.argv[1]

        if command == "list-channels":
            channels = client.list_channels()
            print(f"Found {len(channels)} channels:")
            for ch in channels:
                print(_format_channel(ch))

        elif command == "channel-info":
            channel = client.get_channel_info(sys.argv[2])
            name = channel.get("name", "unknown")
            topic = channel.get("topic", {}).get("value", "")
            purpose = channel.get("purpose", {}).get("value", "")
            members = channel.get("num_members", "?")
            print(f"#{name}")
            print(f"  Members: {members}")
            if topic:
                print(f"  Topic: {topic}")
            if purpose:
                print(f"  Purpose: {purpose}")
            print(f"  ID: {channel.get('id', '')}")

        elif command == "history":
            channel_id = sys.argv[2]
            limit = 100
            for i, arg in enumerate(sys.argv[3:], 3):
                if arg == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
            messages = client.get_channel_history(channel_id, limit=limit)
            # Build user cache for name resolution
            user_ids = {m.get("user") for m in messages if m.get("user")}
            users_cache = {}
            for uid in user_ids:
                try:
                    user = client.get_user_info(uid)
                    users_cache[uid] = user.get("real_name") or user.get("name", uid)
                except (ValueError, RuntimeError):
                    users_cache[uid] = uid
            print(f"Last {len(messages)} messages:")
            for msg in reversed(messages):
                print(_format_message(msg, users=users_cache))

        elif command == "thread":
            channel_id = sys.argv[2]
            thread_ts = sys.argv[3]
            replies = client.get_thread_replies(channel_id, thread_ts)
            # Build user cache
            user_ids = {m.get("user") for m in replies if m.get("user")}
            users_cache = {}
            for uid in user_ids:
                try:
                    user = client.get_user_info(uid)
                    users_cache[uid] = user.get("real_name") or user.get("name", uid)
                except (ValueError, RuntimeError):
                    users_cache[uid] = uid
            print(f"Thread ({len(replies)} messages):")
            for msg in replies:
                print(_format_message(msg, users=users_cache))

        elif command == "users":
            users = client.get_users()
            print(f"Found {len(users)} users:")
            for u in users:
                if not u.get("deleted") and not u.get("is_bot"):
                    print(_format_user(u))

        elif command == "user-info":
            user = client.get_user_info(sys.argv[2])
            name = user.get("name", "unknown")
            real_name = user.get("real_name", "")
            email = user.get("profile", {}).get("email", "")
            title = user.get("profile", {}).get("title", "")
            print(f"@{name}")
            if real_name:
                print(f"  Name: {real_name}")
            if title:
                print(f"  Title: {title}")
            if email:
                print(f"  Email: {email}")
            print(f"  ID: {user.get('id', '')}")

        elif command == "send-message":
            channel_id = sys.argv[2]
            text = sys.argv[3]
            result = client.send_message(channel_id, text)
            print(f"Message sent (ts: {result.get('ts', 'unknown')})")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

        elapsed_time = time.time() - start_time
        print(
            f"\n[Debug] API calls: {client.api_call_count}, "
            f"Time: {elapsed_time:.2f}s",
            file=sys.stderr
        )

    except (ValueError, RuntimeError, ConnectionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except IndexError:
        print("Error: Missing required arguments. Run without arguments for help.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
