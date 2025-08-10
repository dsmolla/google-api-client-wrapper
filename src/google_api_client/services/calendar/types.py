from datetime import datetime, date, time
from typing import Optional, List
from dataclasses import dataclass, field
import re

from src.google_api_client.utils.datetime import convert_datetime_to_readable, current_datetime_local_timezone


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
        """
        Converts the Attendee instance to a dictionary representation.
        Returns:
            A dictionary containing the attendee data.
        """
        attendee = {"email": self.email}
        if self.display_name:
            attendee["displayName"] = self.display_name
        if self.response_status:
            attendee["responseStatus"] = self.response_status
        return attendee

    def __str__(self):
        if self.display_name:
            return f"{self.display_name} <{self.email}>"
        return self.email


@dataclass
class CalendarEvent:
    """
    Represents a calendar event with various attributes.
    Args:
        event_id: Unique identifier for the event.
        summary: A brief title or summary of the event.
        description: A detailed description of the event.
        location: The physical or virtual location of the event.
        start: The start time of the event as a datetime object.
        end: The end time of the event as a datetime object.
        html_link: A hyperlink to the event on Google Calendar.
        attendees: A list of Attendee objects representing the people invited to the event.
        recurrence: A list of strings defining the recurrence rules for the event in RFC 5545 format.
        recurring_event_id: The ID of the recurring event if this event is part of a series.
        creator: The creator of the event.
        organizer: The organizer of the event.
        status: The status of the event (confirmed, tentative, cancelled).
    """
    event_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    html_link: Optional[str] = None
    attendees: List[Attendee] = field(default_factory=list)
    recurrence: List[str] = field(default_factory=list)
    recurring_event_id: Optional[str] = None
    creator: Optional[str] = None
    organizer: Optional[str] = None
    status: Optional[str] = "confirmed"

    def duration_minutes(self) -> Optional[int]:
        """
        Calculate the duration of the event in minutes.
        Returns:
            Duration in minutes, or None if start/end times are missing.
        """
        if self.start and self.end:
            total_seconds = (self.end - self.start).total_seconds()
            return int(total_seconds / 60)
        return None

    def is_today(self) -> bool:
        """
        Check if the event occurs today.
        Returns:
            True if the event is today, False otherwise.
        """
        if self.start:
            return self.start.date() == date.today()
        return False

    def is_all_day(self) -> bool:
        """
        Check if the event is an all-day event.
        Returns:
            True if the event is all-day, False otherwise.
        """
        if not self.start or not self.end:
            return False
        return self.start.time() == time.min and self.end.time() == time.min and (self.end - self.start).days >= 1

    def is_past(self) -> bool:
        """
        Check if the event has already ended.
        Returns:
            True if the event is in the past, False otherwise.
        """
        if self.end:
            return self.end < current_datetime_local_timezone()
        return False

    def is_upcoming(self) -> bool:
        """
        Check if the event is in the future.
        Returns:
            True if the event is upcoming, False otherwise.
        """
        if self.start:
            return self.start > current_datetime_local_timezone()
        return False

    def is_happening_now(self) -> bool:
        """
        Check if the event is currently happening.
        Returns:
            True if the event is happening now, False otherwise.
        """
        if not self.start or not self.end:
            return False
        now = current_datetime_local_timezone()
        return self.start <= now <= self.end

    def conflicts_with(self, other: "CalendarEvent") -> bool:
        """
        Check if this event conflicts with another event.
        Args:
            other: Another CalendarEvent to check for conflicts
        Returns:
            True if the events overlap in time, False otherwise.
        """
        if not self.start or not self.end or not other.start or not other.end:
            return False
        return self.start < other.end and self.end > other.start

    def get_attendee_emails(self) -> List[str]:
        """
        Get a list of all attendee email addresses.
        Returns:
            List of email addresses.
        """
        return [attendee.email for attendee in self.attendees if attendee.email]

    def has_attendee(self, email: str) -> bool:
        """
        Check if a specific email is in the attendee list.
        Args:
            email: Email address to check for
        Returns:
            True if the email is an attendee, False otherwise.
        """
        return any(attendee.email == email for attendee in self.attendees)

    def is_recurring(self) -> bool:
        """
        Check if the event is part of a recurring series.
        Returns:
            True if the event has recurrence rules, False otherwise.
        """
        return bool(self.recurrence or self.recurring_event_id)

    def to_dict(self) -> dict:
        """
        Convert CalendarEvent to dictionary format for Google Calendar API.
        Returns:
            Dictionary representation suitable for API calls.
        """
        event_dict = {}
        
        if self.event_id:
            event_dict["id"] = self.event_id
        if self.summary:
            event_dict["summary"] = self.summary
        if self.description:
            event_dict["description"] = self.description
        if self.location:
            event_dict["location"] = self.location
        if self.html_link:
            event_dict["htmlLink"] = self.html_link
        if self.recurrence:
            event_dict["recurrence"] = self.recurrence
        if self.recurring_event_id:
            event_dict["recurringEventId"] = self.recurring_event_id
        if self.creator:
            event_dict["creator"] = self.creator
        if self.organizer:
            event_dict["organizer"] = self.organizer
        if self.status:
            event_dict["status"] = self.status
            
        if self.attendees:
            event_dict["attendees"] = [attendee.to_dict() for attendee in self.attendees]
            
        return event_dict

    def __repr__(self):
        return (
            f"Summary: {self.summary!r}\n"
            f"Description: {self.description!r}\n"
            f"Location: {self.location!r}\n"
            f"Time: {convert_datetime_to_readable(self.start, self.end)}\n"
            f"Link: {self.html_link!r}\n"
            f"Attendees: {', '.join(self.get_attendee_emails())}\n"
            f"Status: {self.status}\n"
        )