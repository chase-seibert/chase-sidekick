"""Google Calendar API Client - single file implementation with CLI support."""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, List


class GCalendarClient:
    """Google Calendar API client using native Python stdlib."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str, timeout: int = 30):
        """Initialize Google Calendar client with OAuth2 credentials.

        Args:
            client_id: OAuth2 client ID from Google Cloud Console
            client_secret: OAuth2 client secret
            refresh_token: OAuth2 refresh token
            timeout: Request timeout in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.timeout = timeout
        self.access_token = None
        self.api_call_count = 0

    def _refresh_access_token(self) -> str:
        """Refresh OAuth2 access token using refresh token.

        Returns:
            New access token

        Raises:
            ValueError: If token refresh fails
        """
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }

        encoded_data = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(token_url, data=encoded_data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode())
                return result["access_token"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise ValueError(f"Failed to refresh access token: {e.code} - {error_body}")
        except (KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid token response: {e}")

    def _get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        if not self.access_token:
            self.access_token = self._refresh_access_token()
        return self.access_token

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        retry_auth: bool = True
    ) -> Optional[dict]:
        """Make HTTP request to Google Calendar API.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint path
            params: URL query parameters
            json_data: JSON body data
            retry_auth: Whether to retry once on auth failure

        Returns:
            Parsed JSON response as dict, or None for DELETE

        Raises:
            ConnectionError: For network errors
            ValueError: For 4xx client errors
            RuntimeError: For 5xx server errors
        """
        # Build URL
        base_url = "https://www.googleapis.com/calendar/v3"
        url = f"{base_url}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        data = json.dumps(json_data).encode() if json_data else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                self.api_call_count += 1
                body = response.read().decode()
                if not body or body.strip() == "":
                    return None
                return json.loads(body)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""

            # Retry once on 401 (token might be expired)
            if e.code == 401 and retry_auth:
                self.access_token = None  # Force token refresh
                return self._request(method, endpoint, params, json_data, retry_auth=False)

            # Handle 204 No Content (success for DELETE)
            if e.code == 204:
                return None

            if e.code == 404:
                raise ValueError(f"Resource not found: {endpoint}")
            elif e.code >= 400 and e.code < 500:
                raise ValueError(f"Client error {e.code}: {error_body}")
            elif e.code >= 500:
                raise RuntimeError(f"Server error {e.code}: {error_body}")
            else:
                raise ConnectionError(f"HTTP error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Network error: {e.reason}")

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 10,
        order_by: str = "startTime"
    ) -> List[dict]:
        """List calendar events within a date range.

        Args:
            calendar_id: Calendar ID (default: "primary" for main calendar)
            time_min: Start time (RFC3339 timestamp, e.g., "2024-01-01T00:00:00Z")
            time_max: End time (RFC3339 timestamp)
            max_results: Maximum number of events to return
            order_by: Order results by "startTime" or "updated"

        Returns:
            List of event dicts
        """
        params = {
            "maxResults": max_results,
            "singleEvents": "true",  # Expand recurring events
            "orderBy": order_by
        }

        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        result = self._request("GET", f"/calendars/{calendar_id}/events", params=params)
        return result.get("items", []) if result else []

    def get_event(self, event_id: str, calendar_id: str = "primary") -> dict:
        """Get a specific event by ID.

        Args:
            event_id: The event ID
            calendar_id: Calendar ID (default: "primary")

        Returns:
            Event dict with full details
        """
        return self._request("GET", f"/calendars/{calendar_id}/events/{event_id}")

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        calendar_id: str = "primary",
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        tz: str = "UTC"
    ) -> dict:
        """Create a new calendar event.

        Args:
            summary: Event title
            start_time: Start time (RFC3339 timestamp or date for all-day)
            end_time: End time (RFC3339 timestamp or date for all-day)
            calendar_id: Calendar ID (default: "primary")
            description: Event description (optional)
            location: Event location (optional)
            attendees: List of attendee email addresses (optional)
            tz: Timezone for the event (default: "UTC")

        Returns:
            Created event dict
        """
        event_data = {
            "summary": summary,
            "start": {},
            "end": {}
        }

        # Determine if all-day event (date only) or timed event (datetime)
        if "T" in start_time:
            event_data["start"]["dateTime"] = start_time
            event_data["start"]["timeZone"] = tz
            event_data["end"]["dateTime"] = end_time
            event_data["end"]["timeZone"] = tz
        else:
            # All-day event
            event_data["start"]["date"] = start_time
            event_data["end"]["date"] = end_time

        if description:
            event_data["description"] = description
        if location:
            event_data["location"] = location
        if attendees:
            event_data["attendees"] = [{"email": email} for email in attendees]

        return self._request("POST", f"/calendars/{calendar_id}/events", json_data=event_data)

    def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        tz: str = "UTC"
    ) -> dict:
        """Update an existing calendar event.

        Args:
            event_id: The event ID to update
            calendar_id: Calendar ID (default: "primary")
            summary: New event title (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            description: New description (optional)
            location: New location (optional)
            attendees: New list of attendee emails (optional)
            tz: Timezone for the event (default: "UTC")

        Returns:
            Updated event dict
        """
        # Get existing event first
        event = self.get_event(event_id, calendar_id)

        # Update fields
        if summary is not None:
            event["summary"] = summary
        if description is not None:
            event["description"] = description
        if location is not None:
            event["location"] = location
        if attendees is not None:
            event["attendees"] = [{"email": email} for email in attendees]

        if start_time is not None:
            if "T" in start_time:
                event["start"] = {"dateTime": start_time, "timeZone": tz}
            else:
                event["start"] = {"date": start_time}

        if end_time is not None:
            if "T" in end_time:
                event["end"] = {"dateTime": end_time, "timeZone": tz}
            else:
                event["end"] = {"date": end_time}

        return self._request("PUT", f"/calendars/{calendar_id}/events/{event_id}", json_data=event)

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        """Delete a calendar event.

        Args:
            event_id: The event ID to delete
            calendar_id: Calendar ID (default: "primary")
        """
        self._request("DELETE", f"/calendars/{calendar_id}/events/{event_id}")


def _format_event_oneline(event: dict) -> str:
    """Format event as one-line summary."""
    event_id = event.get("id", "")
    summary = event.get("summary", "(No title)")

    # Get start time
    start = event.get("start", {})
    if "dateTime" in start:
        start_str = start["dateTime"][:16].replace("T", " ")  # YYYY-MM-DD HH:MM
    elif "date" in start:
        start_str = start["date"] + " (all-day)"
    else:
        start_str = "Unknown time"

    location = event.get("location", "")
    location_str = f" @ {location}" if location else ""

    return f"{event_id}: {summary}\n  {start_str}{location_str}"


def _format_event_full(event: dict) -> str:
    """Format full event details."""
    lines = [
        f"Event ID: {event.get('id', 'Unknown')}",
        f"Summary: {event.get('summary', '(No title)')}",
    ]

    # Start time
    start = event.get("start", {})
    if "dateTime" in start:
        lines.append(f"Start: {start['dateTime']}")
    elif "date" in start:
        lines.append(f"Start: {start['date']} (all-day)")

    # End time
    end = event.get("end", {})
    if "dateTime" in end:
        lines.append(f"End: {end['dateTime']}")
    elif "date" in end:
        lines.append(f"End: {end['date']} (all-day)")

    # Optional fields
    if "description" in event:
        lines.append(f"Description: {event['description']}")
    if "location" in event:
        lines.append(f"Location: {event['location']}")
    if "attendees" in event:
        attendee_emails = [a.get("email", "") for a in event["attendees"]]
        lines.append(f"Attendees: {', '.join(attendee_emails)}")
    if "htmlLink" in event:
        lines.append(f"Link: {event['htmlLink']}")

    return "\n".join(lines)


def main():
    """CLI interface for Google Calendar client."""
    if len(sys.argv) < 2:
        print("Usage: python -m sidekick.clients.gcalendar <command> [args]")
        print("\nCommands:")
        print("  list [time_min] [time_max] [max_results] - List events in date range")
        print("  get <event_id>                            - Get event details")
        print("  create <summary> <start> <end>            - Create new event")
        print("  update <event_id> <field> <value>         - Update event field")
        print("  delete <event_id>                         - Delete event")
        print("\nExamples:")
        print('  python -m sidekick.clients.gcalendar list "2024-01-01T00:00:00Z" "2024-01-31T23:59:59Z"')
        print('  python -m sidekick.clients.gcalendar get abc123def456')
        print('  python -m sidekick.clients.gcalendar create "Team Meeting" "2024-01-15T14:00:00Z" "2024-01-15T15:00:00Z"')
        print('  python -m sidekick.clients.gcalendar update abc123def456 summary "Updated Title"')
        print('  python -m sidekick.clients.gcalendar delete abc123def456')
        sys.exit(1)

    # Load configuration
    try:
        from sidekick.config import get_google_config
        config = get_google_config()
    except ImportError:
        print("Error: Could not import config module", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Create client
    client = GCalendarClient(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        refresh_token=config["refresh_token"]
    )

    command = sys.argv[1]

    try:
        if command == "list":
            time_min = sys.argv[2] if len(sys.argv) > 2 else None
            time_max = sys.argv[3] if len(sys.argv) > 3 else None
            max_results = int(sys.argv[4]) if len(sys.argv) > 4 else 10

            events = client.list_events(
                time_min=time_min,
                time_max=time_max,
                max_results=max_results
            )
            print(f"Found {len(events)} events:\n")
            for event in events:
                print(_format_event_oneline(event))
                print()

        elif command == "get":
            if len(sys.argv) < 3:
                print("Error: Missing event_id argument", file=sys.stderr)
                sys.exit(1)

            event_id = sys.argv[2]
            event = client.get_event(event_id)
            print(_format_event_full(event))

        elif command == "create":
            if len(sys.argv) < 5:
                print("Error: Missing arguments. Need: summary, start_time, end_time", file=sys.stderr)
                sys.exit(1)

            summary = sys.argv[2]
            start_time = sys.argv[3]
            end_time = sys.argv[4]

            event = client.create_event(summary, start_time, end_time)
            print("Event created successfully!")
            print(_format_event_full(event))

        elif command == "update":
            if len(sys.argv) < 5:
                print("Error: Missing arguments. Need: event_id, field, value", file=sys.stderr)
                sys.exit(1)

            event_id = sys.argv[2]
            field = sys.argv[3]
            value = sys.argv[4]

            # Map field names to update_event parameters
            kwargs = {"event_id": event_id}
            if field in ["summary", "description", "location"]:
                kwargs[field] = value
            elif field in ["start", "start_time"]:
                kwargs["start_time"] = value
            elif field in ["end", "end_time"]:
                kwargs["end_time"] = value
            else:
                print(f"Error: Unknown field '{field}'. Use: summary, description, location, start_time, end_time", file=sys.stderr)
                sys.exit(1)

            event = client.update_event(**kwargs)
            print("Event updated successfully!")
            print(_format_event_full(event))

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Error: Missing event_id argument", file=sys.stderr)
                sys.exit(1)

            event_id = sys.argv[2]
            client.delete_event(event_id)
            print(f"Event deleted successfully: {event_id}")

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            sys.exit(1)

    except (ValueError, RuntimeError, ConnectionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
