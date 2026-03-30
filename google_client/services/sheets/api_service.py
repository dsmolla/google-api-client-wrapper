from typing import Any, List

from google.auth.credentials import Credentials
from googleapiclient.discovery import build

from .types import Spreadsheet, Worksheet, CellRange, CellFormat
from .batch_updater import SheetsBatchUpdater


class SheetsApiService:
    """
    Service layer for Google Sheets API operations.
    """

    def __init__(self, credentials: Credentials, timezone: str):
        self._service = build("sheets", "v4", credentials=credentials)
        self._timezone = timezone

    def _parse_spreadsheet(self, data: dict) -> Spreadsheet:
        """Helper to parse raw spreadsheet payload to a Spreadsheet Pydantic model."""
        worksheets = []
        for sheet_data in data.get("sheets", []):
            props = sheet_data.get("properties", {})
            grid = props.get("gridProperties", {})
            worksheets.append(Worksheet(
                sheet_id=props.get("sheetId", 0),
                title=props.get("title", ""),
                index=props.get("index", 0),
                row_count=grid.get("rowCount", 0),
                column_count=grid.get("columnCount", 0),
                hidden=props.get("hidden", False)
            ))
            
        return Spreadsheet(
            spreadsheet_id=data.get("spreadsheetId", ""),
            title=data.get("properties", {}).get("title", ""),
            url=data.get("spreadsheetUrl", ""),
            worksheets=worksheets
        )

    def create_spreadsheet(self, title: str) -> Spreadsheet:
        """
        Creates a new, blank Google Spreadsheet.
        """
        spreadsheet = {
            'properties': {'title': title}
        }
        result = self._service.spreadsheets().create(body=spreadsheet).execute()
        return self._parse_spreadsheet(result)

    def get_spreadsheet(self, spreadsheet_id: str) -> Spreadsheet:
        """
        Retrieves a specific Google Spreadsheet with its tabs metadata.
        """
        result = self._service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        return self._parse_spreadsheet(result)

    def add_worksheet(self, spreadsheet_id: str, title: str, rows: int = 1000, cols: int = 26) -> Worksheet:
        """
        Adds a new worksheet to the spreadsheet.
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
        """
        try:
            self.batch_updater(spreadsheet_id).delete_worksheet(sheet_id).execute()
            return True
        except Exception:
            return False

    def rename_worksheet(self, spreadsheet_id: str, sheet_id: int, new_title: str) -> bool:
        """
        Renames an existing worksheet.
        """
        try:
            self.batch_updater(spreadsheet_id).rename_worksheet(sheet_id, new_title).execute()
            return True
        except Exception:
            return False

    def get_values(self, spreadsheet_id: str, range_name: str) -> CellRange:
        """
        Retrieves values from a spreadsheet range.
        """
        result = self._service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        return CellRange(
            range_name=result.get("range", range_name),
            values=result.get('values', [])
        )

    def update_values(self, spreadsheet_id: str, sheet_id: int, start_row: int, start_col: int, values: List[List[Any]]) -> bool:
        """
        Sets values in a spreadsheet range.
        """
        try:
            self.batch_updater(spreadsheet_id).update_values(sheet_id, start_row, start_col, values).execute()
            return True
        except Exception:
            return False

    def append_values(self, spreadsheet_id: str, sheet_id: int, values: List[List[Any]]) -> bool:
        """
        Appends values to a spreadsheet logical table.
        """
        try:
            self.batch_updater(spreadsheet_id).append_values(sheet_id, values).execute()
            return True
        except Exception:
            return False

    def clear_values(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int) -> bool:
        """
        Clears values from a given range.
        """
        try:
            self.batch_updater(spreadsheet_id).clear_values(sheet_id, start_row, end_row, start_col, end_col).execute()
            return True
        except Exception:
            return False

    def format_range(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, format: CellFormat) -> bool:
        """
        Applies a CellFormat object to a block.
        """
        try:
            self.batch_updater(spreadsheet_id).format_range(sheet_id, start_row, end_row, start_col, end_col, format).execute()
            return True
        except Exception:
            return False

    def merge_cells(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, merge_type: str = "MERGE_ALL") -> bool:
        """
        Merge cells within the specified range.
        merge_type: MERGE_ALL, MERGE_COLUMNS, or MERGE_ROWS.
        """
        try:
            self.batch_updater(spreadsheet_id).merge_cells(sheet_id, start_row, end_row, start_col, end_col, merge_type).execute()
            return True
        except Exception:
            return False

    def unmerge_cells(self, spreadsheet_id: str, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int) -> bool:
        """
        Unmerges all cells in the specified range.
        """
        try:
            self.batch_updater(spreadsheet_id).unmerge_cells(sheet_id, start_row, end_row, start_col, end_col).execute()
            return True
        except Exception:
            return False

    def auto_resize_columns(self, spreadsheet_id: str, sheet_id: int, start_col: int, end_col: int) -> bool:
        """
        Auto-resizes the width of the columns based on their content.
        """
        try:
            self.batch_updater(spreadsheet_id).auto_resize_columns(sheet_id, start_col, end_col).execute()
            return True
        except Exception:
            return False

    def batch_update(self, spreadsheet_id: str, requests: List[dict]) -> dict:
        """
        Executes a custom batchUpdate for complex requests not directly covered by the wrappers.
        """
        body = {"requests": requests}
        return self._service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body).execute()

    def batch_updater(self, spreadsheet_id: str) -> SheetsBatchUpdater:
        """
        Returns a builder to chain multiple worksheet and cell formatting requests into a single API call.
        """
        return SheetsBatchUpdater(self._service, spreadsheet_id)
