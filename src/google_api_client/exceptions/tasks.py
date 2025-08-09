from .base import APIError


class TasksError(APIError):
    """Base exception for Tasks API errors."""
    pass


class TasksNotFoundError(TasksError):
    """Raised when a task or task list is not found."""
    pass


class TasksPermissionError(TasksError):
    """Raised when the user lacks permission for a tasks operation."""
    pass