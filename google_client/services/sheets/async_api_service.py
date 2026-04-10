import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Optional, Tuple

from google.auth.credentials import Credentials
from googleapiclient.discovery import build

from . import utils
from .types import Spreadsheet, CellRange, CellFormat
from .async_batch_updater import AsyncSheetsBatchUpdater


class AsyncSheetsApiService:
    """
    Async service layer for Sheets API operations.
    """

    def __init__(self, credentials: Credentials, timezone: str = 'UTC'):
        self._executor = ThreadPoolExecutor()
        self._credentials = credentials
        self.timezone = timezone

    def __del__(self):
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

    def _service(self):
        return build("sheets", "v4", credentials=self._credentials)

    def batch_updater(self, spreadsheet_id: str) -> AsyncSheetsBatchUpdater:
        """
        Returns an asynchronous builder to chain multiple worksheet and cell formatting requests into a single API call.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet target.
        """
        return AsyncSheetsBatchUpdater(self._service(), self._executor, spreadsheet_id)

    async def create_spreadsheet(self, title: str) -> Spreadsheet:
        """
        Creates a new, blank Google Spreadsheet asynchronously.
        
        Args:
            title: The title string of the new spreadsheet.
        """
        body = {'properties': {'title': title, 'timeZone': self.timezone}}
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().spreadsheets().create(body=body).execute()
        )
        return utils.convert_api_spreadsheet_to_spreadsheet(result)

    async def get_spreadsheet(self, spreadsheet_id: str) -> Spreadsheet:
        """
        Retrieves a specific Google Spreadsheet with its tabs metadata asynchronously.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().spreadsheets().get(
                spreadsheetId=spreadsheet_id, includeGridData=False).execute()
        )
        return utils.convert_api_spreadsheet_to_spreadsheet(result)

    async def get_values(self, spreadsheet_id: str, range_name: str) -> CellRange:
        """
        Retrieves values from a spreadsheet range asynchronously.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: A1 notation target (e.g. "Sheet1!A1:C10").
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
        )
        return CellRange(
            range_name=result.get('range', range_name),
            values=result.get('values', [])
        )

    async def get_headers(self, spreadsheet_id: str, range_name: str) -> List[str]:
        """
        Fetches only the top row of a given A1-notation range asynchronously to understand the schema.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: Target A1-notation block containing headers.
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
        )
        values = result.get('values', [])
        return values[0] if values else []

    async def get_values_as_dicts(self, spreadsheet_id: str, range_name: str) -> List[dict]:
        """
        Reads an A1-notation range asynchronously and automatically maps the first row as dictionary keys for the following rows.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: Target block bounding the headers and payload.
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
        )
        values = result.get('values', [])
        return utils.parse_values_to_dicts(values)

    async def find_value(self, spreadsheet_id: str, range_name: str, search_string: str) -> Optional[Tuple[int, int]]:
        """
        Searches an A1-notation range asynchronously for a specific string and returns its relative (row_index, col_index).
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: Target block searching constraint.
            search_string: The string value to perform matching against.
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
        )
        values = result.get('values', [])
        for r_idx, row in enumerate(values):
            for c_idx, cell in enumerate(row):
                if search_string.lower() in str(cell).lower():
                    return (r_idx, c_idx)
        return None

    async def add_worksheet(self, spreadsheet_id: str, title: str, rows: int = 1000, cols: int = 26) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).add_worksheet(title, None, rows, cols).execute()
            return True
        except Exception:
            return False

    async def delete_worksheet(self, spreadsheet_id: str, sheet_id: int) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).delete_worksheet(sheet_id).execute()
            return True
        except Exception:
            return False

    async def rename_worksheet(self, spreadsheet_id: str, sheet_id: int, new_title: str) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).rename_worksheet(sheet_id, new_title).execute()
            return True
        except Exception:
            return False

    async def update_values(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).update_values(range_name, values).execute()
            return True
        except Exception:
            return False

    async def append_values(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).append_values(range_name, values).execute()
            return True
        except Exception:
            return False

    async def clear_values(self, spreadsheet_id: str, range_name: str) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).clear_values(range_name).execute()
            return True
        except Exception:
            return False

    async def append_values_from_dicts(self, spreadsheet_id: str, range_name: str, data: List[dict]) -> bool:
        """
        Appends data asynchronously by mapping a list of dicts to the sheet's existing headers.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: A1-notation logic pointing to the start of the table block.
            data: List of key-value payloads to append.
        """
        if not data:
            return True
        headers = await self.get_headers(spreadsheet_id, range_name)
        if not headers:
            headers = list(data[0].keys())
            write_headers = True
        else:
            write_headers = False
        rows_to_write = []
        if write_headers:
            rows_to_write.append(headers)
        for row_dict in data:
            row = []
            for h in headers:
                row.append(row_dict.get(h, ""))
            rows_to_write.append(row)
        try:
            await self.batch_updater(spreadsheet_id).append_values(range_name, rows_to_write).execute()
            return True
        except Exception:
            return False

    async def format_range(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, cell_format: CellFormat) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).format_range(sheet_id, start_row, end_row, start_col, end_col, cell_format).execute()
            return True
        except Exception:
            return False

    async def merge_cells(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, merge_type: str = "MERGE_ALL") -> bool:
        try:
            await self.batch_updater(spreadsheet_id).merge_cells(sheet_id, start_row, end_row, start_col, end_col, merge_type).execute()
            return True
        except Exception:
            return False

    async def unmerge_cells(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).unmerge_cells(sheet_id, start_row, end_row, start_col, end_col).execute()
            return True
        except Exception:
            return False

    async def auto_resize_columns(self, spreadsheet_id: str, sheet_id: int, start_col: int, end_col: int) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).auto_resize_columns(sheet_id, start_col, end_col).execute()
            return True
        except Exception:
            return False

    async def insert_rows(self, spreadsheet_id: str, sheet_id: int, start_index: int, num_rows: int) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).insert_rows(sheet_id, start_index, num_rows).execute()
            return True
        except Exception:
            return False

    async def delete_rows(self, spreadsheet_id: str, sheet_id: int, start_index: int, end_index: int) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).delete_rows(sheet_id, start_index, end_index).execute()
            return True
        except Exception:
            return False

    async def sort_range(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, sort_column_index: int, ascending: bool = True) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).sort_range(sheet_id, start_row, end_row, start_col, end_col, sort_column_index, ascending).execute()
            return True
        except Exception:
            return False

    async def freeze_rows(self, spreadsheet_id: str, sheet_id: int, num_rows: int) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).freeze_rows(sheet_id, num_rows).execute()
            return True
        except Exception:
            return False

    async def add_data_validation(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, dropdown_values: List[str]) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).add_data_validation(sheet_id, start_row, end_row, start_col, end_col, dropdown_values).execute()
            return True
        except Exception:
            return False

    async def duplicate_worksheet(self, spreadsheet_id: str, source_sheet_id: int, new_title: str) -> bool:
        try:
            await self.batch_updater(spreadsheet_id).duplicate_worksheet(source_sheet_id, new_title).execute()
            return True
        except Exception:
            return False

    async def batch_update(self, spreadsheet_id: str, requests: List[dict]) -> dict:
        """
        Executes a custom batchUpdate for complex requests not directly covered by the wrappers asynchronously.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            requests: JSON dictionary payload arrays.
        """
        body = {'requests': requests}
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self._service().spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body).execute()
        )
