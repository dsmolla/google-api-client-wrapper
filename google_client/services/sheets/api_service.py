from typing import Any, List, Optional, Tuple

from google.auth.credentials import Credentials
from googleapiclient.discovery import build

from .types import Spreadsheet, Worksheet, CellRange, CellFormat
from .batch_updater import SheetsBatchUpdater
from . import utils


class SheetsApiService:
    """
    Service layer for Google Sheets API operations.
    """

    def __init__(self, credentials: Credentials, timezone: str):
        self._service = build("sheets", "v4", credentials=credentials)
        self._timezone = timezone



    def create_spreadsheet(self, title: str) -> Spreadsheet:
        """
        Creates a new, blank Google Spreadsheet.
        
        Args:
            title: The title string of the new spreadsheet.
        """
        spreadsheet = {
            'properties': {
                'title': title,
                'timeZone': self._timezone
            }
        }
        result = self._service.spreadsheets().create(body=spreadsheet).execute()
        return utils.convert_api_spreadsheet_to_spreadsheet(result)

    def get_spreadsheet(self, spreadsheet_id: str) -> Spreadsheet:
        """
        Retrieves a specific Google Spreadsheet with its tabs metadata.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
        """
        result = self._service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        return utils.convert_api_spreadsheet_to_spreadsheet(result)

    def add_worksheet(self, spreadsheet_id: str, title: str, rows: int = 1000, cols: int = 26) -> Worksheet:
        """
        Adds a new worksheet to the spreadsheet.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            title: The name of the new tab.
            rows: The total starting row capacity.
            cols: The total starting column capacity.
        """
        response = self.batch_updater(spreadsheet_id).add_worksheet(title, None, rows, cols).execute()
        reply = response.get('replies', [])[0].get('addSheet', {}).get('properties', {})
        grid = reply.get('gridProperties', {})
        
        return Worksheet(
            sheet_id=reply.get('sheetId', 0),
            title=reply.get('title', ''),
            index=reply.get('index', 0),
            row_count=grid.get('rowCount', 0),
            column_count=grid.get('columnCount', 0),
            hidden=reply.get('hidden', False)
        )

    def delete_worksheet(self, spreadsheet_id: str, sheet_id: int) -> bool:
        """
        Deletes a worksheet by its internal sheet ID.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            sheet_id: The integer ID of the specific worksheet tab (0 is typically the first tab).
        """
        try:
            self.batch_updater(spreadsheet_id).delete_worksheet(sheet_id).execute()
            return True
        except Exception:
            return False

    def rename_worksheet(self, spreadsheet_id: str, sheet_id: int, new_title: str) -> bool:
        """
        Renames an existing worksheet.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            sheet_id: The integer ID of the specific worksheet tab.
            new_title: The new name of the tab.
        """
        try:
            self.batch_updater(spreadsheet_id).rename_worksheet(sheet_id, new_title).execute()
            return True
        except Exception:
            return False

    def get_values(self, spreadsheet_id: str, range_name: str) -> CellRange:
        """
        Retrieves values from a spreadsheet range.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: A1 notation target (e.g. "Sheet1!A1:C10").
        """
        result = self._service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        return CellRange(
            range_name=result.get("range", range_name),
            values=result.get('values', [])
        )

    def update_values(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> bool:
        """
        Sets values in a spreadsheet range.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: A1 notation target (e.g. "Sheet1!A1:C10").
            values: A 2D list matrix representing the grid values.
        """
        try:
            self.batch_updater(spreadsheet_id).update_values(range_name, values).execute()
            return True
        except Exception:
            return False

    def append_values(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> bool:
        """
        Appends values to a spreadsheet logical table.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: A1 notation targeting the table or boundary (e.g. "Sheet1!A1").
            values: A 2D list matrix to append at the bottom of the existing table logic.
        """
        try:
            self.batch_updater(spreadsheet_id).append_values(range_name, values).execute()
            return True
        except Exception:
            return False

    def clear_values(self, spreadsheet_id: str, range_name: str) -> bool:
        """
        Clears values from a given range.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: A1 notation target (e.g. "Sheet1!A1:C10").
        """
        try:
            self.batch_updater(spreadsheet_id).clear_values(range_name).execute()
            return True
        except Exception:
            return False

    def format_range(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, format: CellFormat) -> bool:
        """
        Applies a CellFormat object to a block.
        
        Args:
            spreadsheet_id: The unique string identifier.
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
            format: The predefined format struct to apply.
        """
        try:
            self.batch_updater(spreadsheet_id).format_range(sheet_id, start_row, end_row, start_col, end_col, format).execute()
            return True
        except Exception:
            return False

    def merge_cells(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, merge_type: str = "MERGE_ALL") -> bool:
        """
        Merge cells within the specified range.
        
        Args:
            spreadsheet_id: The unique string identifier.
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
            merge_type: "MERGE_ALL", "MERGE_COLUMNS", or "MERGE_ROWS".
        """
        try:
            self.batch_updater(spreadsheet_id).merge_cells(sheet_id, start_row, end_row, start_col, end_col, merge_type).execute()
            return True
        except Exception:
            return False

    def unmerge_cells(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int) -> bool:
        """
        Unmerges all cells in the specified range.
        
        Args:
            spreadsheet_id: The unique string identifier.
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
        """
        try:
            self.batch_updater(spreadsheet_id).unmerge_cells(sheet_id, start_row, end_row, start_col, end_col).execute()
            return True
        except Exception:
            return False

    def auto_resize_columns(self, spreadsheet_id: str, sheet_id: int, start_col: int, end_col: int) -> bool:
        """
        Auto-resizes the width of the columns based on their content.
        
        Args:
            spreadsheet_id: The unique string identifier.
            sheet_id: Target worksheet integer ID.
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
        """
        try:
            self.batch_updater(spreadsheet_id).auto_resize_columns(sheet_id, start_col, end_col).execute()
            return True
        except Exception:
            return False

    def insert_rows(self, spreadsheet_id: str, sheet_id: int, start_index: int, num_rows: int) -> bool:
        """
        Inserts empty rows at a specific location, shifting existing rows down.
        
        Args:
            spreadsheet_id: The unique string identifier.
            sheet_id: Target worksheet integer ID.
            start_index: 0-based row index indicating where to insert.
            num_rows: Number of blank rows to create.
        """
        try:
            self.batch_updater(spreadsheet_id).insert_rows(sheet_id, start_index, num_rows).execute()
            return True
        except Exception:
            return False

    def delete_rows(self, spreadsheet_id: str, sheet_id: int, start_index: int, end_index: int) -> bool:
        """
        Deletes existing rows.
        
        Args:
            spreadsheet_id: The unique string identifier.
            sheet_id: Target worksheet integer ID.
            start_index: 0-based starting row index (inclusive).
            end_index: 0-based ending row index (exclusive).
        """
        try:
            self.batch_updater(spreadsheet_id).delete_rows(sheet_id, start_index, end_index).execute()
            return True
        except Exception:
            return False

    def sort_range(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, sort_column_index: int, ascending: bool = True) -> bool:
        """
        Sorts the data within a specified range structure.
        
        Args:
            spreadsheet_id: The unique string identifier.
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
            sort_column_index: 0-based column index representing the key to sort by.
            ascending: Sort order (A-Z).
        """
        try:
            self.batch_updater(spreadsheet_id).sort_range(sheet_id, start_row, end_row, start_col, end_col, sort_column_index, ascending).execute()
            return True
        except Exception:
            return False

    def freeze_rows(self, spreadsheet_id: str, sheet_id: int, num_rows: int) -> bool:
        """
        Freezes the top N rows so they don't move during scrolling.
        
        Args:
            spreadsheet_id: The unique string identifier.
            sheet_id: Target worksheet integer ID.
            num_rows: Number of top rows to freeze.
        """
        try:
            self.batch_updater(spreadsheet_id).freeze_rows(sheet_id, num_rows).execute()
            return True
        except Exception:
            return False

    def add_data_validation(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, dropdown_values: List[str]) -> bool:
        """
        Injects a dropdown constraint over a range.
        
        Args:
            spreadsheet_id: The unique string identifier.
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
            dropdown_values: List of string options allowed.
        """
        try:
            self.batch_updater(spreadsheet_id).add_data_validation(sheet_id, start_row, end_row, start_col, end_col, dropdown_values).execute()
            return True
        except Exception:
            return False

    def duplicate_worksheet(self, spreadsheet_id: str, source_sheet_id: int, new_title: str) -> bool:
        """
        Creates a copy of an existing worksheet.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            source_sheet_id: Integer sheet ID of the target to copy.
            new_title: Target new string name.
        """
        try:
            self.batch_updater(spreadsheet_id).duplicate_worksheet(source_sheet_id, new_title).execute()
            return True
        except Exception:
            return False

    def get_headers(self, spreadsheet_id: str, range_name: str) -> List[str]:
        """
        Fetches only the top row of a given A1-notation range to understand the schema.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: Target A1-notation block containing headers.
        """
        result = self._service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        return values[0] if values else []

    def get_values_as_dicts(self, spreadsheet_id: str, range_name: str) -> List[dict]:
        """
        Reads an A1-notation range and automatically maps the first row as dictionary keys for the following rows.
        Returns a list of dictionaries, perfect for AI agents parsing JSON.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: Target block bounding the headers and payload.
        """
        result = self._service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        return utils.parse_values_to_dicts(values)

    def find_value(self, spreadsheet_id: str, range_name: str, search_string: str) -> Optional[Tuple[int, int]]:
        """
        Searches an A1-notation range for a specific string and returns its (row_index, col_index) relative to the fetched array.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: Target block searching constraint.
            search_string: The string value to perform matching against.
        """
        result = self._service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        
        for r_idx, row in enumerate(values):
            for c_idx, cell in enumerate(row):
                if search_string.lower() in str(cell).lower():
                    return (r_idx, c_idx)
        return None

    def append_values_from_dicts(self, spreadsheet_id: str, range_name: str, data: List[dict]) -> bool:
        """
        Appends data to a sheet by mapping a list of dicts to the sheet's existing headers.
        If no headers exist, it automatically creates them from the dictionary keys.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            range_name: A1-notation logic pointing to the start of the table block.
            data: List of key-value payloads to append.
        """
        if not data:
            return True
            
        headers = self.get_headers(spreadsheet_id, range_name)
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
            self.batch_updater(spreadsheet_id).append_values(range_name, rows_to_write).execute()
            return True
        except Exception:
            return False

    def batch_update(self, spreadsheet_id: str, requests: List[dict]) -> dict:
        """
        Executes a custom batchUpdate for complex requests not directly covered by the wrappers.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet.
            requests: JSON dictionary payload arrays.
        """
        body = {"requests": requests}
        return self._service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body).execute()

    def batch_updater(self, spreadsheet_id: str) -> SheetsBatchUpdater:
        """
        Returns a builder to chain multiple worksheet and cell formatting requests into a single API call.
        
        Args:
            spreadsheet_id: The unique string identifier of the spreadsheet target.
        """
        return SheetsBatchUpdater(self._service, spreadsheet_id)
