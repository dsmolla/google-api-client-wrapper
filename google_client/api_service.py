import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .services.gmail import GmailApiService
from .services.calendar import CalendarApiService
from .services.tasks import TasksApiService
from .services.drive import DriveApiService

from .services.gmail import AsyncGmailApiService
from .services.calendar import AsyncCalendarApiService
from .services.drive import AsyncDriveApiService
from .services.tasks import AsyncTasksApiService

import pytz


class APIServiceLayer:
    """
    Base class for Google API service layers.
    """

    def __init__(self, user_info: dict, timezone: str = 'UTC'):
        self._credentials = Credentials.from_authorized_user_info(user_info)

        self._gmail = None
        self._calendar = None
        self._tasks = None
        self._drive = None

        self._async_gmail = None
        self._async_calendar = None
        self._async_tasks = None
        self._async_drive = None

        self.timezone = timezone

    def _get_gmail_service(self):
        return build("gmail", "v1", credentials=self._credentials)

    def _get_calendar_service(self):
        return build("calendar", "v3", credentials=self._credentials)

    def _get_tasks_service(self):
        return build("tasks", "v1", credentials=self._credentials)

    def _get_drive_service(self):
        return build("drive", "v3", credentials=self._credentials)

    def refresh_token(self) -> dict:
        self._credentials.refresh(Request())

        self._gmail, self._calendar, self._tasks, self._drive = None, None, None, None
        self._async_gmail, self._async_calendar, self._async_tasks, self._async_drive = None, None, None, None

        return json.loads(self._credentials.to_json())

    @property
    def gmail(self):
        if self._gmail is None:
            self._gmail = GmailApiService(self._credentials, timezone=self.timezone)
        return self._gmail
    @property
    def calendar(self):
        if self._calendar is None:
            self._calendar = CalendarApiService(self._credentials, timezone=self.timezone)
        return self._calendar
    @property
    def tasks(self):
        if self._tasks is None:
            self._tasks = TasksApiService(self._credentials, timezone=self.timezone)
        return self._tasks
    @property
    def drive(self):
        if self._drive is None:
            self._drive = DriveApiService(self._credentials, timezone=self.timezone)
        return self._drive


    @property
    def async_gmail(self):
        if self._async_gmail is None:
            self._async_gmail = AsyncGmailApiService(self._credentials, timezone=self.timezone)
        return self._async_gmail

    @property
    def async_calendar(self):
        if self._async_calendar is None:
            self._async_calendar = AsyncCalendarApiService(self._credentials, timezone=self.timezone)
        return self._async_calendar

    @property
    def async_tasks(self):
        if self._async_tasks is None:
            self._async_tasks = AsyncTasksApiService(self._credentials, timezone=self.timezone)
        return self._async_tasks

    @property
    def async_drive(self):
        if self._async_drive is None:
            self._async_drive = AsyncDriveApiService(self._credentials, timezone=self.timezone)
        return self._async_drive

