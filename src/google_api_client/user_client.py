"""
User-centric Google API Client.

This module provides a clean, user-focused API where each user gets their own
client instance with easy access to all Google services.
"""

from typing import Optional, Dict, Any
from .auth.auth import get_credentials_from_file, get_credentials_from_info
from .auth.auth import get_gmail_service, get_calendar_service, get_tasks_service
from google.oauth2.credentials import Credentials


class UserClient:
    """
    User-centric client that provides clean access to all Google APIs.
    
    Usage Examples:
        # Single user from file
        user = UserClient.from_file()
        events = user.calendar.list_events(number_of_results=10)
        emails = user.gmail.list_emails(max_results=20)
        tasks = user.tasks.list_tasks()
        
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
        
        # Create service proxies
        self.gmail = GmailServiceProxy(self)
        self.calendar = CalendarServiceProxy(self)
        self.tasks = TasksServiceProxy(self)
    
    @classmethod
    def from_file(cls, credentials_path: str = None, token_path: str = None, scopes: list = None) -> "UserClient":
        """
        Create a UserClient from credential files (single user scenario).
        
        Args:
            credentials_path: Path to credentials.json file
            token_path: Path to token.json file  
            scopes: List of OAuth scopes to request
            
        Returns:
            UserClient instance
        """
        credentials = get_credentials_from_file(credentials_path, token_path, scopes)
        return cls(credentials)
    
    @classmethod
    def from_credentials_info(cls, app_credentials: dict, user_token_data: dict = None, scopes: list = None) -> "UserClient":
        """
        Create a UserClient from credential data (multi-user scenario).
        
        Args:
            app_credentials: OAuth client configuration dict
            user_token_data: Previously stored user token data dict
            scopes: List of OAuth scopes to request
            
        Returns:
            UserClient instance
        """
        credentials, _ = get_credentials_from_info(app_credentials, user_token_data, scopes)
        return cls(credentials)
    
    def get_gmail_service(self):
        """Get or create Gmail service for this user."""
        if self._gmail_service is None:
            self._gmail_service = get_gmail_service(self._credentials)
        return self._gmail_service
    
    def get_calendar_service(self):
        """Get or create Calendar service for this user."""
        if self._calendar_service is None:
            self._calendar_service = get_calendar_service(self._credentials)
        return self._calendar_service
    
    def get_tasks_service(self):
        """Get or create Tasks service for this user."""
        if self._tasks_service is None:
            self._tasks_service = get_tasks_service(self._credentials)
        return self._tasks_service


class GmailServiceProxy:
    """Proxy that provides clean access to Gmail operations."""
    
    def __init__(self, user_client: UserClient):
        self._user_client = user_client
    
    def list_emails(self, max_results: Optional[int] = 30, **kwargs):
        """List emails for this user."""
        from .clients.gmail.client import EmailMessage
        service = self._user_client.get_gmail_service()
        return EmailMessage.list_emails(service, max_results=max_results, **kwargs)
    
    def get_email(self, message_id: str):
        """Get specific email for this user."""
        from .clients.gmail.client import EmailMessage
        service = self._user_client.get_gmail_service()
        return EmailMessage.get_email(message_id, service)
    
    def send_email(self, to: list, subject: str = None, **kwargs):
        """Send email as this user."""
        from .clients.gmail.client import EmailMessage
        service = self._user_client.get_gmail_service()
        return EmailMessage.send_email(service, to, subject=subject, **kwargs)
    
    def query(self):
        """Create email query builder for this user."""
        from .clients.gmail.client import EmailMessage
        service = self._user_client.get_gmail_service()
        return EmailMessage.query(service)


class CalendarServiceProxy:
    """Proxy that provides clean access to Calendar operations."""
    
    def __init__(self, user_client: UserClient):
        self._user_client = user_client
    
    def list_events(self, number_of_results: Optional[int] = 100, **kwargs):
        """List calendar events for this user."""
        from .clients.calendar.client import CalendarEvent
        service = self._user_client.get_calendar_service()
        return CalendarEvent.list_events(service, number_of_results=number_of_results, **kwargs)
    
    def get_event(self, event_id: str):
        """Get specific calendar event for this user."""
        from .clients.calendar.client import CalendarEvent
        service = self._user_client.get_calendar_service()
        return CalendarEvent.get_event(service, event_id)
    
    def create_event(self, start, end, summary: str = None, **kwargs):
        """Create calendar event for this user."""
        from .clients.calendar.client import CalendarEvent
        service = self._user_client.get_calendar_service()
        return CalendarEvent.create_event(service, start, end, summary=summary, **kwargs)
    
    def query(self):
        """Create event query builder for this user."""
        from .clients.calendar.client import CalendarEvent
        service = self._user_client.get_calendar_service()
        return CalendarEvent.query(service)


class TasksServiceProxy:
    """Proxy that provides clean access to Tasks operations."""
    
    def __init__(self, user_client: UserClient):
        self._user_client = user_client
    
    def list_tasks(self, task_list_id: str = '@default', max_results: Optional[int] = 100):
        """List tasks for this user."""
        from .clients.tasks.client import Task
        service = self._user_client.get_tasks_service()
        return Task.list_tasks(service, task_list_id, max_results)
    
    def get_task(self, task_list_id: str, task_id: str):
        """Get specific task for this user."""
        from .clients.tasks.client import Task
        service = self._user_client.get_tasks_service()
        return Task.get_task(service, task_list_id, task_id)
    
    def create_task(self, title: str, task_list_id: str = '@default', **kwargs):
        """Create task for this user."""
        from .clients.tasks.client import Task
        service = self._user_client.get_tasks_service()
        return Task.create_task(service, title, task_list_id, **kwargs)
    
    def list_task_lists(self):
        """List task lists for this user."""
        from .clients.tasks.client import TaskList
        service = self._user_client.get_tasks_service()
        return TaskList.list_task_lists(service)
    
    def create_task_list(self, title: str):
        """Create task list for this user."""
        from .clients.tasks.client import TaskList
        service = self._user_client.get_tasks_service()
        return TaskList.create_task_list(service, title)
    
    def query(self):
        """Create task query builder for this user."""
        from .clients.tasks.client import Task
        service = self._user_client.get_tasks_service()
        return Task.query(service)