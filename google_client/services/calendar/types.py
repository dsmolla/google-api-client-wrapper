from datetime import datetime, date, time
from typing import Optional, Dict, List, Any, Literal
from pydantic import BaseModel, Field

from google_client.utils.datetime import convert_datetime_to_readable, current_datetime_local_timezone, \
    convert_datetime_to_local_timezone
from google_client.utils.validation import is_valid_email


class Attendee(BaseModel):
    """
    Represents an attendee of a calendar event with their email, display name, and response status.
    """
    email: str = Field(..., description="The email address of the attendee")
    display_name: Optional[str] = Field(None, description="The display name of the attendee")
    response_status: Optional[Literal["needsAction", "declined", "tentative", "accepted"]] = (
        Field(None, description="The response status of the attendee"))

    def model_post_init(self, __context__: Any):
        if not is_valid_email(self.email):
            raise ValueError("Invalid email format - email address validation failed")

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


class CalendarEvent(BaseModel):
    """
    Represents a calendar event with various attributes.
    """
    event_id: Optional[str] = Field(None, description="Unique identifier for the event")
    summary: Optional[str] = Field(None, description="A brief title or summary of the event")
    description: Optional[str] = Field(None, description="A detailed description of the event")
    location: Optional[str] = Field(None, description="The physical or virtual location of the event")
    start: Optional[datetime] = Field(None, description="The start time of the event as a datetime object")
    end: Optional[datetime] = Field(None, description="The end time of the event as a datetime object")
    html_link: Optional[str] = Field(None, description="A hyperlink to the event on Google Calendar")
    attendees: List[Attendee] = Field(default_factory=list,
                                      description="A list of Attendee objects representing the people invited to the event")
    recurrence: List[str] = Field(default_factory=list,
                                  description="A list of strings defining the recurrence rules for the event in RFC 5545 format")
    recurring_event_id: Optional[str] = Field(None,
                                              description="The ID of the recurring event if this event is part of a series")
    creator: Optional[str] = Field(None, description="The creator of the event")
    organizer: Optional[str] = Field(None, description="The organizer of the event")
    status: Optional[str] = Field("confirmed", description="The status of the event (confirmed, tentative, cancelled)")

    def duration(self) -> Optional[int]:
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
        if self.start:
            event_dict["time"] = convert_datetime_to_readable(self.start, self.end)
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


class TimeSlot(BaseModel):
    """
    Represents a time slot with start and end times.
    Used for representing both busy periods and available time slots.
    """
    start: datetime = Field(..., description="Start datetime of the time slot")
    end: datetime = Field(..., description="End datetime of the time slot")

    def model_post_init(self, __context__: Any):
        if self.start >= self.end:
            raise ValueError("Start time must be before end time")

    def duration(self) -> int:
        """
        Calculate the duration of the time slot in minutes.

        Returns:
            Duration in minutes
        """
        return int((self.end - self.start).total_seconds() / 60)

    def overlaps_with(self, other: "TimeSlot") -> bool:
        """
        Check if this time slot overlaps with another time slot.

        Args:
            other: Another TimeSlot to check for overlap

        Returns:
            True if the time slots overlap, False otherwise
        """
        return self.start < other.end and self.end > other.start

    def contains_time(self, time_point: datetime) -> bool:
        """
        Check if a specific datetime falls within this time slot.

        Args:
            time_point: Datetime to check

        Returns:
            True if the time point is within this slot, False otherwise
        """
        return self.start <= time_point < self.end

    def __str__(self):
        return convert_datetime_to_readable(
            convert_datetime_to_local_timezone(self.start),
            convert_datetime_to_local_timezone(self.end)
        )


class FreeBusyResponse(BaseModel):
    """
    Represents a response from a free/busy query.
    """
    start: datetime = Field(..., description="Start time of the query")
    end: datetime = Field(..., description="End time of the query")
    calendars: Dict[str, List[TimeSlot]] = Field(default_factory=dict,
                                                 description="Dictionary mapping calendar IDs to their busy periods")
    errors: Dict[str, str] = Field(default_factory=dict,
                                   description="Dictionary mapping calendar IDs to any errors encountered")

    def get_busy_periods(self, calendar_id: str = "primary") -> List[TimeSlot]:
        """
        Get busy periods for a specific calendar.

        Args:
            calendar_id: Calendar ID to get busy periods for

        Returns:
            List of TimeSlot objects representing busy periods
        """
        return self.calendars.get(calendar_id, [])

    def is_time_free(self, time_point: datetime, calendar_id: str = "primary") -> bool:
        """
        Check if a specific time is free in the given calendar.

        Args:
            time_point: Datetime to check
            calendar_id: Calendar ID to check

        Returns:
            True if the time is free, False if busy
        """
        if not (self.start <= time_point <= self.end):
            raise ValueError("Time point is outside the queried range")

        busy_periods = self.get_busy_periods(calendar_id)
        return not any(period.contains_time(time_point) for period in busy_periods)

    def is_slot_free(self, slot: TimeSlot, calendar_id: str = "primary") -> bool:
        """
        Check if an entire time slot is free in the given calendar.

        Args:
            slot: TimeSlot to check
            calendar_id: Calendar ID to check

        Returns:
            True if the entire slot is free, False if any part is busy
        """
        busy_periods = self.get_busy_periods(calendar_id)
        return not any(period.overlaps_with(slot) for period in busy_periods)

    def get_free_slots(self, duration_minutes: int = 60, calendar_id: str = "primary") -> List[TimeSlot]:
        """
        Get all free time slots of a specified duration within the queried range.

        Args:
            duration_minutes: Minimum duration for free slots in minutes
            calendar_id: Calendar ID to get free slots for

        Returns:
            List of TimeSlot objects representing available time slots
        """
        from ...utils.datetime import current_datetime_local_timezone

        busy_periods = sorted(self.get_busy_periods(calendar_id), key=lambda x: x.start)
        free_slots = []

        # Start from the beginning of the range or current time (whichever is later)
        current_time = max(self.start, current_datetime_local_timezone())

        # Check time before first busy period
        if busy_periods and current_time < busy_periods[0].start:
            gap_duration = (busy_periods[0].start - current_time).total_seconds() / 60
            if gap_duration >= duration_minutes:
                free_slots.append(TimeSlot(start=current_time, end=busy_periods[0].start))

        # Check gaps between busy periods
        for i in range(len(busy_periods) - 1):
            gap_start = busy_periods[i].end
            gap_end = busy_periods[i + 1].start
            gap_duration = (gap_end - gap_start).total_seconds() / 60

            if gap_duration >= duration_minutes:
                free_slots.append(TimeSlot(start=gap_start, end=gap_end))

        # Check time after last busy period
        if busy_periods:
            gap_start = busy_periods[-1].end
            if gap_start < self.end:
                gap_duration = (self.end - gap_start).total_seconds() / 60
                if gap_duration >= duration_minutes:
                    free_slots.append(TimeSlot(start=gap_start, end=self.end))
        elif current_time < self.end:
            # No busy periods at all
            gap_duration = (self.end - current_time).total_seconds() / 60
            if gap_duration >= duration_minutes:
                free_slots.append(TimeSlot(start=current_time, end=self.end))

        return free_slots

    def has_errors(self) -> bool:
        """
        Check if there were any errors in the freebusy query.

        Returns:
            True if there were errors, False otherwise
        """
        return bool(self.errors)

