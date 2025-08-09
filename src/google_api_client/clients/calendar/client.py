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

    @classmethod
    def query(cls, service: "Resource") -> "EventQueryBuilder":
        """
        Create a new EventQueryBuilder for building complex event queries with a fluent API.
        
        Args:
            service: The calendar service instance.
        
        Returns:
            EventQueryBuilder instance for method chaining
            
        Example:
            events = (CalendarEvent.query(service)
                .limit(50)
                .in_date_range(start_date, end_date)
                .search("meeting")
                .in_calendar("work@company.com")
                .execute())
        """
        from .query_builder import EventQueryBuilder
        return EventQueryBuilder(cls, service)

    @classmethod
    def list_events(
        cls,
        service: "Resource",
        number_of_results: Optional[int] = DEFAULT_MAX_RESULTS,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        query: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> List[Self]:
        """Fetches a list of events from Google Calendar within the specified date range.
        Args:
            service: The calendar service instance.
            number_of_results: Max number of events to retrieve. Defaults to 100. Max allowed: 2500.
            start: Start date and time as a datetime object. Defaults to the start of the current day.
            end: End date and time as a datetime object. Defaults to 7 days from the start date.
            query: Query string to search events by keyword or related content.
            calendar_id: Calendar ID to fetch events from. Defaults to 'primary'.
        Returns:
            A list of CalendarEvent objects representing the events found within the specified range.
            If no events are found, an empty list is returned.
        Raises:
            ValueError: If number_of_results exceeds 2500 or date range is invalid.
        """
        # Input validation
        if number_of_results and (number_of_results < 1 or number_of_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"number_of_results must be between 1 and {MAX_RESULTS_LIMIT}")
        if query and len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query string cannot exceed {MAX_QUERY_LENGTH} characters")
        
        logger.info("Fetching events with number_of_results=%s, start=%s, end=%s, query=%s, calendar_id=%s", 
                   number_of_results, start, end, query, calendar_id)
        
        if start is None:
            start = today_start()
        if end is None:
            end = days_from_today(DEFAULT_DAYS_AHEAD)
        
        if start >= end:
            raise ValueError("Start time must be before end time")
            
        start_iso, end_iso = convert_datetime_to_iso(start), convert_datetime_to_iso(end)
        
        try:
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
            
            events_result = service.events().list(**request_params).execute()
            events = events_result.get("items", [])
            logger.info("Fetched %d events", len(events))
            
            calendar_events = []
            for event in events:
                try:
                    calendar_events.append(cls._from_google_event(event))
                except Exception as e:
                    logger.warning("Skipping invalid event: %s", e)
                    
            return calendar_events
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise CalendarNotFoundError(f"Calendar or event not found: {e}")
            else:
                raise CalendarError(f"Calendar API error: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected calendar service error: {e}")

    @classmethod
    def get_event(cls, service: "Resource", event_id: str) -> "CalendarEvent":
        """
        Retrieves a specific event from the user's Google Calendar using its unique identifier.
        Args:
            service: The calendar service instance.
            event_id: The unique identifier of the event to be retrieved.
        Returns:
            A CalendarEvent object representing the event with the specified ID.
        """
        logger.info("Retrieving event with ID: %s", event_id)
        
        try:
            google_event = service.events().get(calendarId="primary", eventId=event_id).execute()
            logger.info("Event retrieved successfully")
            return cls._from_google_event(google_event)
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise CalendarNotFoundError(f"Calendar or event not found: {e}")
            else:
                raise CalendarError(f"Calendar API error: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected calendar service error: {e}")

    @classmethod
    def create_event(
        cls,
        service: "Resource",
        start: datetime,
        end: datetime,
        summary: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        recurrence: Optional[List[str]] = None,
        attendees: Optional[List[str]] = None
    ) -> "CalendarEvent":
        """
        Creates a new event in the user's primary Google Calendar and returns a CalendarEvent object.
        Args:
            service: The calendar service instance.
            start: The start date and time of the event, as a datetime object.
            end: The end date and time of the event, as a datetime object.
            summary: A short description or title for the event (optional).
            location: The physical or virtual location of the event (optional).
            description: A long format description or detailed explanation of the event (optional).
            recurrence: A list of strings defining the recurrence rules for the event (optional).
            attendees: A list of attendee emails as strings (optional).
        Returns:
            A CalendarEvent object representing the newly created event.
        """
        logger.info("Creating event with summary=%s, start=%s, end=%s", summary, start, end)
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
            
        try:
            event = service.events().insert(calendarId="primary", body=event).execute()
            logger.info("Event created successfully with ID: %s", event.get("id"))
            return cls._from_google_event(event)
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise CalendarNotFoundError(f"Calendar or event not found: {e}")
            else:
                raise CalendarError(f"Calendar API error: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected calendar service error: {e}")

    def sync_changes(self, service: "Resource") -> None:
        """
        Updates this event in the user's Google Calendar with new details.
        Args:
            service: The calendar service instance.
        Raises:
            CalendarError: If the event update fails.
        """
        logger.info("Updating event with ID: %s", self.id)
        
        try:
            updated_event = service.events().update(calendarId="primary", eventId=self.id, body=self.to_dict()).execute()
            logger.info("Event updated successfully")
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise CalendarNotFoundError(f"Calendar or event not found: {e}")
            else:
                raise CalendarError(f"Calendar API error: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected calendar service error: {e}")

    def delete_event(self, service: "Resource", delete_all_recurrence: bool = False) -> None:
        """
        Deletes this event from the user's Google Calendar. Can delete a single event or all in a recurrence series.
        Args:
            service: The calendar service instance.
            delete_all_recurrence: If True, deletes all events in the recurrence series.
        Raises:
            CalendarError: If the event deletion fails.
        """
        logger.info("Deleting event with ID: %s, delete_all_recurrence=%s", self.id, delete_all_recurrence)
        
        try:
            if delete_all_recurrence:
                event = service.events().get(calendarId="primary", eventId=self.id).execute()
                recurring_event_id = event.get("recurringEventId")
                if recurring_event_id:
                    service.events().delete(calendarId="primary", eventId=recurring_event_id).execute()
                    logger.info("All recurring events deleted successfully")
                    return
            service.events().delete(calendarId="primary", eventId=self.id).execute()
            logger.info("Event deleted successfully")
        except HttpError as e:
            if e.resp.status == 403:
                raise CalendarPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise CalendarNotFoundError(f"Calendar or event not found: {e}")
            else:
                raise CalendarError(f"Calendar API error: {e}")
        except Exception as e:
            raise CalendarError(f"Unexpected calendar service error: {e}")

    def add_attendee(self, service: "Resource", email: str) -> None:
        """
        Adds an attendee to the event if they are not already in the list.
        Args:
            service: The calendar service instance.
            email: The email address of the attendee to be added.
        Raises:
            CalendarError: If the attendee addition fails.
        """
        logger.info("Adding attendee with email: %s to event ID: %s", email, self.id)
        if not self.has_attendee(email):
            self.attendees.append(Attendee(email=email))
            self.sync_changes(service)

    def remove_attendee(self, service: "Resource", email: str) -> None:
        """
        Removes an attendee from the event by their email address.
        Args:
            service: The calendar service instance.
            email: The email address of the attendee to be removed.
        Raises:
            CalendarError: If the attendee removal fails.
        """
        self.attendees = [attendee for attendee in self.attendees if attendee.email != email]
        self.sync_changes(service)

    def update_summary(self, service: "Resource", summary: str) -> None:
        """
        Updates the summary of the event.
        Args:
            service: The calendar service instance.
            summary: The new summary for the event.
        Raises:
            CalendarError: If the summary update fails.
        """
        logger.info("Updating summary for event ID: %s to %s", self.id, summary)
        self._validate_text_field(summary, MAX_SUMMARY_LENGTH, "summary")
        self.summary = summary
        self.sync_changes(service)

    def update_description(self, service: "Resource", description: str) -> None:
        """
        Updates the description of the event.
        Args:
            service: The calendar service instance.
            description: The new description for the event.
        Raises:
            CalendarError: If the description update fails.
        """
        logger.info("Updating description for event ID: %s", self.id)
        self._validate_text_field(description, MAX_DESCRIPTION_LENGTH, "description")
        self.description = description
        self.sync_changes(service)

    def update_location(self, service: "Resource", location: str) -> None:
        """
        Updates the location of the event.
        Args:
            service: The calendar service instance.
            location: The new location for the event.
        Raises:
            CalendarError: If the location update fails.
        """
        logger.info("Updating location for event ID: %s to %s", self.id, location)
        self._validate_text_field(location, MAX_LOCATION_LENGTH, "location")
        self.location = location
        self.sync_changes(service)

    def update_start_time(self, service: "Resource", start: datetime) -> None:
        """
        Updates the start time of the event.
        Args:
            service: The calendar service instance.
            start: The new start time as a datetime object.
        Raises:
            CalendarError: If the start time update fails.
        """
        logger.info("Updating start time for event ID: %s to %s", self.id, start)
        self._validate_datetime_range(start, self.end)
        self.start = start
        self.sync_changes(service)

    def update_end_time(self, service: "Resource", end: datetime) -> None:
        """
        Updates the end time of the event.
        Args:
            service: The calendar service instance.
            end: The new end time as a datetime object.
        Raises:
            CalendarError: If the end time update fails.
        """
        logger.info("Updating end time for event ID: %s to %s", self.id, end)
        self._validate_datetime_range(self.start, end)
        self.end = end
        self.sync_changes(service)

    def update_recurrence(self, service: "Resource", recurrence: List[str]) -> None:
        """
        Updates the recurrence rules for the event.
        Args:
            service: The calendar service instance.
            recurrence: A list of strings defining the recurrence rules in RFC 5545 format.
        Raises:
            CalendarError: If the recurrence update fails.
        """
        logger.info("Updating recurrence for event ID: %s", self.id)
        self.recurrence = recurrence
        self.sync_changes(service)

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


    def __repr__(self):
        return (
            f"Summary: {self.summary!r}\n"
            f"Description: {self.description!r}\n"
            f"Location: {self.location!r}\n"
            f"Time: {convert_datetime_to_readable(self.start, self.end)}\n"
            f"Link: {self.htmlLink!r}\n"
            f"Attendees: {', '.join(self.get_attendee_emails())}\n"
        )
