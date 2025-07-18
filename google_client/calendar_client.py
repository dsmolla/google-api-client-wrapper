from datetime import datetime, date, time, timedelta
from typing import Optional, List, Self
from google_client.auth import get_calendar_service
from utils.datetime_util import convert_datetime_to_iso, convert_datetime_to_readable, current_datetime_local_timezone
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

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
        if self.response_status and self.response_status not in ["needsAction", "declined", "tentative", "accepted"]:
            raise ValueError("Invalid response status for attendee.")

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
    attendees: Optional[List[Attendee]] = None
    recurrence: Optional[List[str]] = None
    recurringEventId: Optional[str] = None

    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []
        if self.recurrence is None:
            self.recurrence = []

    @staticmethod
    def _from_google_event(google_event: dict) -> "CalendarEvent":
        """
        Creates a CalendarEvent instance from a Google Calendar API response.
        Args:
            google_event: A dictionary containing event data from Google Calendar API.
        Returns:
            A CalendarEvent instance populated with the data from the dictionary.
        """
        attendees = [
            Attendee(
                email=attendee.get("email"),
                display_name=attendee.get("displayName"),
                response_status=attendee.get("responseStatus")
            ) for attendee in google_event.get("attendees", [])
        ]
        start = google_event.get("start", {})
        end = google_event.get("end", {})
        if start.get("dateTime"):
            start = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        elif start.get("date"):
            start = datetime.strptime(start["date"], "%Y-%m-%d")
        if end.get("dateTime"):
            end = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
        elif end.get("date"):
            end = datetime.strptime(end["date"], "%Y-%m-%d")
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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "summary": self.summary,
            "description": self.description,
            "location": self.location,
            "start": {"dateTime": convert_datetime_to_iso(self.start)},
            "end": {"dateTime": convert_datetime_to_iso(self.end)},
            "htmlLink": self.htmlLink,
            "attendees": [attendee.to_dict() for attendee in self.attendees],
            "recurrence": self.recurrence,
            "recurringEventId": self.recurringEventId,
        }

    @classmethod
    def list_events(
        cls,
        number_of_results: Optional[int] = 100,
        start: datetime = None,
        end: datetime = None,
        query: Optional[str] = None,
    ) -> List[Self]:
        """
        Fetches a list of events from the primary Google Calendar within the specified date range and filters by the given query if specified.
        Args:
            number_of_results: Max number of events to retrieve. Defaults to 100.
            start: Start date and time as a datetime object. Defaults to the start of the current day.
            end: End date and time as a datetime object. Defaults to 7 days from the start date.
            query: Query string to search events by keyword or related content.
        Returns:
            A list of CalendarEvent objects representing the events found within the specified range.
            If no events are found, an empty list is returned.
        """
        logger.info("Fetching events with number_of_results=%s, start=%s, end=%s, query=%s", number_of_results, start, end, query)
        service = get_calendar_service()
        if start is None:
            start = datetime.combine(date.today(), time.min)
        if end is None:
            end = datetime.combine(date.today(), time.min) + timedelta(days=7)
        start_iso, end_iso = convert_datetime_to_iso(start), convert_datetime_to_iso(end)
        try:
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_iso,
                    timeMax=end_iso,
                    maxResults=number_of_results,
                    singleEvents=True,
                    orderBy="startTime",
                    q=query,
                )
                .execute()
            )
            events = events_result.get("items", [])
            logger.info("Fetched %d events", len(events))
            return [cls._from_google_event(event) for event in events]
        except Exception as e:
            logger.error("An error occurred while fetching events: %s", e)
            return []

    @classmethod
    def get_event(cls, event_id: str) -> "CalendarEvent":
        """
        Retrieves a specific event from the user's Google Calendar using its unique identifier.
        Args:
            event_id: The unique identifier of the event to be retrieved.
        Returns:
            A CalendarEvent object representing the event with the specified ID.
        """
        logger.info("Retrieving event with ID: %s", event_id)
        service = get_calendar_service()
        try:
            google_event = service.events().get(calendarId="primary", eventId=event_id).execute()
            logger.info("Event retrieved successfully")
            return cls._from_google_event(google_event)
        except Exception as e:
            logger.error("Error retrieving event: %s", e)
            raise

    @classmethod
    def create_event(
        cls,
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
        service = get_calendar_service()
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
        except Exception as e:
            logger.error("Error creating event: %s", e)
            raise

    def sync_changes(self) -> bool:
        """
        Updates this event in the user's Google Calendar with new details.
        Returns:
            True if the event was updated successfully, False otherwise.
        """
        logger.info("Updating event with ID: %s", self.id)
        service = get_calendar_service()
        try:
            updated_event = service.events().update(calendarId="primary", eventId=self.id, body=self.to_dict()).execute()
            logger.info("Event updated successfully")
            return True
        except Exception as e:
            logger.error("Error updating event: %s", e)
            return False

    def delete_event(self, delete_all_recurrence: bool = False) -> bool:
        """
        Deletes this event from the user's Google Calendar. Can delete a single event or all in a recurrence series.
        Args:
            delete_all_recurrence: If True, deletes all events in the recurrence series.
        Returns:
            True if the event was deleted successfully, False otherwise.
        """
        logger.info("Deleting event with ID: %s, delete_all_recurrence=%s", self.id, delete_all_recurrence)
        service = get_calendar_service()
        try:
            if delete_all_recurrence:
                event = service.events().get(calendarId="primary", eventId=self.id).execute()
                recurring_event_id = event.get("recurringEventId")
                if recurring_event_id:
                    service.events().delete(calendarId="primary", eventId=recurring_event_id).execute()
                    logger.info("All recurring events deleted successfully")
                    return True
            service.events().delete(calendarId="primary", eventId=self.id).execute()
            logger.info("Event deleted successfully")
            return True
        except Exception as e:
            logger.error("Error deleting event: %s", e)
            return False

    def add_attendee(self, email: str) -> bool:
        """
        Adds an attendee to the event if they are not already in the list.
        Args:
            email: The email address of the attendee to be added.

        Returns:
            True if the attendee was added successfully
        """
        logger.info("Adding attendee with email: %s to event ID: %s", email, self.id)
        if not self.has_attendee(email):
            self.attendees.append(Attendee(email=email))
            return self.sync_changes()

        return True

    def remove_attendee(self, email: str) -> bool:
        """
        Removes an attendee from the event by their email address.
        Args:
            email:
                The email address of the attendee to be removed.
        Returns:
            The updated CalendarEvent instance after removing the attendee.
        """
        self.attendees = [attendee for attendee in self.attendees if attendee.email != email]
        return self.sync_changes()

    def update_summary(self, summary: str) -> bool:
        """
        Updates the summary of the event.
        Args:
            summary: The new summary for the event.
        Returns:
            The updated CalendarEvent instance.
        """
        logger.info("Updating summary for event ID: %s to %s", self.id, summary)
        self.summary = summary
        return self.sync_changes()

    def update_description(self, description: str) -> bool:
        """
        Updates the description of the event.
        Args:
            description: The new description for the event.
        Returns:
            The updated CalendarEvent instance.
        """
        logger.info("Updating description for event ID: %s", self.id)
        self.description = description
        return self.sync_changes()

    def update_location(self, location: str) -> bool:
        """
        Updates the location of the event.
        Args:
            location: The new location for the event.
        Returns:
            The updated CalendarEvent instance.
        """
        logger.info("Updating location for event ID: %s to %s", self.id, location)
        self.location = location
        return self.sync_changes()

    def update_start_time(self, start: datetime) -> bool:
        """
        Updates the start time of the event.
        Args:
            start: The new start time as a datetime object.
        Returns:
            The updated CalendarEvent instance.
        """
        logger.info("Updating start time for event ID: %s to %s", self.id, start)
        self.start = start
        return self.sync_changes()

    def update_end_time(self, end: datetime) -> bool:
        """
        Updates the end time of the event.
        Args:
            end: The new end time as a datetime object.
        Returns:
            The updated CalendarEvent instance.
        """
        logger.info("Updating end time for event ID: %s to %s", self.id, end)
        self.end = end
        return self.sync_changes()

    def update_recurrence(self, recurrence: List[str]) -> bool:
        """
        Updates the recurrence rules for the event.
        Args:
            recurrence: A list of strings defining the recurrence rules in RFC 5545 format.
        Returns:
            The updated CalendarEvent instance.
        """
        logger.info("Updating recurrence for event ID: %s", self.id)
        self.recurrence = recurrence
        return self.sync_changes()

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
