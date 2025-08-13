# Tasks Service Package

A comprehensive, user-centric Google Tasks client library that provides clean, intuitive access to task management operations through the Google API. This package enables you to create, organize, search, and manage tasks programmatically with full OAuth2 authentication support.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Core Components](#core-components)
- [Task Operations](#task-operations)
- [Query Builder](#query-builder)
- [Task List Management](#task-list-management)
- [Batch Operations](#batch-operations)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [API Reference](#api-reference)

## Overview

The Tasks service package follows a user-centric design pattern where each user gets their own client instance with OAuth credentials. This enables multi-user scenarios and maintains proper authentication isolation.

### Key Features

- **Complete Task Management**: Create, read, update, delete, and move tasks
- **Powerful Query Builder**: Fluent API for complex task searches and filtering
- **Task List Operations**: Create and manage multiple task lists
- **Date-Smart Filtering**: Intelligent date handling with timezone support
- **Batch Operations**: Efficient bulk task operations
- **Hierarchical Tasks**: Support for subtasks and task organization
- **Security First**: Built-in validation and secure handling of credentials

## Quick Start

```python
from google_client.user_client import UserClient

# Initialize user client with OAuth credentials
user = UserClient.from_file(
    token_file="user_token.json",
    credentials_file="credentials.json",
    scopes=["https://www.googleapis.com/auth/tasks"]
)

# Access Tasks service
tasks = user.tasks

# Create a simple task
task = tasks.create_task(
    title="Complete project proposal",
    notes="Include budget and timeline",
    due=date(2024, 12, 31)
)

# Search for tasks
urgent_tasks = (tasks.query()
    .due_today()
    .show_completed(False)
    .limit(10)
    .execute())

print(f"Found {len(urgent_tasks)} urgent tasks")
```

## Core Components

### TasksApiService

The main service class that provides all Google Tasks operations:

```python
# Access through user client
tasks = user.tasks

# Available operations
all_tasks = tasks.list_tasks()
task = tasks.get_task("task_id_123")
tasks.create_task(title="New Task", due=date.today())
```

### Task

Represents a Google Task with comprehensive metadata and helper methods:

```python
task = tasks.get_task("task_id_here")

print(f"Title: {task.title}")
print(f"Due: {task.due}")
print(f"Status: {task.status}")
print(f"Is overdue: {task.is_overdue()}")
print(f"Is completed: {task.is_completed()}")
```

### TaskQueryBuilder

Fluent API for building complex task queries:

```python
query = (tasks.query()
    .due_today()
    .show_completed(False)
    .in_task_list("work_tasks")
    .limit(20))

tasks_result = query.execute()
```

## Task Operations

### Creating Tasks

#### Simple Task
```python
task = tasks.create_task(
    title="Review quarterly report",
    notes="Focus on financial metrics and growth projections"
)
```

#### Task with Due Date
```python
from datetime import date

task = tasks.create_task(
    title="Submit budget proposal",
    notes="Include departmental breakdowns",
    due=date(2024, 12, 31)
)
```

#### Subtask
```python
# Create parent task first
parent_task = tasks.create_task(title="Website Redesign Project")

# Create subtask
subtask = tasks.create_task(
    title="Create wireframes",
    parent=parent_task.task_id,
    task_list_id="project_list_id"
)
```

### Retrieving Tasks

```python
# Get specific task
task = tasks.get_task("task_id_123")

# List all tasks from default list
all_tasks = tasks.list_tasks()

# List tasks from specific list with filtering
filtered_tasks = tasks.list_tasks(
    task_list_id="work_list_id",
    max_results=50,
    show_completed=False,
    due_max=datetime.now() + timedelta(days=7)
)
```

### Updating Tasks

```python
# Modify task properties
task.title = "Updated task title"
task.notes = "Additional notes added"
task.due = date(2024, 12, 25)

# Save changes
updated_task = tasks.update_task(task)

# Mark as completed
completed_task = tasks.mark_completed(task)

# Mark as incomplete
incomplete_task = tasks.mark_incomplete(task)
```

### Managing Task Position

```python
# Move task to different position
moved_task = tasks.move_task(
    task=task,
    parent="new_parent_id",  # Optional: make it a subtask
    previous="sibling_id"    # Optional: position after this task
)
```

### Deleting Tasks

```python
# Delete a task
success = tasks.delete_task(task)
print(f"Task deleted: {success}")
```

## Query Builder

The TaskQueryBuilder provides a powerful fluent interface for searching and filtering tasks:

### Date-based Filtering

```python
from datetime import date, timedelta

# Tasks due today
today_tasks = tasks.query().due_today().execute()

# Tasks due tomorrow
tomorrow_tasks = tasks.query().due_tomorrow().execute()

# Tasks due this week
week_tasks = tasks.query().due_this_week().execute()

# Tasks due in next 7 days
upcoming_tasks = tasks.query().due_next_days(7).execute()

# Overdue tasks
overdue_tasks = tasks.query().overdue().execute()

# Custom date range
start_date = datetime.now()
end_date = start_date + timedelta(days=30)
range_tasks = tasks.query().due_in_range(start_date, end_date).execute()

# Tasks due before specific date
before_tasks = tasks.query().due_before(date(2024, 12, 31)).execute()

# Tasks due after specific date
after_tasks = tasks.query().due_after(date(2024, 1, 1)).execute()
```

### Completion Filtering

```python
# Tasks completed today
completed_today = tasks.query().completed_today().execute()

# Tasks completed this week
completed_week = tasks.query().completed_this_week().execute()

# Tasks completed in last N days
completed_recent = tasks.query().completed_last_days(7).execute()

# Custom completion date range
completed_range = tasks.query().completed_in_range(
    datetime(2024, 1, 1),
    datetime(2024, 1, 31)
).execute()
```

### Status and Visibility Filtering

```python
# Show/hide completed tasks
active_tasks = tasks.query().show_completed(False).execute()
all_tasks = tasks.query().show_completed(True).execute()

# Show/hide hidden tasks
visible_tasks = tasks.query().show_hidden(False).execute()
```

### Task List Filtering

```python
# Tasks from specific list
work_tasks = tasks.query().in_task_list("work_list_id").execute()

# Tasks from default list
default_tasks = tasks.query().in_task_list("@default").execute()
```

### Complex Queries

```python
# Combine multiple criteria
urgent_work_tasks = (tasks.query()
    .in_task_list("work_list")
    .due_next_days(3)
    .show_completed(False)
    .limit(20)
    .execute())

# Project tasks due this month
project_tasks = (tasks.query()
    .in_task_list("project_list")
    .due_after(date.today().replace(day=1))
    .due_before(date.today().replace(day=31))
    .execute())
```

### Query Utilities

```python
# Get count without retrieving tasks
task_count = tasks.query().due_today().count()

# Get first matching task
next_task = tasks.query().due_after(datetime.now()).first()

# Check if tasks exist
has_overdue = tasks.query().overdue().exists()

# Set result limit
limited_tasks = tasks.query().limit(10).execute()
```

## Task List Management

### Working with Task Lists

```python
# List all task lists
all_lists = tasks.list_task_lists()
for task_list in all_lists:
    print(f"List: {task_list.title} (ID: {task_list.task_list_id})")

# Get specific task list
work_list = tasks.get_task_list("work_list_id")

# Create new task list
new_list = tasks.create_task_list("Project Alpha")

# Update task list name
updated_list = tasks.update_task_list(new_list, "Project Alpha - Phase 1")

# Delete task list (cannot delete default list)
success = tasks.delete_task_list(new_list)
```

## Batch Operations

### Bulk Task Operations

```python
# Get multiple tasks by ID
task_ids = ["task1_id", "task2_id", "task3_id"]
batch_tasks = tasks.batch_get_tasks("list_id", task_ids)

# Create multiple tasks
tasks_data = [
    {"title": "Task 1", "notes": "First task description"},
    {"title": "Task 2", "due": date(2024, 12, 31)},
    {"title": "Task 3", "parent": "parent_task_id"}
]
created_tasks = tasks.batch_create_tasks(tasks_data, "project_list_id")

print(f"Created {len(created_tasks)} tasks in batch")
```

## Error Handling

The Tasks service includes comprehensive error handling:

```python
from google_api_client.services.tasks.exceptions import (
    TasksError,
    TasksNotFoundError,
    TasksPermissionError,
    TaskConflictError,
    InvalidTaskDataError,
    TaskMoveError
)

try:
    task = tasks.get_task("invalid_task_id")
except TasksNotFoundError:
    print("Task not found")
except TasksPermissionError:
    print("Permission denied")
except InvalidTaskDataError:
    print("Invalid task data provided")
except TaskMoveError:
    print("Error moving task")
except TasksError as e:
    print(f"General Tasks API error: {e}")
```

## Examples

### Daily Task Management

```python
from datetime import date

def get_daily_agenda(tasks):
    """Get today's task agenda."""
    today_tasks = tasks.query().due_today().show_completed(False).execute()
    overdue_tasks = tasks.query().overdue().execute()
    
    print(f"Today's Task Agenda:")
    print(f"Due today: {len(today_tasks)}")
    print(f"Overdue: {len(overdue_tasks)}")
    
    # Show today's tasks
    if today_tasks:
        print(f"\nTasks due today:")
        for task in today_tasks:
            print(f"- {task.title}")
    
    # Show overdue tasks
    if overdue_tasks:
        print(f"\nOverdue tasks:")
        for task in overdue_tasks:
            print(f"- {task.title} (due: {task.due})")

# Usage
get_daily_agenda(user.tasks)
```

### Project Task Management

```python
def create_project_structure(tasks, project_name, task_items):
    """Create a complete project with subtasks."""
    
    # Create project task list
    project_list = tasks.create_task_list(f"{project_name} Tasks")
    
    # Create main project task
    main_task = tasks.create_task(
        title=f"{project_name} - Main Project",
        notes=f"Complete all tasks for {project_name}",
        due=date(2024, 12, 31),
        task_list_id=project_list.task_list_id
    )
    
    # Create subtasks
    created_subtasks = []
    for item in task_items:
        subtask = tasks.create_task(
            title=item["title"],
            notes=item.get("notes", ""),
            due=item.get("due"),
            parent=main_task.task_id,
            task_list_id=project_list.task_list_id
        )
        created_subtasks.append(subtask)
    
    print(f"Created project '{project_name}' with {len(created_subtasks)} subtasks")
    return main_task, created_subtasks

# Usage
project_tasks = [
    {"title": "Research requirements", "notes": "Gather all project requirements"},
    {"title": "Design mockups", "due": date(2024, 11, 15)},
    {"title": "Develop prototype", "due": date(2024, 11, 30)},
    {"title": "Test and deploy", "due": date(2024, 12, 15)}
]

main_task, subtasks = create_project_structure(
    user.tasks, 
    "Website Redesign", 
    project_tasks
)
```

### Productivity Analytics

```python
def analyze_productivity(tasks):
    """Analyze task completion patterns."""
    
    # Get completed tasks from this week
    completed_this_week = tasks.query().completed_this_week().execute()
    
    # Get tasks due next week
    due_next_week = tasks.query().due_next_week().show_completed(False).execute()
    
    # Get overdue tasks
    overdue = tasks.query().overdue().execute()
    
    # Calculate productivity metrics
    total_completed = len(completed_this_week)
    upcoming_tasks = len(due_next_week)
    overdue_count = len(overdue)
    
    print(f"Productivity Report:")
    print(f"✅ Completed this week: {total_completed}")
    print(f"📅 Due next week: {upcoming_tasks}")
    print(f"⚠️  Overdue tasks: {overdue_count}")
    
    # Calculate completion rate
    if total_completed + overdue_count > 0:
        completion_rate = (total_completed / (total_completed + overdue_count)) * 100
        print(f"📊 Completion rate: {completion_rate:.1f}%")
    
    # Show overdue tasks for attention
    if overdue:
        print(f"\nOverdue tasks requiring attention:")
        for task in overdue[:5]:  # Show first 5
            days_overdue = (date.today() - task.due).days
            print(f"- {task.title} ({days_overdue} days overdue)")

# Usage
analyze_productivity(user.tasks)
```

### Task Cleanup and Organization

```python
def cleanup_completed_tasks(tasks):
    """Clean up old completed tasks."""
    
    # Find tasks completed more than 30 days ago
    old_completed = (tasks.query()
        .completed_before(datetime.now() - timedelta(days=30))
        .execute())
    
    print(f"Found {len(old_completed)} old completed tasks")
    
    # Option to delete (implement with caution)
    for task_ in old_completd:
        task.delete_task(task_)

# Usage
cleanup_completed_tasks(user.tasks)
```

## API Reference

### TasksApiService

| Method                 | Description             | Parameters                                                                                                             | Returns            |
|------------------------|-------------------------|------------------------------------------------------------------------------------------------------------------------|--------------------|
| `query()`              | Create query builder    | None                                                                                                                   | `TaskQueryBuilder` |
| `list_tasks()`         | List tasks with filters | `task_list_id`, `max_results`, `completed_min`, `completed_max`, `due_min`, `due_max`, `show_completed`, `show_hidden` | `List[Task]`       |
| `get_task()`           | Get specific task       | `task_id: str`, `task_list_id: str`                                                                                    | `Task`             |
| `create_task()`        | Create new task         | `title: str`, `task_list_id`, `notes`, `due`, `parent`, `position`                                                     | `Task`             |
| `update_task()`        | Update existing task    | `task: Task`, `task_list_id: str`                                                                                      | `Task`             |
| `delete_task()`        | Delete task             | `task: Task`, `task_list_id: str`                                                                                      | `bool`             |
| `move_task()`          | Move task position      | `task: Task`, `task_list_id`, `parent`, `previous`                                                                     | `Task`             |
| `mark_completed()`     | Mark as completed       | `task: Task`, `task_list_id: str`                                                                                      | `Task`             |
| `mark_incomplete()`    | Mark as incomplete      | `task: Task`, `task_list_id: str`                                                                                      | `Task`             |
| `list_task_lists()`    | List all task lists     | None                                                                                                                   | `List[TaskList]`   |
| `get_task_list()`      | Get specific task list  | `task_list_id: str`                                                                                                    | `TaskList`         |
| `create_task_list()`   | Create new task list    | `title: str`                                                                                                           | `TaskList`         |
| `update_task_list()`   | Update task list        | `task_list: TaskList`, `title: str`                                                                                    | `TaskList`         |
| `delete_task_list()`   | Delete task list        | `task_list: TaskList`                                                                                                  | `bool`             |
| `batch_get_tasks()`    | Get multiple tasks      | `task_list_id: str`, `task_ids: List[str]`                                                                             | `List[Task]`       |
| `batch_create_tasks()` | Create multiple tasks   | `tasks_data: List[Dict]`, `task_list_id: str`                                                                          | `List[Task]`       |

### TaskQueryBuilder

| Method                  | Description               | Parameters                                 | Returns            |
|-------------------------|---------------------------|--------------------------------------------|--------------------|
| `limit()`               | Set result limit          | `count: int`                               | `TaskQueryBuilder` |
| `due_today()`           | Tasks due today           | None                                       | `TaskQueryBuilder` |
| `due_tomorrow()`        | Tasks due tomorrow        | None                                       | `TaskQueryBuilder` |
| `due_this_week()`       | Tasks due this week       | None                                       | `TaskQueryBuilder` |
| `due_next_week()`       | Tasks due next week       | None                                       | `TaskQueryBuilder` |
| `due_next_days()`       | Tasks due in N days       | `days: int`                                | `TaskQueryBuilder` |
| `overdue()`             | Overdue tasks             | None                                       | `TaskQueryBuilder` |
| `due_before()`          | Due before date           | `max_date: datetime`                       | `TaskQueryBuilder` |
| `due_after()`           | Due after date            | `min_date: datetime`                       | `TaskQueryBuilder` |
| `due_in_range()`        | Due in date range         | `min_date: datetime`, `max_date: datetime` | `TaskQueryBuilder` |
| `completed_today()`     | Completed today           | None                                       | `TaskQueryBuilder` |
| `completed_this_week()` | Completed this week       | None                                       | `TaskQueryBuilder` |
| `completed_last_days()` | Completed in last N days  | `days: int`                                | `TaskQueryBuilder` |
| `completed_before()`    | Completed before date     | `max_date: datetime`                       | `TaskQueryBuilder` |
| `completed_after()`     | Completed after date      | `min_date: datetime`                       | `TaskQueryBuilder` |
| `completed_in_range()`  | Completed in range        | `min_date: datetime`, `max_date: datetime` | `TaskQueryBuilder` |
| `show_completed()`      | Include/exclude completed | `show: bool`                               | `TaskQueryBuilder` |
| `show_hidden()`         | Include/exclude hidden    | `show: bool`                               | `TaskQueryBuilder` |
| `in_task_list()`        | Specify task list         | `task_list_id: str`                        | `TaskQueryBuilder` |
| `execute()`             | Execute query             | None                                       | `List[Task]`       |
| `count()`               | Get count                 | None                                       | `int`              |
| `first()`               | Get first result          | None                                       | `Optional[Task]`   |
| `exists()`              | Check if exists           | None                                       | `bool`             |

### Constants

| Constant                   | Value         | Description                  |
|----------------------------|---------------|------------------------------|
| `MAX_RESULTS_LIMIT`        | 100           | Maximum tasks per query      |
| `DEFAULT_MAX_RESULTS`      | 100           | Default result limit         |
| `MAX_TITLE_LENGTH`         | 1024          | Maximum task title length    |
| `MAX_NOTES_LENGTH`         | 8192          | Maximum notes length         |
| `TASK_STATUS_NEEDS_ACTION` | "needsAction" | Active task status           |
| `TASK_STATUS_COMPLETED`    | "completed"   | Completed task status        |
| `DEFAULT_TASK_LIST_ID`     | "@default"    | Default task list identifier |

---

This Tasks service package provides a comprehensive, secure, and user-friendly interface to Google Tasks operations. The fluent API design makes complex task management operations intuitive while maintaining the flexibility needed for advanced use cases.
