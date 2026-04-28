"""Google Calendar API Client - single file implementation with CLI support."""

import argparse
import sys
import json
import re
import urllib.request
import urllib.parse
import urllib.error
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, List


DEFAULT_AUDIT_INSTANCES = 4
DEFAULT_AUDIT_THRESHOLD = 0.50
DEFAULT_AUDIT_MIN_INSTANCES = 4
DEFAULT_AUDIT_LOOKBACK_DAYS = 180
DEFAULT_AUDIT_LOOKAHEAD_DAYS = 180
DEFAULT_AUDIT_SEND_UPDATES = "all"
RSVP_STATUSES = {"accepted", "declined", "tentative", "needsAction"}
SPLIT_RECURRING_SERIES_RE = re.compile(r"^(.+)_R\d{8}T\d{6}$")


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

    def _calendar_endpoint(self, calendar_id: str, suffix: str) -> str:
        """Build a URL-safe Calendar API endpoint for a calendar."""
        return f"/calendars/{urllib.parse.quote(calendar_id, safe='')}{suffix}"

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

    def list_events_paginated(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 2500,
        order_by: str = "startTime",
        single_events: bool = True
    ) -> List[dict]:
        """List all calendar events in a range, following nextPageToken pages."""
        params = {
            "maxResults": max_results,
            "orderBy": order_by
        }
        if single_events:
            params["singleEvents"] = "true"
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        events = []
        page_token = None
        while True:
            if page_token:
                params["pageToken"] = page_token
            else:
                params.pop("pageToken", None)

            result = self._request("GET", self._calendar_endpoint(calendar_id, "/events"), params=params)
            if not result:
                break
            events.extend(result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return events

    def list_event_instances(
        self,
        event_id: str,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 2500,
        max_items: Optional[int] = None
    ) -> List[dict]:
        """List instances for one recurring event, following nextPageToken pages."""
        page_size = min(max_results, max_items) if max_items else max_results
        params = {"maxResults": page_size}
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        events = []
        page_token = None
        event_path = urllib.parse.quote(event_id, safe="")
        while True:
            if page_token:
                params["pageToken"] = page_token
            else:
                params.pop("pageToken", None)

            result = self._request(
                "GET",
                self._calendar_endpoint(calendar_id, f"/events/{event_path}/instances"),
                params=params
            )
            if not result:
                break
            events.extend(result.get("items", []))
            if max_items and len(events) >= max_items:
                return events[:max_items]
            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return events

    def get_event(self, event_id: str, calendar_id: str = "primary") -> dict:
        """Get a specific event by ID.

        Args:
            event_id: The event ID
            calendar_id: Calendar ID (default: "primary")

        Returns:
            Event dict with full details
        """
        return self._request(
            "GET",
            self._calendar_endpoint(calendar_id, f"/events/{urllib.parse.quote(event_id, safe='')}")
        )

    def patch_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        patch_data: Optional[dict] = None,
        send_updates: str = "all"
    ) -> dict:
        """Patch an event with partial data."""
        params = {"sendUpdates": send_updates}
        return self._request(
            "PATCH",
            self._calendar_endpoint(calendar_id, f"/events/{urllib.parse.quote(event_id, safe='')}"),
            params=params,
            json_data=patch_data or {}
        )

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

    def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        send_updates: str = "all"
    ) -> None:
        """Delete a calendar event.

        Args:
            event_id: The event ID to delete
            calendar_id: Calendar ID (default: "primary")
            send_updates: Whether to send notifications ("all", "externalOnly", "none")
        """
        params = {"sendUpdates": send_updates}
        self._request("DELETE", f"/calendars/{calendar_id}/events/{event_id}", params=params)

    def respond_to_event(
        self,
        event_id: str,
        response_status: str,
        calendar_id: str = "primary",
        comment: Optional[str] = None,
        send_updates: str = "all"
    ) -> dict:
        """Respond to a calendar event invitation.

        Args:
            event_id: The event ID
            response_status: "accepted", "declined", or "tentative"
            calendar_id: Calendar ID (default: "primary")
            comment: Optional comment to include with response
            send_updates: Whether to send notifications ("all", "externalOnly", "none")

        Returns:
            Updated event dict

        Raises:
            ValueError: If user is not an attendee of the event
        """
        # Get event to find current user's attendee entry
        event = self.get_event(event_id, calendar_id)

        # Find user's attendee entry (marked with "self": true)
        user_attendee = None
        for attendee in event.get("attendees", []):
            if attendee.get("self"):
                user_attendee = attendee
                break

        if not user_attendee:
            raise ValueError("Cannot respond to event: user is not an attendee")

        # Update user's response status
        user_attendee["responseStatus"] = response_status
        if comment:
            user_attendee["comment"] = comment

        # PATCH the event with only the attendees field
        # Using PATCH instead of PUT to avoid overwriting other fields
        patch_data = {"attendees": event["attendees"]}
        params = {"sendUpdates": send_updates}
        return self._request("PATCH", f"/calendars/{calendar_id}/events/{event_id}", params=params, json_data=patch_data)

    def decline_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        message: Optional[str] = None,
        send_updates: str = "all"
    ) -> dict:
        """Decline a calendar event invitation.

        Args:
            event_id: The event ID
            calendar_id: Calendar ID (default: "primary")
            message: Optional decline message
            send_updates: Whether to send notifications ("all", "externalOnly", "none")

        Returns:
            Updated event dict
        """
        return self.respond_to_event(event_id, "declined", calendar_id, message, send_updates)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def _event_start(event: dict) -> Optional[datetime]:
    return _parse_datetime(event.get("start", {}).get("dateTime"))


def _format_dt(dt: Optional[datetime]) -> str:
    if dt is None:
        return "unknown"
    return dt.astimezone().strftime("%Y-%m-%d %I:%M %p %Z").replace(" 0", " ")


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def _is_recurring_meeting_instance(event: dict) -> bool:
    if event.get("status") == "cancelled":
        return False
    if not event.get("recurringEventId"):
        return False
    if event.get("start", {}).get("date") and not event.get("start", {}).get("dateTime"):
        return False
    return len(event.get("attendees") or []) > 1


def _recurring_family_id(series_id: str) -> str:
    match = SPLIT_RECURRING_SERIES_RE.match(series_id or "")
    return match.group(1) if match else series_id


def _group_recurring_instances_by_family(events: List[dict]) -> dict:
    grouped = defaultdict(list)
    for event in events:
        recurring_id = event.get("recurringEventId")
        if not recurring_id:
            continue
        grouped[_recurring_family_id(recurring_id)].append(event)
    return grouped


def _attendee_by_email(event: dict) -> dict:
    attendees = {}
    for attendee in event.get("attendees") or []:
        email = _normalize_email(attendee.get("email"))
        if email:
            attendees[email] = attendee
    return attendees


def _is_excluded_attendee(attendee: dict, organizer_email: str) -> bool:
    email = _normalize_email(attendee.get("email"))
    if not email:
        return True
    if attendee.get("self"):
        return True
    if attendee.get("resource"):
        return True
    return email == organizer_email


def _response_status(attendee: Optional[dict]) -> str:
    if not attendee:
        return "missing"
    status = attendee.get("responseStatus") or "needsAction"
    return status if status in RSVP_STATUSES else "unknown"


def _analyze_attendees(
    master_event: dict,
    instances: List[dict],
    threshold: float,
    min_instances: int
) -> tuple:
    organizer_email = _normalize_email(master_event.get("organizer", {}).get("email"))
    instance_attendees = [_attendee_by_email(instance) for instance in instances]
    attendee_stats = []
    suggestions = []

    for attendee in master_event.get("attendees") or []:
        email = _normalize_email(attendee.get("email"))
        if _is_excluded_attendee(attendee, organizer_email):
            continue

        counts = Counter()
        seen_count = 0
        for attendees in instance_attendees:
            status = _response_status(attendees.get(email))
            counts[status] += 1
            if status != "missing":
                seen_count += 1

        bad_count = counts["declined"] + counts["needsAction"]
        bad_rate = bad_count / seen_count if seen_count else 0.0
        stat = {
            "email": email,
            "display_name": attendee.get("displayName", ""),
            "seen_instances": seen_count,
            "evaluated_instances": len(instances),
            "accepted": counts["accepted"],
            "declined": counts["declined"],
            "tentative": counts["tentative"],
            "needs_action": counts["needsAction"],
            "missing": counts["missing"],
            "bad_count": bad_count,
            "bad_rate": round(bad_rate, 4),
        }
        attendee_stats.append(stat)
        if len(instances) >= min_instances and seen_count >= min_instances and bad_rate >= threshold:
            suggestions.append(stat)

    attendee_stats.sort(key=lambda item: (-item["bad_rate"], item["email"]))
    suggestions.sort(key=lambda item: (-item["bad_rate"], item["email"]))
    return attendee_stats, suggestions


def _owner_label(record: dict) -> str:
    if record.get("owned_by_me"):
        return "Meetings I own"
    name = record.get("owner_name")
    email = record.get("owner_email", "unknown")
    return f"{name} ({email})" if name else email


def _format_audit_counts(stat: dict) -> str:
    return (
        f"A {stat['accepted']}, D {stat['declined']}, "
        f"T {stat['tentative']}, NR {stat['needs_action']}"
    )


def _render_suggestions_table(suggestions: List[dict]) -> List[str]:
    if not suggestions:
        return ["No suggested removals."]
    lines = [
        "| Attendee | Non-attendance rate | RSVP counts | Seen |",
        "| --- | ---: | --- | ---: |",
    ]
    for stat in suggestions:
        rate = f"{stat['bad_rate'] * 100:.0f}%"
        lines.append(
            f"| `{stat['email']}` | {rate} | {_format_audit_counts(stat)} | "
            f"{stat['seen_instances']}/{stat['evaluated_instances']} |"
        )
    return lines


def _unique_recurring_series(events: List[dict]) -> List[dict]:
    series = {}
    for event in events:
        if not _is_recurring_meeting_instance(event):
            continue
        series_id = _recurring_family_id(event["recurringEventId"])
        existing = series.get(series_id)
        if not existing or (_event_start(event) or datetime.max.replace(tzinfo=timezone.utc)) < (_event_start(existing) or datetime.max.replace(tzinfo=timezone.utc)):
            series[series_id] = event
    return sorted(series.values(), key=lambda event: _event_start(event) or datetime.max.replace(tzinfo=timezone.utc))


def _is_evaluable_instance(event: dict) -> bool:
    if event.get("status") == "cancelled":
        return False
    if event.get("start", {}).get("date") and not event.get("start", {}).get("dateTime"):
        return False
    return len(event.get("attendees") or []) > 1


def _audit_recurring_meetings(
    client: GCalendarClient,
    calendar_id: str,
    created_at: datetime,
    instances_to_check: int,
    threshold: float,
    min_instances: int,
    lookback_days: int,
    lookahead_days: int
) -> tuple:
    upcoming_events = client.list_events_paginated(
        calendar_id=calendar_id,
        time_min=_iso_z(created_at),
        time_max=_iso_z(created_at + timedelta(days=lookahead_days)),
    )
    past_events = client.list_events_paginated(
        calendar_id=calendar_id,
        time_min=_iso_z(created_at - timedelta(days=lookback_days)),
        time_max=_iso_z(created_at),
    )
    past_instances_by_family = _group_recurring_instances_by_family(past_events)
    recurring_meetings = _unique_recurring_series(upcoming_events)
    reviewed_meetings = []
    records = []

    for next_instance in recurring_meetings:
        series_id = next_instance["recurringEventId"]
        reviewed = {
            "series_id": series_id,
            "summary": next_instance.get("summary") or "(No title)",
            "owner_email": _normalize_email(next_instance.get("organizer", {}).get("email")) or "unknown",
            "owner_name": next_instance.get("organizer", {}).get("displayName", ""),
            "owned_by_me": bool(next_instance.get("organizer", {}).get("self")),
            "next_occurrence": _iso_z(_event_start(next_instance)) if _event_start(next_instance) else "",
            "status": "reviewed",
            "recommendation_count": 0,
        }
        try:
            master_event = client.get_event(series_id, calendar_id)
            owner = master_event.get("organizer") or next_instance.get("organizer") or {}
            reviewed.update({
                "summary": master_event.get("summary") or reviewed["summary"],
                "owner_email": _normalize_email(owner.get("email")) or "unknown",
                "owner_name": owner.get("displayName", ""),
                "owned_by_me": bool(owner.get("self")),
            })
            prior_instances = client.list_event_instances(
                series_id,
                calendar_id=calendar_id,
                time_min=_iso_z(created_at - timedelta(days=lookback_days)),
                time_max=_iso_z(created_at),
            )
        except Exception as exc:
            reviewed["status"] = f"skipped: {exc}"
            reviewed_meetings.append(reviewed)
            print(f"Warning: skipped recurring meeting {series_id}: {exc}", file=sys.stderr)
            continue
        combined_prior_instances = {
            event.get("id"): event
            for event in prior_instances + past_instances_by_family.get(_recurring_family_id(series_id), [])
            if event.get("id")
        }

        evaluated_instances = sorted(
            [event for event in combined_prior_instances.values() if _is_evaluable_instance(event)],
            key=lambda event: _event_start(event) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )[:instances_to_check]
        if len(evaluated_instances) < min_instances:
            reviewed["status"] = f"insufficient history ({len(evaluated_instances)}/{min_instances} instances in {lookback_days} days)"
            reviewed_meetings.append(reviewed)
            continue

        attendee_stats, suggestions = _analyze_attendees(
            master_event,
            evaluated_instances,
            threshold=threshold,
            min_instances=min_instances
        )
        if not suggestions:
            reviewed["status"] = "no recommendations"
            reviewed_meetings.append(reviewed)
            continue

        reviewed["status"] = "recommended removals"
        reviewed["recommendation_count"] = len(suggestions)
        reviewed_meetings.append(reviewed)
        owner = master_event.get("organizer") or next_instance.get("organizer") or {}
        owned_by_me = bool(owner.get("self"))
        guests_can_modify = bool(master_event.get("guestsCanModify") or next_instance.get("guestsCanModify"))
        records.append({
            "series_id": series_id,
            "summary": master_event.get("summary") or next_instance.get("summary") or "(No title)",
            "owner_email": _normalize_email(owner.get("email")) or "unknown",
            "owner_name": owner.get("displayName", ""),
            "owned_by_me": owned_by_me,
            "guests_can_modify": guests_can_modify,
            "actionable": bool(owned_by_me or guests_can_modify),
            "calendar_id": calendar_id,
            "html_link": master_event.get("htmlLink") or next_instance.get("htmlLink", ""),
            "next_occurrence": _iso_z(_event_start(next_instance)) if _event_start(next_instance) else "",
            "evaluated_instances": [
                {
                    "event_id": instance.get("id", ""),
                    "start": _iso_z(_event_start(instance)) if _event_start(instance) else "",
                }
                for instance in evaluated_instances
            ],
            "evaluated_instance_count": len(evaluated_instances),
            "attendee_stats": attendee_stats,
            "suggested_removals": suggestions,
        })

    records.sort(
        key=lambda record: (
            not record["owned_by_me"],
            record["owner_email"],
            record["summary"].lower(),
            record["series_id"]
        )
    )
    return records, reviewed_meetings


def _build_attendance_audit_output(records: List[dict], reviewed_meetings: List[dict], settings: dict, created_at: datetime) -> dict:
    suggestion_count = sum(len(record.get("suggested_removals", [])) for record in records)
    actionable_count = sum(1 for record in records if record.get("actionable"))
    return {
        "created_at": _iso_z(created_at),
        "settings": settings,
        "summary": {
            "unique_recurring_meetings_scanned": len(reviewed_meetings),
            "meetings_with_suggested_removals": len(records),
            "suggested_attendee_removals": suggestion_count,
            "actionable_meetings_with_suggestions": actionable_count,
        },
        "meetings_reviewed": reviewed_meetings,
        "recommended_removals": records,
    }


def _parse_email_list(value: str) -> List[str]:
    emails = []
    for chunk in value.split(","):
        email = _normalize_email(chunk)
        if email:
            emails.append(email)
    return emails


def _remove_attendees_from_recurring_event(
    client: GCalendarClient,
    calendar_id: str,
    series_id: str,
    emails: List[str],
    send_updates: str
) -> dict:
    requested = {_normalize_email(email) for email in emails if _normalize_email(email)}
    if not requested:
        return {
            "status": "noop",
            "summary": "",
            "requested_emails": [],
            "removed_emails": [],
            "missing_emails": [],
            "protected_emails": [],
        }

    master = client.get_event(series_id, calendar_id)
    if master.get("attendeesOmitted"):
        raise ValueError("Cannot safely patch attendees because the event returned attendeesOmitted=true")

    organizer_email = _normalize_email(master.get("organizer", {}).get("email"))
    kept_attendees = []
    removed_emails = []
    protected_emails = []
    current_emails = set()

    for attendee in master.get("attendees") or []:
        email = _normalize_email(attendee.get("email"))
        if email:
            current_emails.add(email)
        if email in requested:
            if attendee.get("self") or attendee.get("resource") or email == organizer_email:
                protected_emails.append(email)
                kept_attendees.append(attendee)
            else:
                removed_emails.append(email)
        else:
            kept_attendees.append(attendee)

    missing_emails = sorted(requested - current_emails)
    if not removed_emails:
        return {
            "status": "noop",
            "summary": master.get("summary", "(No title)"),
            "requested_emails": sorted(requested),
            "removed_emails": [],
            "missing_emails": missing_emails,
            "protected_emails": sorted(protected_emails),
        }

    updated = client.patch_event(
        series_id,
        calendar_id=calendar_id,
        patch_data={"attendees": kept_attendees},
        send_updates=send_updates
    )
    return {
        "status": "success",
        "summary": master.get("summary", "(No title)"),
        "requested_emails": sorted(requested),
        "removed_emails": sorted(removed_emails),
        "missing_emails": missing_emails,
        "protected_emails": sorted(protected_emails),
        "updated_event_id": updated.get("id", series_id) if updated else series_id,
    }


def _remove_attendees_from_future_instances(
    client: GCalendarClient,
    calendar_id: str,
    series_id: str,
    emails: List[str],
    send_updates: str,
    future_start: Optional[datetime] = None,
    max_instances: int = 2500
) -> dict:
    requested = {_normalize_email(email) for email in emails if _normalize_email(email)}
    if not requested:
        return {
            "status": "noop",
            "summary": "",
            "requested_emails": [],
            "removed_emails": [],
            "missing_emails": [],
            "protected_emails": [],
            "updated_instances": 0,
        }

    future_start = future_start or _now_utc()
    master = client.get_event(series_id, calendar_id)
    instances = client.list_event_instances(
        series_id,
        calendar_id=calendar_id,
        time_min=_iso_z(future_start),
        max_items=max_instances,
    )

    updated_instances = 0
    removed_emails = set()
    protected_emails = set()
    seen_emails = set()

    for instance in instances:
        if instance.get("status") == "cancelled":
            continue
        attendees = instance.get("attendees") or []
        if not attendees:
            continue

        organizer_email = _normalize_email(instance.get("organizer", {}).get("email") or master.get("organizer", {}).get("email"))
        kept_attendees = []
        removed_from_instance = []

        for attendee in attendees:
            email = _normalize_email(attendee.get("email"))
            if email:
                seen_emails.add(email)
            if email in requested:
                if attendee.get("self") or attendee.get("resource") or email == organizer_email:
                    protected_emails.add(email)
                    kept_attendees.append(attendee)
                else:
                    removed_emails.add(email)
                    removed_from_instance.append(email)
            else:
                kept_attendees.append(attendee)

        if removed_from_instance:
            client.patch_event(
                instance["id"],
                calendar_id=calendar_id,
                patch_data={"attendees": kept_attendees},
                send_updates=send_updates
            )
            updated_instances += 1

    missing_emails = sorted(requested - seen_emails)
    status = "success" if updated_instances else "noop"
    return {
        "status": status,
        "summary": master.get("summary", "(No title)"),
        "requested_emails": sorted(requested),
        "removed_emails": sorted(removed_emails),
        "missing_emails": missing_emails,
        "protected_emails": sorted(protected_emails),
        "updated_instances": updated_instances,
        "max_instances": max_instances,
        "future_start": _iso_z(future_start),
    }


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

    # Conference data (Zoom, Meet, etc.)
    if "conferenceData" in event:
        conf = event["conferenceData"]
        if "entryPoints" in conf:
            for entry in conf["entryPoints"]:
                if entry.get("entryPointType") == "video":
                    lines.append(f"Video Link: {entry.get('uri', '')}")
        if "conferenceSolution" in conf:
            lines.append(f"Conference: {conf['conferenceSolution'].get('name', '')}")
    elif "hangoutLink" in event:
        lines.append(f"Hangout Link: {event['hangoutLink']}")

    if "attendees" in event:
        attendee_emails = [a.get("email", "") for a in event["attendees"]]
        lines.append(f"Attendees: {', '.join(attendee_emails)}")
    if "htmlLink" in event:
        lines.append(f"Link: {event['htmlLink']}")

    return "\n".join(lines)


def _attendance_audit_audit_command(client: GCalendarClient, args: argparse.Namespace) -> int:
    created_at = _now_utc()
    records, reviewed_meetings = _audit_recurring_meetings(
        client,
        calendar_id=args.calendar_id,
        created_at=created_at,
        instances_to_check=args.instances,
        threshold=args.threshold,
        min_instances=args.min_instances,
        lookback_days=args.lookback_days,
        lookahead_days=args.lookahead_days,
    )
    settings = {
        "instances": args.instances,
        "threshold": args.threshold,
        "min_instances": args.min_instances,
        "lookback_days": args.lookback_days,
        "lookahead_days": args.lookahead_days,
    }
    output = _build_attendance_audit_output(
        records,
        reviewed_meetings,
        settings,
        created_at,
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


def _handle_attendance_audit_cli(client: Optional[GCalendarClient], argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m sidekick.clients.gcalendar attendance-audit",
        description="Audit recurring meetings by Google Calendar RSVP history."
    )
    subparsers = parser.add_subparsers(dest="audit_command", required=True)

    audit = subparsers.add_parser("audit", help="print recurring meeting attendance audit data as JSON")
    audit.add_argument("--calendar-id", default="primary")
    audit.add_argument("--instances", type=int, default=DEFAULT_AUDIT_INSTANCES)
    audit.add_argument("--threshold", type=float, default=DEFAULT_AUDIT_THRESHOLD)
    audit.add_argument("--min-instances", type=int, default=DEFAULT_AUDIT_MIN_INSTANCES)
    audit.add_argument("--lookback-days", type=int, default=DEFAULT_AUDIT_LOOKBACK_DAYS)
    audit.add_argument("--lookahead-days", type=int, default=DEFAULT_AUDIT_LOOKAHEAD_DAYS)
    args = parser.parse_args(argv)

    if args.audit_command == "audit":
        return _attendance_audit_audit_command(client, args)
    parser.error(f"Unknown attendance-audit command: {args.audit_command}")
    return 2


def _handle_remove_attendees_cli(client: GCalendarClient, argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m sidekick.clients.gcalendar remove-attendees",
        description="Remove attendees from one Calendar event or recurring master event."
    )
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--emails", required=True, help="comma-separated email addresses to remove")
    parser.add_argument("--calendar-id", default="primary")
    parser.add_argument("--scope", default="future-instances", choices=["future-instances", "whole-series"])
    parser.add_argument("--future-start", default="", help="RFC3339 start for future-instance removals; defaults to now")
    parser.add_argument("--max-instances", type=int, default=2500, help="safety cap for future-instance removals")
    parser.add_argument("--send-updates", default=DEFAULT_AUDIT_SEND_UPDATES, choices=["all", "externalOnly", "none"])
    args = parser.parse_args(argv)

    emails = _parse_email_list(args.emails)
    if args.scope == "whole-series":
        result = _remove_attendees_from_recurring_event(
            client,
            args.calendar_id,
            args.event_id,
            emails,
            args.send_updates,
        )
    else:
        future_start = _parse_datetime(args.future_start) if args.future_start else None
        if args.future_start and future_start is None:
            raise ValueError(f"Invalid --future-start datetime: {args.future_start}")
        result = _remove_attendees_from_future_instances(
            client,
            args.calendar_id,
            args.event_id,
            emails,
            args.send_updates,
            future_start=future_start,
            max_instances=args.max_instances,
        )

    summary = result.get("summary") or args.event_id
    result["summary"] = summary
    result["scope"] = args.scope
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main():
    """CLI interface for Google Calendar client."""
    if len(sys.argv) < 2:
        print("Usage: python -m sidekick.clients.gcalendar <command> [args]")
        print("\nCommands:")
        print("  list [time_min] [time_max] [max_results] - List events in date range")
        print("  get <event_id>                            - Get event details")
        print("  create <summary> <start> <end>            - Create new event")
        print("  update <event_id> <field> <value>         - Update event field")
        print("  delete <event_id> [--no-notify]           - Delete event")
        print("  decline <event_id> [message] [--no-notify] - Decline event invitation")
        print("  respond <event_id> <status> [comment] [--no-notify] - Respond to event (accepted/declined/tentative)")
        print("  attendance-audit <subcommand>             - Audit recurring meeting RSVP history")
        print("  remove-attendees --event-id ID --emails EMAILS - Remove attendees from an event")
        print("\nFlags:")
        print("  --no-notify  - Don't send email notifications to attendees/organizers")
        print("\nExamples:")
        print('  python -m sidekick.clients.gcalendar list "2024-01-01T00:00:00Z" "2024-01-31T23:59:59Z"')
        print('  python -m sidekick.clients.gcalendar get abc123def456')
        print('  python -m sidekick.clients.gcalendar create "Team Meeting" "2024-01-15T14:00:00Z" "2024-01-15T15:00:00Z"')
        print('  python -m sidekick.clients.gcalendar update abc123def456 summary "Updated Title"')
        print('  python -m sidekick.clients.gcalendar delete abc123def456 --no-notify')
        print('  python -m sidekick.clients.gcalendar decline abc123def456 "Out of office" --no-notify')
        print('  python -m sidekick.clients.gcalendar respond abc123def456 accepted "See you there!"')
        print('  python -m sidekick.clients.gcalendar attendance-audit audit')
        print('  python -m sidekick.clients.gcalendar remove-attendees --event-id abc123def456 --emails "a@example.com,b@example.com"')
        sys.exit(1)

    command = sys.argv[1]
    if command == "attendance-audit" and ("--help" in sys.argv[2:] or "-h" in sys.argv[2:]):
        sys.exit(_handle_attendance_audit_cli(None, sys.argv[2:]))
    if command == "remove-attendees" and ("--help" in sys.argv[2:] or "-h" in sys.argv[2:]):
        sys.exit(_handle_remove_attendees_cli(None, sys.argv[2:]))

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

    try:
        if command == "attendance-audit":
            sys.exit(_handle_attendance_audit_cli(client, sys.argv[2:]))

        elif command == "remove-attendees":
            sys.exit(_handle_remove_attendees_cli(client, sys.argv[2:]))

        elif command == "list":
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
            send_updates = "none" if "--no-notify" in sys.argv else "all"
            client.delete_event(event_id, send_updates=send_updates)
            print(f"Event deleted successfully: {event_id}")

        elif command == "decline":
            if len(sys.argv) < 3:
                print("Error: Missing event_id argument", file=sys.stderr)
                sys.exit(1)

            event_id = sys.argv[2]
            message = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "--no-notify" else None
            send_updates = "none" if "--no-notify" in sys.argv else "all"

            event = client.decline_event(event_id, message=message, send_updates=send_updates)
            notify_msg = " (no notifications sent)" if send_updates == "none" else ""
            print(f"Event declined successfully!{notify_msg}")
            print(_format_event_full(event))

        elif command == "respond":
            if len(sys.argv) < 4:
                print("Error: Missing arguments. Need: event_id, status (accepted/declined/tentative)", file=sys.stderr)
                sys.exit(1)

            event_id = sys.argv[2]
            response_status = sys.argv[3]
            comment = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "--no-notify" else None
            send_updates = "none" if "--no-notify" in sys.argv else "all"

            if response_status not in ["accepted", "declined", "tentative"]:
                print("Error: status must be 'accepted', 'declined', or 'tentative'", file=sys.stderr)
                sys.exit(1)

            event = client.respond_to_event(event_id, response_status, comment=comment, send_updates=send_updates)
            notify_msg = " (no notifications sent)" if send_updates == "none" else ""
            print(f"Event response set to '{response_status}' successfully!{notify_msg}")
            print(_format_event_full(event))

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            sys.exit(1)

    except (ValueError, RuntimeError, ConnectionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
