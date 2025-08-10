from ...exceptions.base import APIError


class TasksError(APIError):
    """Base exception for Tasks API errors."""
    pass


class TasksNotFoundError(TasksError):
    """Raised when a task or task list is not found."""
    pass


class TasksPermissionError(TasksError):
    """Raised when the user lacks permission for a tasks operation."""
    pass


class TaskConflictError(TasksError):
    """Raised when there is a conflict with task operations."""
    pass


class InvalidTaskDataError(TasksError):
    """Raised when task data is invalid or malformed."""
    pass


class TaskListConflictError(TasksError):
    """Raised when there is a conflict with task list operations."""
    pass


class TaskMoveError(TasksError):
    """Raised when there are issues with moving tasks."""
    pass