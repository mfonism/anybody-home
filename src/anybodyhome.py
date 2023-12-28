import datetime
import pathlib
import pprint

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
        calendar = service.calendars().get(calendarId="")

        page_token = None
        while True:
            calendar_list = service.calendarList().list(pageToken=page_token).execute()
            print("Calendar List")
            pprint.pprint(calendar_list)
            print()
            print()
            for calendar_list_entry in calendar_list["items"]:
                print(calendar_list_entry["summary"])
            page_token = calendar_list.get("nextPageToken")
            if not page_token:
                break

    except HttpError as error:
        print(f"An error occured: {error}")


if __name__ == "__main__":
    main()
