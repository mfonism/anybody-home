import datetime
import os
import pathlib
from datetime import datetime, timedelta, timezone
from pprint import pprint

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

UTC = timezone.utc


def auth(scopes=None):
    scopes = scopes.copy()

    def auth_decorator(func):
        def wrapper(*args, **kwargs):
            credentials_dir = pathlib.Path().parent / "credentials"
            token_file_path = credentials_dir / "token.json"

            creds = None
            if token_file_path.exists():
                creds = Credentials.from_authorized_user_file(token_file_path, scopes)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    creds_file_path = credentials_dir / "credentials.json"
                    flow = InstalledAppFlow.from_client_secrets_file(
                        creds_file_path, scopes
                    )
                    creds = flow.run_local_server(port=0)

                token_file_path.write_text(creds.to_json())

            return func(*args, **kwargs, credentials=creds)

        return wrapper

    return auth_decorator


@auth(scopes=["https://www.googleapis.com/auth/calendar.readonly"])
def fetch_eng_ooos(start_in=0, period=60 * 60, credentials=None):
    # OOOs fetched will exclude those which:
    # * end before `start_in` seconds from now
    # * start after `start_in` + `period` seconds from now
    time_min = datetime.now(UTC) + timedelta(seconds=start_in)
    time_max = time_min + timedelta(period)

    try:
        service = build("calendar", "v3", credentials=credentials)
        page_token = None

        ooos = []
        while True:
            events = (
                service.events()
                .list(
                    calendarId=os.getenv("OOO_ENG_CALENDAR_ID"),
                    pageToken=page_token,
                    maxResults=10,
                    showDeleted=False,
                    singleEvents=True,
                    orderBy="startTime",
                    timeMin=time_min.isoformat(),
                    timeMax=time_max.isoformat(),
                )
                .execute()
            )

            for event in events["items"]:
                ooo = {"creator": event["creator"]["email"]}

                if "attendees" in event:
                    iter_attendees = (
                        attendee["email"] for attendee in event["attendees"]
                    )
                    attendees = list(
                        email
                        for email in iter_attendees
                        if (not email == ooo["creator"])
                        and (not email.endswith("@group.calendar.google.com"))
                    )

                    if len(attendees) > 0:
                        ooo["attendees"] = attendees

                ooo["start"] = ooo_start = dict()
                ooo["end"] = ooo_end = dict()
                ooos.append(ooo)

                event_start = event["start"]
                if "date" in event_start:
                    ooo_start["date"] = datetime.strptime(
                        event_start["date"], "%Y-%m-%d"
                    )
                else:
                    ooo_start["date_time"] = datetime.fromisoformat(
                        event_start["dateTime"]
                    )
                    if "timezone" in event_start:
                        ooo_start["time_zone"] = event_start["timezone"]

                event_end = event["end"]
                if "date" in event_end:
                    ooo_end["date"] = datetime.strptime(event_end["date"], "%Y-%m-%d")
                else:
                    ooo_end["date_time"] = datetime.fromisoformat(event_end["dateTime"])
                    if "timezone" in event_end:
                        ooo_end["time_zone"] = event_end["timezone"]

            page_token = events.get("nextPageToken")
            if not page_token:
                break

        return ooos

    except HttpError as error:
        print(f"An error occured: {error}")


if __name__ == "__main__":
    next_fourteen_days = 60 * 60 * 24 * 14
    res = fetch_eng_ooos(period=next_fourteen_days)
    pprint("Fetched!")
    pprint(res)
