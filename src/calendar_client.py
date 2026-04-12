from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Tuple

from dateutil.parser import isoparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from classifier import CategoryRule, classify_event

# Full Calendar scope: events list/patch AND colors.get(). The Colors API does not
# accept calendar.events alone (403 insufficientPermissions).
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Last-resort palette if colors.get() fails (matches typical Google Calendar API v3).
_FALLBACK_EVENT_COLORS = {
    "1": {"background": "#a4bdfc", "foreground": "#1d1d1d"},
    "2": {"background": "#7ae7bf", "foreground": "#1d1d1d"},
    "3": {"background": "#dbadff", "foreground": "#1d1d1d"},
    "4": {"background": "#ff887c", "foreground": "#1d1d1d"},
    "5": {"background": "#fbd75b", "foreground": "#1d1d1d"},
    "6": {"background": "#ffb878", "foreground": "#1d1d1d"},
    "7": {"background": "#46d6db", "foreground": "#1d1d1d"},
    "8": {"background": "#e1e1e1", "foreground": "#1d1d1d"},
    "9": {"background": "#5484ed", "foreground": "#1d1d1d"},
    "10": {"background": "#51b749", "foreground": "#1d1d1d"},
    "11": {"background": "#dc2127", "foreground": "#1d1d1d"},
}


@dataclass
class RunStats:
    scanned: int = 0
    matched: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    cancelled: int = 0


def _parse_start(start: Dict) -> datetime:
    if not start:
        return datetime.min.replace(tzinfo=timezone.utc)
    if "dateTime" in start:
        return isoparse(start["dateTime"])
    # All-day events use midnight date; treat as UTC for sorting and range ops.
    return datetime.fromisoformat(f"{start['date']}T00:00:00+00:00")


class CalendarColorFixer:
    def __init__(
        self,
        calendar_id: str,
        credentials_file: str,
        token_file: str,
        past_days: int,
        future_days: int,
        rules_by_name: Dict[str, CategoryRule],
        priority: List[str],
        allowed_organizers: Optional[List[str]] = None,
    ) -> None:
        self.calendar_id = calendar_id
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.past_days = past_days
        self.future_days = future_days
        self.rules_by_name = rules_by_name
        self.priority = priority
        self.allowed_organizers = {email.lower() for email in allowed_organizers or []}
        self.service = self._build_service()

    def _token_has_required_scopes(self, creds: Credentials) -> bool:
        granted = set(creds.scopes or [])
        return granted >= set(SCOPES)

    def _build_service(self):
        creds = None
        try:
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        except FileNotFoundError:
            pass

        if creds and not self._token_has_required_scopes(creds):
            logging.warning(
                "Saved token is missing required OAuth scopes; removing %s for re-consent.",
                self.token_file,
            )
            try:
                os.remove(self.token_file)
            except OSError:
                pass
            creds = None

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
            token_dir = os.path.dirname(self.token_file)
            if token_dir:
                os.makedirs(token_dir, exist_ok=True)
            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    def print_event_colors(self) -> None:
        try:
            response = self.service.colors().get().execute()
            event_colors = response.get("event", {})
        except HttpError as exc:
            if exc.resp.status == 403:
                logging.warning(
                    "colors.get() returned 403; using bundled palette. "
                    "Ensure OAuth consent includes Calendar scope %s then delete token and retry.",
                    SCOPES[0],
                )
                event_colors = _FALLBACK_EVENT_COLORS
            else:
                raise
        for color_id, values in sorted(event_colors.items(), key=lambda item: int(item[0])):
            print(
                f"id={color_id} background={values.get('background')} "
                f"foreground={values.get('foreground')}"
            )

    def _iter_events(self) -> Iterable[Dict]:
        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=self.past_days)).isoformat()
        time_max = (now + timedelta(days=self.future_days)).isoformat()

        page_token = None
        while True:
            response = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    singleEvents=True,
                    orderBy="startTime",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=2500,
                    pageToken=page_token,
                )
                .execute()
            )
            for event in response.get("items", []):
                yield event
            page_token = response.get("nextPageToken")
            if not page_token:
                break

    def _allowed_organizer(self, event: Dict) -> bool:
        if not self.allowed_organizers:
            return True
        organizer = (event.get("organizer") or {}).get("email", "").lower()
        return organizer in self.allowed_organizers

    def fix_colors(self, dry_run: bool = True) -> Tuple[RunStats, List[str]]:
        stats = RunStats()
        changes: List[str] = []

        events = sorted(
            list(self._iter_events()),
            key=lambda item: _parse_start(item.get("start", {})),
        )

        for event in events:
            stats.scanned += 1
            event_id = event.get("id", "<unknown>")
            summary = event.get("summary", "<no title>")

            if event.get("status") == "cancelled":
                stats.cancelled += 1
                continue

            if not self._allowed_organizer(event):
                stats.skipped += 1
                continue

            rule = classify_event(event, self.rules_by_name, self.priority)
            if not rule:
                stats.skipped += 1
                continue

            stats.matched += 1
            current_color = event.get("colorId")
            if current_color == rule.color_id:
                stats.unchanged += 1
                continue

            change_message = (
                f"{summary} ({event_id}) color {current_color or 'default'} -> {rule.color_id}"
            )
            changes.append(change_message)

            if dry_run:
                logging.info("DRY-RUN update: %s", change_message)
                continue

            self.service.events().patch(
                calendarId=self.calendar_id,
                eventId=event_id,
                body={"colorId": rule.color_id},
            ).execute()
            stats.updated += 1
            logging.info("Updated: %s", change_message)

        return stats, changes

