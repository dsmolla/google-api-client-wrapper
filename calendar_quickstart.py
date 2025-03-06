import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dataclasses import dataclass


    pass

class Calendar:
    def __init__(self):
        self.SCOPES = ["https://www.googleapis.com/auth/calendar"]
        self.creds = None
        self.service = None
        self.__authenticate()

    def _authenticate(self):
        if os.path.exists("token.json"):
            self.creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(self.creds.to_json())
        self.service = build("calendar", "v3", credentials=self.creds)
    
    def _build_start_end_time(self, date: str = None, dateTime: str = None, timezone: str = 'America/Los_Angeles'):
        """
        Build the start or end time for an event.

        Args:
            date (str): The date of the event.
            dateTime (str): The date and time of the event.
            timezone (str): The timezone of the event.
        
        Returns:
            dict: The start or end time of the event.
        """

        if date:
            return {"date": date, "timeZone": timezone}
        elif dateTime:
            return {"dateTime": dateTime, "timeZone": timezone}
        else:
            raise ValueError("Either date or dateTime must be provided.")
    
    def _build_attendees(self, attendees: list):
        """
        Build the attendees for an event.

        Args:
            attendees (list): The attendees of the event.
        
        Returns:
            list: The attendees of the event.
        """

        return [{"email": attendee} for attendee in attendees]

    def _build_reminders(self, useDefault: bool, overrides: dict):
        """
        Build the reminders for an event.

        Args:
            useDefault (bool): Whether to use the default reminders.
            overrides (dict): The reminder overrides in the format {"method": str, "minutes": int}.
                                Method can be "email" or "popup".
        
        Returns:
            dict: The reminders for the event.
        """

        return {"useDefault": useDefault, 
                "overrides": [{"method": reminder["method"], "minutes": reminder["minutes"]}
                              for reminder in overrides
                              ]
                }
        

    def _build_event_payload(
            self,
        summary: str,
        location: str,
        description: str,
        start: dict,
        end: dict,
        recurrence: list,
        attendees: list,
        reminders: dict,
        # attachments: list,
        end_time_unspecified: bool=False,
        timezone="America/Los_Angeles"
    ):
        """
        Build a properly formatted event payload for the Google Calendar API.

        Args:
            summary (str): The event title.
            location (str): The event location.
            description (str): The event description.
            start (dict): The event start time.
            end (dict): The event end time.
            end_time_unspecified (bool): Whether the end time is unspecified.
            recurrence (list): The event recurrence.
            attendees (list): The event attendees.
            reminders (dict): The event reminders.
            attachments (list): The event attachments.
            eventtype (str): The event type.
            birthdayProperties (dict): The event birthday properties.
            timezone (str): The event timezone.
        
        """

        event = {
            "summary": summary,
            "location": location,
            "description": description,
        }
        event["start"] = self._build_start_end_time(**start)    
        event["end"] = self._build_start_end_time(**end)
        event["recurrence"] = recurrence
        event["attendees"] = self._build_attendees(attendees)
        event["reminders"] = self._build_reminders(**reminders)










# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Refer to the Python quickstart on how to setup the environment:
# https://developers.google.com/calendar/quickstart/python
# Change the scope to 'https://www.googleapis.com/auth/calendar' and delete any
# stored credentials.


creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
service = build("calendar", "v3", credentials=creds)



def add_to_cal():
    event = {
    'summary': 'Google I/O 2015',
    'location': '800 Howard St., San Francisco, CA 94103',
    'description': 'A chance to hear more about Google\'s developer products.',
    'start': {
        'dateTime': '2025-03-06T09:00:00-07:00',
        'timeZone': 'America/Los_Angeles',
    },
    'end': {
        'dateTime': '2025-03-06T17:00:00-07:00',
        'timeZone': 'America/Los_Angeles',
    },
    'recurrence': [
        'RRULE:FREQ=DAILY;COUNT=2'
    ],
    'attendees': [
        {'email': 'dagmawishewadeg@gmail.com'}
    ],
    'reminders': {
        'useDefault': False,
        'overrides': [
        {'method': 'email', 'minutes': 24 * 60},
        {'method': 'popup', 'minutes': 10},
        ],
    },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    print('Event created: %s' % (event.get('htmlLink')))



def display_events():
  """Shows basic usage of the Google Calendar API.
  Prints the start and name of the next 10 events on the user's calendar.
  """
  try:
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            id_ = calendar_list_entry['id']
            name = calendar_list_entry['summary']
            print(f"Getting the upcoming 10 events for {name}\n")


            # Call the Calendar API
            now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
            events_result = (
                service.events()
                .list(
                    calendarId=id_,
                    timeMin=now,
                    maxResults=10,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            if not events:
                print("No upcoming events found.\n")
                continue

            # Prints the start and name of the next 10 events
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                print(start, event["summary"])
            print("\n")


        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break

  except HttpError as error:
    print(f"An error occurred: {error}")


add_to_cal()