import asyncio
import json
from datetime import datetime, timedelta, timezone

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
# Docs and Sheets tests
# ---------------------------------------------------------------------------

def test_docs_basic():
    doc = api.docs.create_document("[TEST] Basic Doc")
    check("documentId" in doc, "doc creation failed")
    doc_id = doc["documentId"]
    fetched = api.docs.get_document(doc_id)
    check(fetched["title"] == "[TEST] Basic Doc", "fetched title mismatch")
    api.drive.delete(doc_id)

def test_sheets_basic():
    sheet = api.sheets.create_spreadsheet("[TEST] Basic Sheet")
    check(sheet.spreadsheet_id is not None, "sheet creation failed")
    sheet_id = sheet.spreadsheet_id
    fetched = api.sheets.get_spreadsheet(sheet_id)
    check(fetched.title == "[TEST] Basic Sheet", "fetched title mismatch")
    
    values = [["A", "B", "C"], ["1", "2", "3"]]
    api.sheets.update_values(sheet_id, "Sheet1!A1:C2", values)
    cells = api.sheets.get_values(sheet_id, "Sheet1!A1:C2")
    check(len(cells.values) == 2 and cells.values[0][0] == "A", "sheet update_values failed")
    
    api.drive.delete(sheet_id)


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

    return [
        ("async batch_delete_emails",       test_async_batch_delete_emails),
        ("async batch_mark_as_read",        test_async_batch_mark_as_read),
        ("async batch_mark_as_unread",      test_async_batch_mark_as_unread),
        ("async batch_delete_threads",      test_async_batch_delete_threads),
        ("async batch_delete_events",       test_async_batch_delete_events),
        ("async batch_delete_tasks",        test_async_batch_delete_tasks),
        ("async batch_mark_completed",      test_async_batch_mark_completed),
        ("async batch_mark_incomplete",     test_async_batch_mark_incomplete),
        ("async drive batch_get",           test_async_drive_batch_get),
        ("async drive batch_delete",        test_async_drive_batch_delete),
        ("async drive batch_move_to_trash", test_async_drive_batch_move_to_trash),
        ("async drive batch_move",          test_async_drive_batch_move),
        ("async drive batch_copy",          test_async_drive_batch_copy),
        ("async drive batch_share",         test_async_drive_batch_share),
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

    drive_sync_tests = [
        ("drive batch_get",           test_drive_batch_get),
        ("drive batch_delete",        test_drive_batch_delete),
        ("drive batch_move_to_trash", test_drive_batch_move_to_trash),
        ("drive batch_move",          test_drive_batch_move),
        ("drive batch_copy",          test_drive_batch_copy),
        ("drive batch_share",         test_drive_batch_share),
    ]

    # print("\n=== Sync Tests ===")
    # for name, fn in sync_tests:
    #     run_test(name, fn)

    print("\n=== Drive Sync Tests ===")
    for name, fn in drive_sync_tests:
        run_test(name, fn)

    docs_sheets_tests = [
        ("docs basic", test_docs_basic),
        ("sheets basic", test_sheets_basic),
    ]

    print("\n=== Docs & Sheets Tests ===")
    for name, fn in docs_sheets_tests:
        run_test(name, fn)

    print("\n=== Async Tests ===")
    run_async_tests()

    total = passed + failed
    print(f"\n=== Results: {passed}/{total} passed ===\n")
