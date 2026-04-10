# Sheets Service Package

A comprehensive Google Sheets client library that provides clean, intuitive access to Sheets operations through the Google API. This package enables you to manage spreadsheets, read and write data, format cells, and perform complex batch mutations programmatically with both synchronous and asynchronous support.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
  - [Synchronous Usage](#synchronous-usage)
  - [Asynchronous Usage](#asynchronous-usage)
- [Core Components](#core-components)
- [Spreadsheet Operations](#spreadsheet-operations)
- [Worksheet Operations](#worksheet-operations)
- [Data Operations](#data-operations)
- [Formatting and Styles](#formatting-and-styles)
- [Grid Mutations](#grid-mutations)
- [Fluent Batch Updater](#fluent-batch-updater)
- [Async API](#async-api)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [API Reference](#api-reference)

## Overview

The Sheets service package provides both synchronous and asynchronous APIs for Google Sheets operations, with proper OAuth2 authentication and timezone support.

### Key Features

- **Document Management**: Create, read, and manage Google Spreadsheets
- **Worksheet Operations**: Add, rename, delete, and duplicate inner tabs
- **Intuitive Data Reading**: Extract ranges as raw arrays or automatically parse tabular data into `List[dict]` via headers
- **Data Writing**: Overwrite, append rows, or insert smart dictionary payloads easily
- **Formatting Engine**: Apply rich text colors, backgrounds, alignments, and complex borders using native Pydantic models
- **Grid Structural Integrity**: Freeze rows, auto-resize columns, insert/delete bounds, and merge cells
- **Powerful Fluent Batch Updater**: Build massive, multi-faceted grid mutations and commit them to Google in a single network request
- **Validation & Flow**: Add dropdowns (`add_data_validation`) and sort data dynamically
- **Async/Await Support**: Full thread-pool execution for concurrent extraction & mutation patterns
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

# Access Sheets service
sheets = api_service.sheets

# Create a spreadsheet
spreadsheet = sheets.create_spreadsheet(title="Annual Budget")
sheet_id = spreadsheet.worksheets[0].sheet_id
spreadsheet_id = spreadsheet.spreadsheet_id

# Write headers and append data natively
data = [
    {"Month": "January", "Revenue": 10000, "Expenses": 5000},
    {"Month": "February", "Revenue": 12000, "Expenses": 5500}
]
sheets.append_values_from_dicts(spreadsheet_id, "Sheet1!A1", data)

# Read it back into dictionaries
records = sheets.get_values_as_dicts(spreadsheet_id, "Sheet1!A1:C3")
print(f"Found {len(records)} records")

# Format the headers
from google_client.services.sheets.types import CellFormat
header_fmt = CellFormat(bold=True, background_color_hex="#EFEFEF")
sheets.format_range(spreadsheet_id, sheet_id, 0, 1, 0, 3, header_fmt)
```

### Asynchronous Usage

```python
import asyncio
from google_client.api_service import APIServiceLayer
import json
from google_client.services.sheets.types import CellFormat

async def main():
    with open('user_token.json', 'r') as f:
        user_info = json.load(f)

    api_service = APIServiceLayer(user_info, timezone='America/New_York')
    async_sheets = api_service.async_sheets

    # Read records from an existing sheet concurrently
    task1 = async_sheets.get_values_as_dicts("spreadsheet_1_id", "Data!A:Z")
    task2 = async_sheets.get_values_as_dicts("spreadsheet_2_id", "Data!A:Z")
    results = await asyncio.gather(task1, task2)

    print(f"File 1 rows: {len(results[0])}")
    print(f"File 2 rows: {len(results[1])}")

    header_fmt = CellFormat(bold=True, text_color_hex="#FFFFFF", background_color_hex="#333333")

    # Chain massive grid manipulations over the wire concurrently
    await (async_sheets.batch_updater("spreadsheet_1_id")
        .freeze_rows(sheet_id=0, num_rows=1)
        .format_range(sheet_id=0, start_row=0, end_row=1, start_col=0, end_col=5, format=header_fmt)
        .auto_resize_columns(sheet_id=0, start_col=0, end_col=10)
        .add_data_validation(sheet_id=0, start_row=1, end_row=1000, start_col=2, end_col=3, dropdown_values=["Pending", "Approved", "Denied"])
        .execute())

# Run async code
asyncio.run(main())
```

## Core Components

### SheetsApiService

The main synchronous service class that provides all standalone operations:

```python
# Access through APIServiceLayer
sheets = api_service.sheets

# Retrieve raw metadata
metadata = sheets.get_spreadsheet("spreadsheet_id")
print(f"Workbook URL: {metadata.url}")

for ws in metadata.worksheets:
    print(ws.title, ws.row_count, ws.column_count)
```

### Data Models

Data mapping is strongly typed via standard Pydantic records defined in `types.py`:

- `Spreadsheet`: High-level wrapper containing the spreadsheet ID, URL, title, and inner Worksheets.
- `Worksheet`: Tab metadata (Title, sheet_id, index, row bounds, visibility).
- `CellRange`: Wraps raw list-of-lists arrays (`values`) tied to a given A1 `range_name`. Features internal map routers via `to_dict_list()`.
- `CellFormat`: Defines rendering (bold, italics, hex backgrounds, sizes).
- `CellBorders` and `Border`: Encompasses geometric cell border stylings.

## Spreadsheet Operations

Create and retrieve master Google Sheet documents:

```python
# Blank generation
workbook = sheets.create_spreadsheet("Project Tracking Tracker")

# Retrieve full document representation
workbook = sheets.get_spreadsheet("your_document_id")

# Find a specific worksheet ID easily
target_tab = workbook.get_worksheet_by_title("Q3 Summary")
if target_tab:
    print(target_tab.sheet_id)
```

## Worksheet Operations

Dynamically alter the inner-tabs (worksheets) of the document. Most of these require the numeric `sheet_id` (derived from `spreadsheet.worksheets[i].sheet_id`), rather than the string title.

```python
# Add a new tab (defaults to 1000x26 cells)
new_sheet = sheets.add_worksheet("spreadsheet_id", title="Analytics", rows=5000, cols=50)

# Rename
sheets.rename_worksheet("spreadsheet_id", sheet_id=new_sheet.sheet_id, new_title="Analytics 2024")

# Duplicate
sheets.duplicate_worksheet("spreadsheet_id", source_sheet_id=new_sheet.sheet_id, new_title="Analytics 2025")

# Delete
sheets.delete_worksheet("spreadsheet_id", sheet_id=new_sheet.sheet_id)
```

## Data Operations

Read and write raw semantic data effortlessly.

### Reading Data

```python
# Extract exactly an unbounded range
cell_range = sheets.get_values("spreadsheet_id", "Sheet1!A1:Z")

# Parse 2D lists
for numeric_row in cell_range.values:
    print(numeric_row[0])  # Column A

# Semantic Table Reading (Extremely powerful for LLMs)
# Automatically assumes Row 0 is headers and generates objects:
records = sheets.get_values_as_dicts("spreadsheet_id", "Data!A1:C")
for record in records:
    print(record.get("User ID"), record.get("Email"))

# Fast header lookup (peeks the top bound)
headers = sheets.get_headers("spreadsheet_id", "Data!A:Z")
```

### Searching Data

```python
# Search for coordinate placement of string values
coord = sheets.find_value("spreadsheet_id", "Inventory!A1:Z500", "SKU-99042")
if coord:
    row_idx, col_idx = coord
    print(f"Found item at bounds [{row_idx}, {col_idx}]")
```

### Writing Data

```python
# Raw array overwriting
sheets.update_values("spreadsheet_id", "Sheet1!A2", [
    ["Bob", "Engineering", 120000],
    ["Alice", "Design", 115000]
])

# Value appending (automatically detects the bottom of the table)
sheets.append_values("spreadsheet_id", "Sheet1!A1", [
    ["Charlie", "Sales", 90000]
])

# Semantic appending (Maps kwargs to discovered header blocks!)
data_payload = [{"Name": "Diana", "Department": "HR", "Salary": 85000}]
sheets.append_values_from_dicts("spreadsheet_id", "Sheet1!A1:C", data_payload)

# Clear regional data
sheets.clear_values("spreadsheet_id", "Sheet1!A2:Z1000")
```

## Formatting and Styles

Manage cell fonts, colors, logic, and physical borders. Note that formats are completely decoupled into the `batch_updater()` lifecycle, or you can use the builder facade implementations directly on the ApiService.

```python
from google_client.services.sheets.types import CellFormat, CellBorders, Border, BorderStyle

# Create Border architecture
main_border = Border(style=BorderStyle.SOLID_THICK, color_hex="#000000")
borders = CellBorders(
    top=main_border,
    bottom=main_border,
    inner_vertical=Border(style=BorderStyle.DASHED)
)

# Apply to CellFormat architecture
alert_format = CellFormat(
    bold=True,
    text_color_hex="#FF0000",
    background_color_hex="#FCE4D6",
    borders=borders
)

# Broadcast the format update over grid bounds. 
# NOTE: Formatter arguments are 0-indexed bounds [start, end)
sheets.format_range("spreadsheet_id", sheet_id=0, start_row=0, end_row=5, start_col=0, end_col=1, format=alert_format)
```

## Grid Mutations

Alter the geometric structure of the document matrix.

```python
# Freeze rows (pin them while scrolling)
sheets.freeze_rows("spreadsheet_id", sheet_id=0, num_rows=2)

# Insert physical rows (shifts content down)
sheets.insert_rows("spreadsheet_id", sheet_id=0, start_index=1, num_rows=10)

# Delete physical rows
sheets.delete_rows("spreadsheet_id", sheet_id=0, start_index=5, end_index=15)

# Resize columns to content limits automatically
sheets.auto_resize_columns("spreadsheet_id", sheet_id=0, start_col=0, end_col=5)

# Merging / Unmerging
sheets.merge_cells("spreadsheet_id", sheet_id=0, start_row=0, end_row=1, start_col=0, end_col=5, merge_type="MERGE_ALL")
sheets.unmerge_cells("spreadsheet_id", sheet_id=0, start_row=0, end_row=1, start_col=0, end_col=5)

# Dropdown / Data Validations
sheets.add_data_validation("spreadsheet_id", sheet_id=0, start_row=1, end_row=100, start_col=2, end_col=3, dropdown_values=["Yes", "No", "Maybe"])

# Sorting
sheets.sort_range("spreadsheet_id", sheet_id=0, start_row=1, end_row=100, start_col=0, end_col=5, sort_column_index=2, ascending=False)
```

## Fluent Batch Updater

The most powerful design piece of the API wrapper is the `batch_updater()`. Google Sheets operations are highly slow and expensive if executed sequentially across an HTTP network boundary. Building a single Batch API request eliminates request bloat and avoids exhausting Google quotas rapidly.

Every structural method (all formats, mutations, adding sheets) inside `SheetsApiService` actually resolves onto this batch builder internally anyway!

```python
# Use the Fluent Builder to stack 6 structural changes into exactly 1 HTTP request!
success = (sheets.batch_updater("spreadsheet_id")
    .add_worksheet("Logs")                                      # Step 1
    .update_values("Logs!A1", [["Timestamp", "Level", "Msg"]])  # Step 2
    .format_range(sheet_id=1, format=header_fmt,                # Step 3
                  start_row=0, end_row=1, start_col=0, end_col=3)
    .freeze_rows(sheet_id=1, num_rows=1)                        # Step 4
    .auto_resize_columns(sheet_id=1, start_col=0, end_col=3)    # Step 5
    .add_data_validation(sheet_id=1, start_row=1, end_row=1000, 
                         start_col=1, end_col=2, 
                         dropdown_values=["INFO", "ERROR"])     # Step 6
    .execute())                                                 # Transmit Payload!
```

## Async API

The asynchronous module utilizes Python's `ThreadPoolExecutor` safely bound to the `asyncio` event loop. You do not need to alter how you treat mutations. The `AsyncSheetsBatchUpdater` correctly abstracts the async pipeline natively into its underlying execution bounds, letting you unleash full grid formatting matrices simultaneously across various workbooks.

### Concurrent Performance

```python
async def parallel_creation_and_population():
    # Execute batch chains completely concurrently across different sheets!
    
    board_1 = async_sheets.batch_updater(id_1).add_worksheet("Log").freeze_rows(0,1).execute()
    board_2 = async_sheets.batch_updater(id_2).add_worksheet("Log").freeze_rows(0,1).execute()

    await asyncio.gather(board_1, board_2)
```

### Async API Methods

All standard `SheetsApiService` methods have robust async equivalents. Awaiting them guarantees thread safety:
- `async_sheets.create_spreadsheet()` → `await async_sheets.create_spreadsheet()`
- `async_sheets.get_values()` → `await async_sheets.get_values()`
- `async_sheets.get_values_as_dicts()` → `await async_sheets.get_values_as_dicts()`
- `async_sheets.append_values_from_dicts()` → `await async_sheets.append_values_from_dicts()`
- And every chainable element within `await async_sheets.batch_updater().execute()`...


## Error Handling

The APIs execute via generic capture handling block models, safely retaining execution bounds for failed ranges.

```python
try:
    values = sheets.get_values("invalid_sheet_id", "Sheet1!A1")
except Exception as e:
    # Will fail natively due to Google API permission faults
    pass

# Most boolean endpoints (like mutations) will catch exceptions softly
# and return False if grid properties conflict rather than crashing standard runtimes.
success = sheets.freeze_rows("spreadsheet_id", sheet_id=999, num_rows=1)
if not success:
    print("Could not freeze bounds! Sheet ID may be illegitimate.")
```

## Examples

### Generating Extrapolated Report Ledgers

```python
def serialize_report_ledger(sheets, records_dict, target_spreadsheet_id):
    """Dynamically drops and overrides a sheet tab, placing dict information smoothly"""
    
    # Generate backup duplicate in case of regression
    sheets.duplicate_worksheet(target_spreadsheet_id, 0, "Archived_Backup")
    
    # Force push dictionary mapping array natively
    sheets.clear_values(target_spreadsheet_id, "Report!A:Z")
    
    payload = []
    for uid, stats in records_dict.items():
         payload.append({
             "User ID": uid, 
             "Messages Sent": stats['count'],
             "First Touch": stats['timestamp'],
             "Priority": "High" if stats['count'] > 10 else "Low"
         })
         
    # Commits to grid!
    sheets.append_values_from_dicts(target_spreadsheet_id, "Report!A1", payload)
    
    # Pin Header
    sheets.freeze_rows(target_spreadsheet_id, 0, 1)

```

## API Reference

### SheetsApiService

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `create_spreadsheet()` | Creates spreadsheet | `title: str` | `Spreadsheet` |
| `get_spreadsheet()` | Retreive metadata | `spreadsheet_id: str` | `Spreadsheet` |
| `get_values()` | Reads 2D generic block | `spreadsheet_id: str, range_name: str` | `CellRange` |
| `get_headers()` | Reads row 0 bindings | `spreadsheet_id: str, range_name: str` | `List[str]` |
| `get_values_as_dicts()` | Maps block to dictionaries | `spreadsheet_id: str, range_name: str` | `List[dict]` |
| `find_value()` | Exact cell coordinate search | `spreadsheet_id: str, range: str, search_string: str` | `Optional[Tuple[int, int]]` |
| `update_values()` | Forces array overlay bypass | `spreadsheet_id: str, range_name: str, values: List[List[Any]]` | `bool` |
| `append_values()` | Appends arrays beneath table | `spreadsheet_id: str, range_name: str, values: List[List[Any]]` | `bool` |
| `append_values_from_dicts()` | Intelligently maps Dict arrays | `spreadsheet_id: str, range_name: str, data: List[dict]` | `bool` |
| `add_worksheet()` | Creates new grid | `spreadsheet_id: str, title: str, rows: int = 1000, cols: int = 26` | `Worksheet` |
| `delete_worksheet()` | Deletes grid by ID | `spreadsheet_id: str, sheet_id: int` | `bool` |
| `rename_worksheet()` | Overwrites tab title | `spreadsheet_id: str, sheet_id: int, new_title: str`| `bool` |
| `duplicate_worksheet()` | Clones tab content entirely | `spreadsheet_id: str, source_sheet_id: int, new_title: str` | `bool` |
| `batch_updater()` | Triggers fluent chained API | `spreadsheet_id: str` | `SheetsBatchUpdater` |

### Fluent Batch Updater Nodes (BaseSheetsBatchUpdater)

Every method acts globally via the chain `api_service.sheets.batch_updater(id).[NODE]()`, and must finish with `.execute()`.

| Method | Description | Parameters |
|------|-------------|------------|
| `add_worksheet()` | Queues tab creation | `title: str, sheet_id: Optional[int], rows: int, cols: int` |
| `delete_worksheet()` | Queues tab deletion | `sheet_id: int` |
| `rename_worksheet()` | Queues tab rename | `sheet_id: int, new_title: str` |
| `duplicate_worksheet()`| Queues grid cloning | `source_sheet_id: int, new_title: str` |
| `update_values()` | Pushes local overwrite | `range_name: str, values: List[List[Any]]` |
| `append_values()` | Pushes tabular append | `range_name: str, values: List[List[Any]]` |
| `clear_values()` | Pushes regional wipe | `range_name: str` |
| `format_range()` | Applies stylistic rules | `sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, format: CellFormat` |
| `merge_cells()` | Binds coordinate bounds | `sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, merge_type: str` |
| `unmerge_cells()` | Obliterates bound merges | `sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int` |
| `auto_resize_columns()`| Locks column dimension padding | `sheet_id: int, start_col: int, end_col: int` |
| `insert_rows()` | Spawns literal cell rows padding | `sheet_id: int, start_index: int, num_rows: int` |
| `delete_rows()` | Clears semantic constraints entirely | `sheet_id: int, start_index: int, end_index: int` |
| `freeze_rows()` | Clips header scroll panes | `sheet_id: int, num_rows: int` |
| `sort_range()` | Matrix numerical / alphabetic ordering | `sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, sort_column_index: int, ascending: bool` |
| `add_data_validation()`| Inserts dropdown GUI lists | `sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, dropdown_values: List[str]` |
| `execute()` | Executes REST mutation compilation | None |
