import asyncio
import json
from datetime import datetime, timedelta
from time import sleep

from google_client.api_service import APIServiceLayer

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

with open("user_token.json") as f:
    user_info = json.load(f)

api = APIServiceLayer(user_info, timezone="UTC")

gmail = api.gmail
calendar = api.calendar
tasks = api.tasks
drive = api.drive
async_gmail = api.async_gmail
async_calendar = api.async_calendar
async_tasks = api.async_tasks
async_drive = api.async_drive
sheets = api.sheets
async_sheets = api.async_sheets
docs = api.docs
async_docs = api.async_docs

# Set to a real Google account email for batch_share tests
TEST_SHARE_EMAIL = "devpyagent@gmail.com"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def check(condition, msg="assertion failed"):
    if not condition:
        raise AssertionError(msg)


def run_test(name, fn):
    global passed, failed
    label = f"  Testing {name}..."
    print(label, end="", flush=True)
    try:
        fn()
        pad = max(1, 60 - len(label))
        print(" " * pad + "PASS")
        passed += 1
    except Exception as e:
        pad = max(1, 60 - len(label))
        print(" " * pad + f"FAIL: {e}")
        failed += 1
        raise e


def make_test_events(n=3):
    tomorrow = datetime.now().replace(
        hour=9, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)
    return [
        {
            "summary": f"[TEST] Batch Event {i + 1}",
            "start": tomorrow + timedelta(hours=i),
            "end": tomorrow + timedelta(hours=i + 1),
        }
        for i in range(n)
    ]


def make_test_tasks(prefix, n=3):
    return [{"title": f"[TEST] {prefix} {i + 1}"} for i in range(n)]


def make_test_files(drive_svc, prefix, n=3):
    return [
        drive_svc.upload_file_content(
            f"test content {i + 1}".encode(), name=f"[TEST] {prefix} {i + 1}", mime_type="text/plain"
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------

def test_batch_delete_emails():
    drafts = [
        gmail.create_draft(to=["test@example.com"], subject=f"[TEST] Draft {i + 1}")
        for i in range(3)
    ]
    message_ids = [d.message_id for d in drafts]

    results = gmail.batch_delete_emails(message_ids, permanent=False)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(r is True for r in results), f"unexpected errors: {results}")

    # purge from trash
    gmail.batch_delete_emails(message_ids, permanent=True)


def test_batch_mark_as_read():
    ids = gmail.list_emails(label_ids=["INBOX"], max_results=3)
    check(len(ids) >= 3, "need at least 3 INBOX emails")
    ids = ids[:3]

    gmail.batch_mark_as_unread(ids)  # ensure unread first

    results = gmail.batch_mark_as_read(ids)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(r is True for r in results), f"unexpected errors: {results}")

    emails = [gmail.get_email(mid) for mid in ids]
    check(all(e.is_read for e in emails), "not all emails are marked read")


def test_batch_mark_as_unread():
    ids = gmail.list_emails(label_ids=["INBOX"], max_results=3)
    check(len(ids) >= 3, "need at least 3 INBOX emails")
    ids = ids[:3]

    gmail.batch_mark_as_read(ids)  # ensure read first

    results = gmail.batch_mark_as_unread(ids)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(r is True for r in results), f"unexpected errors: {results}")

    emails = [gmail.get_email(mid) for mid in ids]
    check(all(not e.is_read for e in emails), "not all emails are marked unread")

    # restore
    gmail.batch_mark_as_read(ids)


def test_batch_delete_threads():
    drafts = [
        gmail.create_draft(to=["test@example.com"], subject=f"[TEST] Thread {i + 1}")
        for i in range(3)
    ]
    thread_ids = [d.thread_id for d in drafts]

    results = gmail.batch_delete_threads(thread_ids, permanent=False)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(r is True for r in results), f"unexpected errors: {results}")

    # purge from trash
    for tid in thread_ids:
        gmail.delete_thread(tid, permanent=True)


def test_batch_delete_events():
    created = calendar.batch_create_events(make_test_events(3))
    check(
        all(not isinstance(e, tuple) for e in created),
        f"event creation errors: {[e for e in created if isinstance(e, tuple)]}",
    )
    event_ids = [e.event_id for e in created]

    results = calendar.batch_delete_events(event_ids)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(r is True for r in results), f"unexpected errors: {results}")


def test_batch_delete_tasks():
    created = tasks.batch_create_tasks(make_test_tasks("Delete Me"))
    check(
        all(not isinstance(t, tuple) for t in created),
        f"task creation errors: {[t for t in created if isinstance(t, tuple)]}",
    )
    task_ids = [t.task_id for t in created]

    results = tasks.batch_delete_tasks(task_ids)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(r is True for r in results), f"unexpected errors: {results}")


def test_batch_mark_completed():
    created = tasks.batch_create_tasks(make_test_tasks("Complete Me"))
    check(
        all(not isinstance(t, tuple) for t in created),
        f"task creation errors: {[t for t in created if isinstance(t, tuple)]}",
    )

    results = tasks.batch_mark_completed(created)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(
        all(not isinstance(r, tuple) for r in results),
        f"unexpected errors: {[r for r in results if isinstance(r, tuple)]}",
    )
    check(
        all(r.status == "completed" for r in results),
        f"not all tasks marked completed: {[r.status for r in results]}",
    )

    tasks.batch_delete_tasks([r.task_id for r in results])


def test_batch_mark_incomplete():
    created = tasks.batch_create_tasks(make_test_tasks("Incomplete Me"))
    check(all(not isinstance(t, tuple) for t in created))
    completed = tasks.batch_mark_completed(created)
    check(all(not isinstance(t, tuple) for t in completed))

    results = tasks.batch_mark_incomplete([t.task_id for t in completed])
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(
        all(not isinstance(r, tuple) for r in results),
        f"unexpected errors: {[r for r in results if isinstance(r, tuple)]}",
    )
    check(
        all(r.status == "needsAction" for r in results),
        f"not all tasks marked incomplete: {[r.status for r in results]}",
    )

    tasks.batch_delete_tasks([r.task_id for r in results])


def test_drive_batch_get():
    files = make_test_files(drive, "Get")
    item_ids = [f.item_id for f in files]

    results = drive.batch_get(item_ids)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
    check(all(r.name.startswith("[TEST]") for r in results), "unexpected items returned")

    drive.batch_delete(item_ids)


def test_drive_batch_delete():
    files = make_test_files(drive, "Delete")
    item_ids = [f.item_id for f in files]

    results = drive.batch_delete(item_ids)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(r is True for r in results), f"unexpected errors: {results}")


def test_drive_batch_move_to_trash():
    files = make_test_files(drive, "Trash")

    results = drive.batch_move_to_trash(files)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
    check(all(r.trashed for r in results), "not all items moved to trash")

    drive.batch_delete([r.item_id for r in results])


def test_drive_batch_move():
    files = make_test_files(drive, "Move")
    target = drive.create_folder("[TEST] Move Target")

    results = drive.batch_move(files, target)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
    check(
        all(target.folder_id in r.parent_ids for r in results),
        "not all items moved to target folder",
    )

    drive.batch_delete([r.item_id for r in results])
    drive.delete(target)


def test_drive_batch_copy():
    files = make_test_files(drive, "Copy")
    dest = drive.create_folder("[TEST] Copy Dest")

    results = drive.batch_copy(files, dest)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
    check(
        all(dest.folder_id in r.parent_ids for r in results),
        "copies not placed in destination folder",
    )

    drive.batch_delete([f.item_id for f in files])
    drive.batch_delete([r.item_id for r in results])
    drive.delete(dest)


def test_drive_batch_share():
    files = make_test_files(drive, "Share")

    results = drive.batch_share(files, email=TEST_SHARE_EMAIL, role="reader", notify=False)
    check(len(results) == 3, f"expected 3 results, got {len(results)}")
    check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
    check(all(r.role == "reader" for r in results), "not all permissions are reader")
    check(
        all(r.email_address == TEST_SHARE_EMAIL for r in results),
        "email address mismatch on permissions",
    )

    drive.batch_delete([f.item_id for f in files])


# ---------------------------------------------------------------------------
# Sheets tests
# ---------------------------------------------------------------------------

def test_sheets_worksheets():
    sp = sheets.create_spreadsheet("Test Worksheets")
    ws = sheets.add_worksheet(sp.spreadsheet_id, "New Tab", 10, 10)
    check(ws.title == "New Tab")

    sheets.rename_worksheet(sp.spreadsheet_id, ws.sheet_id, "Renamed Tab")
    sp_updated = sheets.get_spreadsheet(sp.spreadsheet_id)
    check(any(w.title == "Renamed Tab" for w in sp_updated.worksheets))

    sheets.delete_worksheet(sp.spreadsheet_id, ws.sheet_id)
    sp_deleted = sheets.get_spreadsheet(sp.spreadsheet_id)
    check(not any(w.title == "Renamed Tab" for w in sp_deleted.worksheets))


def test_sheets_values():
    sp = sheets.create_spreadsheet("Test Values")
    # update A1:B2
    sheets.update_values(sp.spreadsheet_id, "Sheet1!A1", [["A", "B"], ["C", "D"]])
    val = sheets.get_values(sp.spreadsheet_id, "Sheet1!A1:B2")
    check(val.values == [["A", "B"], ["C", "D"]])

    # append
    sheets.append_values(sp.spreadsheet_id, "Sheet1!A1:B2", [["E", "F"]])
    val_append = sheets.get_values(sp.spreadsheet_id, "Sheet1!A1:B3")
    check(len(val_append.values) == 3)

    # clear
    sheets.clear_values(sp.spreadsheet_id, "Sheet1!A1:B3")
    val_cleared = sheets.get_values(sp.spreadsheet_id, "Sheet1!A1:B3")
    check(not val_cleared.values)


def test_sheets_formatting():
    from google_client.services.sheets.types import CellFormat, CellBorders, Border, BorderStyle
    sp = sheets.create_spreadsheet("Test Formatting")
    sheet_id = sp.worksheets[0].sheet_id

    fmt = CellFormat(
        bold=True,
        text_color_hex="#ff0000",
        borders=CellBorders(
            bottom=Border(style=BorderStyle.SOLID_THICK, color_hex="#000000")
        )
    )
    sheets.format_range(sp.spreadsheet_id, sheet_id, 0, 1, 0, 1, fmt)

    # merge and unmerge
    sheets.merge_cells(sp.spreadsheet_id, sheet_id, 0, 2, 0, 2)
    sheets.unmerge_cells(sp.spreadsheet_id, sheet_id, 0, 2, 0, 2)

    # auto resize
    sheets.auto_resize_columns(sp.spreadsheet_id, sheet_id, 0, 2)


def test_sheets_ai_agent_operations():
    sp = sheets.create_spreadsheet("Test AI Agent")
    # write dicts
    data = [
        {"Name": "Alice", "Age": "30", "Role": "Engineer"},
        {"Name": "Bob", "Age": "25", "Role": "Designer"},
    ]
    sheets.append_values_from_dicts(sp.spreadsheet_id, "Sheet1!A1", data)

    # read headers
    headers = sheets.get_headers(sp.spreadsheet_id, "Sheet1!A1:C1")
    check(headers == ["Name", "Age", "Role"], "Headers mapping failed")

    # read dicts
    read_data = sheets.get_values_as_dicts(sp.spreadsheet_id, "Sheet1!A1:C3")
    check(len(read_data) == 2, "Dicts mapping failed")
    check(read_data[0]["Name"] == "Alice", "Data integrity lost")

    # find value
    pos = sheets.find_value(sp.spreadsheet_id, "Sheet1!A1:C3", "Bob")
    check(pos is not None, "Value not found")
    check(pos[0] == 2, "Incorrect row index")  # A1=headers, A2=Alice, A3=Bob


def test_sheets_structural_mutations():
    sp = sheets.create_spreadsheet("Test Mutations")
    sheet_id = sp.worksheets[0].sheet_id

    updater = sheets.batch_updater(sp.spreadsheet_id)
    updater.insert_rows(sheet_id, 1, 2)
    updater.delete_rows(sheet_id, 1, 2)
    updater.freeze_rows(sheet_id, 1)
    updater.add_data_validation(sheet_id, 0, 10, 0, 1, ["Yes", "No"])
    updater.sort_range(sheet_id, 0, 10, 0, 5, 0, ascending=True)
    updater.duplicate_worksheet(sheet_id, "Cloned Tab")
    updater.execute()


def test_sheets_batch_updater():
    from google_client.services.sheets.types import CellFormat
    sp = sheets.create_spreadsheet("Test Batch")

    updater = sheets.batch_updater(sp.spreadsheet_id)
    updater.add_worksheet("Batch Tab", sheet_id=999)
    updater.update_values("Batch Tab!A1", [["1", "2"], ["3", "4"]])
    updater.format_range(999, 0, 2, 0, 2, CellFormat(bold=True))
    updater.append_values("Batch Tab!A1:B2", [["5", "6"]])
    updater.execute()

    # Verify the results via getters
    sp_updated = sheets.get_spreadsheet(sp.spreadsheet_id)
    check(any(w.title == "Batch Tab" for w in sp_updated.worksheets), "Worksheet was not added")

    val = sheets.get_values(sp.spreadsheet_id, "Batch Tab!A1:B3")
    check(len(val.values) == 3, f"Expected 3 rows, got {len(val.values) if val.values else 0}")
    check(val.values[0] == ["1", "2"], "Initial updated values lost")
    check(val.values[2] == ["5", "6"], "Appended values missing")


# ---------------------------------------------------------------------------
# Docs tests
# ---------------------------------------------------------------------------

def test_docs_basic():
    doc = docs.create_document("Test Basic Doc")
    check(doc.title == "Test Basic Doc", "Title mismatch")
    fetched = docs.get_document(doc.document_id)
    check(fetched.document_id == doc.document_id, "ID mismatch")


def test_docs_formatting_and_reading():
    doc = docs.create_document("Test Formatting Doc")
    doc_id = doc.document_id

    # Test insertions
    docs.insert_text(doc_id, "Hello World!\n", index=1)
    docs.insert_table(doc_id, rows=2, columns=2, index=14)
    docs.replace_all_text(doc_id, "World", "Universe")

    # Test formatting
    docs.update_text_style(doc_id, start_index=1, end_index=6, bold=True, italic=True)
    docs.update_paragraph_alignment(doc_id, start_index=1, end_index=6, alignment="CENTER")
    docs.update_heading_style(doc_id, start_index=1, end_index=6, heading_id="HEADING_1")
    docs.insert_page_break(doc_id, index=15)

    # Test reading
    extracted_text = docs.get_document_text(doc_id)
    check("Hello Universe" in extracted_text, "Inserted and replaced text not found in extracted text")


def test_docs_advanced():
    doc = docs.create_document("Test Advanced Doc")
    doc_id = doc.document_id

    # Test Table helper
    data = [["Col1", "Col2"], ["Val1", "https://example.com"]]
    docs.insert_table_with_data(doc_id, index=1, data=data)

    text = docs.get_document_text(doc_id)
    check("Val1" in text, "Table text missing")

    # Test delete text
    docs.insert_text(doc_id, "DELETE ME", index=1)
    docs.delete_text(doc_id, start_index=1, end_index=10)
    updated_text = docs.get_document_text(doc_id)
    check("DELETE ME" not in updated_text, "Failed to delete text")

    # Test links extraction
    links = docs.get_document_links(doc_id)
    check(isinstance(links, list), "Links extraction failed to return list")


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------

async def _run_async_tests():
    # --- batch_delete_emails ---
    async def test_async_batch_delete_emails():
        drafts = [
            await async_gmail.create_draft(
                to=["test@example.com"], subject=f"[TEST] Async Draft {i + 1}"
            )
            for i in range(3)
        ]
        message_ids = [d.message_id for d in drafts]
        results = await async_gmail.batch_delete_emails(message_ids, permanent=False)
        check(len(results) == 3)
        check(all(r is True for r in results), f"unexpected errors: {results}")
        await async_gmail.batch_delete_emails(message_ids, permanent=True)

    # --- batch_mark_as_read ---
    async def test_async_batch_mark_as_read():
        ids = await async_gmail.list_emails(label_ids=["INBOX"], max_results=3)
        check(len(ids) >= 3, "need at least 3 INBOX emails")
        ids = ids[:3]
        await async_gmail.batch_mark_as_unread(ids)
        results = await async_gmail.batch_mark_as_read(ids)
        check(len(results) == 3)
        check(all(r is True for r in results), f"unexpected errors: {results}")
        emails = [await async_gmail.get_email(mid) for mid in ids]
        check(all(e.is_read for e in emails), "not all emails are marked read")

    # --- batch_mark_as_unread ---
    async def test_async_batch_mark_as_unread():
        ids = await async_gmail.list_emails(label_ids=["INBOX"], max_results=3)
        check(len(ids) >= 3, "need at least 3 INBOX emails")
        ids = ids[:3]
        await async_gmail.batch_mark_as_read(ids)
        results = await async_gmail.batch_mark_as_unread(ids)
        check(len(results) == 3)
        check(all(r is True for r in results), f"unexpected errors: {results}")
        emails = [await async_gmail.get_email(mid) for mid in ids]
        check(all(not e.is_read for e in emails), "not all emails are marked unread")
        await async_gmail.batch_mark_as_read(ids)

    # --- batch_delete_threads ---
    async def test_async_batch_delete_threads():
        drafts = [
            await async_gmail.create_draft(
                to=["test@example.com"], subject=f"[TEST] Async Thread {i + 1}"
            )
            for i in range(3)
        ]
        thread_ids = [d.thread_id for d in drafts]
        results = await async_gmail.batch_delete_threads(thread_ids, permanent=False)
        check(len(results) == 3)
        check(all(r is True for r in results), f"unexpected errors: {results}")
        for tid in thread_ids:
            await async_gmail.delete_thread(tid, permanent=True)

    # --- batch_delete_events ---
    async def test_async_batch_delete_events():
        created = await async_calendar.batch_create_events(make_test_events(3))
        check(all(not isinstance(e, tuple) for e in created))
        event_ids = [e.event_id for e in created]
        results = await async_calendar.batch_delete_events(event_ids)
        check(len(results) == 3)
        check(all(r is True for r in results), f"unexpected errors: {results}")

    # --- batch_delete_tasks ---
    async def test_async_batch_delete_tasks():
        created = await async_tasks.batch_create_tasks(make_test_tasks("Async Delete Me"))
        check(all(not isinstance(t, tuple) for t in created))
        task_ids = [t.task_id for t in created]
        results = await async_tasks.batch_delete_tasks(task_ids)
        check(len(results) == 3)
        check(all(r is True for r in results), f"unexpected errors: {results}")

    # --- batch_mark_completed ---
    async def test_async_batch_mark_completed():
        created = await async_tasks.batch_create_tasks(make_test_tasks("Async Complete Me"))
        check(all(not isinstance(t, tuple) for t in created))
        results = await async_tasks.batch_mark_completed(created)
        check(len(results) == 3)
        check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
        check(all(r.status == "completed" for r in results))
        await async_tasks.batch_delete_tasks([r.task_id for r in results])

    # --- batch_mark_incomplete ---
    async def test_async_batch_mark_incomplete():
        created = await async_tasks.batch_create_tasks(make_test_tasks("Async Incomplete Me"))
        check(all(not isinstance(t, tuple) for t in created))
        completed = await async_tasks.batch_mark_completed(created)
        check(all(not isinstance(t, tuple) for t in completed))
        results = await async_tasks.batch_mark_incomplete([t.task_id for t in completed])
        check(len(results) == 3)
        check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
        check(all(r.status == "needsAction" for r in results))
        await async_tasks.batch_delete_tasks([r.task_id for r in results])

    # --- drive batch_get ---
    async def test_async_drive_batch_get():
        files = [
            await async_drive.upload_file_content(
                f"test content {i + 1}".encode(), name=f"[TEST] Async Get {i + 1}", mime_type="text/plain"
            )
            for i in range(3)
        ]
        item_ids = [f.item_id for f in files]
        results = await async_drive.batch_get(item_ids)
        check(len(results) == 3, f"expected 3 results, got {len(results)}")
        check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
        check(all(r.name.startswith("[TEST]") for r in results), "unexpected items returned")
        await async_drive.batch_delete(item_ids)

    # --- drive batch_delete ---
    async def test_async_drive_batch_delete():
        files = [
            await async_drive.upload_file_content(
                f"test content {i + 1}".encode(), name=f"[TEST] Async Delete {i + 1}", mime_type="text/plain"
            )
            for i in range(3)
        ]
        item_ids = [f.item_id for f in files]
        results = await async_drive.batch_delete(item_ids)
        check(len(results) == 3, f"expected 3 results, got {len(results)}")
        check(all(r is True for r in results), f"unexpected errors: {results}")

    # --- drive batch_move_to_trash ---
    async def test_async_drive_batch_move_to_trash():
        files = [
            await async_drive.upload_file_content(
                f"test content {i + 1}".encode(), name=f"[TEST] Async Trash {i + 1}", mime_type="text/plain"
            )
            for i in range(3)
        ]
        results = await async_drive.batch_move_to_trash(files)
        check(len(results) == 3, f"expected 3 results, got {len(results)}")
        check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
        check(all(r.trashed for r in results), "not all items moved to trash")
        await async_drive.batch_delete([r.item_id for r in results])

    # --- drive batch_move ---
    async def test_async_drive_batch_move():
        files = [
            await async_drive.upload_file_content(
                f"test content {i + 1}".encode(), name=f"[TEST] Async Move {i + 1}", mime_type="text/plain"
            )
            for i in range(3)
        ]
        target = await async_drive.create_folder("[TEST] Async Move Target")
        results = await async_drive.batch_move(files, target)
        check(len(results) == 3, f"expected 3 results, got {len(results)}")
        check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
        check(
            all(target.folder_id in r.parent_ids for r in results),
            "not all items moved to target folder",
        )
        await async_drive.batch_delete([r.item_id for r in results])
        await async_drive.delete(target)

    # --- drive batch_copy ---
    async def test_async_drive_batch_copy():
        files = [
            await async_drive.upload_file_content(
                f"test content {i + 1}".encode(), name=f"[TEST] Async Copy {i + 1}", mime_type="text/plain"
            )
            for i in range(3)
        ]
        dest = await async_drive.create_folder("[TEST] Async Copy Dest")
        results = await async_drive.batch_copy(files, dest)
        check(len(results) == 3, f"expected 3 results, got {len(results)}")
        check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
        check(
            all(dest.folder_id in r.parent_ids for r in results),
            "copies not placed in destination folder",
        )

        await async_drive.batch_delete([f.item_id for f in files])
        await async_drive.batch_delete([r.item_id for r in results])
        await async_drive.delete(dest)

    # --- drive batch_share ---
    async def test_async_drive_batch_share():
        files = [
            await async_drive.upload_file_content(
                f"test content {i + 1}".encode(), name=f"[TEST] Async Share {i + 1}", mime_type="text/plain"
            )
            for i in range(3)
        ]
        results = await async_drive.batch_share(files, email=TEST_SHARE_EMAIL, role="reader", notify=False)
        check(len(results) == 3, f"expected 3 results, got {len(results)}")
        check(all(not isinstance(r, tuple) for r in results), f"errors: {results}")
        check(all(r.role == "reader" for r in results), "not all permissions are reader")
        check(
            all(r.email_address == TEST_SHARE_EMAIL for r in results),
            "email address mismatch on permissions",
        )
        await async_drive.batch_delete([f.item_id for f in files])

    # --- async sheets operations ---
    async def test_async_sheets_operations():
        sp = await async_sheets.create_spreadsheet("Async Test Spreadsheet")

        await async_sheets.add_worksheet(sp.spreadsheet_id, "Async Tab", 10, 10)

        data = [{"Name": "Async Alice"}, {"Name": "Async Bob"}]
        await async_sheets.append_values_from_dicts(sp.spreadsheet_id, "Async Tab!A1", data)

        updater = async_sheets.batch_updater(sp.spreadsheet_id)
        updater.insert_rows(0, 1, 1)
        await updater.execute()

        headers = await async_sheets.get_headers(sp.spreadsheet_id, "Async Tab!A1:A")
        check(len(headers) > 0, "Async headers not found")

    # --- async docs operations ---
    async def test_async_docs_operations():
        doc = await async_docs.create_document("Async Test Docs")
        doc_id = doc.document_id
        await async_docs.insert_text(doc_id, "Async Docs Content\n", 1)
        await async_docs.delete_text(doc_id, start_index=1, end_index=20)

        await async_docs.insert_table_with_data(doc_id, index=1, data=[["A", "B"], ["C", "D"]])
        extracted_text = await async_docs.get_document_text(doc_id)
        check("C" in extracted_text, "Async extracted text mismatch")

        links = await async_docs.get_document_links(doc_id)
        check(isinstance(links, list), "Links extraction list validation failed")

    return [
        # ("async batch_delete_emails",       test_async_batch_delete_emails),
        # ("async batch_mark_as_read",        test_async_batch_mark_as_read),
        # ("async batch_mark_as_unread",      test_async_batch_mark_as_unread),
        # ("async batch_delete_threads",      test_async_batch_delete_threads),
        # ("async batch_delete_events",       test_async_batch_delete_events),
        # ("async batch_delete_tasks",        test_async_batch_delete_tasks),
        # ("async batch_mark_completed",      test_async_batch_mark_completed),
        # ("async batch_mark_incomplete",     test_async_batch_mark_incomplete),
        # ("async drive batch_get",           test_async_drive_batch_get),
        # ("async drive batch_delete",        test_async_drive_batch_delete),
        # ("async drive batch_move_to_trash", test_async_drive_batch_move_to_trash),
        # ("async drive batch_move",          test_async_drive_batch_move),
        # ("async drive batch_copy",          test_async_drive_batch_copy),
        # ("async drive batch_share",         test_async_drive_batch_share),
        ("async sheets operations", test_async_sheets_operations),
        ("async docs operations", test_async_docs_operations),
    ]


def run_async_tests():
    async def _run():
        tests = await _run_async_tests()
        for name, fn in tests:
            await _run_single_async(name, fn)

    async def _run_single_async(name, fn):
        global passed, failed
        label = f"  Testing {name}..."
        print(label, end="", flush=True)
        try:
            await fn()
            pad = max(1, 60 - len(label))
            print(" " * pad + "PASS")
            passed += 1
        except Exception as e:
            pad = max(1, 60 - len(label))
            print(" " * pad + f"FAIL: {e}")
            failed += 1

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # sync_tests = [
    #     ("batch_delete_emails",   test_batch_delete_emails),
    #     ("batch_mark_as_read",    test_batch_mark_as_read),
    #     ("batch_mark_as_unread",  test_batch_mark_as_unread),
    #     ("batch_delete_threads",  test_batch_delete_threads),
    #     ("batch_delete_events",   test_batch_delete_events),
    #     ("batch_delete_tasks",    test_batch_delete_tasks),
    #     ("batch_mark_completed",  test_batch_mark_completed),
    #     ("batch_mark_incomplete", test_batch_mark_incomplete),
    # ]

    # drive_sync_tests = [
    #     ("drive batch_get",           test_drive_batch_get),
    #     ("drive batch_delete",        test_drive_batch_delete),
    #     ("drive batch_move_to_trash", test_drive_batch_move_to_trash),
    #     ("drive batch_move",          test_drive_batch_move),
    #     ("drive batch_copy",          test_drive_batch_copy),
    #     ("drive batch_share",         test_drive_batch_share),
    # ]

    # print("\n=== Sync Tests ===")
    # for name, fn in sync_tests:
    #     run_test(name, fn)

    # print("\n=== Drive Sync Tests ===")
    # for name, fn in drive_sync_tests:
    #     run_test(name, fn)

    sheets_tests = [
        ("sheets worksheets", test_sheets_worksheets),
        ("sheets values", test_sheets_values),
        ("sheets formatting", test_sheets_formatting),
        ("sheets AI agent ops", test_sheets_ai_agent_operations),
        ("sheets structure muts", test_sheets_structural_mutations),
        ("sheets batch_updater", test_sheets_batch_updater),
    ]

    print("\n=== Sheets Tests ===")
    for name, fn in sheets_tests:
        run_test(name, fn)

    docs_tests = [
        ("docs basic", test_docs_basic),
        ("docs formatting/reading", test_docs_formatting_and_reading),
        ("docs advanced (tables/delete)", test_docs_advanced),
    ]

    print("\n=== Docs Tests ===")
    for name, fn in docs_tests:
        run_test(name, fn)

    print("\n=== Async Tests ===")
    run_async_tests()

    total = passed + failed
    print(f"\n=== Results: {passed}/{total} passed ===\n")

# from google_client.api_service import APIServiceLayer
# import json
#
# token = open("user_token.json", "r")
# token = json.load(token)
#
# api_service = APIServiceLayer(token, 'America/New_York')
