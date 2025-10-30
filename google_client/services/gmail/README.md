# Gmail Service Package

A comprehensive Gmail client library that provides clean, intuitive access to Gmail operations through the Google API. This package enables you to send, receive, search, and manage emails programmatically with both synchronous and asynchronous support.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
  - [Synchronous Usage](#synchronous-usage)
  - [Asynchronous Usage](#asynchronous-usage)
- [Core Components](#core-components)
- [Email Operations](#email-operations)
- [Query Builder](#query-builder)
- [Threading Support](#threading-support)
- [Label Management](#label-management)
- [Attachment Handling](#attachment-handling)
- [Async API](#async-api)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [API Reference](#api-reference)

## Overview

The Gmail service package provides both synchronous and asynchronous APIs for Gmail operations, with proper OAuth2 authentication and timezone support.

### Key Features

- **Intuitive Email Operations**: Send, reply, forward, and manage emails
- **Powerful Query Builder**: Fluent API for complex email searches
- **Thread Management**: Work with Gmail conversation threads
- **Label Operations**: Create, modify, and manage Gmail labels
- **Attachment Support**: Upload, download, and manage email attachments
- **Batch Operations**: Efficient bulk email operations with concurrent async support
- **Async/Await Support**: Full async implementation for high-performance applications
- **Security First**: Built-in validation and secure handling of credentials

## Quick Start

### Synchronous Usage

```python
from google_client.api_service import APIServiceLayer
import json

# Load user credentials
with open('user_token.json', 'r') as f:
    user_info = json.load(f)

# Initialize API service layer
api_service = APIServiceLayer(user_info, timezone='America/New_York')

# Access Gmail service
gmail = api_service.gmail

# Send a simple email
gmail.send_email(
    to=["recipient@example.com"],
    subject="Hello from Gmail API",
    body_text="This is a test email sent using the Gmail API!"
)

# Search for emails
emails = (gmail.query()
    .from_sender("important@company.com")
    .with_subject("meeting")
    .last_days(7)
    .execute())

print(f"Found {len(emails)} emails")
```

### Asynchronous Usage

```python
import asyncio
from google_client.api_service import APIServiceLayer
import json

async def main():
    # Load user credentials
    with open('user_token.json', 'r') as f:
        user_info = json.load(f)

    # Initialize API service layer
    api_service = APIServiceLayer(user_info, timezone='America/New_York')

    # Access async Gmail service
    gmail = api_service.async_gmail

    # Send a simple email (async)
    await gmail.send_email(
        to=["recipient@example.com"],
        subject="Hello from Gmail API",
        body_text="This is a test email sent using the async Gmail API!"
    )

    # Search for emails (async)
    emails = await (gmail.query()
        .from_sender("important@company.com")
        .with_subject("meeting")
        .last_days(7)
        .execute())

    # Batch get emails concurrently (much faster!)
    message_ids = await gmail.list_emails(max_results=50)
    emails = await gmail.batch_get_emails(message_ids[:10])

    print(f"Found {len(emails)} emails")

# Run async code
asyncio.run(main())
```

## Core Components

### GmailApiService

The main synchronous service class that provides all Gmail operations:

```python
# Access through APIServiceLayer
gmail = api_service.gmail

# Available operations
emails = gmail.list_emails()
email = gmail.get_email(message_id)
gmail.send_email(to=["user@example.com"], subject="Test")

# Query builder for complex searches
emails = (gmail.query()
    .from_sender("boss@company.com")
    .with_subject("urgent")
    .is_unread()
    .execute())
```

### EmailMessage

Represents a Gmail message with comprehensive metadata:

```python
email = gmail.get_email("message_id_here")

print(f"Subject: {email.subject}")
print(f"From: {email.sender}")
print(f"Date: {email.date_time}")
print(f"Has attachments: {email.has_attachments()}")
print(f"Is read: {email.is_read}")
```

### EmailQueryBuilder

Fluent API for building complex email queries:

```python
query = (gmail.query()
    .from_sender("boss@company.com")
    .with_subject("urgent")
    .is_unread()
    .with_attachments()
    .last_days(3))

emails = query.execute()
```

## Email Operations

### Sending Emails

#### Simple Text Email
```python
gmail.send_email(
    to=["recipient@example.com"],
    subject="Simple Text Email",
    body_text="This is a plain text email."
)
```

#### HTML Email with Attachments
```python
gmail.send_email(
    to=["recipient@example.com"],
    cc=["cc@example.com"],
    subject="Rich HTML Email",
    body_html="<h1>Hello!</h1><p>This is <b>HTML</b> content.</p>",
    attachment_paths=["./document.pdf", "./image.jpg"]
)
```

### Creating Draft Emails

#### Simple Draft
```python
draft = gmail.create_draft(
    to=["recipient@example.com"],
    subject="Draft Email",
    body_text="This is a draft email that can be saved and sent later."
)
```

#### Draft with HTML and Attachments
```python
draft = gmail.create_draft(
    to=["recipient@example.com"],
    cc=["cc@example.com"],
    subject="Draft with Attachments",
    body_html="<h1>Draft Email</h1><p>This draft includes attachments.</p>",
    attachment_paths=["./document.pdf"],
    thread_id="existing_thread_id"  # Optional: add to existing thread
)
```

### Replying to Emails

```python
# Get original email
original = gmail.get_email("original_message_id")

# Send reply
reply = gmail.reply(
    original_email=original,
    body_text="Thanks for your email. I'll get back to you soon.",
    reply_all=True  # Include all original recipients
)
```

### Forwarding Emails

```python
# Forward with attachments
forwarded = gmail.forward(
    original_email=original,
    to=["colleague@example.com"],
    include_attachments=True
)
```

### Managing Email Status

```python
# Mark as read/unread
gmail.mark_as_read(email)
gmail.mark_as_unread(email)

# Add/remove labels
gmail.add_label(email, ["IMPORTANT", "Work"])
gmail.remove_label(email, ["UNREAD"])

# Delete email
gmail.delete_email(email, permanent=False)  # Move to trash
gmail.delete_email(email, permanent=True)   # Permanent deletion
```

## Query Builder

The EmailQueryBuilder provides a powerful fluent interface for searching emails:

### Basic Searches

```python
# Search by sender
emails = gmail.query().from_sender("boss@company.com").execute()

# Search by recipient
emails = gmail.query().to_recipient("me@example.com").execute()

# Search by subject
emails = gmail.query().with_subject("meeting").execute()

# Full-text search
emails = gmail.query().search("project deadline").execute()

# Exact match search
emails = gmail.query().search("urgent task", exact_match=True).execute()
```

### Date-based Filtering

```python
from datetime import date, timedelta

# Emails from today
emails = gmail.query().today().execute()

# Emails from yesterday
emails = gmail.query().yesterday().execute()

# Emails from last 7 days
emails = gmail.query().last_days(7).execute()

# Emails from this week
emails = gmail.query().this_week().execute()

# Emails from this month
emails = gmail.query().this_month().execute()

# Custom date range
start_date = date.today() - timedelta(days=30)
end_date = date.today()
emails = gmail.query().in_date_range(start_date, end_date).execute()

# After specific date
emails = gmail.query().after_date(date(2024, 1, 1)).execute()

# Before specific date
emails = gmail.query().before_date(date(2024, 12, 31)).execute()
```

### Advanced Filtering

```python
# Attachment filtering
emails = gmail.query().with_attachments().execute()
emails = gmail.query().without_attachments().execute()

# Read status
emails = gmail.query().is_read().execute()
emails = gmail.query().is_unread().execute()

# Starred emails
emails = gmail.query().is_starred().execute()

# Important emails
emails = gmail.query().is_important().execute()

# Folder/label filtering
emails = gmail.query().in_folder("inbox").execute()
emails = gmail.query().with_label("Work").execute()

# Size filtering
emails = gmail.query().larger_than(5).execute()  # Larger than 5MB
emails = gmail.query().smaller_than(1).execute()  # Smaller than 1MB
```

### Complex Queries

```python
# Combine multiple criteria
urgent_work_emails = (gmail.query()
    .from_sender("boss@company.com")
    .search("urgent")
    .is_unread()
    .last_days(3)
    .limit(20)
    .execute())

# Meeting emails with attachments from last week
meeting_emails = (gmail.query()
    .search("meeting")
    .with_attachments()
    .last_days(7)
    .execute())
```

### Query Utilities

```python
# Get count without retrieving emails
count = gmail.query().from_sender("notifications@service.com").count()

# Get first matching email
first_email = gmail.query().is_unread().first()

# Check if emails exist
has_unread = gmail.query().is_unread().exists()

# Get threads instead of individual messages
threads = gmail.query().from_sender("boss@company.com").get_threads()
```

## Threading Support

Gmail organizes related emails into conversation threads:

### Working with Threads

```python
# List threads
threads = gmail.list_threads(max_results=50)

# Get specific thread
thread = gmail.get_thread("thread_id_here")

# Thread information
print(f"Thread has {len(thread.messages)} messages")
print(f"Unread count: {thread.get_unread_count()}")
print(f"Has unread: {thread.has_unread_messages()}")

# Get latest message in thread
latest = thread.get_latest_message()

# Get all participants
participants = thread.get_participants()
```

### Thread Operations

```python
# Delete entire thread
gmail.delete_thread(thread, permanent=False)

# Modify thread labels
gmail.modify_thread_labels(
    thread,
    add_labels=["Work", "Priority"],
    remove_labels=["UNREAD"]
)

# Untrash thread
gmail.untrash_thread(thread)
```

## Label Management

### Working with Labels

```python
# List all labels
labels = gmail.list_labels()
for label in labels:
    print(f"Label: {label.name} (ID: {label.id}, Type: {label.type})")

# Create new label
new_label = gmail.create_label("Project Alpha")

# Update label name
updated_label = gmail.update_label(new_label, "Project Alpha - Phase 1")

# Delete label
gmail.delete_label(new_label)
```

### Email Label Operations

```python
# Add labels to email
gmail.add_label(email, ["Work", "Important"])

# Remove labels from email
gmail.remove_label(email, ["UNREAD"])

# Check if email has label
if email.has_label("IMPORTANT"):
    print("This email is marked as important")
```

## Attachment Handling

### Working with Attachments

```python
# Check for attachments
if email.has_attachments():
    print(f"Email has {len(email.attachments)} attachments")
    
    for attachment in email.attachments:
        print(f"File: {attachment.filename}")
        print(f"Size: {attachment.size} bytes")
        print(f"Type: {attachment.mime_type}")
```

### Downloading Attachments

```python
# Download single attachment
for attachment in email.attachments:
    gmail.download_attachment(attachment, download_folder="./downloads")

# Get attachment payload as bytes
attachment_data = gmail.get_attachment_payload(attachment)
with open(f"./custom/{attachment.filename}", "wb") as f:
    f.write(attachment_data)
```

### Sending Emails with Attachments

```python
# From file paths
gmail.send_email(
    to=["recipient@example.com"],
    subject="Files Attached",
    body_text="Please find attached files.",
    attachment_paths=["./report.pdf", "./data.xlsx"]
)
```

## Batch Operations

Handle multiple emails efficiently:

### Batch Email Retrieval

```python
# Get multiple emails by ID
message_ids = ["msg1_id", "msg2_id", "msg3_id"]
emails = gmail.batch_get_emails(message_ids)

print(f"Retrieved {len(emails)} emails in batch")
```

### Batch Email Sending

```python
# Send multiple emails at once
email_data_list = [
    {
        "to": ["user1@example.com"],
        "subject": "Welcome to our service",
        "body_text": "Thank you for signing up!"
    },
    {
        "to": ["user2@example.com"],
        "subject": "Account confirmation",
        "body_html": "<h1>Please confirm your account</h1>"
    },
    {
        "to": ["user3@example.com"],
        "subject": "Newsletter",
        "body_text": "Latest updates...",
        "attachment_paths": ["./newsletter.pdf"]
    }
]

sent_emails = gmail.batch_send_emails(email_data_list)
print(f"Sent {len(sent_emails)} emails in batch")
```

## Async API

All Gmail operations are available in async versions for high-performance applications. The async API provides true concurrent operations using Python's `async`/`await` syntax.

### Accessing Async Gmail

```python
from google_client.api_service import APIServiceLayer
import asyncio

# Access async version
api_service = APIServiceLayer(user_info, timezone='America/New_York')
async_gmail = api_service.async_gmail
```

### Async Examples

```python
import asyncio

async def gmail_operations():
    # All sync methods have async equivalents
    email = await async_gmail.get_email(message_id)
    await async_gmail.send_email(
        to=["user@example.com"],
        subject="Test",
        body_text="Hello!"
    )

    # Concurrent operations are much faster
    message_ids = await async_gmail.list_emails(max_results=100)

    # Batch get emails concurrently (10x-100x faster!)
    emails = await async_gmail.batch_get_emails(message_ids[:50])

    # Async query builder
    emails = await (async_gmail.query()
        .from_sender("boss@company.com")
        .unread()
        .last_days(30)
        .execute())

asyncio.run(gmail_operations())
```

### Performance Benefits

Async operations shine when fetching multiple emails:

```python
import time

# Sync: Sequential (slower)
start = time.time()
emails = []
for msg_id in message_ids[:50]:
    emails.append(gmail.get_email(msg_id))
print(f"Sync: {time.time() - start:.2f}s")  # ~15-20 seconds

# Async: Concurrent (faster)
start = time.time()
emails = await async_gmail.batch_get_emails(message_ids[:50])
print(f"Async: {time.time() - start:.2f}s")  # ~1-2 seconds
```

### Async API Methods

All synchronous methods have async equivalents:
- `async_gmail.list_emails()` → `await async_gmail.list_emails()`
- `async_gmail.get_email()` → `await async_gmail.get_email()`
- `async_gmail.send_email()` → `await async_gmail.send_email()`
- `async_gmail.batch_get_emails()` → `await async_gmail.batch_get_emails()`
- `async_gmail.reply()` → `await async_gmail.reply()`
- `async_gmail.forward()` → `await async_gmail.forward()`
- `async_gmail.mark_as_read()` → `await async_gmail.mark_as_read()`
- And all other methods...

## Error Handling

The Gmail service includes comprehensive error handling:

```python
from google_client.services.gmail.exceptions import (
    GmailError,
    EmailNotFoundError,
    AttachmentNotFoundError,
    GmailPermissionError,
    GmailQuotaExceededError
)

try:
    email = gmail.get_email("invalid_message_id")
except EmailNotFoundError:
    print("Email not found")
except GmailPermissionError:
    print("Permission denied")
except GmailQuotaExceededError:
    print("API quota exceeded")
except GmailError as e:
    print(f"Gmail API error: {e}")
```

## Examples

### Daily Email Summary

```python
from datetime import date

def get_daily_summary(gmail):
    """Get summary of today's emails."""
    today_emails = gmail.query().today().execute()
    unread_emails = gmail.query().today().is_unread().execute()
    
    print(f"Today's Email Summary:")
    print(f"Total emails: {len(today_emails)}")
    print(f"Unread emails: {len(unread_emails)}")
    
    # Show unread emails from important senders
    important_unread = (gmail.query()
        .today()
        .is_unread()
        .from_sender("boss@company.com")
        .execute())
    
    if important_unread:
        print(f"\nImportant unread emails: {len(important_unread)}")
        for email in important_unread:
            print(f"- {email.subject}")

# Usage
get_daily_summary(user.gmail)
```

### Bulk Email Operations

```python
def process_promotional_emails(gmail):
    """Move promotional emails to a specific label."""
    
    # Find promotional emails
    promo_emails = (gmail.query()
        .search("unsubscribe OR promotional")
        .in_folder("inbox")
        .limit(100)
        .execute())
    
    # Create promotional label if it doesn't exist
    try:
        promo_label = gmail.create_label("Promotional")
    except:
        # Label might already exist
        labels = gmail.list_labels()
        promo_label = next((l for l in labels if l.name == "Promotional"), None)
    
    # Move emails to promotional label
    for email in promo_emails:
        gmail.add_label(email, [promo_label.id])
        gmail.remove_label(email, ["INBOX"])
        gmail.mark_as_read(email)
    
    print(f"Processed {len(promo_emails)} promotional emails")

# Usage
process_promotional_emails(user.gmail)
```

### Auto-Reply System

```python
def setup_auto_reply(gmail, out_of_office_message):
    """Set up auto-reply for new emails."""
    
    # Get unread emails
    unread_emails = gmail.query().is_unread().execute()
    
    for email in unread_emails:
        # Skip if email is from yourself
        if email.is_from("me"):
            continue
            
        # Skip if already replied to this sender today
        existing_replies = (gmail.query()
            .to_recipient(email.sender.email)
            .today()
            .execute())
        
        if existing_replies:
            continue
            
        # Send auto-reply
        gmail.reply(
            original_email=email,
            body_text=out_of_office_message
        )
        
        # Mark original as read
        gmail.mark_as_read(email)
        
        print(f"Auto-replied to {email.sender.email}")

# Usage
auto_reply_msg = """
Thank you for your email. I am currently out of office and will respond when I return.
For urgent matters, please contact emergency@company.com.
"""
setup_auto_reply(user.gmail, auto_reply_msg)
```

## API Reference

### GmailApiService

| Method                 | Description                  | Parameters                                                                                                                   | Returns              |
|------------------------|------------------------------|------------------------------------------------------------------------------------------------------------------------------|----------------------|
| `query()`              | Create query builder         | None                                                                                                                         | `EmailQueryBuilder`  |
| `list_emails()`        | List emails with filters     | `max_results`, `query`, `include_spam_trash`, `label_ids`                                                                    | `List[EmailMessage]` |
| `get_email()`          | Get specific email           | `message_id: str`                                                                                                            | `EmailMessage`       |
| `send_email()`         | Send new email               | `to`, `subject`, `body_text`, `body_html`, `cc`, `bcc`, `attachment_paths`, `reply_to_message_id`, `references`, `thread_id` | `EmailMessage`       |
| `create_draft()`       | Create draft email           | `to`, `subject`, `body_text`, `body_html`, `cc`, `bcc`, `attachment_paths`, `reply_to_message_id`, `references`, `thread_id` | `EmailMessage`       |
| `reply()`              | Reply to email               | `original_email`, `body_text`, `body_html`, `attachment_paths`, `reply_all`                                                  | `EmailMessage`       |
| `forward()`            | Forward email                | `original_email`, `to`, `include_attachments`                                                                                | `EmailMessage`       |
| `batch_get_emails()`   | Get multiple emails          | `message_ids: List[str]`                                                                                                     | `List[EmailMessage]` |
| `batch_send_emails()`  | Send multiple emails         | `email_data_list: List[Dict[str, Any]]`                                                                                      | `List[EmailMessage]` |
| `mark_as_read()`       | Mark email as read           | `email: Union[EmailMessage, str]`                                                                                            | `bool`               |
| `mark_as_unread()`     | Mark email as unread         | `email: Union[EmailMessage, str]`                                                                                            | `bool`               |
| `add_label()`          | Add labels to email          | `email: Union[EmailMessage, str]`, `labels: List[str]`                                                                       | `bool`               |
| `remove_label()`       | Remove labels from email     | `email: Union[EmailMessage, str]`, `labels: List[str]`                                                                       | `bool`               |
| `delete_email()`       | Delete email                 | `email: Union[EmailMessage, str]`, `permanent: bool`                                                                         | `bool`               |
| `create_label()`       | Create new label             | `name: str`                                                                                                                  | `Label`              |
| `list_labels()`        | List all labels              | None                                                                                                                         | `List[Label]`        |
| `delete_label()`       | Delete label                 | `label: Union[Label, str]`                                                                                                   | `bool`               |
| `update_label()`       | Update label name            | `label: Union[Label, str]`, `new_name: str`                                                                                  | `Label`              |

### EmailQueryBuilder

| Method                  | Description         | Parameters                           | Returns                  |
|-------------------------|---------------------|--------------------------------------|--------------------------|
| `limit()`               | Set result limit    | `count: int`                         | `EmailQueryBuilder`      |
| `search()`              | Add search term     | `query: str`, `exact_match: bool`    | `EmailQueryBuilder`      |
| `from_sender()`         | Filter by sender    | `email: str`                         | `EmailQueryBuilder`      |
| `to_recipient()`        | Filter by recipient | `email: str`                         | `EmailQueryBuilder`      |
| `with_subject()`        | Filter by subject   | `subject: str`                       | `EmailQueryBuilder`      |
| `with_attachments()`    | Has attachments     | None                                 | `EmailQueryBuilder`      |
| `without_attachments()` | No attachments      | None                                 | `EmailQueryBuilder`      |
| `is_read()`             | Is read             | None                                 | `EmailQueryBuilder`      |
| `is_unread()`           | Is unread           | None                                 | `EmailQueryBuilder`      |
| `is_starred()`          | Is starred          | None                                 | `EmailQueryBuilder`      |
| `is_important()`        | Is important        | None                                 | `EmailQueryBuilder`      |
| `in_folder()`           | In folder/label     | `folder: str`                        | `EmailQueryBuilder`      |
| `with_label()`          | Has label           | `label: str`                         | `EmailQueryBuilder`      |
| `today()`               | From today          | None                                 | `EmailQueryBuilder`      |
| `yesterday()`           | From yesterday      | None                                 | `EmailQueryBuilder`      |
| `last_days()`           | From last N days    | `days: int`                          | `EmailQueryBuilder`      |
| `this_week()`           | From this week      | None                                 | `EmailQueryBuilder`      |
| `this_month()`          | From this month     | None                                 | `EmailQueryBuilder`      |
| `in_date_range()`       | Date range          | `start_date: date`, `end_date: date` | `EmailQueryBuilder`      |
| `after_date()`          | After date          | `date_obj: date`                     | `EmailQueryBuilder`      |
| `before_date()`         | Before date         | `date_obj: date`                     | `EmailQueryBuilder`      |
| `larger_than()`         | Larger than size    | `size_mb: int`                       | `EmailQueryBuilder`      |
| `smaller_than()`        | Smaller than size   | `size_mb: int`                       | `EmailQueryBuilder`      |
| `execute()`             | Execute query       | None                                 | `List[EmailMessage]`     |
| `count()`               | Get count           | None                                 | `int`                    |
| `first()`               | Get first result    | None                                 | `Optional[EmailMessage]` |
| `exists()`              | Check if exists     | None                                 | `bool`                   |
| `get_threads()`         | Get as threads      | None                                 | `List[EmailThread]`      |

### Constants

Available constants from `google_client.services.gmail.constants`:

| Constant            | Value    | Description                     |
|---------------------|----------|---------------------------------|
| `MAX_BODY_LENGTH`   | 25000000 | Maximum email body size (~25MB) |
| `MAX_SUBJECT_LENGTH`| 998      | Maximum subject length          |

**Note:** The `list_emails()` and `list_threads()` methods default to `max_results=100`. There is no enforced maximum limit - use pagination for large result sets.

---

This Gmail service package provides a comprehensive, secure, and user-friendly interface to Gmail operations. The fluent API design makes complex email operations intuitive while maintaining the flexibility needed for advanced use cases.
