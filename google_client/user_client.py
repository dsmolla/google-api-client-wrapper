"""
User-centric Google API Client.

This module provides a clean, user-focused API where each user gets their own
client instance with easy access to all Google services.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from . services.gmail import GmailApiService
from . services.calendar import CalendarApiService
from . services.tasks import TasksApiService
from . services.drive import DriveApiService


# SCOPES = [
#     'https://www.googleapis.com/auth/calendar',
#     'https://mail.google.com/',
#     'https://www.googleapis.com/auth/tasks',
#     'https://www.googleapis.com/auth/drive'
# ]


class UserClient:
    """
    User-centric client that provides clean access to all Google APIs.
    
    Usage Examples:
        # Single user from file
        user = UserClient.from_file()
        events = user.calendar.list_events(number_of_results=10)
        emails = user.gmail.list_emails(max_results=20)
        tasks = user.tasks.list_tasks()
        files = user.drive.list(max_results=10)
        
        # Multi-user scenario
        user_1 = UserClient.from_credentials_info(app_creds, user1_token)
        user_2 = UserClient.from_credentials_info(app_creds, user2_token)
        
        user_1_events = user_1.calendar.list_events()
        user_2_events = user_2.calendar.list_events()
    """
    
    def __init__(self, credentials: Credentials):
        """
        Initialize user client with credentials.
        
        Args:
            credentials: Google OAuth2 credentials for this user
        """
        self._credentials = credentials

        self._gmail_service = None
        self._calendar_service = None
        self._tasks_service = None
        self._drive_service = None

        self._gmail = None
        self._calendar = None
        self._tasks = None
        self._drive = None


    @classmethod
    def from_credentials_info(
            cls,
            app_credentials: dict,
            user_token_data: dict = None,
            scopes: list = None,
            port: int = 8080
    ) -> tuple["UserClient", dict]:
        """
        Create a UserClient from credential data.

        Args:
            app_credentials: OAuth client configuration dict
            user_token_data: Previously stored user token data dict
            scopes: List of OAuth scopes to request

        Returns:
            tuple: (UserClient instance, updated_token_data_to_store)
        """
        scopes = scopes
        creds = None

        # Try to load existing credentials from memory
        if user_token_data:
            creds = Credentials.from_authorized_user_info(user_token_data, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(app_credentials, scopes)
                creds = flow.run_local_server(port=port)

        # Return credentials and token data to store
        token_data_to_store = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }

        return cls(creds), token_data_to_store

    @classmethod
    def from_file(
            cls,
            token_path: str = None,
            credentials_path: str = None,
            scopes: list = None,
            port: int = 8080
    ) -> "UserClient":
        """
        Create a UserClient from credential data.

        Args:
            token_path: Path to previously stored user's token file (contents of token.json)
            credentials_path: Path to OAuth client's credential file (contents of credentials.json)
            scopes: List of OAuth scopes to request

        Returns:
            A UserClient instance

        """

        credentials_path = credentials_path
        scopes = scopes

        creds = None

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, scopes
                )
                creds = flow.run_local_server(port=port)

            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return cls(creds)

    def _get_gmail_service(self):
        """Get or create Gmail API service for this user."""
        if self._gmail_service is None:
            self._gmail_service = build("gmail", "v1", credentials=self._credentials)
        return self._gmail_service
    
    def _get_calendar_service(self):
        """Get or create Calendar API service for this user."""
        if self._calendar_service is None:
            self._calendar_service = build("calendar", "v3", credentials=self._credentials)
        return self._calendar_service
    
    def _get_tasks_service(self):
        """Get or create Tasks API service for this user."""
        if self._tasks_service is None:
            self._tasks_service = build("tasks", "v1", credentials=self._credentials)
        return self._tasks_service
    
    def _get_drive_service(self):
        """Get or create Drive API service for this user."""
        if self._drive_service is None:
            self._drive_service = build("drive", "v3", credentials=self._credentials)
        return self._drive_service

    @property
    def gmail(self):
        """Gmail service layer for this user."""
        if self._gmail is None:
            self._gmail = GmailApiService(self._get_gmail_service())
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

