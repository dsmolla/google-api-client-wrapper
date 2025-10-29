from datetime import date, datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field


class TaskList(BaseModel):
    """
    Represents a Google Task List.
    """
    task_list_id: Optional[str] = Field(None, description="Unique identifier for the task list")
    title: Optional[str] = Field(None, description="The title of the task list")
    updated: Optional[datetime] = Field(None, description="Last modification time")

    def to_dict(self) -> dict:
        """
        Convert TaskList to dictionary format for Google Tasks API.
        Returns:
            Dictionary representation suitable for API calls.
        """
        task_list_dict = {}
        if self.task_list_id:
            task_list_dict['id'] = self.task_list_id
        if self.title:
            task_list_dict['title'] = self.title
        if self.updated:
            task_list_dict['updated'] = self.updated.isoformat() + 'Z'
        return task_list_dict

    def __repr__(self):
        return f"TaskList(id={self.task_list_id!r}, title={self.title!r})"


class Task(BaseModel):
    """
    Represents a Google Task.
    """
    task_id: Optional[str] = Field(None, description="Unique identifier for the task")
    title: Optional[str] = Field(None, description="The title of the task")
    notes: Optional[str] = Field(None, description="Notes describing the task")
    status: Optional[str] = Field("needsAction", description="Status of the task ('needsAction' or 'completed')")
    due: Optional[date] = Field(None, description="Due date of the task")
    completed: Optional[date] = Field(None, description="Completion date of the task")
    updated: Optional[datetime] = Field(None, description="Last modification time")
    parent: Optional[str] = Field(None, description="Parent task identifier")
    position: Optional[str] = Field(None, description="Position in the task list")
    task_list_id: Optional[str] = Field(None, description="ID of the task list this task belongs to")

    def is_completed(self) -> bool:
        """
        Check if the task is completed.
        Returns:
            True if the task is completed, False otherwise.
        """
        return self.status == 'completed'

    def is_overdue(self) -> bool:
        """
        Check if the task is overdue.
        Returns:
            True if the task has a due date that has passed and is not completed.
        """
        if not self.due or self.is_completed():
            return False
        return self.due < date.today()

    def is_due_today(self) -> bool:
        """
        Check if the task is due today.
        Returns:
            True if the task is due today, False otherwise.
        """
        if not self.due:
            return False
        return self.due == date.today()

    def is_due_soon(self, days: int = 3) -> bool:
        """
        Check if the task is due within the next N days.
        Args:
            days: Number of days to check ahead (default: 3)
        Returns:
            True if the task is due within the specified days.
        """
        if not self.due or self.is_completed():
            return False
        today = date.today()
        return today <= self.due <= (today + timedelta(days=days))

    def has_parent(self) -> bool:
        """
        Check if the task has a parent task.
        Returns:
            True if the task has a parent, False otherwise.
        """
        return bool(self.parent)

    def has_notes(self) -> bool:
        """
        Check if the task has notes.
        Returns:
            True if the task has notes, False otherwise.
        """
        return bool(self.notes and self.notes.strip())

    def to_dict(self) -> dict:
        """
        Convert Task to dictionary format for Google Tasks API.
        Returns:
            Dictionary representation suitable for API calls.
        """
        task_dict = {}
        if self.task_id:
            task_dict['id'] = self.task_id
        if self.title:
            task_dict['title'] = self.title
        if self.notes:
            task_dict['notes'] = self.notes
        if self.status:
            task_dict['status'] = self.status
        if self.due:
            # Convert date to datetime for API compatibility
            due_datetime = datetime.combine(self.due, datetime.min.time())
            task_dict['due'] = due_datetime.isoformat() + 'Z'
        if self.completed:
            # Convert date to datetime for API compatibility
            completed_datetime = datetime.combine(self.completed, datetime.min.time())
            task_dict['completed'] = completed_datetime.isoformat() + 'Z'
        if self.parent:
            task_dict['parent'] = self.parent
        if self.position:
            task_dict['position'] = self.position
        return task_dict

    def __repr__(self):
        due_str = self.due.strftime("%a %m-%d-%Y") if self.due else None
        return (
            f"Task(id={self.task_id!r}, title={self.title!r}, "
            f"status={self.status!r}, due={due_str})"
        )