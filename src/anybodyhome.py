from datetime import datetime
import pathlib
from pprint import pprint
import os

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main():
    CREDENTIALS_DIR = pathlib.Path().parent / "credentials"

    token_file_path = CREDENTIALS_DIR / "token.json"
    creds = None
    if token_file_path.exists():
        creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_file_path = CREDENTIALS_DIR / "credentials.json"
            flow = InstalledAppFlow.from_client_secrets_file(creds_file_path, SCOPES)
            creds = flow.run_local_server(port=0)

        token_file_path.write_text(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        page_token = None
        page_count = 0
        ooos = []
        while True:
            page_count += 1

            events = (
                service.events()
                .list(calendarId=os.getenv("OOO_ENG_CALENDAR_ID"), pageToken=page_token)
                .execute()
            )

            for event in events["items"]:
                if event["status"] == "cancelled":
                    continue

                ooo = {"creator": event["creator"]["email"]}
                ooo["start"] = ooo_start = dict()
                ooo["end"] = ooo_end = dict()
                ooos.append(ooo)

                event_start = event["start"]
                start_date = event_start.get("date")
                if start_date is not None:
                    ooo_start["date"] = datetime.strptime(start_date, "%Y-%m-%d")
                else:
                    ooo_start["date_time"] = datetime.fromisoformat(
                        event_start["dateTime"]
                    )
                    if timezone := event_start.get("timeZone") and timezone is not None:
                        ooo_start["time_zone"] = timezone

                event_end = event["end"]
                end_date = event_end.get("date")
                if end_date is not None:
                    ooo_end["date"] = datetime.strptime(end_date, "%Y-%m-%d")
                else:
                    ooo_end["date_time"] = datetime.fromisoformat(event_end["dateTime"])
                    if timezone := event_end.get("timeZone") and timezone is not None:
                        ooo_end["time_zone"] = timezone

            page_token = events.get("nextPageToken")
            if not page_token or page_count >= 2:
                break

        pprint(ooos)
    except HttpError as error:
        print(f"An error occured: {error}")


if __name__ == "__main__":
    main()
