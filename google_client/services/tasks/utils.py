from datetime import datetime, date, time
from typing import Optional, Dict, Any

from google_client.utils.datetime import iso_to_datetime
from google_client.utils.validation import validate_text_field, sanitize_header_value
from .constants import MAX_TITLE_LENGTH, MAX_NOTES_LENGTH, VALID_TASK_STATUSES
from .types import Task, TaskList


def validate_task_status(status: Optional[str]) -> None:
    """Validates task status."""
    if status and status not in VALID_TASK_STATUSES:
        raise ValueError(f"Invalid task status: {status}. Must be one of: {', '.join(VALID_TASK_STATUSES)}")


def from_google_task(google_task: Dict[str, Any], task_list_id: str, timezone: str) -> Task:
    """
    Create a Task instance from a Google Tasks API response.
    
    Args:
        google_task: Dictionary containing task data from Google Tasks API
        task_list_id: The ID of the task list this task belongs to
        timezone: Timezone
        
    Returns:
        Task instance populated with the data from the dictionary
    """
    try:
        task_id = google_task.get('id')
        title = google_task.get('title', '').strip() if google_task.get('title') else None
        notes = google_task.get('notes', '').strip() if google_task.get('notes') else None
        status = google_task.get('status', 'needsAction')

        if status not in VALID_TASK_STATUSES:
            status = 'needsAction'

        if due := google_task.get('due'):
            due = datetime.fromisoformat(due).date()
        if completed := google_task.get('completed'):
            completed = datetime.fromisoformat(completed).date()
        if updated := google_task.get('updated'):
            updated = iso_to_datetime(updated, timezone)

        parent = google_task.get('parent')
        position = google_task.get('position')

        return Task(
            task_id=task_id,
            title=title,
            notes=notes,
            status=status,
            due=due,
            completed=completed,
            updated=updated,
            parent=parent,
            position=position,
            task_list_id=task_list_id
        )

    except Exception:
        raise ValueError("Invalid task data - failed to parse Google task")


def from_google_task_list(google_task_list: Dict[str, Any], timezone: str) -> TaskList:
    """
    Create a TaskList instance from a Google Tasks API response.
    
    Args:
        google_task_list: Dictionary containing task list data from Google Tasks API
        timezone: Timezone
        
    Returns:
        TaskList instance populated with the data from the dictionary
    """
    try:
        task_list_id = google_task_list.get('id')
        title = google_task_list.get('title', '').strip() if google_task_list.get('title') else None
        if updated := google_task_list.get('updated'):
            updated = iso_to_datetime(updated, timezone)

        return TaskList(
            task_list_id=task_list_id,
            title=title,
            updated=updated
        )

    except Exception:
        raise ValueError("Invalid task list data - failed to parse Google task list")


def create_task_body(
        title: str,
        notes: Optional[str] = None,
        due: Optional[date] = None,
        parent: Optional[str] = None,
        position: Optional[str] = None,
        status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create task body dictionary for Google Tasks API.
    
    Args:
        title: Task title
        notes: Task notes
        due: Due date
        parent: Parent task ID
        position: Position in task list
        status: Task status
        
    Returns:
        Dictionary suitable for Tasks API requests

    Raises:
        ValueError: If required fields are invalid
    """
    if not title or not title.strip():
        raise ValueError("Task title cannot be empty")

    # Validate text fields
    validate_text_field(title, MAX_TITLE_LENGTH, "title")
    validate_text_field(notes, MAX_NOTES_LENGTH, "notes")
    validate_task_status(status)

    # Build task body
    task_body = {
        'title': sanitize_header_value(title)
    }

    if notes:
        task_body['notes'] = sanitize_header_value(notes)
    if due:
        due_datetime = datetime.combine(due, time.min)
        task_body['due'] = due_datetime.isoformat() + 'Z'
    if parent:
        task_body['parent'] = parent
    if position:
        task_body['position'] = position
    if status:
        task_body['status'] = status

    return task_body


def create_task_list_body(title: str) -> Dict[str, Any]:
    """
    Create task list body dictionary for Google Tasks API.
    
    Args:
        title: Task list title
        
    Returns:
        Dictionary suitable for Tasks API requests
        
    Raises:
        ValueError: If required fields are invalid
    """
    if not title or not title.strip():
        raise ValueError("Task list title cannot be empty")

    # Validate title length
    validate_text_field(title, MAX_TITLE_LENGTH, "title")

    return {
        'title': sanitize_header_value(title)
    }
