import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# from .services.gmail import GmailApiService
from .services.calendar import CalendarApiService
from .services.tasks import TasksApiService
from .services.drive import DriveApiService

from .services.gmail.async_api_service import GmailApiService

class APIServiceLayer:
    """
    Base class for Google API service layers.
    """

    def __init__(self, user_info: dict):
        self._credentials = Credentials.from_authorized_user_info(user_info)

        self._gmail = None
        self._calendar = None
        self._tasks = None
        self._drive = None

    def refresh_token(self) -> dict:
        self._credentials.refresh(Request())
        self._gmail, self._calendar, self._tasks, self._drive = None, None, None, None
        return json.loads(self._credentials.to_json())

    def _get_gmail_service(self):
        return build("gmail", "v1", credentials=self._credentials)

    def _get_calendar_service(self):
        return build("calendar", "v3", credentials=self._credentials)

    def _get_tasks_service(self):
        return build("tasks", "v1", credentials=self._credentials)

    def _get_drive_service(self):
        return build("drive", "v3", credentials=self._credentials)

    @property
    def gmail(self):
        """Gmail service layer for this user."""
        if self._gmail is None:
            self._gmail = GmailApiService(self._credentials)
        return self._gmail

    @property
    def calendar(self):
        """Calendar service layer for this user."""
        if self._calendar is None:
            self._calendar = CalendarApiService(self._get_calendar_service())
        return self._calendar

    @property
    def tasks(self):
        """Tasks service layer for this user."""
        if self._tasks is None:
            self._tasks = TasksApiService(self._get_tasks_service())
        return self._tasks

    @property
    def drive(self):
        """Drive service layer for this user."""
        if self._drive is None:
            self._drive = DriveApiService(self._get_drive_service())
        return self._drive
