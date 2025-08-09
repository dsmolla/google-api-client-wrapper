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

    def __post_init__(self):
        if self.title and len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")

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

    @classmethod
    def list_task_lists(cls, service: "Resource") -> List["TaskList"]:
        """
        Fetches a list of task lists from Google Tasks.
        Args:
            service: The tasks service instance.
        Returns:
            A list of TaskList objects representing the task lists found.
        """
        logger.info("Fetching task lists from Google Tasks")
        
        try:
            result = service.tasklists().list().execute()
            task_lists = result.get('items', [])
            logger.info("Found %d task lists", len(task_lists))
            
            task_list_objects = []
            for task_list in task_lists:
                try:
                    task_list_objects.append(cls._from_google_tasklist(task_list))
                except Exception as e:
                    logger.warning("Skipping invalid task list: %s", e)
            
            return task_list_objects
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    @classmethod
    def get_task_list(cls, service: "Resource", task_list_id: str) -> "TaskList":
        """
        Retrieves a specific task list by its ID.
        Args:
            service: The tasks service instance.
            task_list_id: The unique identifier of the task list to retrieve.
        Returns:
            A TaskList object representing the task list.
        """
        logger.info("Retrieving task list with ID: %s", task_list_id)
        
        try:
            google_tasklist = service.tasklists().get(tasklist=task_list_id).execute()
            logger.info("Task list retrieved successfully")
            return cls._from_google_tasklist(google_tasklist)
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    @classmethod
    def create_task_list(cls, service: "Resource", title: str) -> "TaskList":
        """
        Creates a new task list in Google Tasks.
        Args:
            service: The tasks service instance.
            title: The title of the task list to create.
        Returns:
            A TaskList object representing the created task list.
        """
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")
        
        logger.info("Creating task list with title: %s", title)
        
        try:
            body = {'title': title}
            google_tasklist = service.tasklists().insert(body=body).execute()
            logger.info("Task list created successfully with ID: %s", google_tasklist.get('id'))
            return cls._from_google_tasklist(google_tasklist)
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    def update_task_list(self, service: "Resource", title: str) -> "TaskList":
        """
        Updates the title of this task list.
        Args:
            service: The tasks service instance.
            title: The new title for the task list.
        Returns:
            The updated TaskList object.
        """
        if not self.id:
            raise ValueError("TaskList must have an ID to be updated")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")
        
        logger.info("Updating task list %s to new title: %s", self.id, title)
        
        try:
            body = {
                'id': self.id,  # Include the ID in the body as well
                'title': title
            }
            google_tasklist = service.tasklists().update(
                tasklist=self.id,
                body=body
            ).execute()
            self.title = google_tasklist.get('title')
            logger.info("Task list updated successfully")
            return self
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    def delete_task_list(self, service: "Resource") -> bool:
        """
        Deletes this task list.
        Args:
            service: The tasks service instance.
        Returns:
            True if the task list was successfully deleted, False otherwise.
        """
        logger.info("Deleting task list with ID: %s", self.id)
        
        try:
            service.tasklists().delete(tasklist=self.id).execute()
            logger.info("Task list deleted successfully")
            return True
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

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

    def __post_init__(self):
        if self.title and len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Task title cannot exceed {MAX_TITLE_LENGTH} characters")
        if self.notes and len(self.notes) > MAX_NOTES_LENGTH:
            raise ValueError(f"Task notes cannot exceed {MAX_NOTES_LENGTH} characters")
        if self.status and self.status not in ['needsAction', 'completed']:
            raise ValueError(f"Invalid task status: {self.status}. Must be 'needsAction' or 'completed'")

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

    @classmethod
    def query(cls, service: "Resource") -> "TaskQueryBuilder":
        """
        Create a new TaskQueryBuilder for building complex task queries with a fluent API.
        
        Args:
            service: The tasks service instance.
        
        Returns:
            TaskQueryBuilder instance for method chaining
            
        Example:
            tasks = (Task.query(service)
                .limit(50)
                .due_before(end_date)
                .completed_after(start_date)
                .show_completed(True)
                .execute())
        """
        from .query_builder import TaskQueryBuilder
        return TaskQueryBuilder(cls, service)

    @classmethod
    def _list_tasks_with_filters(cls, service: "Resource", **kwargs) -> List["Task"]:
        """
        Internal method to fetch tasks with advanced filtering support for query builder.
        Args:
            service: The tasks service instance.
            **kwargs: Request parameters including tasklist, maxResults, completedMin, etc.
        Returns:
            A list of Task objects representing the tasks found.
        """
        task_list_id = kwargs.get('tasklist', '@default')
        max_results = kwargs.get('maxResults', DEFAULT_MAX_RESULTS)
        
        if max_results is not None and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"maxResults must be between 1 and {MAX_RESULTS_LIMIT}")

        logger.info("Fetching tasks from task list with filters: %s", task_list_id)
        
        try:
            # Filter out None values and prepare request params
            request_params = {k: v for k, v in kwargs.items() if v is not None}
            
            result = service.tasks().list(**request_params).execute()
            tasks = result.get('items', [])
            logger.info("Found %d tasks", len(tasks))
            
            task_objects = []
            for task in tasks:
                try:
                    task_objects.append(cls._from_google_task(task, task_list_id))
                except Exception as e:
                    logger.warning("Skipping invalid task: %s", e)
            
            return task_objects
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    @classmethod
    def list_tasks(cls, service: "Resource", task_list_id: str='@default', max_results: Optional[int] = DEFAULT_MAX_RESULTS) -> List["Task"]:
        """
        Fetches a list of tasks from a specific task list.
        Args:
            service: The tasks service instance.
            task_list_id: The ID of the task list to fetch tasks from.
            max_results: Maximum number of tasks to retrieve.
        Returns:
            A list of Task objects representing the tasks found.
        """
        if max_results is not None and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

        logger.info("Fetching tasks from task list: %s", task_list_id)
        
        try:
            request_params = {
                'tasklist': task_list_id,
                'maxResults': max_results
            }
            
            result = service.tasks().list(**request_params).execute()
            tasks = result.get('items', [])
            logger.info("Found %d tasks", len(tasks))
            
            task_objects = []
            for task in tasks:
                try:
                    task_objects.append(cls._from_google_task(task, task_list_id))
                except Exception as e:
                    logger.warning("Skipping invalid task: %s", e)
            
            return task_objects
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    @classmethod
    def get_task(cls, service: "Resource", task_list_id: str, task_id: str) -> "Task":
        """
        Retrieves a specific task by its ID.
        Args:
            service: The tasks service instance.
            task_list_id: The ID of the task list containing the task.
            task_id: The unique identifier of the task to retrieve.
        Returns:
            A Task object representing the task.
        """
        logger.info("Retrieving task with ID: %s from list: %s", task_id, task_list_id)
        
        try:
            google_task = service.tasks().get(tasklist=task_list_id, task=task_id).execute()
            logger.info("Task retrieved successfully")
            return cls._from_google_task(google_task, task_list_id)
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    @classmethod
    def create_task(
        cls,
        service: "Resource",
        title: str,
        task_list_id: str = '@default',
        notes: Optional[str] = None,
        due: Optional[date] = None,
        parent: Optional[str] = None
    ) -> "Task":
        """
        Creates a new task in the specified task list.
        Args:
            service: The tasks service instance.
            task_list_id: The ID of the task list to create the task in.
            title: The title of the task.
            notes: Notes for the task (optional).
            due: Due date for the task (optional). Time not supported by Google API.
            parent: Parent task ID (optional).
        Returns:
            A Task object representing the created task.
        """
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Task title cannot exceed {MAX_TITLE_LENGTH} characters")
        if notes and len(notes) > MAX_NOTES_LENGTH:
            raise ValueError(f"Task notes cannot exceed {MAX_NOTES_LENGTH} characters")
        
        logger.info("Creating task with title: %s in list: %s", title, task_list_id)
        
        try:
            body = {'title': title}
            if notes:
                body['notes'] = notes
            if due:
                body['due'] = datetime.combine(due, time.min).isoformat() + 'Z'
            if parent:
                body['parent'] = parent
            
            google_task = service.tasks().insert(tasklist=task_list_id, body=body).execute()
            logger.info("Task created successfully with ID: %s", google_task.get('id'))
            return cls._from_google_task(google_task, task_list_id)
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    def update_task(
            self,
            service: "Resource",
            title: str=None,
            notes: str=None,
            status: str=None,
            completed: date=None,
            due: date=None
    ) -> "Task":
        """
        Updates this task in Google Tasks.
        Args:
            service: The tasks service instance.
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
        
        try:
            body = self.to_dict()
            if title:
                body['title'] = title
            if notes:
                body['notes'] = notes
            if status:
                body['status'] = status
            if completed:
                body['completed'] = datetime.combine(completed, time.min).isoformat() + 'Z'
            if due:
                body['due'] = datetime.combine(due, time.min).isoformat() + 'Z'

            google_task = service.tasks().update(
                tasklist=self.task_list_id,
                task=self.id,
                body=body
            ).execute()

            logger.info("Task updated successfully")
            # Update the current object with the response
            updated_task = self._from_google_task(google_task, self.task_list_id)
            self.__dict__.update(updated_task.__dict__)
            return self
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    def delete_task(self, service: "Resource") -> bool:
        """
        Deletes this task.
        Args:
            service: The tasks service instance.
        Returns:
            True if the task was successfully deleted, False otherwise.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be deleted")
        
        logger.info("Deleting task with ID: %s", self.id)
        
        try:
            service.tasks().delete(tasklist=self.task_list_id, task=self.id).execute()
            logger.info("Task deleted successfully")
            return True
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    def move_task(self, service: "Resource", parent: Optional[str] = None, previous: Optional[str] = None) -> "Task":
        """
        Moves this task to a different position in the task list.
        Args:
            service: The tasks service instance.
            parent: Parent task ID (optional).
            previous: Previous sibling task ID (optional).
        Returns:
            The updated Task object.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be moved")
        
        logger.info("Moving task with ID: %s", self.id)
        
        try:
            request_params = {
                'tasklist': self.task_list_id,
                'task': self.id
            }
            if parent:
                request_params['parent'] = parent
            if previous:
                request_params['previous'] = previous
            
            google_task = service.tasks().move(**request_params).execute()
            logger.info("Task moved successfully")
            # Update the current object with the response
            updated_task = self._from_google_task(google_task, self.task_list_id)
            self.__dict__.update(updated_task.__dict__)
            return self
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task or task list not found: {e}")
            else:
                raise TasksError(f"Tasks API error: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected tasks service error: {e}")

    def mark_completed(self, service: "Resource") -> "Task":
        """
        Marks this task as completed.
        Args:
            service: The tasks service instance.
        Returns:
            The updated Task object.
        """
        return self.update_task(service, status='completed', completed=date.today())

    def mark_incomplete(self, service: "Resource") -> "Task":
        """
        Marks this task as needing action (incomplete).
        Args:
            service: The tasks service instance.
        Returns:
            The updated Task object.
        """
        return self.update_task(service, status='needsAction')

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

    def __repr__(self):
        return (
            f"Task(id={self.id!r}, title={self.title!r}, "
            f"status={self.status!r}, due={self.due.strftime("%a %m-%d-%Y") if self.due else None})"
        )