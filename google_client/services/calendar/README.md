# Calendar Service Package

A comprehensive Google Calendar client library that provides clean, intuitive access to calendar operations through the Google API. This package enables you to create, manage, and schedule calendar events programmatically with both synchronous and asynchronous support.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
  - [Synchronous Usage](#synchronous-usage)
  - [Asynchronous Usage](#asynchronous-usage)
- [Core Components](#core-components)
- [Event Operations](#event-operations)
- [Query Builder](#query-builder)
- [Free/Busy Scheduling](#freebusy-scheduling)
- [Batch Operations](#batch-operations)
- [Async API](#async-api)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [API Reference](#api-reference)

## Overview

The Calendar service package provides both synchronous and asynchronous APIs for Google Calendar operations, with proper OAuth2 authentication and timezone support.

### Key Features

- **Intuitive Event Operations**: Create, update, delete, and manage calendar events
- **Powerful Query Builder**: Fluent API for complex event searches
- **Free/Busy Scheduling**: Check availability and find optimal meeting times
- **Batch Operations**: Efficient bulk calendar operations with concurrent async support
- **Async/Await Support**: Full async implementation for high-performance applications
- **Timezone Support**: Automatic timezone handling and conversion
- **Security First**: Built-in validation and secure handling of credentials

## Quick Start

### Synchronous Usage

```python
from google_client.api_service import APIServiceLayer
from datetime import datetime, timedelta
import json

# Load user credentials
with open('user_token.json', 'r') as f:
    user_info = json.load(f)

# Initialize API service layer
api_service = APIServiceLayer(user_info, timezone='America/New_York')

# Access Calendar service
calendar = api_service.calendar

# Create a simple event
calendar.create_event(
    start=datetime.now() + timedelta(hours=1),
    end=datetime.now() + timedelta(hours=2),
    summary="Team Meeting",
    description="Weekly sync with the development team",
    location="Conference Room A"
)

# Search for events
events = (calendar.query()
    .search("meeting")
    .today()
    .with_location()
    .execute())

print(f"Found {len(events)} meetings today")
```

### Asynchronous Usage

```python
import asyncio
from google_client.api_service import APIServiceLayer
from datetime import datetime, timedelta
import json

async def main():
    # Load user credentials
    with open('user_token.json', 'r') as f:
        user_info = json.load(f)

    # Initialize API service layer
    api_service = APIServiceLayer(user_info, timezone='America/New_York')

    # Access async Calendar service
    calendar = api_service.async_calendar

    # Create a simple event (async)
    await calendar.create_event(
        start=datetime.now() + timedelta(hours=1),
        end=datetime.now() + timedelta(hours=2),
        summary="Team Meeting",
        description="Weekly sync with the development team",
        location="Conference Room A"
    )

    # Search for events (async)
    events = await (calendar.query()
        .search("meeting")
        .today()
        .with_location()
        .execute())

    # Batch get events concurrently
    event_ids = [event.event_id for event in events[:10]]
    events_detail = await calendar.batch_get_events(event_ids)

    print(f"Found {len(events)} meetings today")

# Run async code
asyncio.run(main())
```

## Core Components

### CalendarApiService

The main synchronous service class that provides all calendar operations:

```python
# Access through APIServiceLayer
calendar = api_service.calendar

# Available operations
events = calendar.list_events()
event = calendar.get_event(event_id)
calendar.create_event(start=start_time, end=end_time, summary="Meeting")

# Query builder for complex searches
events = (calendar.query()
    .search("meeting")
    .today()
    .with_location()
    .execute())
```

### CalendarEvent

Represents a calendar event with comprehensive metadata:

```python
event = calendar.get_event("event_id_here")

print(f"Summary: {event.summary}")
print(f"Location: {event.location}")
print(f"Start: {event.start}")
print(f"Duration: {event.duration()} minutes")
print(f"Has attendees: {len(event.attendees) > 0}")
print(f"Is happening now: {event.is_happening_now()}")
```

### EventQueryBuilder

Fluent API for building complex event queries:

```python
query = (calendar.query()
    .search("meeting")
    .today()
    .with_location()
    .by_attendee("colleague@company.com"))

events = query.execute()
```

## Event Operations

### Creating Events

#### Simple Event
```python
calendar.create_event(
    start=datetime(2024, 12, 15, 14, 0),
    end=datetime(2024, 12, 15, 15, 0),
    summary="Team Meeting"
)
```

#### Event with Details
```python
from google_api_client.services.calendar.types import Attendee

calendar.create_event(
    start=datetime(2024, 12, 15, 10, 0),
    end=datetime(2024, 12, 15, 11, 30),
    summary="Project Review",
    description="Quarterly project review meeting",
    location="Conference Room A",
    attendees=[
        Attendee("john@company.com", "John Doe", "accepted"),
        Attendee("jane@company.com", "Jane Smith", "tentative")
    ]
)
```

### Managing Events

```python
# Get specific event
event = calendar.get_event("event_id_here")

# Update event
event.summary = "Updated Meeting Title"
event.location = "Room B"
updated_event = calendar.update_event(event)

# Delete event
calendar.delete_event(event)

# Event information
print(f"Duration: {event.duration()} minutes")
print(f"Is today: {event.is_today()}")
print(f"Is happening now: {event.is_happening_now()}")
print(f"Has attendee: {event.has_attendee('john@company.com')}")
```

## Query Builder

The EventQueryBuilder provides a powerful fluent interface for searching events:

### Basic Searches

```python
# Search by text
events = calendar.query().search("meeting").execute()

# Search by attendee
events = calendar.query().by_attendee("colleague@company.com").execute()

# Search with location
events = calendar.query().with_location().execute()
events = calendar.query().without_location().execute()

# Search in specific calendar
events = calendar.query().in_calendar("work@company.com").execute()
```

### Date-based Filtering

```python
from datetime import date, timedelta

# Events from today
events = calendar.query().today().execute()

# Events from tomorrow
events = calendar.query().tomorrow().execute()

# Events from last 7 days
events = calendar.query().last_days(7).execute()

# Events from this week
events = calendar.query().this_week().execute()

# Events from next week
events = calendar.query().next_week().execute()

# Events from this month
events = calendar.query().this_month().execute()

# Events from next N days
events = calendar.query().next_days(14).execute()

# Custom date range
events = calendar.query().in_date_range(
    start=datetime(2024, 1, 1),
    end=datetime(2024, 1, 31)
).execute()

# From specific date
events = calendar.query().from_date(datetime(2024, 1, 1)).execute()

# To specific date
events = calendar.query().to_date(datetime(2024, 12, 31)).execute()
```

### Complex Queries

```python
# Combine multiple criteria
important_meetings = (calendar.query()
    .search("project")
    .today()
    .with_location()
    .by_attendee("boss@company.com")
    .limit(10)
    .execute())

# Meeting planning
today_meetings = (calendar.query()
    .today()
    .search("meeting")
    .execute())

# Weekly review
week_events = (calendar.query()
    .this_week()
    .limit(50)
    .execute())
```

### Query Utilities

```python
# Get count without retrieving events
count = calendar.query().search("meeting").count()

# Get first matching event
first_event = calendar.query().today().first()

# Check if events exist
has_meetings = calendar.query().search("meeting").exists()
```

## Free/Busy Scheduling

Check availability and find optimal meeting times:

### Basic Free/Busy Queries

```python
from datetime import datetime, timedelta

# Check availability for a time range
start_time = datetime.now()
end_time = start_time + timedelta(hours=8)

freebusy_response = calendar.get_freebusy(
    start=start_time,
    end=end_time,
    calendar_ids=["primary", "work@company.com"]
)

# Check if specific time is free
is_free = freebusy_response.is_time_free(
    datetime.now() + timedelta(hours=2)
)

# Get busy periods
busy_periods = freebusy_response.get_busy_periods("primary")
for period in busy_periods:
    print(f"Busy: {period}")
```

### Finding Free Time Slots

```python
# Find available 1-hour slots
free_slots = calendar.find_free_slots(
    start=datetime.now(),
    end=datetime.now() + timedelta(days=1),
    duration_minutes=60
)

# Find 30-minute slots across multiple calendars
free_slots = calendar.find_free_slots(
    start=datetime.now(),
    end=datetime.now() + timedelta(days=7),
    duration_minutes=30,
    calendar_ids=["primary", "team@company.com"]
)

for slot in free_slots:
    print(f"Available: {slot}")
```

### Advanced Scheduling

```python
# Check if a time slot is completely free
from google_api_client.services.calendar.types import TimeSlot

proposed_slot = TimeSlot(
    start=datetime.now() + timedelta(hours=2),
    end=datetime.now() + timedelta(hours=3)
)

is_slot_free = freebusy_response.is_slot_free(proposed_slot)
```

## Batch Operations

Handle multiple events efficiently:

### Batch Retrieval

```python
# Get multiple events by ID
event_ids = ["event1", "event2", "event3"]
events = calendar.batch_get_events(event_ids)

# Also works with calendar ID specification
events = calendar.batch_get_events(event_ids, calendar_id="work@company.com")
```

### Batch Creation

```python
# Create multiple events at once
events_data = [
    {
        "start": datetime.now() + timedelta(hours=1),
        "end": datetime.now() + timedelta(hours=2),
        "summary": "Morning Standup",
        "location": "Room A"
    },
    {
        "start": datetime.now() + timedelta(hours=3),
        "end": datetime.now() + timedelta(hours=4),
        "summary": "Code Review",
        "description": "Weekly code review session"
    }
]

created_events = calendar.batch_create_events(events_data)

# Create in specific calendar
created_events = calendar.batch_create_events(events_data, calendar_id="team@company.com")
```

## Async API

All Calendar operations are available in async versions for high-performance applications. The async API provides true concurrent operations using Python's `async`/`await` syntax.

### Accessing Async Calendar

```python
from google_client.api_service import APIServiceLayer
import asyncio

# Access async version
api_service = APIServiceLayer(user_info, timezone='America/New_York')
async_calendar = api_service.async_calendar
```

### Async Examples

```python
import asyncio
from datetime import datetime, timedelta

async def calendar_operations():
    # All sync methods have async equivalents
    event = await async_calendar.create_event(
        start=datetime.now(),
        end=datetime.now() + timedelta(hours=1),
        summary="Team Standup"
    )

    # List events
    events = await async_calendar.list_events(
        start=datetime.now(),
        end=datetime.now() + timedelta(days=7)
    )

    # Concurrent operations are much faster
    event_ids = [e.event_id for e in events[:10]]
    events_detail = await async_calendar.batch_get_events(event_ids)

    # Async query builder
    meetings = await (async_calendar.query()
        .search("standup")
        .this_week()
        .execute())

    # Check free/busy
    busy_times = await async_calendar.get_freebusy(
        start=datetime.now(),
        end=datetime.now() + timedelta(days=1),
        calendar_ids=["primary"]
    )

asyncio.run(calendar_operations())
```

### Performance Benefits

Async operations shine when creating or fetching multiple events:

```python
import time

# Sync: Sequential (slower)
start = time.time()
for event_data in events_data[:20]:
    calendar.create_event(**event_data)
print(f"Sync: {time.time() - start:.2f}s")  # ~10-15 seconds

# Async: Concurrent (faster)
start = time.time()
await async_calendar.batch_create_events(events_data[:20])
print(f"Async: {time.time() - start:.2f}s")  # ~1-2 seconds
```

### Async API Methods

All synchronous methods have async equivalents:
- `async_calendar.list_events()` → `await async_calendar.list_events()`
- `async_calendar.get_event()` → `await async_calendar.get_event()`
- `async_calendar.create_event()` → `await async_calendar.create_event()`
- `async_calendar.update_event()` → `await async_calendar.update_event()`
- `async_calendar.delete_event()` → `await async_calendar.delete_event()`
- `async_calendar.get_freebusy()` → `await async_calendar.get_freebusy()`
- `async_calendar.batch_get_events()` → `await async_calendar.batch_get_events()`
- And all other methods...

## Error Handling

The Calendar service includes comprehensive error handling:

```python
from google_client.services.calendar.exceptions import (
    CalendarError,
    EventNotFoundError,
    CalendarNotFoundError,
    CalendarPermissionError,
    EventConflictError,
    InvalidEventDataError
)

try:
    event = calendar.get_event("invalid_event_id")
except EventNotFoundError:
    print("Event not found")
except CalendarPermissionError:
    print("Permission denied")
except CalendarError as e:
    print(f"Calendar API error: {e}")
```

## Examples

### Daily Schedule Overview

```python
from datetime import datetime

def get_daily_schedule(calendar):
    """Get today's schedule with details."""
    today_events = calendar.query().today().execute()
    
    print(f"Today's Schedule ({len(today_events)} events):")
    
    for event in sorted(today_events, key=lambda e: e.start or datetime.min):
        start_time = event.start.strftime("%H:%M") if event.start else "All day"
        duration = f"({event.duration()} min)" if event.duration() else ""
        location = f"at {event.location}" if event.location else ""
        
        print(f"  {start_time} - {event.summary} {duration} {location}")
        
        if event.is_happening_now():
            print("    🔴 Happening now!")

# Usage
get_daily_schedule(user.calendar)
```

### Smart Meeting Scheduler

```python
def find_optimal_meeting_time(calendar, attendees, duration_minutes=60):
    """Find the best meeting time for all attendees."""
    
    # Get calendars for all attendees
    calendar_ids = ["primary"] + attendees
    
    # Look for slots in the next 5 business days
    start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=5)
    
    # Find free slots
    free_slots = calendar.find_free_slots(
        start=start,
        end=end,
        duration_minutes=duration_minutes,
        calendar_ids=calendar_ids
    )
    
    # Filter for business hours (9 AM - 5 PM)
    business_slots = []
    for slot in free_slots:
        if 9 <= slot.start.hour <= 16:  # Allow 1 hour before 5 PM
            business_slots.append(slot)
    
    # Return top 3 options
    return business_slots[:3]

# Usage
available_times = find_optimal_meeting_time(
    calendar,
    attendees=["colleague1@company.com", "colleague2@company.com"],
    duration_minutes=90
)

print("Suggested meeting times:")
for i, slot in enumerate(available_times, 1):
    print(f"{i}. {slot}")
```

### Calendar Analytics

```python
def analyze_calendar_patterns(calendar, days=30):
    """Analyze calendar usage patterns."""
    
    start = datetime.now() - timedelta(days=days)
    end = datetime.now()
    
    events = calendar.query().in_date_range(start, end).execute()
    
    # Basic metrics
    total_events = len(events)
    total_hours = sum(event.duration() or 0 for event in events) / 60
    
    # Meeting analysis
    meetings_with_attendees = [e for e in events if len(e.attendees) > 0]
    solo_events = [e for e in events if len(e.attendees) == 0]
    
    # Location analysis
    remote_meetings = [e for e in events if e.location and 
                      any(keyword in e.location.lower() 
                          for keyword in ['zoom', 'teams', 'meet', 'webex'])]
    
    in_person_meetings = [e for e in events if e.location and 
                         any(keyword in e.location.lower() 
                             for keyword in ['room', 'office', 'building'])]
    
    # Time analysis
    morning_events = [e for e in events if e.start and e.start.hour < 12]
    afternoon_events = [e for e in events if e.start and e.start.hour >= 12]
    
    return {
        "total_events": total_events,
        "total_hours": round(total_hours, 1),
        "meetings_with_attendees": len(meetings_with_attendees),
        "solo_events": len(solo_events),
        "remote_meetings": len(remote_meetings),
        "in_person_meetings": len(in_person_meetings),
        "morning_events": len(morning_events),
        "afternoon_events": len(afternoon_events),
        "avg_event_duration": round(total_hours / total_events, 1) if total_events > 0 else 0
    }

# Usage
stats = analyze_calendar_patterns(user.calendar, days=30)
print(f"Calendar Analytics (last 30 days):")
for key, value in stats.items():
    print(f"  {key.replace('_', ' ').title()}: {value}")
```

### Conflict Detection

```python
def check_for_conflicts(calendar, days_ahead=7):
    """Check for scheduling conflicts in upcoming events."""
    
    start = datetime.now()
    end = start + timedelta(days=days_ahead)
    
    events = calendar.query().in_date_range(start, end).execute()
    
    # Sort events by start time
    events.sort(key=lambda e: e.start or datetime.min)
    
    conflicts = []
    
    for i, event1 in enumerate(events):
        for event2 in events[i+1:]:
            if event1.conflicts_with(event2):
                conflicts.append((event1, event2))
    
    if conflicts:
        print(f"Found {len(conflicts)} scheduling conflicts:")
        for event1, event2 in conflicts:
            print(f"  Conflict: '{event1.summary}' and '{event2.summary}'")
    else:
        print("No scheduling conflicts found!")
    
    return conflicts

# Usage
conflicts = check_for_conflicts(user.calendar, days_ahead=14)
```

## API Reference

### CalendarApiService

| Method                  | Description              | Parameters                                                                                     | Returns               |
|-------------------------|--------------------------|------------------------------------------------------------------------------------------------|-----------------------|
| `query()`               | Create query builder     | None                                                                                           | `EventQueryBuilder`   |
| `list_events()`         | List events with filters | `max_results`, `start`, `end`, `query`, `calendar_id`                                          | `List[CalendarEvent]` |
| `get_event()`           | Get specific event       | `event_id: str`, `calendar_id: str`                                                            | `CalendarEvent`       |
| `create_event()`        | Create new event         | `start`, `end`, `summary`, `description`, `location`, `attendees`, `recurrence`, `calendar_id` | `CalendarEvent`       |
| `update_event()`        | Update existing event    | `event: CalendarEvent`, `calendar_id: str`                                                     | `CalendarEvent`       |
| `delete_event()`        | Delete event             | `event: CalendarEvent`, `calendar_id: str`                                                     | `bool`                |
| `batch_get_events()`    | Get multiple events      | `event_ids: List[str]`, `calendar_id: str`                                                     | `List[CalendarEvent]` |
| `batch_create_events()` | Create multiple events   | `events_data: List[Dict]`, `calendar_id: str`                                                  | `List[CalendarEvent]` |
| `get_freebusy()`        | Query free/busy info     | `start`, `end`, `calendar_ids: List[str]`                                                      | `FreeBusyResponse`    |
| `find_free_slots()`     | Find available slots     | `start`, `end`, `duration_minutes`, `calendar_ids`                                             | `List[TimeSlot]`      |

### EventQueryBuilder

| Method               | Description        | Parameters                         | Returns                   |
|----------------------|--------------------|------------------------------------|---------------------------|
| `limit()`            | Set result limit   | `count: int`                       | `EventQueryBuilder`       |
| `search()`           | Add search term    | `query: str`                       | `EventQueryBuilder`       |
| `by_attendee()`      | Filter by attendee | `email: str`                       | `EventQueryBuilder`       |
| `with_location()`    | Has location       | None                               | `EventQueryBuilder`       |
| `without_location()` | No location        | None                               | `EventQueryBuilder`       |
| `in_calendar()`      | Specific calendar  | `calendar_id: str`                 | `EventQueryBuilder`       |
| `today()`            | From today         | None                               | `EventQueryBuilder`       |
| `tomorrow()`         | From tomorrow      | None                               | `EventQueryBuilder`       |
| `this_week()`        | From this week     | None                               | `EventQueryBuilder`       |
| `next_week()`        | From next week     | None                               | `EventQueryBuilder`       |
| `this_month()`       | From this month    | None                               | `EventQueryBuilder`       |
| `next_days()`        | From next N days   | `days: int`                        | `EventQueryBuilder`       |
| `last_days()`        | From last N days   | `days: int`                        | `EventQueryBuilder`       |
| `in_date_range()`    | Date range         | `start: datetime`, `end: datetime` | `EventQueryBuilder`       |
| `from_date()`        | From date          | `start: datetime`                  | `EventQueryBuilder`       |
| `to_date()`          | To date            | `end: datetime`                    | `EventQueryBuilder`       |
| `execute()`          | Execute query      | None                               | `List[CalendarEvent]`     |
| `count()`            | Get count          | None                               | `int`                     |
| `first()`            | Get first result   | None                               | `Optional[CalendarEvent]` |
| `exists()`           | Check if exists    | None                               | `bool`                    |

### Constants

Available constants from `google_client.services.calendar.constants`:

| Constant              | Value     | Description                |
|-----------------------|-----------|----------------------------|
| `DEFAULT_CALENDAR_ID` | "primary" | Default calendar ID        |

**Note:**
- The `list_events()` method defaults to `max_results=100` and `end` date defaults to 7 days from start
- For event status use literal strings: `"confirmed"`, `"tentative"`, `"cancelled"`
- For attendee responses use: `"needsAction"`, `"declined"`, `"tentative"`, `"accepted"`
- The `find_free_slots()` method requires `duration_minutes` parameter (no default value)

---

This Calendar service package provides a comprehensive, secure, and user-friendly interface to Google Calendar operations. The fluent API design makes complex scheduling operations intuitive while maintaining the flexibility needed for advanced calendar management use cases.
