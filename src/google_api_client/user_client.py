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
        self._gmail_api_service = None
        self._calendar_api_service = None
        self._tasks_api_service = None
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
        """Get or create Gmail API service for this user."""
        if self._gmail_api_service is None:
            self._gmail_api_service = get_gmail_service(self._credentials)
        return self._gmail_api_service
    
    def get_calendar_service(self):
        """Get or create Calendar API service for this user."""
        if self._calendar_api_service is None:
            self._calendar_api_service = get_calendar_service(self._credentials)
        return self._calendar_api_service
    
    def get_tasks_service(self):
        """Get or create Tasks API service for this user."""
        if self._tasks_api_service is None:
            self._tasks_api_service = get_tasks_service(self._credentials)
        return self._tasks_api_service

    def get_gmail_service_layer(self):
        """Get or create Gmail service layer for this user."""
        if self._gmail_service is None:
            from .clients.gmail.client import GmailService
            self._gmail_service = GmailService(self.get_gmail_service(), self)
        return self._gmail_service
    
    def get_calendar_service_layer(self):
        """Get or create Calendar service layer for this user."""
        if self._calendar_service is None:
            from .clients.calendar.client import CalendarService
            self._calendar_service = CalendarService(self.get_calendar_service(), self)
        return self._calendar_service
    
    def get_tasks_service_layer(self):
        """Get or create Tasks service layer for this user."""
        if self._tasks_service is None:
            from .clients.tasks.client import TasksService
            self._tasks_service = TasksService(self.get_tasks_service(), self)
        return self._tasks_service


class GmailServiceProxy:
    """Proxy that provides clean access to Gmail operations."""
    
    def __init__(self, user_client: UserClient):
        self._user_client = user_client
    
    def list_emails(self, max_results: Optional[int] = 30, **kwargs):
        """List emails for this user."""
        gmail_service = self._user_client.get_gmail_service_layer()
        return gmail_service.list_emails(max_results=max_results, **kwargs)
    
    def get_email(self, message_id: str):
        """Get specific email for this user."""
        gmail_service = self._user_client.get_gmail_service_layer()
        return gmail_service.get_email(message_id)
    
    def send_email(self, to: list, subject: str = None, **kwargs):
        """Send email as this user."""
        gmail_service = self._user_client.get_gmail_service_layer()
        return gmail_service.send_email(to, subject=subject, **kwargs)
    
    def list_labels(self):
        """List Gmail labels for this user."""
        gmail_service = self._user_client.get_gmail_service_layer()
        return gmail_service.list_labels()
    
    def create_label(self, name: str):
        """Create Gmail label for this user."""
        gmail_service = self._user_client.get_gmail_service_layer()
        return gmail_service.create_label(name)
    
    def get_label(self, label_id: str):
        """Get specific Gmail label for this user."""
        gmail_service = self._user_client.get_gmail_service_layer()
        return gmail_service.get_label(label_id)
    
    def _delete_label(self, label_id: str) -> bool:
        """Delete Gmail label for this user."""
        gmail_service = self._user_client.get_gmail_service_layer()
        return gmail_service._delete_label(label_id)
    
    def _update_label(self, label_id: str, new_name: str):
        """Update Gmail label for this user."""
        gmail_service = self._user_client.get_gmail_service_layer()
        return gmail_service._update_label(label_id, new_name)
    
    def query(self):
        """Create email query builder for this user."""
        gmail_service = self._user_client.get_gmail_service_layer()
        return gmail_service.query()


class CalendarServiceProxy:
    """Proxy that provides clean access to Calendar operations."""
    
    def __init__(self, user_client: UserClient):
        self._user_client = user_client
    
    def list_events(self, number_of_results: Optional[int] = 100, **kwargs):
        """List calendar events for this user."""
        calendar_service = self._user_client.get_calendar_service_layer()
        return calendar_service.list_events(number_of_results=number_of_results, **kwargs)
    
    def get_event(self, event_id: str):
        """Get specific calendar event for this user."""
        calendar_service = self._user_client.get_calendar_service_layer()
        return calendar_service.get_event(event_id)
    
    def create_event(self, start, end, summary: str = None, **kwargs):
        """Create calendar event for this user."""
        calendar_service = self._user_client.get_calendar_service_layer()
        return calendar_service.create_event(start, end, summary=summary, **kwargs)
    
    def _update_event(self, event_id: str, event):
        """Update calendar event for this user."""
        calendar_service = self._user_client.get_calendar_service_layer()
        return calendar_service._update_event(event_id, event)
    
    def _delete_event(self, event_id: str, delete_all_recurrence: bool = False):
        """Delete calendar event for this user."""
        calendar_service = self._user_client.get_calendar_service_layer()
        return calendar_service._delete_event(event_id, delete_all_recurrence)
    
    def query(self):
        """Create event query builder for this user."""
        calendar_service = self._user_client.get_calendar_service_layer()
        return calendar_service.query()


class TasksServiceProxy:
    """Proxy that provides clean access to Tasks operations."""
    
    def __init__(self, user_client: UserClient):
        self._user_client = user_client
    
    def list_tasks(self, task_list_id: str = '@default', max_results: Optional[int] = 100):
        """List tasks for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service.list_tasks(task_list_id, max_results)
    
    def get_task(self, task_list_id: str, task_id: str):
        """Get specific task for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service.get_task(task_list_id, task_id)
    
    def create_task(self, title: str, task_list_id: str = '@default', **kwargs):
        """Create task for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service.create_task(title, task_list_id, **kwargs)
    
    def list_task_lists(self):
        """List task lists for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service.list_task_lists()
    
    def get_task_list(self, task_list_id: str):
        """Get specific task list for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service.get_task_list(task_list_id)
    
    def create_task_list(self, title: str):
        """Create task list for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service.create_task_list(title)
    
    def _update_task(self, task_list_id: str, task_id: str, title: str = None, notes: str = None, 
                    status: str = None, completed = None, due = None):
        """Update task for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service._update_task(task_list_id, task_id, title, notes, status, completed, due)
    
    def _delete_task(self, task_list_id: str, task_id: str) -> bool:
        """Delete task for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service._delete_task(task_list_id, task_id)
    
    def _move_task(self, task_list_id: str, task_id: str, parent = None, previous = None):
        """Move task for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service._move_task(task_list_id, task_id, parent, previous)
    
    def _update_task_list(self, task_list_id: str, title: str):
        """Update task list for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service._update_task_list(task_list_id, title)
    
    def _delete_task_list(self, task_list_id: str) -> bool:
        """Delete task list for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service._delete_task_list(task_list_id)
    
    def query(self):
        """Create task query builder for this user."""
        tasks_service = self._user_client.get_tasks_service_layer()
        return tasks_service.query()