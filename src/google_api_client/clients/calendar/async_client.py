import asyncio
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Union, Dict, Any
from ...auth.credentials import get_async_calendar_service
from ...utils.datetime import convert_datetime_to_iso, convert_datetime_to_readable, current_datetime_local_timezone, today_start, days_from_today
from dataclasses import dataclass, field
import logging
import re
from contextlib import asynccontextmanager
from aiogoogle.excs import HTTPError

logger = logging.getLogger(__name__)

# Constants (imported from sync version)
MAX_RESULTS_LIMIT = 2500
MAX_SUMMARY_LENGTH = 1024
MAX_DESCRIPTION_LENGTH = 8192
MAX_LOCATION_LENGTH = 1024
MAX_QUERY_LENGTH = 500
DEFAULT_MAX_RESULTS = 100
DEFAULT_DAYS_AHEAD = 7

# Custom Exception Classes
class AsyncCalendarError(Exception):
    """Base exception for async calendar operations."""
    pass

class AsyncCalendarPermissionError(AsyncCalendarError):
    """Raised when the user lacks permission for a calendar operation."""
    pass

class AsyncCalendarNotFoundError(AsyncCalendarError):
    """Raised when a calendar or event is not found."""
    pass

@asynccontextmanager
async def async_calendar_service():
    """Async context manager for calendar service connections with error handling."""
    try:
        async with get_async_calendar_service() as (aiogoogle, calendar_service):
            yield aiogoogle, calendar_service
    except HTTPError as e:
        if e.res.status_code == 403:
            raise AsyncCalendarPermissionError(f"Permission denied: {e}")
        elif e.res.status_code == 404:
            raise AsyncCalendarNotFoundError(f"Calendar or event not found: {e}")
        else:
            raise AsyncCalendarError(f"Calendar API error: {e}")
    except Exception as e:
        raise AsyncCalendarError(f"Unexpected calendar service error: {e}")

@dataclass
class AsyncAttendee:
    """
    Async version of Attendee class.
    """
    email: str
    display_name: Optional[str] = None
    response_status: Optional[str] = None

    def __post_init__(self):
        if not self.email:
            raise ValueError("Attendee email cannot be empty.")
        if not self._is_valid_email(self.email):
            raise ValueError(f"Invalid email format: {self.email}")
        if self.response_status and self.response_status not in ["needsAction", "declined", "tentative", "accepted"]:
            raise ValueError(f"Invalid response status: {self.response_status}. Must be one of: needsAction, declined, tentative, accepted")
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format using regex."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def to_dict(self) -> dict:
        attendee = {"email": self.email}
        if self.display_name:
            attendee["displayName"] = self.display_name
        if self.response_status:
            attendee["responseStatus"] = self.response_status
        return attendee

@dataclass
class AsyncCalendarEvent:
    """
    Async version of CalendarEvent with all async methods.
    """
    id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    htmlLink: Optional[str] = None
    attendees: List[AsyncAttendee] = field(default_factory=list)
    recurrence: List[str] = field(default_factory=list)
    recurringEventId: Optional[str] = None

    def __post_init__(self):
        self._validate_datetime_range(self.start, self.end)
        self._validate_text_field(self.summary, MAX_SUMMARY_LENGTH, "summary")
        self._validate_text_field(self.description, MAX_DESCRIPTION_LENGTH, "description")
        self._validate_text_field(self.location, MAX_LOCATION_LENGTH, "location")

    def _validate_datetime_range(self, start: Optional[datetime], end: Optional[datetime]) -> None:
        """Validates that start time is before end time."""
        if start and end and start >= end:
            raise ValueError("Event start time must be before end time")
    
    def _validate_text_field(self, value: Optional[str], max_length: int, field_name: str) -> None:
        """Validates text field length and content."""
        if value and len(value) > max_length:
            raise ValueError(f"Event {field_name} cannot exceed {max_length} characters")

    @staticmethod
    def _from_google_event(google_event: dict) -> "AsyncCalendarEvent":
        """
        Creates an AsyncCalendarEvent instance from a Google Calendar API response.
        """
        attendees = []
        for attendee_data in google_event.get("attendees", []):
            email = attendee_data.get("email")
            if email and AsyncAttendee._is_valid_email(email):
                try:
                    attendees.append(AsyncAttendee(
                        email=email,
                        display_name=attendee_data.get("displayName"),
                        response_status=attendee_data.get("responseStatus")
                    ))
                except ValueError as e:
                    logger.warning("Skipping invalid attendee: %s", e)
        
        start = AsyncCalendarEvent._parse_datetime(google_event.get("start", {}))
        end = AsyncCalendarEvent._parse_datetime(google_event.get("end", {}))
        
        return AsyncCalendarEvent(
            id=google_event.get("id"),
            summary=google_event.get("summary"),
            description=google_event.get("description"),
            location=google_event.get("location"),
            start=start,
            end=end,
            htmlLink=google_event.get("htmlLink"),
            attendees=attendees,
            recurrence=google_event.get("recurrence"),
            recurringEventId=google_event.get("recurringEventId"),
        )

    @staticmethod
    def _parse_datetime(datetime_data: dict) -> Optional[datetime]:
        """Safely parse datetime from Google Calendar API response."""
        if not datetime_data:
            return None
        try:
            if datetime_data.get("dateTime"):
                return datetime.fromisoformat(datetime_data["dateTime"].replace("Z", "+00:00"))
            elif datetime_data.get("date"):
                return datetime.strptime(datetime_data["date"], "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse datetime: %s", e)
        return None

    def to_dict(self) -> dict:
        """Convert AsyncCalendarEvent to dictionary format for Google Calendar API."""
        if not self.start or not self.end:
            raise ValueError("Event must have both start and end times")
        
        event_dict = {
            "summary": self.summary,
            "description": self.description,
            "location": self.location,
            "start": {"dateTime": convert_datetime_to_iso(self.start)},
            "end": {"dateTime": convert_datetime_to_iso(self.end)},
            "attendees": [attendee.to_dict() for attendee in self.attendees],
        }
        
        if self.id:
            event_dict["id"] = self.id
        if self.htmlLink:
            event_dict["htmlLink"] = self.htmlLink
        if self.recurrence:
            event_dict["recurrence"] = self.recurrence
        if self.recurringEventId:
            event_dict["recurringEventId"] = self.recurringEventId
            
        return event_dict

    # Utility methods (same as sync version)
    def duration(self) -> Optional[int]:
        if self.start and self.end:
            total_seconds = (self.end - self.start).total_seconds()
            return int(total_seconds / 60)
        return None

    def is_today(self) -> bool:
        if self.start:
            return self.start.date() == date.today()
        return False

    def is_all_day(self) -> bool:
        if not self.start or not self.end:
            return False
        return self.start.time() == time.min and self.end.time() == time.min and (self.end - self.start).days >= 1

    def is_past(self) -> bool:
        if self.end:
            return self.end < current_datetime_local_timezone()
        return False

    def is_upcoming(self) -> bool:
        if self.start:
            return self.start > current_datetime_local_timezone()
        return False

    def is_happening_now(self) -> bool:
        if not self.start or not self.end:
            return False
        now = current_datetime_local_timezone()
        return self.start <= now <= self.end

    def conflicts_with(self, other: "AsyncCalendarEvent") -> bool:
        if not self.start or not self.end or not other.start or not other.end:
            return False
        return self.start < other.end and self.end > other.start

    def get_attendee_emails(self) -> List[str]:
        return [attendee.email for attendee in self.attendees if attendee.email]

    def has_attendee(self, email: str) -> bool:
        return any(attendee.email == email for attendee in self.attendees)

    def __repr__(self):
        return (
            f"Summary: {self.summary!r}\n"
            f"Description: {self.description!r}\n"
            f"Location: {self.location!r}\n"
            f"Time: {convert_datetime_to_readable(self.start, self.end)}\n"
            f"Link: {self.htmlLink!r}\n"
            f"Attendees: {', '.join(self.get_attendee_emails())}\n"
        )

    @classmethod
    def query(cls) -> "AsyncEventQueryBuilder":
        """
        Create a new AsyncEventQueryBuilder for building complex event queries with a fluent API.
        
        Returns:
            AsyncEventQueryBuilder instance for method chaining
            
        Example:
            events = await (AsyncCalendarEvent.query()
                .limit(50)
                .in_date_range(start_date, end_date)
                .search("meeting")
                .in_calendar("work@company.com")
                .execute())
        """
        from .async_query_builder import AsyncEventQueryBuilder
        return AsyncEventQueryBuilder(cls)

    @classmethod
    async def list_events(
        cls,
        number_of_results: Optional[int] = DEFAULT_MAX_RESULTS,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        query: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> List["AsyncCalendarEvent"]:
        """Async version of list_events for fetching events from Google Calendar.
        Args:
            number_of_results: Max number of events to retrieve. Defaults to 100. Max allowed: 2500.
            start: Start date and time as a datetime object. Defaults to the start of the current day.
            end: End date and time as a datetime object. Defaults to 7 days from the start date.
            query: Query string to search events by keyword or related content.
            calendar_id: Calendar ID to fetch events from. Defaults to 'primary'.
        Returns:
            A list of AsyncCalendarEvent objects representing the events found within the specified range.
        Raises:
            ValueError: If number_of_results exceeds 2500 or date range is invalid.
            AsyncCalendarError: If API call fails.
        """
        # Input validation
        if number_of_results and (number_of_results < 1 or number_of_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"number_of_results must be between 1 and {MAX_RESULTS_LIMIT}")
        if query and len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query string cannot exceed {MAX_QUERY_LENGTH} characters")
        
        logger.info("Async fetching events with number_of_results=%s, start=%s, end=%s, query=%s, calendar_id=%s", 
                   number_of_results, start, end, query, calendar_id)
        
        if start is None:
            start = today_start()
        if end is None:
            end = days_from_today(DEFAULT_DAYS_AHEAD)
        
        if start >= end:
            raise ValueError("Start time must be before end time")
            
        start_iso, end_iso = convert_datetime_to_iso(start), convert_datetime_to_iso(end)
        
        async with async_calendar_service() as (aiogoogle, calendar_service):
            request_params = {
                "calendarId": calendar_id,
                "timeMin": start_iso,
                "timeMax": end_iso,
                "maxResults": number_of_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }
            
            if query:
                request_params["q"] = query
            
            events_result = await aiogoogle.as_user(
                calendar_service.events.list(**request_params)
            )
            events = events_result.get("items", [])
            logger.info("Async fetched %d events", len(events))
            
            calendar_events = []
            for event in events:
                try:
                    calendar_events.append(cls._from_google_event(event))
                except Exception as e:
                    logger.warning("Skipping invalid event: %s", e)
                    
            return calendar_events

    @classmethod
    async def get_event(cls, event_id: str, calendar_id: str = "primary") -> "AsyncCalendarEvent":
        """
        Async version of get_event for retrieving a specific event.
        Args:
            event_id: The unique identifier of the event to be retrieved.
            calendar_id: Calendar ID to fetch event from. Defaults to 'primary'.
        Returns:
            An AsyncCalendarEvent object representing the event with the specified ID.
        Raises:
            AsyncCalendarError: If API call fails.
        """
        logger.info("Async retrieving event with ID: %s", event_id)
        
        async with async_calendar_service() as (aiogoogle, calendar_service):
            google_event = await aiogoogle.as_user(
                calendar_service.events.get(calendarId=calendar_id, eventId=event_id)
            )
            logger.info("Async event retrieved successfully")
            return cls._from_google_event(google_event)

    @classmethod
    async def create_event(
        cls,
        start: datetime,
        end: datetime,
        summary: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        recurrence: Optional[List[str]] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = "primary",
    ) -> "AsyncCalendarEvent":
        """
        Async version of create_event for creating a new event.
        Args:
            start: The start date and time of the event, as a datetime object.
            end: The end date and time of the event, as a datetime object.
            summary: A short description or title for the event (optional).
            location: The physical or virtual location of the event (optional).
            description: A long format description or detailed explanation of the event (optional).
            recurrence: A list of strings defining the recurrence rules for the event (optional).
            attendees: A list of attendee emails as strings (optional).
            calendar_id: Calendar ID to create event in. Defaults to 'primary'.
        Returns:
            An AsyncCalendarEvent object representing the newly created event.
        Raises:
            ValueError: If input validation fails.
            AsyncCalendarError: If API call fails.
        """
        logger.info("Async creating event with summary=%s, start=%s, end=%s", summary, start, end)
        
        # Validate input parameters
        if start >= end:
            raise ValueError("Event start time must be before end time")
        if summary and len(summary) > MAX_SUMMARY_LENGTH:
            raise ValueError(f"Event summary cannot exceed {MAX_SUMMARY_LENGTH} characters")
        if description and len(description) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"Event description cannot exceed {MAX_DESCRIPTION_LENGTH} characters")
        if location and len(location) > MAX_LOCATION_LENGTH:
            raise ValueError(f"Event location cannot exceed {MAX_LOCATION_LENGTH} characters")
            
        attendees_list = [{"email": attendee} for attendee in attendees] if attendees else []
        start_iso = convert_datetime_to_iso(start)
        end_iso = convert_datetime_to_iso(end)
        
        event = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
            "attendees": attendees_list,
        }
        if recurrence:
            event["recurrence"] = recurrence
            
        async with async_calendar_service() as (aiogoogle, calendar_service):
            created_event = await aiogoogle.as_user(
                calendar_service.events.insert(calendarId=calendar_id, json=event)
            )
            logger.info("Async event created successfully with ID: %s", created_event.get("id"))
            return cls._from_google_event(created_event)

    async def sync_changes(self, calendar_id: str = "primary") -> None:
        """
        Async version of sync_changes for updating event details.
        Args:
            calendar_id: Calendar ID to update event in. Defaults to 'primary'.
        Raises:
            AsyncCalendarError: If the event update fails.
        """
        logger.info("Async updating event with ID: %s", self.id)
        
        async with async_calendar_service() as (aiogoogle, calendar_service):
            await aiogoogle.as_user(
                calendar_service.events.update(
                    calendarId=calendar_id, 
                    eventId=self.id, 
                    json=self.to_dict()
                )
            )
            logger.info("Async event updated successfully")

    async def delete_event(self, delete_all_recurrence: bool = False, calendar_id: str = "primary") -> None:
        """
        Async version of delete_event for deleting events.
        Args:
            delete_all_recurrence: If True, deletes all events in the recurrence series.
            calendar_id: Calendar ID to delete event from. Defaults to 'primary'.
        Raises:
            AsyncCalendarError: If the event deletion fails.
        """
        logger.info("Async deleting event with ID: %s, delete_all_recurrence=%s", self.id, delete_all_recurrence)
        
        async with async_calendar_service() as (aiogoogle, calendar_service):
            if delete_all_recurrence:
                event = await aiogoogle.as_user(
                    calendar_service.events.get(calendarId=calendar_id, eventId=self.id)
                )
                recurring_event_id = event.get("recurringEventId")
                if recurring_event_id:
                    await aiogoogle.as_user(
                        calendar_service.events.delete(calendarId=calendar_id, eventId=recurring_event_id)
                    )
                    logger.info("Async all recurring events deleted successfully")
                    return
            
            await aiogoogle.as_user(
                calendar_service.events.delete(calendarId=calendar_id, eventId=self.id)
            )
            logger.info("Async event deleted successfully")

    async def add_attendee(self, email: str) -> None:
        """
        Async version of add_attendee for adding attendees.
        Args:
            email: The email address of the attendee to be added.
        Raises:
            AsyncCalendarError: If the attendee addition fails.
        """
        logger.info("Async adding attendee with email: %s to event ID: %s", email, self.id)
        if not self.has_attendee(email):
            self.attendees.append(AsyncAttendee(email=email))
            await self.sync_changes()

    async def remove_attendee(self, email: str) -> None:
        """
        Async version of remove_attendee for removing attendees.
        Args:
            email: The email address of the attendee to be removed.
        Raises:
            AsyncCalendarError: If the attendee removal fails.
        """
        self.attendees = [attendee for attendee in self.attendees if attendee.email != email]
        await self.sync_changes()

    async def update_summary(self, summary: str) -> None:
        """
        Async version of update_summary for updating event summary.
        Args:
            summary: The new summary for the event.
        Raises:
            AsyncCalendarError: If the summary update fails.
        """
        logger.info("Async updating summary for event ID: %s to %s", self.id, summary)
        self._validate_text_field(summary, MAX_SUMMARY_LENGTH, "summary")
        self.summary = summary
        await self.sync_changes()

    async def update_description(self, description: str) -> None:
        """
        Async version of update_description for updating event description.
        Args:
            description: The new description for the event.
        Raises:
            AsyncCalendarError: If the description update fails.
        """
        logger.info("Async updating description for event ID: %s", self.id)
        self._validate_text_field(description, MAX_DESCRIPTION_LENGTH, "description")
        self.description = description
        await self.sync_changes()

    async def update_location(self, location: str) -> None:
        """
        Async version of update_location for updating event location.
        Args:
            location: The new location for the event.
        Raises:
            AsyncCalendarError: If the location update fails.
        """
        logger.info("Async updating location for event ID: %s to %s", self.id, location)
        self._validate_text_field(location, MAX_LOCATION_LENGTH, "location")
        self.location = location
        await self.sync_changes()

    async def update_start_time(self, start: datetime) -> None:
        """
        Async version of update_start_time for updating event start time.
        Args:
            start: The new start time as a datetime object.
        Raises:
            AsyncCalendarError: If the start time update fails.
        """
        logger.info("Async updating start time for event ID: %s to %s", self.id, start)
        self._validate_datetime_range(start, self.end)
        self.start = start
        await self.sync_changes()

    async def update_end_time(self, end: datetime) -> None:
        """
        Async version of update_end_time for updating event end time.
        Args:
            end: The new end time as a datetime object.
        Raises:
            AsyncCalendarError: If the end time update fails.
        """
        logger.info("Async updating end time for event ID: %s to %s", self.id, end)
        self._validate_datetime_range(self.start, end)
        self.end = end
        await self.sync_changes()

    async def update_recurrence(self, recurrence: List[str]) -> None:
        """
        Async version of update_recurrence for updating event recurrence.
        Args:
            recurrence: A list of strings defining the recurrence rules in RFC 5545 format.
        Raises:
            AsyncCalendarError: If the recurrence update fails.
        """
        logger.info("Async updating recurrence for event ID: %s", self.id)
        self.recurrence = recurrence
        await self.sync_changes()

    # Batch Operations for Concurrent Processing
    @classmethod
    async def batch_create_events(
        cls,
        events_data: List[Dict[str, Any]],
        calendar_id: str = "primary"
    ) -> List["AsyncCalendarEvent"]:
        """
        Create multiple events concurrently for better performance.
        Args:
            events_data: List of dictionaries containing event data.
                        Each dict should have: start, end, summary, location, description, etc.
            calendar_id: Calendar ID to create events in. Defaults to 'primary'.
        Returns:
            List of AsyncCalendarEvent objects representing the created events.
        Raises:
            AsyncCalendarError: If any event creation fails.
        """
        logger.info("Batch creating %d events", len(events_data))
        
        async def create_single_event(event_data):
            return await cls.create_event(
                start=event_data["start"],
                end=event_data["end"],
                summary=event_data.get("summary"),
                location=event_data.get("location"),
                description=event_data.get("description"),
                recurrence=event_data.get("recurrence"),
                attendees=event_data.get("attendees"),
                calendar_id=calendar_id
            )
        
        # Create all events concurrently
        tasks = [create_single_event(event_data) for event_data in events_data]
        created_events = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        successful_events = []
        for i, result in enumerate(created_events):
            if isinstance(result, Exception):
                logger.error("Failed to create event %d: %s", i, result)
                raise AsyncCalendarError(f"Failed to create event {i}: {result}")
            successful_events.append(result)
        
        logger.info("Successfully batch created %d events", len(successful_events))
        return successful_events

    @classmethod
    async def batch_get_events(
        cls,
        event_ids: List[str],
        calendar_id: str = "primary"
    ) -> List["AsyncCalendarEvent"]:
        """
        Retrieve multiple events concurrently for better performance.
        Args:
            event_ids: List of event IDs to retrieve.
            calendar_id: Calendar ID to fetch events from. Defaults to 'primary'.
        Returns:
            List of AsyncCalendarEvent objects.
        Raises:
            AsyncCalendarError: If any event retrieval fails.
        """
        logger.info("Batch retrieving %d events", len(event_ids))
        
        async def get_single_event(event_id):
            return await cls.get_event(event_id, calendar_id)
        
        # Retrieve all events concurrently
        tasks = [get_single_event(event_id) for event_id in event_ids]
        events = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        successful_events = []
        for i, result in enumerate(events):
            if isinstance(result, Exception):
                logger.error("Failed to retrieve event %s: %s", event_ids[i], result)
                raise AsyncCalendarError(f"Failed to retrieve event {event_ids[i]}: {result}")

            successful_events.append(result)
        
        logger.info("Successfully batch retrieved %d events", len(successful_events))
        return successful_events

    @classmethod
    async def batch_update_events(
        cls,
        events: List["AsyncCalendarEvent"],
        calendar_id: str = "primary"
    ) -> None:
        """
        Update multiple events concurrently for better performance.
        Args:
            events: List of AsyncCalendarEvent objects to update.
            calendar_id: Calendar ID to update events in. Defaults to 'primary'.
        Raises:
            AsyncCalendarError: If any event update fails.
        """
        logger.info("Batch updating %d events", len(events))
        
        async def update_single_event(event):
            await event.sync_changes(calendar_id)
        
        # Update all events concurrently
        tasks = [update_single_event(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Failed to update event %s: %s", events[i].id, result)
                raise AsyncCalendarError(f"Failed to update event {events[i].id}: {result}")
        
        logger.info("Successfully batch updated %d events", len(events))

    @classmethod
    async def batch_delete_events(
        cls,
        event_ids: List[str],
        delete_all_recurrence: bool = False,
        calendar_id: str = "primary"
    ) -> None:
        """
        Delete multiple events concurrently for better performance.
        Args:
            event_ids: List of event IDs to delete.
            delete_all_recurrence: If True, deletes all events in recurrence series.
            calendar_id: Calendar ID to delete events from. Defaults to 'primary'.
        Raises:
            AsyncCalendarError: If any event deletion fails.
        """
        logger.info("Batch deleting %d events", len(event_ids))
        
        async def delete_single_event(event_id):
            # Create a temporary event object for deletion
            temp_event = AsyncCalendarEvent(id=event_id)
            await temp_event.delete_event(delete_all_recurrence, calendar_id)
        
        # Delete all events concurrently
        tasks = [delete_single_event(event_id) for event_id in event_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Failed to delete event %s: %s", event_ids[i], result)
                raise AsyncCalendarError(f"Failed to delete event {event_ids[i]}: {result}")
        
        logger.info("Successfully batch deleted %d events", len(event_ids))

    @classmethod
    async def concurrent_list_multiple_calendars(
        cls,
        calendar_ids: List[str],
        number_of_results: Optional[int] = DEFAULT_MAX_RESULTS,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        query: Optional[str] = None,
    ) -> Dict[str, List["AsyncCalendarEvent"]]:
        """
        List events from multiple calendars concurrently for better performance.
        Args:
            calendar_ids: List of calendar IDs to fetch events from.
            number_of_results: Max number of events per calendar.
            start: Start date and time filter.
            end: End date and time filter.
            query: Query string to search events.
        Returns:
            Dictionary mapping calendar_id to list of events.
        Raises:
            AsyncCalendarError: If any calendar listing fails.
        """
        logger.info("Concurrently listing events from %d calendars", len(calendar_ids))
        
        async def list_calendar_events(calendar_id):
            return await cls.list_events(
                number_of_results=number_of_results,
                start=start,
                end=end,
                query=query,
                calendar_id=calendar_id
            )
        
        # List events from all calendars concurrently
        tasks = [list_calendar_events(calendar_id) for calendar_id in calendar_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions and build result dictionary
        calendar_events = {}
        for i, result in enumerate(results):
            calendar_id = calendar_ids[i]
            if isinstance(result, Exception):
                logger.error("Failed to list events from calendar %s: %s", calendar_id, result)
                raise AsyncCalendarError(f"Failed to list events from calendar {calendar_id}: {result}")
            calendar_events[calendar_id] = result
        
        total_events = sum(len(events) for events in calendar_events.values())
        logger.info("Successfully listed %d total events from %d calendars", total_events, len(calendar_ids))
        return calendar_events