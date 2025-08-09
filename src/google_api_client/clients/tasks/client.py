from datetime import date, datetime, time
from typing import Optional, List, Self, TYPE_CHECKING
from ...utils.datetime import convert_datetime_to_readable, convert_datetime_to_local_timezone, convert_datetime_to_iso
from dataclasses import dataclass, field
import logging
from googleapiclient.errors import HttpError

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)

# Constants
MAX_RESULTS_LIMIT = 100
MAX_TITLE_LENGTH = 1024
MAX_NOTES_LENGTH = 8192
DEFAULT_MAX_RESULTS = 100

# Import exceptions from centralized location
from ...exceptions.tasks import TasksError, TasksPermissionError, TasksNotFoundError


@dataclass
class TaskList:
    """
    Represents a Google Task List.
    Args:
        id: Unique identifier for the task list.
        title: The title of the task list.
        updated: Last modification time.
    """
    id: Optional[str] = None
    title: Optional[str] = None
    updated: Optional[datetime] = None
    _user_client: Optional["UserClient"] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.title and len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")

    def set_user_client(self, user_client):
        """Set user context for this task list."""
        from ...user_client import UserClient
        self._user_client = user_client

    def _get_user_client(self):
        """Get the user client for this task list."""
        if self._user_client is None:
            raise ValueError("Task list must have user context. Use user.tasks methods to get task lists.")
        return self._user_client

    @staticmethod
    def _from_google_tasklist(google_tasklist: dict) -> "TaskList":
        """
        Creates a TaskList instance from a Google Tasks API response.
        Args:
            google_tasklist: A dictionary containing task list data from Google Tasks API.
        Returns:
            A TaskList instance populated with the data from the dictionary.
        """
        updated = None
        if google_tasklist.get('updated'):
            try:
                updated = datetime.fromisoformat(google_tasklist['updated'].replace('Z', '+00:00'))
                updated = convert_datetime_to_local_timezone(updated)
            except:
                logger.warning("Failed to parse updated time: %s", google_tasklist.get('updated'))

        return TaskList(
            id=google_tasklist.get('id'),
            title=google_tasklist.get('title'),
            updated=updated
        )

    def to_dict(self) -> dict:
        """Convert TaskList to dictionary format for Google Tasks API."""
        task_list_dict = {}
        if self.id:
            task_list_dict['id'] = self.id
        if self.title:
            task_list_dict['title'] = self.title
        return task_list_dict


    def update_task_list(self, title: str) -> "TaskList":
        """
        Updates the title of this task list.
        Args:
            title: The new title for the task list.
        Returns:
            The updated TaskList object.
        """
        if not self.id:
            raise ValueError("TaskList must have an ID to be updated")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")
        
        logger.info("Updating task list %s to new title: %s", self.id, title)
        user_client = self._get_user_client()
        updated_list = user_client.tasks._update_task_list(self.id, title)
        self.title = updated_list.title
        return self

    def delete_task_list(self) -> bool:
        """
        Deletes this task list.
        Returns:
            True if the task list was successfully deleted, False otherwise.
        """
        logger.info("Deleting task list with ID: %s", self.id)
        user_client = self._get_user_client()
        return user_client.tasks._delete_task_list(self.id)

    @staticmethod
    def _list_task_lists_with_service(service: "Resource") -> List["TaskList"]:
        """Implementation of list_task_lists using direct service."""
        # This will contain the original implementation
        # For now, return empty list - to be implemented
        return []

    @staticmethod
    def _get_task_list_with_service(service: "Resource", task_list_id: str) -> "TaskList":
        """Implementation of get_task_list using direct service."""
        # This will contain the original implementation
        # For now, return a basic task list - to be implemented
        return TaskList(id=task_list_id, title="Temp List")

    @staticmethod
    def _create_task_list_with_service(service: "Resource", title: str) -> "TaskList":
        """Implementation of create_task_list using direct service."""
        # This will contain the original implementation
        # For now, return a basic task list - to be implemented
        return TaskList(id="temp", title=title)

    def __repr__(self):
        return f"TaskList(id={self.id!r}, title={self.title!r})"


@dataclass
class Task:
    """
    Represents a Google Task.
    Args:
        id: Unique identifier for the task.
        title: The title of the task.
        notes: Notes describing the task.
        status: Status of the task ('needsAction' or 'completed').
        due: Due date of the task.
        completed: Completion date of the task.
        updated: Last modification time.
        parent: Parent task identifier.
        position: Position in the task list.
        task_list_id: ID of the task list this task belongs to.
    """
    id: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    due: Optional[date] = None
    completed: Optional[date] = None
    updated: Optional[date] = None
    parent: Optional[str] = None
    position: Optional[str] = None
    task_list_id: Optional[str] = None
    _user_client: Optional["UserClient"] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.title and len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Task title cannot exceed {MAX_TITLE_LENGTH} characters")
        if self.notes and len(self.notes) > MAX_NOTES_LENGTH:
            raise ValueError(f"Task notes cannot exceed {MAX_NOTES_LENGTH} characters")
        if self.status and self.status not in ['needsAction', 'completed']:
            raise ValueError(f"Invalid task status: {self.status}. Must be 'needsAction' or 'completed'")

    def set_user_client(self, user_client):
        """Set user context for this task."""
        from ...user_client import UserClient
        self._user_client = user_client

    def _get_user_client(self):
        """Get the user client for this task."""
        if self._user_client is None:
            raise ValueError("Task must have user context. Use user.tasks methods to get tasks.")
        return self._user_client

    @staticmethod
    def _from_google_task(google_task: dict, task_list_id: Optional[str] = None) -> "Task":
        """
        Creates a Task instance from a Google Tasks API response.
        Args:
            google_task: A dictionary containing task data from Google Tasks API.
            task_list_id: The ID of the task list this task belongs to.
        Returns:
            A Task instance populated with the data from the dictionary.
        """
        def parse_datetime_field(field_value):
            if not field_value:
                return None
            try:
                dt = datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                dt = date(dt.year, dt.month, dt.day)
                return dt
            except:
                logger.warning("Failed to parse datetime: %s", field_value)
                return None

        return Task(
            id=google_task.get('id'),
            title=google_task.get('title'),
            notes=google_task.get('notes'),
            status=google_task.get('status'),
            due=parse_datetime_field(google_task.get('due')),
            completed=parse_datetime_field(google_task.get('completed')),
            updated=parse_datetime_field(google_task.get('updated')),
            parent=google_task.get('parent'),
            position=google_task.get('position'),
            task_list_id=task_list_id
        )

    def to_dict(self) -> dict:
        """Convert Task to dictionary format for Google Tasks API."""
        task_dict = {}
        if self.id:
            task_dict['id'] = self.id
        if self.title:
            task_dict['title'] = self.title
        if self.notes:
            task_dict['notes'] = self.notes
        if self.status:
            task_dict['status'] = self.status
        if self.due:
            task_dict['due'] = datetime.combine(self.due, time.min).isoformat() + 'Z'
        if self.completed:
            task_dict['completed'] = datetime.combine(self.completed, time.min).isoformat() + 'Z'
        if self.parent:
            task_dict['parent'] = self.parent
        if self.position:
            task_dict['position'] = self.position
        return task_dict


    def update_task(
            self,
            title: str=None,
            notes: str=None,
            status: str=None,
            completed: date=None,
            due: date=None
    ) -> "Task":
        """
        Updates this task in Google Tasks.
        Args:
            title: The title of the task (optional).
            notes: Notes for the task (optional).
            status: The status of the task (optional).
            completed: The completed date of the task (optional).
            due: Due date for the task (optional).

        Returns:
            The updated Task object.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be updated")
        
        logger.info("Updating task with ID: %s", self.id)
        user_client = self._get_user_client()
        return user_client.tasks._update_task(self.task_list_id, self.id, title, notes, status, completed, due)

    def delete_task(self) -> bool:
        """
        Deletes this task.
        Returns:
            True if the task was successfully deleted, False otherwise.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be deleted")
        
        logger.info("Deleting task with ID: %s", self.id)
        user_client = self._get_user_client()
        return user_client.tasks._delete_task(self.task_list_id, self.id)

    def move_task(self, parent: Optional[str] = None, previous: Optional[str] = None) -> "Task":
        """
        Moves this task to a different position in the task list.
        Args:
            parent: Parent task ID (optional).
            previous: Previous sibling task ID (optional).
        Returns:
            The updated Task object.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be moved")
        
        logger.info("Moving task with ID: %s", self.id)
        user_client = self._get_user_client()
        return user_client.tasks._move_task(self.task_list_id, self.id, parent, previous)

    def mark_completed(self) -> "Task":
        """
        Marks this task as completed.
        Returns:
            The updated Task object.
        """
        return self.update_task(status='completed', completed=date.today())

    def mark_incomplete(self) -> "Task":
        """
        Marks this task as needing action (incomplete).
        Returns:
            The updated Task object.
        """
        return self.update_task(status='needsAction')

    def is_completed(self) -> bool:
        """
        Checks if the task is completed.
        Returns:
            True if the task is completed, False otherwise.
        """
        return self.status == 'completed'

    def is_overdue(self) -> bool:
        """
        Checks if the task is overdue.
        Returns:
            True if the task has a due date that has passed and is not completed.
        """
        if not self.due or self.is_completed():
            return False
        return self.due < date.today()

    @staticmethod
    def _list_tasks_with_service(service: "Resource", task_list_id: str='@default', max_results: Optional[int] = 100) -> List["Task"]:
        """Implementation of list_tasks using direct service."""
        # This will contain the original implementation
        # For now, return empty list - to be implemented
        return []

    @staticmethod
    def _get_task_with_service(service: "Resource", task_list_id: str, task_id: str) -> "Task":
        """Implementation of get_task using direct service."""
        # This will contain the original implementation
        # For now, return a basic task - to be implemented
        return Task(id=task_id, title="Temp Task", task_list_id=task_list_id)

    @staticmethod
    def _create_task_with_service(service: "Resource", title: str, task_list_id: str = '@default', **kwargs) -> "Task":
        """Implementation of create_task using direct service."""
        # This will contain the original implementation
        # For now, return a basic task - to be implemented
        return Task(id="temp", title=title, task_list_id=task_list_id)

    def __repr__(self):
        return (
            f"Task(id={self.id!r}, title={self.title!r}, "
            f"status={self.status!r}, due={self.due.strftime("%a %m-%d-%Y") if self.due else None})"
        )


class TasksService:
    """
    Service layer for Tasks API operations.
    Contains all Tasks API functionality that was removed from dataclasses.
    """
    
    def __init__(self, service: "Resource", user_client: "UserClient"):
        """
        Initialize Tasks service.
        
        Args:
            service: The Tasks API service instance
            user_client: The user client for context
        """
        self._service = service
        self._user_client = user_client

    def list_tasks(self, task_list_id: str = '@default', max_results: Optional[int] = 100) -> List[Task]:
        """List tasks for the user."""
        tasks = Task._list_tasks_with_service(self._service, task_list_id, max_results)
        # Set user context for each task
        for task in tasks:
            task.set_user_client(self._user_client)
        return tasks

    def get_task(self, task_list_id: str, task_id: str) -> Task:
        """Get specific task by ID."""
        task = Task._get_task_with_service(self._service, task_list_id, task_id)
        task.set_user_client(self._user_client)
        return task

    def create_task(self, title: str, task_list_id: str = '@default', **kwargs) -> Task:
        """Create task for the user."""
        task = Task._create_task_with_service(self._service, title, task_list_id, **kwargs)
        task.set_user_client(self._user_client)
        return task

    def list_task_lists(self) -> List[TaskList]:
        """List task lists for the user."""
        task_lists = TaskList._list_task_lists_with_service(self._service)
        # Set user context for each task list
        for task_list in task_lists:
            task_list.set_user_client(self._user_client)
        return task_lists

    def get_task_list(self, task_list_id: str) -> TaskList:
        """Get specific task list by ID."""
        task_list = TaskList._get_task_list_with_service(self._service, task_list_id)
        task_list.set_user_client(self._user_client)
        return task_list

    def create_task_list(self, title: str) -> TaskList:
        """Create task list for the user."""
        task_list = TaskList._create_task_list_with_service(self._service, title)
        task_list.set_user_client(self._user_client)
        return task_list

    def _update_task(self, task_list_id: str, task_id: str, title: str = None, notes: str = None, 
                    status: str = None, completed: date = None, due: date = None) -> Task:
        """Update task."""
        # This will contain the original update_task implementation
        # For now, return a basic task - to be implemented
        task = Task(id=task_id, title=title or "Updated Task", task_list_id=task_list_id)
        task.set_user_client(self._user_client)
        return task

    def _delete_task(self, task_list_id: str, task_id: str) -> bool:
        """Delete task."""
        # This will contain the original delete_task implementation
        # For now, return True - to be implemented
        return True

    def _move_task(self, task_list_id: str, task_id: str, parent: Optional[str] = None, previous: Optional[str] = None) -> Task:
        """Move task."""
        # This will contain the original move_task implementation
        # For now, return a basic task - to be implemented
        task = Task(id=task_id, title="Moved Task", task_list_id=task_list_id)
        task.set_user_client(self._user_client)
        return task

    def _update_task_list(self, task_list_id: str, title: str) -> TaskList:
        """Update task list."""
        # This will contain the original update_task_list implementation
        # For now, return a basic task list - to be implemented
        task_list = TaskList(id=task_list_id, title=title)
        task_list.set_user_client(self._user_client)
        return task_list

    def _delete_task_list(self, task_list_id: str) -> bool:
        """Delete task list."""
        # This will contain the original delete_task_list implementation
        # For now, return True - to be implemented
        return True

    def query(self):
        """Create task query builder for this user."""
        from .query_builder import TaskQueryBuilder
        return TaskQueryBuilder(Task, self._service, self._user_client)