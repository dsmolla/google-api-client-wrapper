import re
from datetime import datetime, date, time
from typing import Optional, Dict, Any
import logging

from .types import Task, TaskList
from .constants import (
    MAX_TITLE_LENGTH, MAX_NOTES_LENGTH, VALID_TASK_STATUSES,
    RFC3339_FORMAT
)
from ...utils.datetime import convert_datetime_to_local_timezone

logger = logging.getLogger(__name__)


def validate_text_field(value: Optional[str], max_length: int, field_name: str) -> None:
    """Validates text field length and content."""
    if value and len(value) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")


def validate_task_status(status: Optional[str]) -> None:
    """Validates task status."""
    if status and status not in VALID_TASK_STATUSES:
        raise ValueError(f"Invalid task status: {status}. Must be one of: {', '.join(VALID_TASK_STATUSES)}")


def sanitize_header_value(value: str) -> str:
    """
    Sanitize a string value for safe use in API requests.
    
    Args:
        value: The string to sanitize
    
    Returns:
        Sanitized string safe for use in API calls
    """
    if not value:
        return ""
    
    # Remove control characters that could cause issues
    sanitized = re.sub(r'[\r\n\x00-\x1f\x7f-\x9f]', '', value)
    
    # Remove any quotes that could break the structure
    sanitized = sanitized.replace('"', '')
    
    return sanitized.strip()


def parse_datetime_field(field_value: Optional[str]) -> Optional[date]:
    """
    Parse datetime field from Google Tasks API response to date.
    
    Args:
        field_value: ISO datetime string from API
        
    Returns:
        Parsed date object or None if parsing fails
    """
    if not field_value:
        return None
        
    try:
        # Handle different formats from Tasks API
        if field_value.endswith('Z'):
            dt = datetime.fromisoformat(field_value.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(field_value)
            
        # Convert to local timezone and return date
        dt = convert_datetime_to_local_timezone(dt)
        return dt.date()
    except (ValueError, TypeError) as e:
        logger.warning("Failed to parse datetime: %s", e)
        return None


def parse_update_datetime_field(field_value: Optional[str]) -> Optional[datetime]:
    """
    Parse update datetime field from Google Tasks API response.
    
    Args:
        field_value: ISO datetime string from API
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not field_value:
        return None
        
    try:
        # Handle different formats from Tasks API
        if field_value.endswith('Z'):
            dt = datetime.fromisoformat(field_value.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(field_value)
            
        # Convert to local timezone
        return convert_datetime_to_local_timezone(dt)
    except (ValueError, TypeError) as e:
        logger.warning("Failed to parse datetime: %s", e)
        return None


def from_google_task(google_task: Dict[str, Any], task_list_id: Optional[str] = None) -> Task:
    """
    Create a Task instance from a Google Tasks API response.
    
    Args:
        google_task: Dictionary containing task data from Google Tasks API
        task_list_id: The ID of the task list this task belongs to
        
    Returns:
        Task instance populated with the data from the dictionary
    """
    try:
        task_id = google_task.get('id')
        title = google_task.get('title', '').strip() if google_task.get('title') else None
        notes = google_task.get('notes', '').strip() if google_task.get('notes') else None
        status = google_task.get('status', 'needsAction')
        
        # Validate status
        if status not in VALID_TASK_STATUSES:
            logger.warning("Invalid task status: %s, defaulting to needsAction", status)
            status = 'needsAction'
        
        # Parse dates
        due = parse_datetime_field(google_task.get('due'))
        completed = parse_datetime_field(google_task.get('completed'))
        updated = parse_datetime_field(google_task.get('updated'))
        
        # Parse hierarchy
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
        
    except Exception as e:
        logger.error("Failed to parse Google Task: %s", e)
        logger.debug("Task data: %s", str(google_task)[:500])
        raise ValueError(f"Invalid task data: {e}")


def from_google_task_list(google_task_list: Dict[str, Any]) -> TaskList:
    """
    Create a TaskList instance from a Google Tasks API response.
    
    Args:
        google_task_list: Dictionary containing task list data from Google Tasks API
        
    Returns:
        TaskList instance populated with the data from the dictionary
    """
    try:
        task_list_id = google_task_list.get('id')
        title = google_task_list.get('title', '').strip() if google_task_list.get('title') else None
        updated = parse_update_datetime_field(google_task_list.get('updated'))
        
        return TaskList(
            task_list_id=task_list_id,
            title=title,
            updated=updated
        )
        
    except Exception as e:
        logger.error("Failed to parse Google TaskList: %s", e)
        logger.debug("TaskList data: %s", str(google_task_list)[:500])
        raise ValueError(f"Invalid task list data: {e}")


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
    
    # Add optional fields
    if notes:
        task_body['notes'] = sanitize_header_value(notes)
    if due:
        # Convert date to datetime for API compatibility
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