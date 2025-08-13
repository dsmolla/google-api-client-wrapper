from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict

from googleapiclient.errors import HttpError

from ...utils.datetime import convert_datetime_to_iso, today_start
from .types import CalendarEvent, Attendee, FreeBusyResponse, TimeSlot
from . import utils
from .constants import DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT, DEFAULT_CALENDAR_ID, DEFAULT_FREEBUSY_DURATION_MINUTES
from .exceptions import (
    CalendarError, CalendarPermissionError, EventNotFoundError,
    CalendarNotFoundError, EventConflictError, InvalidEventDataError
)


class CalendarApiService:
    """
    Service layer for Calendar API operations.
    Contains all Calendar API functionality that was removed from dataclasses.
    """
    
    def __init__(self, service: Any):
        """
        Initialize Calendar service.
        
        Args:
            service: The Calendar API service instance
        """
        self._service = service

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
        return EventQueryBuilder(self)

    def list_events(
            self,
            max_results: Optional[int] = DEFAULT_MAX_RESULTS,
            start: Optional[datetime] = today_start(),
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
            end: End time for events (exclusive). Defaults to 30 days from start date
            query: Text search query string.
            calendar_id: Calendar ID to query (default: 'primary').
            single_events: Whether to expand recurring events into instances.
            order_by: How to order the events ('startTime' or 'updated').

        Returns:
            A list of CalendarEvent objects representing the events found.
            If no events are found, an empty list is returned.
        """
        # Input validation
        if max_results and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

        if not end:
            end = start + timedelta(days=30)

        try:
            # Build request parameters
            request_params = {
                'calendarId': calendar_id,
                'maxResults': max_results,
                'singleEvents': single_events,
            }
            
            if order_by and single_events:
                request_params['orderBy'] = order_by

            # Add time range filters
            if start:
                request_params['timeMin'] = convert_datetime_to_iso(start)
            if end:
                request_params['timeMax'] = convert_datetime_to_iso(end)
            if query:
                request_params['q'] = query

            # Make API call
            result = self._service.events().list(**request_params).execute()
            events_data = result.get('items', [])


            # Parse events
            calendar_events = []
            for event_data in events_data:
                try:
                    calendar_events.append(utils.from_google_event(event_data))
                except Exception as e:
                    pass

            return calendar_events

        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied")
            elif e.resp.status == 404:
                raise CalendarNotFoundError(f"Calendar not found")
            else:
                raise CalendarError(f"Calendar API error listing events")
        except Exception as e:
            raise CalendarError(f"Unexpected error listing events")

    def get_event(self, event_id: str, calendar_id: str = DEFAULT_CALENDAR_ID) -> CalendarEvent:
        """
        Retrieves a specific event from Google Calendar using its unique identifier.

        Args:
            event_id: The unique identifier of the event to be retrieved.
            calendar_id: Calendar ID containing the event (default: 'primary').

        Returns:
            A CalendarEvent object representing the event with the specified ID.
        """

        try:
            event_data = self._service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return utils.from_google_event(event_data)
            
        except HttpError as e:
            if e.resp.status == 404:
                raise EventNotFoundError(f"Event not found")
            elif e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied accessing event")
            else:
                raise CalendarError(f"Calendar API error getting event")
        except Exception as e:
            raise CalendarError(f"Unexpected error getting event")

    def create_event(
            self,
            start: datetime,
            end: datetime,
            summary: str = None,
            description: str = None,
            location: str = None,
            attendees: List[Attendee] = None,
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
            recurrence: List of recurrence rules in RFC 5545 format.
            calendar_id: Calendar ID to create event in (default: 'primary').

        Returns:
            A CalendarEvent object representing the created event.
        """
        # Create event preparation

        try:
            # Create event body using utils
            event_body = utils.create_event_body(
                start=start,
                end=end,
                summary=summary,
                description=description,
                location=location,
                attendees=attendees,
                recurrence=recurrence
            )

            # Make API call
            created_event = self._service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            calendar_event = utils.from_google_event(created_event)
            return calendar_event
            
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied creating event")
            elif e.resp.status == 409:
                raise EventConflictError(f"Event conflict")
            else:
                raise CalendarError(f"Calendar API error creating event")
        except ValueError as e:
            raise InvalidEventDataError(f"Invalid event data")
        except Exception as e:
            raise CalendarError(f"Unexpected error creating event")

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

        try:
            # Convert event to API format
            event_body = event.to_dict()
            
            # Remove fields that shouldn't be updated
            fields_to_remove = ['id', 'htmlLink', 'recurringEventId']
            for field in fields_to_remove:
                event_body.pop(field, None)
            
            # Add datetime fields if they exist
            if event.start and event.end:
                event_body['start'] = {'dateTime': convert_datetime_to_iso(event.start)}
                event_body['end'] = {'dateTime': convert_datetime_to_iso(event.end)}

            # Make API call
            updated_event = self._service.events().update(
                calendarId=calendar_id,
                eventId=event.event_id,
                body=event_body
            ).execute()
            
            updated_calendar_event = utils.from_google_event(updated_event)
            return updated_calendar_event
            
        except HttpError as e:
            if e.resp.status == 404:
                raise EventNotFoundError(f"Event not found")
            elif e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied updating event")
            elif e.resp.status == 409:
                raise EventConflictError(f"Event conflict during update")
            else:
                raise CalendarError(f"Calendar API error updating event")
        except ValueError as e:
            raise InvalidEventDataError(f"Invalid event data")
        except Exception as e:
            raise CalendarError(f"Unexpected error updating event")

    def delete_event(
            self,
            event: CalendarEvent,
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> bool:
        """
        Deletes a calendar event.

        Args:
            event: The Calendar event to delete.
            calendar_id: Calendar ID containing the event (default: 'primary').

        Returns:
            True if the operation was successful, False otherwise.
        """

        try:
            self._service.events().delete(
                calendarId=calendar_id,
                eventId=event.event_id
            ).execute()
            
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                raise EventNotFoundError(f"Event not found")
            elif e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied deleting event")
            else:
                raise CalendarError(f"Calendar API error deleting event")
        except Exception as e:
            raise CalendarError(f"Unexpected error deleting event")

    def batch_get_events(self, event_ids: List[str], calendar_id: str = DEFAULT_CALENDAR_ID) -> List[CalendarEvent]:
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
                pass

        return calendar_events

    def batch_create_events(self, events_data: List[Dict[str, Any]], calendar_id: str = DEFAULT_CALENDAR_ID) -> List[CalendarEvent]:
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
                pass

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
        
        # Validate the request parameters
        utils.validate_freebusy_request(start, end, calendar_ids)
        
        try:
            # Make the API call
            request_body = {
                "timeMin": convert_datetime_to_iso(start),
                "timeMax": convert_datetime_to_iso(end),
                "items": [{"id": cal_id} for cal_id in calendar_ids]
            }

            result = self._service.freebusy().query(body=request_body).execute()
            
            # Parse and return the response
            return utils.parse_freebusy_response(result)
            
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError("Permission denied for freebusy query")
            elif e.resp.status == 404:
                raise CalendarNotFoundError("One or more calendars not found")
            else:
                raise CalendarError(f"Calendar API error during freebusy query")
        except ValueError as e:
            raise ValueError(f"Invalid freebusy request")
        except Exception as e:
            raise CalendarError(f"Unexpected error during freebusy query")

    def find_free_slots(
        self,
        start: datetime,
        end: datetime,
        duration_minutes: int = DEFAULT_FREEBUSY_DURATION_MINUTES,
        calendar_ids: Optional[List[str]] = None
    ) -> List[TimeSlot]:
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
        from .constants import MIN_TIME_SLOT_DURATION_MINUTES, MAX_TIME_SLOT_DURATION_MINUTES
        
        if duration_minutes < MIN_TIME_SLOT_DURATION_MINUTES:
            raise ValueError(f"Duration must be at least {MIN_TIME_SLOT_DURATION_MINUTES} minutes")
        if duration_minutes > MAX_TIME_SLOT_DURATION_MINUTES:
            raise ValueError(f"Duration cannot exceed {MAX_TIME_SLOT_DURATION_MINUTES} minutes")
        
        # Get freebusy information
        freebusy_response = self.get_freebusy(start, end, calendar_ids)
        
        # If multiple calendars, we need to find slots that are free in ALL calendars
        if len(calendar_ids or [DEFAULT_CALENDAR_ID]) == 1:
            calendar_id = calendar_ids[0] if calendar_ids else DEFAULT_CALENDAR_ID
            return freebusy_response.get_free_slots(duration_minutes, calendar_id)
        else:
            # For multiple calendars, collect all busy periods from all calendars
            all_busy_periods = []
            for calendar_id in (calendar_ids or [DEFAULT_CALENDAR_ID]):
                all_busy_periods.extend(freebusy_response.get_busy_periods(calendar_id))
            
            # Merge overlapping busy periods
            merged_busy = utils.merge_overlapping_time_slots(all_busy_periods)
            
            # Create a temporary response with merged busy periods for the primary calendar
            temp_response = FreeBusyResponse(
                start=start,
                end=end,
                calendars={DEFAULT_CALENDAR_ID: merged_busy}
            )
            
            return temp_response.get_free_slots(duration_minutes, DEFAULT_CALENDAR_ID)

