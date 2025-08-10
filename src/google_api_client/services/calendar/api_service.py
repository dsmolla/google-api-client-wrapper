from datetime import datetime
from typing import Optional, List, Any, Dict
import logging

from googleapiclient.errors import HttpError

from ...utils.log_sanitizer import sanitize_for_logging
from ...utils.datetime import convert_datetime_to_iso, today_start
from .types import CalendarEvent, Attendee
from . import utils
from .constants import DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT, DEFAULT_CALENDAR_ID
from .exceptions import (
    CalendarError, CalendarPermissionError, EventNotFoundError,
    CalendarNotFoundError, EventConflictError, InvalidEventDataError
)

logger = logging.getLogger(__name__)


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
            start: Start time for events (inclusive).
            end: End time for events (exclusive).
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

        sanitized = sanitize_for_logging(
            max_results=max_results, start=start, end=end, 
            query=query, calendar_id=calendar_id
        )
        logger.info(
            "Fetching events with max_results=%s, start=%s, end=%s, query=%s, calendar_id=%s",
            sanitized['max_results'], sanitized['start'], sanitized['end'],
            sanitized['query'], sanitized['calendar_id']
        )

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

            logger.info("Found %d event items", len(events_data))

            # Parse events
            calendar_events = []
            for event_data in events_data:
                try:
                    calendar_events.append(utils.from_google_event(event_data))
                except Exception as e:
                    logger.warning("Failed to parse event: %s", e)

            logger.info("Successfully parsed %d complete events", len(calendar_events))
            return calendar_events

        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise CalendarNotFoundError(f"Calendar not found: {e}")
            else:
                raise CalendarError(f"Calendar API error listing events: {e}")
        except Exception as e:
            logger.error("An error occurred while fetching events: %s", e)
            raise CalendarError(f"Unexpected error listing events: {e}")

    def get_event(self, event_id: str, calendar_id: str = DEFAULT_CALENDAR_ID) -> CalendarEvent:
        """
        Retrieves a specific event from Google Calendar using its unique identifier.

        Args:
            event_id: The unique identifier of the event to be retrieved.
            calendar_id: Calendar ID containing the event (default: 'primary').

        Returns:
            A CalendarEvent object representing the event with the specified ID.
        """
        logger.info("Retrieving event with ID: %s from calendar: %s", event_id, calendar_id)

        try:
            event_data = self._service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info("Event retrieved successfully")
            return utils.from_google_event(event_data)
            
        except HttpError as e:
            if e.resp.status == 404:
                raise EventNotFoundError(f"Event not found: {event_id}")
            elif e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied accessing event: {e}")
            else:
                raise CalendarError(f"Calendar API error getting event {event_id}: {e}")
        except Exception as e:
            logger.error("Error retrieving event: %s", e)
            raise CalendarError(f"Unexpected error getting event: {e}")

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
        sanitized = sanitize_for_logging(summary=summary, start=start, end=end)
        logger.info("Creating event with summary=%s, start=%s, end=%s", 
                   sanitized['summary'], sanitized['start'], sanitized['end'])

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
            logger.info("Event created successfully with ID: %s", calendar_event.event_id)
            return calendar_event
            
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied creating event: {e}")
            elif e.resp.status == 409:
                raise EventConflictError(f"Event conflict: {e}")
            else:
                raise CalendarError(f"Calendar API error creating event: {e}")
        except ValueError as e:
            raise InvalidEventDataError(f"Invalid event data: {e}")
        except Exception as e:
            logger.error("Error creating event: %s", e)
            raise CalendarError(f"Unexpected error creating event: {e}")

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
        logger.info("Updating event with ID: %s", event.event_id)

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
            logger.info("Event updated successfully")
            return updated_calendar_event
            
        except HttpError as e:
            if e.resp.status == 404:
                raise EventNotFoundError(f"Event not found: {event.event_id}")
            elif e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied updating event: {e}")
            elif e.resp.status == 409:
                raise EventConflictError(f"Event conflict during update: {e}")
            else:
                raise CalendarError(f"Calendar API error updating event {event.event_id}: {e}")
        except ValueError as e:
            raise InvalidEventDataError(f"Invalid event data: {e}")
        except Exception as e:
            logger.error("Error updating event: %s", e)
            raise CalendarError(f"Unexpected error updating event: {e}")

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
        logger.info("Deleting event with ID: %s", event.event_id)

        try:
            self._service.events().delete(
                calendarId=calendar_id,
                eventId=event.event_id
            ).execute()
            
            logger.info("Event deleted successfully")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                raise EventNotFoundError(f"Event not found: {event.event_id}")
            elif e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied deleting event: {e}")
            else:
                raise CalendarError(f"Calendar API error deleting event {event.event_id}: {e}")
        except Exception as e:
            logger.error("Error deleting event: %s", e)
            raise CalendarError(f"Unexpected error deleting event: {e}")

    def batch_get_events(self, event_ids: List[str], calendar_id: str = DEFAULT_CALENDAR_ID) -> List[CalendarEvent]:
        """
        Retrieves multiple events by their IDs.

        Args:
            event_ids: List of event IDs to retrieve.
            calendar_id: Calendar ID containing the events (default: 'primary').

        Returns:
            List of CalendarEvent objects.
        """
        logger.info("Batch retrieving %d events", len(event_ids))

        calendar_events = []
        for event_id in event_ids:
            try:
                calendar_events.append(self.get_event(event_id, calendar_id))
            except Exception as e:
                logger.warning("Failed to fetch event %s: %s", event_id, e)

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
        logger.info("Batch creating %d events", len(events_data))

        created_events = []
        for event_data in events_data:
            try:
                created_events.append(self.create_event(calendar_id=calendar_id, **event_data))
            except Exception as e:
                logger.warning("Failed to create event: %s", e)

        return created_events