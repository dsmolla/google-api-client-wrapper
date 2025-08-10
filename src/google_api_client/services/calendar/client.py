from datetime import datetime, date, time, timedelta
from typing import Optional, List, Self, Union, TYPE_CHECKING
from ...utils.datetime import convert_datetime_to_iso, convert_datetime_to_readable, current_datetime_local_timezone, today_start, days_from_today
from dataclasses import dataclass, field
import logging
import re
from googleapiclient.errors import HttpError

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)

# Constants
MAX_RESULTS_LIMIT = 2500
MAX_SUMMARY_LENGTH = 1024
MAX_DESCRIPTION_LENGTH = 8192
MAX_LOCATION_LENGTH = 1024
MAX_QUERY_LENGTH = 500
DEFAULT_MAX_RESULTS = 100
DEFAULT_DAYS_AHEAD = 7

# Import exceptions from centralized location
from ...exceptions.calendar import CalendarError, CalendarPermissionError, CalendarNotFoundError

@dataclass
class Attendee:
    """
    Represents an attendee of a calendar event with their email, display name, and response status.
    Args:
        email: The email address of the attendee.
        display_name: The display name of the attendee (optional).
        response_status: The response status of the attendee (optional).
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
class CalendarEvent:
    """
    Represents a calendar event with various attributes.
    Args:
        id: Unique identifier for the event.
        summary: A brief title or summary of the event.
        description: A detailed description of the event.
        location: The physical or virtual location of the event.
        start: The start time of the event as a datetime object.
        end: The end time of the event as a datetime object.
        htmlLink: A hyperlink to the event on Google Calendar.
        attendees: A list of Attendee objects representing the people invited to the event.
        recurrence: A list of strings defining the recurrence rules for the event in RFC 5545 format.
        recurringEventId: The ID of the recurring event if this event is part of a series.
    """
    id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    htmlLink: Optional[str] = None
    attendees: List[Attendee] = field(default_factory=list)
    recurrence: List[str] = field(default_factory=list)
    recurringEventId: Optional[str] = None
    _user_client: Optional["UserClient"] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._validate_datetime_range(self.start, self.end)
        self._validate_text_field(self.summary, MAX_SUMMARY_LENGTH, "summary")
        self._validate_text_field(self.description, MAX_DESCRIPTION_LENGTH, "description")
        self._validate_text_field(self.location, MAX_LOCATION_LENGTH, "location")

    def set_user_client(self, user_client):
        """Set user context for this event."""
        from ...user_client import UserClient
        self._user_client = user_client

    def _get_user_client(self):
        """Get the user client for this event."""
        if self._user_client is None:
            raise ValueError("Calendar event must have user context. Use user.calendar methods to get events.")
        return self._user_client

    def _validate_datetime_range(self, start: Optional[datetime], end: Optional[datetime]) -> None:
        """Validates that start time is before end time."""
        if start and end and start >= end:
            raise ValueError("Event start time must be before end time")
    
    def _validate_text_field(self, value: Optional[str], max_length: int, field_name: str) -> None:
        """Validates text field length and content."""
        if value and len(value) > max_length:
            raise ValueError(f"Event {field_name} cannot exceed {max_length} characters")

    @staticmethod
    def _from_google_event(google_event: dict) -> "CalendarEvent":
        """
        Creates a CalendarEvent instance from a Google Calendar API response.
        Args:
            google_event: A dictionary containing event data from Google Calendar API.
        Returns:
            A CalendarEvent instance populated with the data from the dictionary.
        """
        attendees = []
        for attendee_data in google_event.get("attendees", []):
            email = attendee_data.get("email")
            if email and Attendee._is_valid_email(email):
                try:
                    attendees.append(Attendee(
                        email=email,
                        display_name=attendee_data.get("displayName"),
                        response_status=attendee_data.get("responseStatus")
                    ))
                except ValueError as e:
                    logger.warning("Skipping invalid attendee: %s", e)
        start = CalendarEvent._parse_datetime(google_event.get("start", {}))
        end = CalendarEvent._parse_datetime(google_event.get("end", {}))
        return CalendarEvent(
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
        """Convert CalendarEvent to dictionary format for Google Calendar API."""
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


    def sync_changes(self) -> None:
        """
        Updates this event in the user's Google Calendar with new details.
        Raises:
            CalendarError: If the event update fails.
        """
        logger.info("Updating event with ID: %s", self.id)
        user_client = self._get_user_client()
        return user_client.calendar._update_event(self.id, self)

    def delete_event(self, delete_all_recurrence: bool = False) -> None:
        """
        Deletes this event from the user's Google Calendar. Can delete a single event or all in a recurrence series.
        Args:
            delete_all_recurrence: If True, deletes all events in the recurrence series.
        Raises:
            CalendarError: If the event deletion fails.
        """
        logger.info("Deleting event with ID: %s, delete_all_recurrence=%s", self.id, delete_all_recurrence)
        user_client = self._get_user_client()
        return user_client.calendar._delete_event(self.id, delete_all_recurrence)

    def add_attendee(self, email: str) -> None:
        """
        Adds an attendee to the event if they are not already in the list.
        Args:
            email: The email address of the attendee to be added.
        Raises:
            CalendarError: If the attendee addition fails.
        """
        logger.info("Adding attendee with email: %s to event ID: %s", email, self.id)
        if not self.has_attendee(email):
            self.attendees.append(Attendee(email=email))
            self.sync_changes()

    def remove_attendee(self, email: str) -> None:
        """
        Removes an attendee from the event by their email address.
        Args:
            email: The email address of the attendee to be removed.
        Raises:
            CalendarError: If the attendee removal fails.
        """
        self.attendees = [attendee for attendee in self.attendees if attendee.email != email]
        self.sync_changes()

    def update_summary(self, summary: str) -> None:
        """
        Updates the summary of the event.
        Args:
            summary: The new summary for the event.
        Raises:
            CalendarError: If the summary update fails.
        """
        logger.info("Updating summary for event ID: %s to %s", self.id, summary)
        self._validate_text_field(summary, MAX_SUMMARY_LENGTH, "summary")
        self.summary = summary
        self.sync_changes()

    def update_description(self, description: str) -> None:
        """
        Updates the description of the event.
        Args:
            description: The new description for the event.
        Raises:
            CalendarError: If the description update fails.
        """
        logger.info("Updating description for event ID: %s", self.id)
        self._validate_text_field(description, MAX_DESCRIPTION_LENGTH, "description")
        self.description = description
        self.sync_changes()

    def update_location(self, location: str) -> None:
        """
        Updates the location of the event.
        Args:
            location: The new location for the event.
        Raises:
            CalendarError: If the location update fails.
        """
        logger.info("Updating location for event ID: %s to %s", self.id, location)
        self._validate_text_field(location, MAX_LOCATION_LENGTH, "location")
        self.location = location
        self.sync_changes()

    def update_start_time(self, start: datetime) -> None:
        """
        Updates the start time of the event.
        Args:
            start: The new start time as a datetime object.
        Raises:
            CalendarError: If the start time update fails.
        """
        logger.info("Updating start time for event ID: %s to %s", self.id, start)
        self._validate_datetime_range(start, self.end)
        self.start = start
        self.sync_changes()

    def update_end_time(self, end: datetime) -> None:
        """
        Updates the end time of the event.
        Args:
            end: The new end time as a datetime object.
        Raises:
            CalendarError: If the end time update fails.
        """
        logger.info("Updating end time for event ID: %s to %s", self.id, end)
        self._validate_datetime_range(self.start, end)
        self.end = end
        self.sync_changes()

    def update_recurrence(self, recurrence: List[str]) -> None:
        """
        Updates the recurrence rules for the event.
        Args:
            recurrence: A list of strings defining the recurrence rules in RFC 5545 format.
        Raises:
            CalendarError: If the recurrence update fails.
        """
        logger.info("Updating recurrence for event ID: %s", self.id)
        self.recurrence = recurrence
        self.sync_changes()

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

    def conflicts_with(self, other: "CalendarEvent") -> bool:
        if not self.start or not self.end or not other.start or not other.end:
            return False
        return self.start < other.end and self.end > other.start

    def get_attendee_emails(self) -> List[str]:
        return [attendee.email for attendee in self.attendees if attendee.email]

    def has_attendee(self, email: str) -> bool:
        return any(attendee.email == email for attendee in self.attendees)

    @staticmethod
    def _list_events_with_service(service: "Resource", **kwargs) -> List["CalendarEvent"]:
        """Implementation of list_events using direct service."""
        logger.info("Fetching calendar events with kwargs: %s", kwargs)
        
        number_of_results = kwargs.get('number_of_results', DEFAULT_MAX_RESULTS)
        if number_of_results and (number_of_results < 1 or number_of_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"number_of_results must be between 1 and {MAX_RESULTS_LIMIT}")
        
        try:
            request_params = {
                'calendarId': kwargs.get('calendar_id', 'primary'),
                'maxResults': number_of_results or DEFAULT_MAX_RESULTS,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            # Add time range filters if provided
            if kwargs.get('start'):
                request_params['timeMin'] = convert_datetime_to_iso(kwargs['start'])
            if kwargs.get('end'):
                request_params['timeMax'] = convert_datetime_to_iso(kwargs['end'])
            if kwargs.get('query'):
                request_params['q'] = kwargs['query']
            
            events_result = service.events().list(**request_params).execute()
            events_data = events_result.get('items', [])
            
            calendar_events = []
            for event_data in events_data:
                try:
                    calendar_event = CalendarEvent._from_google_event(event_data)
                    calendar_events.append(calendar_event)
                except Exception as e:
                    logger.warning("Failed to parse event %s: %s", event_data.get('id'), e)
                    continue
            
            logger.info("Retrieved %d calendar events", len(calendar_events))
            return calendar_events
            
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise CalendarNotFoundError(f"Calendar not found: {e}")
            else:
                raise CalendarError(f"Calendar API error listing events: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected error listing events: {e}")

    @staticmethod
    def _get_event_with_service(service: "Resource", event_id: str, calendar_id: str = 'primary') -> "CalendarEvent":
        """Implementation of get_event using direct service."""
        logger.info("Fetching calendar event with ID: %s", event_id)
        
        try:
            event_data = service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            calendar_event = CalendarEvent._from_google_event(event_data)
            return calendar_event
            
        except HttpError as e:
            if e.resp.status == 404:
                raise CalendarNotFoundError(f"Event not found: {event_id}")
            elif e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied accessing event: {e}")
            else:
                raise CalendarError(f"Calendar API error getting event {event_id}: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected error getting event: {e}")

    @staticmethod
    def _create_event_with_service(service: "Resource", start, end, summary: str = None, **kwargs) -> "CalendarEvent":
        """Implementation of create_event using direct service."""
        logger.info("Creating calendar event: %s", summary)
        
        if not start or not end:
            raise ValueError("Event must have both start and end times")
        if start >= end:
            raise ValueError("Event start time must be before end time")
        
        try:
            event_body = {
                'summary': summary or "New Event",
                'start': {'dateTime': convert_datetime_to_iso(start)},
                'end': {'dateTime': convert_datetime_to_iso(end)}
            }
            
            # Add optional fields if provided
            if kwargs.get('description'):
                event_body['description'] = kwargs['description']
            if kwargs.get('location'):
                event_body['location'] = kwargs['location']
            if kwargs.get('attendees'):
                event_body['attendees'] = [
                    attendee.to_dict() if hasattr(attendee, 'to_dict') else attendee 
                    for attendee in kwargs['attendees']
                ]
            if kwargs.get('recurrence'):
                event_body['recurrence'] = kwargs['recurrence']
            
            calendar_id = kwargs.get('calendar_id', 'primary')
            
            created_event = service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            calendar_event = CalendarEvent._from_google_event(created_event)
            logger.info("Calendar event created successfully with ID: %s", calendar_event.id)
            return calendar_event
            
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied creating event: {e}")
            elif e.resp.status == 409:
                raise CalendarError(f"Event conflict: {e}")
            else:
                raise CalendarError(f"Calendar API error creating event: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected error creating event: {e}")

    def __repr__(self):
        return (
            f"Summary: {self.summary!r}\n"
            f"Description: {self.description!r}\n"
            f"Location: {self.location!r}\n"
            f"Time: {convert_datetime_to_readable(self.start, self.end)}\n"
            f"Link: {self.htmlLink!r}\n"
            f"Attendees: {', '.join(self.get_attendee_emails())}\n"
        )


class CalendarService:
    """
    Service layer for Calendar API operations.
    Contains all Calendar API functionality that was removed from dataclasses.
    """
    
    def __init__(self, service: "Resource", user_client: "UserClient"):
        """
        Initialize Calendar service.
        
        Args:
            service: The Calendar API service instance
            user_client: The user client for context
        """
        self._service = service
        self._user_client = user_client

    def list_events(self, number_of_results: Optional[int] = 100, **kwargs) -> List[CalendarEvent]:
        """List calendar events for the user."""
        events = CalendarEvent._list_events_with_service(self._service, number_of_results=number_of_results, **kwargs)
        # Set user context for each event
        for event in events:
            event.set_user_client(self._user_client)
        return events

    def get_event(self, event_id: str) -> CalendarEvent:
        """Get specific calendar event by ID."""
        event = CalendarEvent._get_event_with_service(self._service, event_id)
        event.set_user_client(self._user_client)
        return event

    def create_event(self, start, end, summary: str = None, **kwargs) -> CalendarEvent:
        """Create calendar event for the user."""
        event = CalendarEvent._create_event_with_service(self._service, start, end, summary=summary, **kwargs)
        event.set_user_client(self._user_client)
        return event

    def _update_event(self, event_id: str, event: CalendarEvent, calendar_id: str = 'primary') -> CalendarEvent:
        """Update calendar event."""
        logger.info("Updating calendar event with ID: %s", event_id)
        
        try:
            event_body = event.to_dict()
            # Remove fields that shouldn't be updated
            event_body.pop('id', None)
            event_body.pop('htmlLink', None)
            event_body.pop('recurringEventId', None)
            
            updated_event = self._service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event_body
            ).execute()
            
            updated_calendar_event = CalendarEvent._from_google_event(updated_event)
            updated_calendar_event.set_user_client(self._user_client)
            logger.info("Calendar event updated successfully")
            return updated_calendar_event
            
        except HttpError as e:
            if e.resp.status == 404:
                raise CalendarNotFoundError(f"Event not found: {event_id}")
            elif e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied updating event: {e}")
            elif e.resp.status == 409:
                raise CalendarError(f"Event conflict during update: {e}")
            else:
                raise CalendarError(f"Calendar API error updating event {event_id}: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected error updating event: {e}")

    def _delete_event(self, event_id: str, delete_all_recurrence: bool = False, calendar_id: str = 'primary') -> bool:
        """Delete calendar event."""
        logger.info("Deleting calendar event with ID: %s, delete_all_recurrence: %s", event_id, delete_all_recurrence)
        
        try:
            request_params = {
                'calendarId': calendar_id,
                'eventId': event_id
            }
            
            if delete_all_recurrence:
                request_params['sendNotifications'] = False
                
            self._service.events().delete(**request_params).execute()
            
            logger.info("Calendar event deleted successfully")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                raise CalendarNotFoundError(f"Event not found: {event_id}")
            elif e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied deleting event: {e}")
            else:
                raise CalendarError(f"Calendar API error deleting event {event_id}: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected error deleting event: {e}")

    def query(self):
        """Create event query builder for this user."""
        from .query_builder import EventQueryBuilder
        return EventQueryBuilder(CalendarEvent, self._service, self._user_client)
