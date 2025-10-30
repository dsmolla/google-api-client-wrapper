# Drive Service Package

A comprehensive Google Drive client library that provides clean, intuitive access to Drive operations through the Google API. This package enables you to manage files, folders, permissions, and perform complex searches programmatically with both synchronous and asynchronous support.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
  - [Synchronous Usage](#synchronous-usage)
  - [Asynchronous Usage](#asynchronous-usage)
- [Core Components](#core-components)
- [File Operations](#file-operations)
- [Folder Operations](#folder-operations)
- [Query Builder](#query-builder)
- [Permissions and Sharing](#permissions-and-sharing)
- [Directory Tree Operations](#directory-tree-operations)
- [Async API](#async-api)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [API Reference](#api-reference)

## Overview

The Drive service package provides both synchronous and asynchronous APIs for Google Drive operations, with proper OAuth2 authentication and timezone support.

### Key Features

- **Comprehensive File Management**: Upload, download, copy, move, and delete files
- **Folder Operations**: Create, navigate, and manage folder hierarchies
- **Powerful Query Builder**: Fluent API for complex file and folder searches
- **Permission Management**: Share files and folders with granular access control
- **Directory Tree Navigation**: Visual and programmatic folder structure exploration
- **Batch Operations**: Efficient bulk file operations with concurrent async support
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

# Access Drive service
drive = api_service.drive

# Upload a file
file = drive.upload_file(
    file_path="document.pdf",
    name="My Important Document",
    description="Project documentation"
)

# Search for files
files = (drive.query()
    .search("meeting notes")
    .file_type("application/pdf")
    .limit(10)
    .execute())

# Create a folder and upload to it
folder = drive.create_folder("Project Files")
file_in_folder = drive.upload_file(
    "report.docx", 
    parent_folder_id=folder.folder_id
)

print(f"Found {len(files)} files matching search")
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

    # Access async Drive service
    drive = api_service.async_drive

    # Upload a file (async)
    file = await drive.upload_file(
        file_path="document.pdf",
        name="My Important Document",
        description="Project documentation"
    )

    # Search for files (async)
    files = await (drive.query()
        .search("meeting notes")
        .file_type("application/pdf")
        .limit(10)
        .execute())

    # Create folder and upload file concurrently
    folder = await drive.create_folder("Project Files")
    file_in_folder = await drive.upload_file(
        "report.docx",
        parent_folder_id=folder.folder_id
    )

    print(f"Found {len(files)} files matching search")

# Run async code
asyncio.run(main())
```

## Core Components

### DriveApiService

The main synchronous service class that provides all Drive operations:

```python
# Access through APIServiceLayer
drive = api_service.drive

# Available operations
files = drive.list()
file = drive.get("file_id_here")
drive.upload_file("document.pdf", name="My Document")

# Query builder for complex searches
files = (drive.query()
    .search("important documents")
    .in_folder(folder_id)
    .file_type("application/pdf")
    .execute())
```

### DriveFile

Represents a Google Drive file with comprehensive metadata:

```python
file = drive.get("file_id_here")

print(f"Name: {file.name}")
print(f"Size: {file.human_readable_size()}")
print(f"Modified: {file.modified_time}")
print(f"Is Google Doc: {file.is_google_doc()}")
print(f"Owner: {file.owners[0] if file.owners else 'Unknown'}")
```

### DriveQueryBuilder

Fluent API for building complex file and folder queries:

```python
query = (drive.query()
    .search("important documents")
    .in_folder(folder_id)
    .created_after(datetime(2024, 1, 1))
    .file_type("application/pdf")
    .limit(50))

files = query.execute()
```

## File Operations

### Uploading Files

#### Upload from Local File
```python
file = drive.upload_file(
    file_path="document.pdf",
    name="Important Document",
    parent_folder_id="folder_id",
    description="Project documentation"
)
```

#### Upload Content Directly
```python
file = drive.upload_file_content(
    content="Hello, World!",
    name="greeting.txt",
    mime_type="text/plain",
    parent_folder_id="folder_id"
)
```

### Downloading Files

#### Download to Local File

```python
local_path = drive.download_file(
  file=file,
  destination_folder="./downloads",
  file_name="custom_name.pdf"
)
```

#### Download Content to Memory

```python
content_bytes = drive.get_file_payload(file)
content_str = content_bytes.decode('utf-8')
```

### Managing Files

```python
# Get file by ID
file = drive.get("file_id_here")

# Copy file
copied_file = drive.copy(
    item=file,
    new_name="Copy of Document",
    destination_folder=target_folder
)

# Rename file
renamed_file = drive.rename(file, "New Name")

# Move file to different folder
moved_file = drive.move(file, target_folder)

# Move to trash
trashed_file = drive.move_to_trash(file)

# Permanent deletion
success = drive.delete(file)
```

## Folder Operations

### Creating Folders

#### Simple Folder Creation
```python
folder = drive.create_folder("Project Documents")
```

#### Nested Folder Creation
```python
nested_folder = drive.create_folder(
    name="Reports",
    parent_folder=project_folder,
    description="Monthly reports"
)
```

#### Create Folder Path
```python
# Creates the entire path if it doesn't exist
final_folder = drive.create_folder_path(
    path="/Projects/2024/Q1/Reports",
    description="Q1 2024 Reports"
)
```

### Folder Navigation

```python
# Find folder by path
folder = drive.get_folder_by_path("/Documents/Projects")

# Get parent folder
parent = drive.get_parent_folder(file)

# List folder contents
contents = drive.list_folder_contents(folder)

# Get only files in folder
files = drive.list_folder_contents(
    folder,
    include_folders=False,
    include_files=True
)

# Get only subfolders
subfolders = drive.list_folder_contents(
    folder,
    include_folders=True,
    include_files=False
)
```

## Query Builder

The DriveQueryBuilder provides a powerful fluent interface for searching files and folders:

### Basic Searches

```python
# Search by file name and content
files = drive.query().search("meeting notes").execute()

# Search in file names only
files = drive.query().name_contains("report").execute()

# Exact name match
files = drive.query().name_equals("budget.xlsx").execute()
```

### Folder Filtering

```python
# Files in specific folder
files = drive.query().in_folder(folder_id).execute()

# Files in any of several folders
files = drive.query().in_any_folder([folder1, folder2]).execute()

# Files NOT in specific folder
files = drive.query().not_in_folder(folder_id).execute()
```

### File Type Filtering

```python
# By MIME type
pdfs = drive.query().file_type("application/pdf").execute()

# Only folders
folders = drive.query().folders_only().execute()

# Only files (no folders)
files = drive.query().files_only().execute()

# Folders with specific name
project_folders = drive.query().folders_named("Project").execute()

# By file extension
docs = drive.query().with_extension(".docx").execute()
```

### Date-based Filtering

```python
from datetime import datetime

# Files created after date
recent = (drive.query()
    .created_after(datetime(2024, 1, 1))
    .execute())

# Files modified in date range
updated = (drive.query()
    .modified_after(datetime(2024, 1, 1))
    .modified_before(datetime(2024, 2, 1))
    .execute())
```

### Ownership and Sharing

```python
# Files owned by user
my_files = drive.query().owned_by_me().execute()

# Files shared with user
shared = drive.query().shared_with_me().execute()

# Starred files
starred = drive.query().starred().execute()

# Include/exclude trashed files
active = drive.query().trashed(False).execute()
deleted = drive.query().trashed(True).execute()
```

### Sorting and Limits

```python
# Order by name (A-Z)
files = drive.query().order_by_name().execute()

# Order by modification time (newest first)
files = drive.query().order_by_modified_time().execute()

# Custom ordering
files = drive.query().order_by("size", ascending=False).execute()

# Limit results
files = drive.query().limit(50).execute()
```

### Complex Queries

```python
# Combine multiple filters
important_docs = (drive.query()
    .search("important")
    .file_type("application/pdf")
    .in_folder(documents_folder)
    .created_after(datetime(2024, 1, 1))
    .owned_by_me()
    .order_by_modified_time()
    .limit(20)
    .execute())

# Custom query string
files = drive.query().custom_query("parents in 'folder_id' and starred = true").execute()
```

## Permissions and Sharing

### Share Files and Folders

#### Share with Specific User
```python
permission = drive.share(
    item=file,
    email="user@example.com",
    role="writer",  # reader, writer, commenter, owner
    notify=True,
    message="Please review this document"
)
```

**Permission roles:**
- `reader`: Can view and download
- `writer`: Can edit, comment, and share  
- `commenter`: Can view and add comments
- `owner`: Full control (transfer ownership)

### Managing Permissions

```python
# Get all permissions for a file/folder
permissions = drive.get_permissions(file)
for perm in permissions:
    print(f"{perm.display_name or perm.email_address}: {perm.role}")

# Remove permission
success = drive.remove_permission(file, permission_id)
```

## Directory Tree Operations

### Visual Directory Trees

```python
# Print visual tree structure
drive.print_directory_tree(
    folder=root_folder,
    max_depth=2,
    show_files=True,
    show_sizes=True,
    show_dates=True
)
```

Output example:
```
📁 Project Root/
├── 📁 Documents/
│   ├── 📄 proposal.pdf (2.3 MB) [2024-01-15]
│   └── 📄 notes.txt (1.2 KB) [2024-01-16]
└── 📁 Images/
    └── 📄 logo.png (45.7 KB) [2024-01-10]
```

### Programmatic Directory Trees

```python
# Get directory structure as nested dictionary
tree = drive.get_directory_tree(
    folder=root_folder,
    max_depth=3,
    include_files=True
)

# Navigate the tree structure
for child in tree['children']:
    if child['type'] == 'folder':
        print(f"Folder: {child['name']}")
    else:
        print(f"File: {child['name']} ({child['size']} bytes)")
```

## Async API

All Drive operations are available in async versions for high-performance applications. The async API provides true concurrent operations using Python's `async`/`await` syntax.

### Accessing Async Drive

```python
from google_client.api_service import APIServiceLayer
import asyncio

# Access async version
api_service = APIServiceLayer(user_info, timezone='UTC')
async_drive = api_service.async_drive
```

### Async Examples

```python
import asyncio

async def drive_operations():
    # All sync methods have async equivalents
    file = await async_drive.upload_file("document.pdf")
    files = await async_drive.list(max_results=20)
    folder = await async_drive.create_folder("Project")

    # Concurrent operations are much faster
    results = await asyncio.gather(
        async_drive.get("file_id_1"),
        async_drive.get("file_id_2"),
        async_drive.get("file_id_3"),
    )

    # Async query builder
    files = await (async_drive.query()
        .search("important")
        .file_type("application/pdf")
        .limit(50)
        .execute())

asyncio.run(drive_operations())
```

### Performance Benefits

Async operations shine when performing multiple operations:

```python
import time

# Sync: Sequential (slower)
start = time.time()
for file_id in file_ids[:20]:
    file = drive.get(file_id)
print(f"Sync: {time.time() - start:.2f}s")  # ~5-10 seconds

# Async: Concurrent (faster)
start = time.time()
tasks = [async_drive.get(file_id) for file_id in file_ids[:20]]
files = await asyncio.gather(*tasks)
print(f"Async: {time.time() - start:.2f}s")  # ~0.5-1 second
```

### Async API Methods

All synchronous methods have async equivalents:
- `async_drive.list()` → `await async_drive.list()`
- `async_drive.get()` → `await async_drive.get()`
- `async_drive.upload_file()` → `await async_drive.upload_file()`
- `async_drive.download_file()` → `await async_drive.download_file()`
- `async_drive.create_folder()` → `await async_drive.create_folder()`
- `async_drive.share()` → `await async_drive.share()`
- And all other methods...

## Error Handling

The Drive service provides basic error handling for common scenarios:

```python
from google_client.services.drive.exceptions import (
    DriveError,
    FileNotFoundError,
    FolderNotFoundError,
    PermissionDeniedError
)

try:
    file = drive.get("invalid_file_id")
except FileNotFoundError:
    print("File not found")
except FolderNotFoundError:
    print("Folder not found")
except PermissionDeniedError:
    print("Access denied")
except DriveError as e:
    print(f"Drive API error: {e}")
```

**Note:** For more specific error handling (uploads, downloads, sharing), catch the base `DriveError` exception and inspect the error message or underlying Google API errors.

## Examples

### File Management Workflow

```python
from google_client.api_service import APIServiceLayer
from datetime import datetime
import json

# Load credentials
with open('user_token.json', 'r') as f:
    user_info = json.load(f)

api_service = APIServiceLayer(user_info, timezone='UTC')
drive = api_service.drive

def organize_project_files(drive):
    """Create project structure and organize files."""

    # Create project folder structure
    project_folder = drive.create_folder("Project Alpha")
    docs_folder = drive.create_folder("Documents", parent_folder=project_folder)
    images_folder = drive.create_folder("Images", parent_folder=project_folder)

    # Upload files to appropriate folders
    proposal = drive.upload_file(
        "proposal.pdf",
        parent_folder_id=docs_folder.folder_id,
        description="Project proposal document"
    )

    # Share project folder with team
    drive.share(
        item=project_folder,
        email="team@company.com",
        role="writer",
        message="Project folder for Team Alpha"
    )

    print(f"Created project structure with folders: {project_folder.name}")
    return project_folder

# Usage
project = organize_project_files(drive)
```

### Bulk File Operations

```python
def cleanup_old_files(drive):
    """Find and archive old files."""
    
    # Find files older than 1 year
    old_files = (drive.query()
        .owned_by_me()
        .modified_before(datetime(2023, 1, 1))
        .files_only()
        .limit(100)
        .execute())
    
    if not old_files:
        print("No old files found")
        return
    
    # Create archive folder
    archive_folder = drive.create_folder("Archive 2023")
    
    # Move old files to archive
    for file in old_files:
        try:
            drive.move(file, archive_folder)
            print(f"Archived: {file.name}")
        except PermissionDeniedError:
            print(f"Cannot archive {file.name}: Permission denied")
    
    print(f"Archived {len(old_files)} old files")

# Usage
cleanup_old_files(drive)
```

### File Search and Analysis

```python
def analyze_drive_usage(drive):
    """Analyze Drive usage patterns."""
    
    # Get all files owned by user
    all_files = (drive.query()
        .owned_by_me()
        .files_only()
        .limit(1000)
        .execute())
    
    # Analyze by file type
    file_types = {}
    total_size = 0
    
    for file in all_files:
        mime_type = file.mime_type or "unknown"
        if mime_type not in file_types:
            file_types[mime_type] = {"count": 0, "size": 0}
        
        file_types[mime_type]["count"] += 1
        if file.size:
            file_types[mime_type]["size"] += file.size
            total_size += file.size
    
    # Print analysis
    print(f"Drive Usage Analysis:")
    print(f"Total files: {len(all_files)}")
    print(f"Total size: {format_size(total_size)}")
    print(f"\nBreakdown by file type:")
    
    for mime_type, stats in sorted(file_types.items(), 
                                  key=lambda x: x[1]["size"], 
                                  reverse=True):
        print(f"  {mime_type}: {stats['count']} files, {format_size(stats['size'])}")

def format_size(size_bytes):
    """Format bytes to human readable."""
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"

# Usage
analyze_drive_usage(drive)
```

## API Reference

### DriveApiService

| Method                    | Description                | Parameters                                                          | Returns                 |
|---------------------------|----------------------------|---------------------------------------------------------------------|-------------------------|
| `query()`                 | Create query builder       | None                                                                | `DriveQueryBuilder`     |
| `list()`                  | List files and folders     | `query`, `max_results`, `order_by`, `fields`                        | `List[DriveItem]`       |
| `get()`                   | Get specific file/folder   | `item_id: str`, `fields`                                            | `DriveItem`             |
| `upload_file()`           | Upload file from path      | `file_path`, `name`, `parent_folder_id`, `description`, `mime_type` | `DriveFile`             |
| `upload_file_content()`   | Upload content directly    | `content`, `name`, `parent_folder_id`, `description`, `mime_type`   | `DriveFile`             |
| `download_file()`         | Download to local file     | `file`, `dest_directory`, `file_name`                               | `str`                   |
| `download_file_content()` | Download content to memory | `file: DriveFile`                                                   | `bytes`                 |
| `create_folder()`         | Create new folder          | `name`, `parent_folder`, `description`                              | `DriveFolder`           |
| `create_folder_path()`    | Create folder path         | `path`, `root_folder_id`, `description`                             | `DriveFolder`           |
| `get_folder_by_path()`    | Find folder by path        | `path`, `root_folder_id`                                            | `Optional[DriveFolder]` |
| `list_folder_contents()`  | List folder contents       | `folder`, `include_folders`, `include_files`, `max_results`         | `List[DriveItem]`       |
| `copy()`                  | Copy file/folder           | `item`, `new_name`, `parent_folder`                                 | `DriveItem`             |
| `rename()`                | Rename file/folder         | `item`, `name`                                                      | `DriveItem`             |
| `move()`                  | Move to different folder   | `item`, `target_folder`, `remove_from_current_parents`              | `DriveItem`             |
| `delete()`                | Delete permanently         | `item: DriveItem`                                                   | `bool`                  |
| `move_to_trash()`         | Move to trash              | `item: DriveItem`                                                   | `DriveItem`             |
| `share()`                 | Share with user            | `item`, `email`, `role`, `notify`, `message`                        | `Permission`            |
| `get_permissions()`       | Get all permissions        | `item: DriveItem`                                                   | `List[Permission]`      |
| `remove_permission()`     | Remove permission          | `item`, `permission_id`                                             | `bool`                  |

### DriveQueryBuilder

| Method                     | Description             | Parameters                               | Returns             |
|----------------------------|-------------------------|------------------------------------------|---------------------|
| `limit()`                  | Set result limit        | `count: int`                             | `DriveQueryBuilder` |
| `search()`                 | Add search term         | `query: str`                             | `DriveQueryBuilder` |
| `name_contains()`          | Filter by name content  | `text: str`                              | `DriveQueryBuilder` |
| `name_equals()`            | Filter by exact name    | `name: str`                              | `DriveQueryBuilder` |
| `in_folder()`              | Filter by parent folder | `folder: Union[str, DriveFolder]`        | `DriveQueryBuilder` |
| `in_any_folder()`          | Filter by any parent    | `folders: List[Union[str, DriveFolder]]` | `DriveQueryBuilder` |
| `not_in_folder()`          | Exclude from folder     | `folder: Union[str, DriveFolder]`        | `DriveQueryBuilder` |
| `file_type()`              | Filter by MIME type     | `mime_type: str`                         | `DriveQueryBuilder` |
| `folders_only()`           | Only folders            | None                                     | `DriveQueryBuilder` |
| `files_only()`             | Only files              | None                                     | `DriveQueryBuilder` |
| `folders_named()`          | Folders with name       | `name: str`                              | `DriveQueryBuilder` |
| `folders_containing()`     | Folders containing text | `text: str`                              | `DriveQueryBuilder` |
| `shared_with_me()`         | Shared files            | None                                     | `DriveQueryBuilder` |
| `owned_by_me()`            | Owned files             | None                                     | `DriveQueryBuilder` |
| `starred()`                | Starred files           | None                                     | `DriveQueryBuilder` |
| `trashed()`                | Trashed files           | `include_trashed: bool`                  | `DriveQueryBuilder` |
| `created_after()`          | Created after date      | `date_time: datetime`                    | `DriveQueryBuilder` |
| `created_before()`         | Created before date     | `date_time: datetime`                    | `DriveQueryBuilder` |
| `modified_after()`         | Modified after date     | `date_time: datetime`                    | `DriveQueryBuilder` |
| `modified_before()`        | Modified before date    | `date_time: datetime`                    | `DriveQueryBuilder` |
| `with_extension()`         | Filter by extension     | `extension: str`                         | `DriveQueryBuilder` |
| `custom_query()`           | Add custom query        | `query: str`                             | `DriveQueryBuilder` |
| `order_by()`               | Set sort order          | `field: str`, `ascending: bool`          | `DriveQueryBuilder` |
| `order_by_name()`          | Sort by name            | `ascending: bool`                        | `DriveQueryBuilder` |
| `order_by_modified_time()` | Sort by modified time   | `ascending: bool`                        | `DriveQueryBuilder` |
| `order_by_created_time()`  | Sort by created time    | `ascending: bool`                        | `DriveQueryBuilder` |
| `execute()`                | Execute query           | None                                     | `List[DriveItem]`   |

### Constants

Available constants from `google_client.services.drive.constants`:

| Constant                   | Value                                             | Description                     |
|----------------------------|---------------------------------------------------|---------------------------------|
| `MAX_FILE_SIZE`            | 5368709120                                        | Maximum file size (5GB)         |
| `DEFAULT_CHUNK_SIZE`       | 1048576                                           | Default upload chunk size (1MB) |
| `FOLDER_MIME_TYPE`         | "application/vnd.google-apps.folder"              | MIME type for folders           |
| `GOOGLE_DOCS_MIME_TYPE`    | "application/vnd.google-apps.document"            | MIME type for Google Docs       |
| `GOOGLE_SHEETS_MIME_TYPE`  | "application/vnd.google-apps.spreadsheet"         | MIME type for Google Sheets     |
| `GOOGLE_SLIDES_MIME_TYPE`  | "application/vnd.google-apps.presentation"        | MIME type for Google Slides     |
| `DEFAULT_FILE_FIELDS`      | "id,name,size,mimeType,createdTime,..."          | Default fields returned by API  |

**Note:** For permission roles (`"reader"`, `"writer"`, `"commenter"`, `"owner"`) and special folder IDs (`"root"`, `"trash"`), use string literals directly instead of constants.

---

This Drive service package provides a comprehensive, secure, and user-friendly interface to Google Drive operations. The fluent API design makes complex file and folder operations intuitive while maintaining the flexibility needed for advanced use cases.
