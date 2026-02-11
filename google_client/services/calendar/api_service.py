import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict, Union

from google.auth.credentials import Credentials
from googleapiclient.discovery import build

from google_client.utils.datetime import datetime_to_iso, current_datetime
from . import utils
from .constants import DEFAULT_CALENDAR_ID
from .types import Calendar, CalendarEvent, Attendee, FreeBusyResponse, TimeSlot


class CalendarApiService:
    """
    Service layer for Calendar API operations.
    """

    def __init__(self, credentials: Credentials, timezone: str):
        self._service = build("calendar", "v3", credentials=credentials)
        self._timezone = timezone

    def query(self):
        """
        Create a new EventQueryBuilder for building complex event queries with a fluent API.

        Returns:
            EventQueryBuilder instance for method chaining

        Example:
            events = (user.calendar.query()
                .limit(50)
                .today()
                .search("meeting")
                .with_location()
                .execute())
        """
        from .query_builder import EventQueryBuilder
        return EventQueryBuilder(self, self._timezone)

    def list_calendars(self, max_results: int = 250) -> List[Calendar]:
        payload = self._service.calendarList().list(maxResults=max_results).execute()
        calendars = []
        for item in payload["items"]:
            calendars.append(
                Calendar(
                    id=item.get('id'),
                    summary=item.get('summary'),
                    description=item.get('description'),
                    backgroundColor=item.get('backgroundColor'),
                    foregroundColor=item.get('foregroundColor'),
                    deleted=item.get('deleted', False),
                )
            )

        return calendars

    def delete_calendar(self, calendar: Calendar | str) -> None:
        if isinstance(calendar, Calendar):
            calendar = calendar.id

        self._service.calendarList().delete(calendarId=calendar).execute()

    def get_calendar(self, calendar_id: str) -> Calendar:
        calendar = self._service.calendarList().get(calendarId=calendar_id).execute()
        return Calendar(
            id=calendar.get('id'),
            summary=calendar.get('summary'),
            description=calendar.get('description'),
            backgroundColor=calendar.get('backgroundColor'),
            foregroundColor=calendar.get('foregroundColor'),
            deleted=calendar.get('deleted', False),
        )

    def create_calendar(
            self,
            summary: str,
            description: str = None,
            background_color: str = None,
            foreground_color: str = None,
    ) -> Calendar:
        body = {'summary': summary, 'timezone': self._timezone}
        if description:
            body['description'] = description
        if background_color:
            body['backgroundColor'] = background_color
        if foreground_color:
            body['foreground_color'] = foreground_color

        payload = self._service.calendars().insert(body=body).execute()
        return Calendar(
            id=payload.get('id'),
            summary=payload.get('summary'),
            description=payload.get('description'),
            backgroundColor=payload.get('backgroundColor'),
            foregroundColor=payload.get('foregroundColor'),
            deleted=payload.get('deleted', False),
        )

    def update_calendar(self, calendar: Calendar):
        payload = self._service.calendars().update(calendarId=calendar.id, body=calendar.to_dict()).execute()
        return Calendar(
            id=payload.get('id'),
            summary=payload.get('summary'),
            description=payload.get('description'),
            backgroundColor=payload.get('backgroundColor'),
            foregroundColor=payload.get('foregroundColor'),
            deleted=payload.get('deleted', False),
        )

    def list_events(
            self,
            max_results: Optional[int] = 100,
            start: Optional[datetime] = None,
            end: Optional[datetime] = None,
            query: Optional[str] = None,
            calendar_id: str = DEFAULT_CALENDAR_ID,
            single_events: bool = True,
            order_by: str = 'startTime'
    ) -> List[CalendarEvent]:
        """
        Fetches a list of events from Google Calendar with optional filtering.

        Args:
            max_results: Maximum number of events to retrieve. Defaults to 100.
            start: Start time for events (inclusive). Defaults to today.
            end: End time for events (exclusive). Defaults to 7 days from start date
            query: Text search query string.
            calendar_id: Calendar ID to query (default: 'primary').
            single_events: Whether to expand recurring events into instances.
            order_by: How to order the events ('startTime' or 'updated').

        Returns:
            A list of CalendarEvent objects representing the events found.
            If no events are found, an empty list is returned.
        """

        if max_results < 1:
            raise ValueError(f"max_results must be at least 1")

        if not start:
            start = datetime.combine(current_datetime(self._timezone).today(), datetime.min.time())
        if not end:
            end = start + timedelta(days=7)

        if start >= end:
            raise ValueError("start date should be before end date")

        start = datetime_to_iso(start, self._timezone)
        end = datetime_to_iso(end, self._timezone)

        request_params = {
            'calendarId': calendar_id,
            'maxResults': max_results,
            'singleEvents': single_events,
            'timeMin': start,
            'timeMax': end,
        }

        if order_by and single_events:
            request_params['orderBy'] = order_by
        if query:
            request_params['q'] = query

        result = self._service.events().list(**request_params).execute()
        events = [utils.from_google_event(event, calendar_id, self._timezone) for event in result.get('items', [])]
        while result.get('nextPageToken') and len(events) < max_results:
            result = self._service.events().list(**request_params, pageToken=result['nextPageToken']).execute()
            events.extend([utils.from_google_event(event, calendar_id, self._timezone) for event in result.get('items', [])])

        return events

    def get_event(self, event_id: str, calendar_id: str = DEFAULT_CALENDAR_ID) -> CalendarEvent:
        """
        Retrieves a specific event from Google Calendar using its unique identifier.

        Args:
            event_id: The unique identifier of the event to be retrieved.
            calendar_id: Calendar ID containing the event (default: 'primary').

        Returns:
            A CalendarEvent object representing the event with the specified ID.
        """

        event_data = self._service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        return utils.from_google_event(event_data, calendar_id, self._timezone)

    def create_event(
            self,
            start: datetime,
            end: datetime,
            summary: str = None,
            description: str = None,
            location: str = None,
            attendees: List[Attendee] = None,
            create_google_meet: bool = False,
            recurrence: List[str] = None,
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> CalendarEvent:
        """
        Creates a new calendar event.

        Args:
            start: Event start datetime.
            end: Event end datetime.
            summary: Brief title or summary of the event.
            description: Detailed description of the event.
            location: Physical or virtual location of the event.
            attendees: List of Attendee objects for invited people.
            create_google_meet: Whether to include a Google Meets meeting in the event.
            recurrence: List of recurrence rules in RFC 5545 format.
            calendar_id: Calendar ID to create event in (default: 'primary').

        Returns:
            A CalendarEvent object representing the created event.
        """
        if start >= end:
            raise ValueError("end datetime should be after start datetime.")

        event_body = {
            'summary': summary or "New Event",
            'start': {'dateTime': datetime_to_iso(start, self._timezone), 'timeZone': self._timezone},
            'end': {'dateTime': datetime_to_iso(end, self._timezone), 'timeZone': self._timezone},
        }

        if description:
            event_body['description'] = description
        if location:
            event_body['location'] = location
        if attendees:
            event_body['attendees'] = [attendee.to_dict() for attendee in attendees]
        if recurrence:
            event_body['recurrence'] = recurrence
        if create_google_meet:
            event_body['conferenceData'] = {
                "createRequest": {
                    "requestId": uuid.uuid4().hex,
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    }
                }
            }

        created_event = self._service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            conferenceDataVersion=1
        ).execute()

        calendar_event = utils.from_google_event(created_event, calendar_id, self._timezone)
        return calendar_event

    def add_meeting(self, event: CalendarEvent | str, calendar_id: str = None) -> CalendarEvent:
        """
        Add a Google Meet conference to an existing calendar event.

        Args:
            event: A CalendarEvent object or an event ID string.
            calendar_id: Calendar ID (required when event is a string, ignored when event is a CalendarEvent).

        Returns:
            The updated CalendarEvent with a Google Meet link.

        Raises:
            ValueError: If event is a string and calendar_id is not provided.
        """
        event_patch = {
            'conferenceData': {
                'createRequest': {
                    'requestId': uuid.uuid4().hex,
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }
        if isinstance(event, CalendarEvent):
            event_id = event.event_id
            calendar_id = event.calendar_id
        else:
            if calendar_id is None:
                raise ValueError("Calendar ID is required.")
            event_id = event

        payload = self._service.events().patch(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_patch,
            conferenceDataVersion=1
        ).execute()
        event = utils.from_google_event(payload, calendar_id, self._timezone)
        return event

    def update_event(
            self,
            event: CalendarEvent,
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> CalendarEvent:
        """
        Updates an existing calendar event.

        Args:
            event: CalendarEvent object with updated data.
            calendar_id: Calendar ID containing the event (default: 'primary').

        Returns:
            A CalendarEvent object representing the updated event.
        """

        if event.start >= event.end:
            raise ValueError("end datetime should be after start datetime.")

        event_body = event.to_dict()
        fields_to_remove = ['id', 'htmlLink', 'recurringEventId']
        for field in fields_to_remove:
            event_body.pop(field, None)

        event_body['start'] = {'dateTime': datetime_to_iso(event.start, self._timezone), 'timeZone': self._timezone}
        event_body['end'] = {'dateTime': datetime_to_iso(event.end, self._timezone), 'timeZone': self._timezone}

        updated_event = self._service.events().update(
            calendarId=calendar_id,
            eventId=event.event_id,
            body=event_body
        ).execute()

        updated_calendar_event = utils.from_google_event(updated_event, calendar_id, self._timezone)
        return updated_calendar_event

    def delete_event(
            self,
            event: Union[CalendarEvent, str],
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> None:
        """
        Deletes a calendar event.

        Args:
            event: The Calendar event to delete.
            calendar_id: Calendar ID containing the event (default: 'primary').

        Returns:
            True if the operation was successful, False otherwise.
        """

        if isinstance(event, CalendarEvent):
            event = event.event_id

        self._service.events().delete(
            calendarId=calendar_id,
            eventId=event
        ).execute()

    def batch_get_events(
            self,
            event_ids: List[str],
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> List[CalendarEvent | Exception]:
        """
        Retrieves multiple events by their IDs.

        Args:
            event_ids: List of event IDs to retrieve.
            calendar_id: Calendar ID containing the events (default: 'primary').

        Returns:
            List of CalendarEvent objects.
        """

        calendar_events = []
        for event_id in event_ids:
            try:
                calendar_events.append(self.get_event(event_id, calendar_id))
            except Exception as e:
                calendar_events.append(e)

        return calendar_events

    def batch_create_events(
            self,
            events_data: List[Dict[str, Any]],
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> List[CalendarEvent | Exception]:
        """
        Creates multiple events.

        Args:
            events_data: List of dictionaries containing event parameters.
            calendar_id: Calendar ID to create events in (default: 'primary').

        Returns:
            List of created CalendarEvent objects.
        """

        created_events = []
        for event_data in events_data:
            try:
                created_events.append(self.create_event(calendar_id=calendar_id, **event_data))
            except Exception as e:
                created_events.append(e)

        return created_events

    def get_freebusy(
            self,
            start: datetime,
            end: datetime,
            calendar_ids: Optional[List[str]] = None,
    ) -> FreeBusyResponse:
        """
        Query free/busy information for specified calendars and time range.

        Args:
            start: Start datetime for the query
            end: End datetime for the query
            calendar_ids: List of calendar IDs to query (defaults to primary calendar)

        Returns:
            FreeBusyResponse object containing availability information

        Raises:
            CalendarError: If the API request fails
            ValueError: If the parameters are invalid
        """

        if calendar_ids is None:
            calendar_ids = [DEFAULT_CALENDAR_ID]

        request_body = {
            "timeMin": datetime_to_iso(start, self._timezone),
            "timeMax": datetime_to_iso(end, self._timezone),
            "items": [{"id": cal_id} for cal_id in calendar_ids]
        }

        result = self._service.freebusy().query(body=request_body).execute()
        return utils.parse_freebusy_response(result, self._timezone)

    def find_free_slots(
            self,
            start: datetime,
            end: datetime,
            duration_minutes: int,
            calendar_ids: Optional[List[str]] = None
    ) -> Dict[str, List[TimeSlot]]:
        """
        Find all available time slots of a specified duration within a time range.

        Args:
            start: Start datetime for the search
            end: End datetime for the search
            duration_minutes: Minimum duration for free slots in minutes
            calendar_ids: List of calendar IDs to check (defaults to primary calendar)

        Returns:
            List of TimeSlot objects representing available time slots

        Raises:
            CalendarError: If the API request fails
            ValueError: If the parameters are invalid
        """

        if calendar_ids is None:
            calendar_ids = [DEFAULT_CALENDAR_ID]

        freebusy_response = self.get_freebusy(start, end, calendar_ids)

        free_slots = {}
        for calendar_id in calendar_ids:
            free_slots[calendar_id] = freebusy_response.get_free_slots(duration_minutes, calendar_id)

        return free_slots
