import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict, Union

from google.auth.credentials import Credentials
from googleapiclient.discovery import build

from . import utils
from .constants import DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT, DEFAULT_CALENDAR_ID, DEFAULT_FREEBUSY_DURATION_MINUTES
from .types import CalendarEvent, Attendee, FreeBusyResponse, TimeSlot, Calendar
from ...utils.datetime import datetime_to_iso, current_datetime


class AsyncCalendarApiService:
    def __init__(self, credentials: Credentials, timezone: str):
        self._executor = ThreadPoolExecutor()
        self._credentials = credentials
        self._timezone = timezone

    def _service(self):
        return build("calendar", "v3", credentials=self._credentials)

    def query(self):
        from .async_query_builder import AsyncEventQueryBuilder
        return AsyncEventQueryBuilder(self, self._timezone)
    
    async def list_calendars(self, max_results: int = 250) -> List[Calendar]:
        loop = asyncio.get_event_loop()
        payload = await loop.run_in_executor(
            self._executor,
            lambda: self._service().calendarList().list(maxResults=max_results).execute()
        )
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

    async def delete_calendar(self, calendar: Calendar | str) -> None:
        if isinstance(calendar, Calendar):
            calendar = calendar.id

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: self._service().calendarList().delete(calendarId=calendar).execute()
        )

    async def get_calendar(self, calendar_id: str) -> Calendar:
        loop = asyncio.get_event_loop()
        calendar = await loop.run_in_executor(
            self._executor,
            lambda: self._service().calendarList().get(calendarId=calendar_id).execute()
        )
        return Calendar(
            id=calendar.get('id'),
            summary=calendar.get('summary'),
            description=calendar.get('description'),
            backgroundColor=calendar.get('backgroundColor'),
            foregroundColor=calendar.get('foregroundColor'),
            deleted=calendar.get('deleted', False),
        )

    async def create_calendar(
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

        loop = asyncio.get_event_loop()
        payload = await loop.run_in_executor(
            self._executor,
            lambda: self._service().calendars().insert(body=body).execute()
        )
        return Calendar(
            id=payload.get('id'),
            summary=payload.get('summary'),
            description=payload.get('description'),
            backgroundColor=payload.get('backgroundColor'),
            foregroundColor=payload.get('foregroundColor'),
            deleted=payload.get('deleted', False),
        )

    async def update_calendar(self, calendar: Calendar):
        loop = asyncio.get_event_loop()
        payload = await loop.run_in_executor(
            self._executor,
            lambda: self._service().calendars().update(calendarId=calendar.id, body=calendar.to_dict()).execute()
        )
        return Calendar(
            id=payload.get('id'),
            summary=payload.get('summary'),
            description=payload.get('description'),
            backgroundColor=payload.get('backgroundColor'),
            foregroundColor=payload.get('foregroundColor'),
            deleted=payload.get('deleted', False),
        )

    async def list_events(
            self,
            max_results: Optional[int] = DEFAULT_MAX_RESULTS,
            start: Optional[datetime] = None,
            end: Optional[datetime] = None,
            query: Optional[str] = None,
            calendar_id: str = DEFAULT_CALENDAR_ID,
            single_events: bool = True,
            order_by: str = 'startTime'
    ) -> List[CalendarEvent]:

        if max_results < 1 or max_results > MAX_RESULTS_LIMIT:
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

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

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().events().list(**request_params).execute()
        )

        events = [utils.from_google_event(event, self._timezone) for event in result.get('items', [])]
        return events

    async def get_event(self, event_id: str, calendar_id: str = DEFAULT_CALENDAR_ID) -> CalendarEvent:
        loop = asyncio.get_event_loop()
        event_data = await loop.run_in_executor(
            self._executor,
            lambda: self._service().events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
        )

        return utils.from_google_event(event_data, self._timezone)

    async def create_event(
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

        loop = asyncio.get_event_loop()
        created_event = await loop.run_in_executor(
            self._executor,
            lambda: self._service().events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
        )

        calendar_event = utils.from_google_event(created_event, self._timezone)
        return calendar_event

    async def update_event(
            self,
            event: CalendarEvent,
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> CalendarEvent:

        if event.start >= event.end:
            raise ValueError("end datetime should be after start datetime.")

        event_body = event.to_dict()
        fields_to_remove = ['id', 'htmlLink', 'recurringEventId']
        for field in fields_to_remove:
            event_body.pop(field, None)

        event_body['start'] = {'dateTime': datetime_to_iso(event.start, self._timezone), 'timeZone': self._timezone}
        event_body['end'] = {'dateTime': datetime_to_iso(event.end, self._timezone), 'timeZone': self._timezone}

        loop = asyncio.get_event_loop()
        updated_event = await loop.run_in_executor(
            self._executor,
            lambda: self._service().events().update(
                calendarId=calendar_id,
                eventId=event.event_id,
                body=event_body
            ).execute()
        )

        updated_calendar_event = utils.from_google_event(updated_event, self._timezone)
        return updated_calendar_event

    async def delete_event(
            self,
            event: Union[CalendarEvent, str],
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> None:

        if isinstance(event, CalendarEvent):
            event = event.event_id

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: self._service().events().delete(
                calendarId=calendar_id,
                eventId=event
            ).execute()
        )

    async def batch_get_events(
            self,
            event_ids: List[str],
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> List[CalendarEvent]:
        tasks = []
        for event_id in event_ids:
            task = asyncio.create_task(self.get_event(event_id, calendar_id))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def batch_create_events(
            self,
            events_data: List[Dict[str, Any]],
            calendar_id: str = DEFAULT_CALENDAR_ID
    ) -> List[CalendarEvent]:
        tasks = []
        for event_data in events_data:
            task = asyncio.create_task(self.create_event(calendar_id=calendar_id, **event_data))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def get_freebusy(
            self,
            start: datetime,
            end: datetime,
            calendar_ids: Optional[List[str]] = None,
    ) -> FreeBusyResponse:
        if calendar_ids is None:
            calendar_ids = [DEFAULT_CALENDAR_ID]

        request_body = {
            "timeMin": datetime_to_iso(start, self._timezone),
            "timeMax": datetime_to_iso(end, self._timezone),
            "items": [{"id": cal_id} for cal_id in calendar_ids]
        }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().freebusy().query(body=request_body).execute()
        )

        return utils.parse_freebusy_response(result, self._timezone)

    async def find_free_slots(
            self,
            start: datetime,
            end: datetime,
            duration_minutes: int = DEFAULT_FREEBUSY_DURATION_MINUTES,
            calendar_ids: Optional[List[str]] = None
    ) -> Dict['str', List[TimeSlot]]:

        if calendar_ids is None:
            calendar_ids = [DEFAULT_CALENDAR_ID]

        freebusy_response = await self.get_freebusy(start, end, calendar_ids)

        free_slots = {}
        for calendar_id in calendar_ids:
            free_slots[calendar_id] = freebusy_response.get_free_slots(duration_minutes, calendar_id)

        return free_slots
