from typing import List, Any, Optional, TypeVar, Self
from .types import CellFormat

class BaseSheetsBatchUpdater:
    """
    Base builder class for chaining multiple spreadsheet modification requests 
    into a single Google Sheets API batchUpdate call.
    """

    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.requests: List[dict[str, Any]] = []
        self.value_update_requests: List[dict[str, Any]] = []
        self.value_append_requests: List[dict[str, Any]] = []
        self.value_clear_requests: List[str] = []

    def add_worksheet( self, title: str, sheet_id: Optional[int] = None, rows: int = 1000, cols: int = 26) -> Self:
        """
        Add a new worksheet to the spreadsheet.
        
        Args:
            title: The name of the new tab.
            sheet_id: Optional integer ID for the new tab (auto-generated if None).
            rows: The total starting row capacity.
            cols: The total starting column capacity.
        """
        props: dict[str, Any] = {
            "title": title,
            "gridProperties": {
                "rowCount": rows,
                "columnCount": cols
            }
        }
        if sheet_id is not None:
            props["sheetId"] = sheet_id

        self.requests.append({
            "addSheet": {
                "properties": props
            }
        })
        return self

    def _convert_value_to_cell_data(self, val: Any) -> dict:
        """Helper to convert a Python value to Google's ExtendedValue format."""
        if val is None:
            return {}
        if isinstance(val, bool):
            return {"userEnteredValue": {"boolValue": val}}
        if isinstance(val, (int, float)):
            return {"userEnteredValue": {"numberValue": val}}
        if isinstance(val, str) and val.startswith("="):
            return {"userEnteredValue": {"formulaValue": val}}
        return {"userEnteredValue": {"stringValue": str(val)}}

    def update_values( self, range_name: str, values: List[List[Any]]) -> Self:
        """
        Updates values in a spreadsheet range using A1 notation.
        
        Args:
            range_name: A1 notation target (e.g. "Sheet1!A1:C10").
            values: A 2D list matrix representing the grid values.
        """
        self.value_update_requests.append({
            "range": range_name,
            "values": values
        })
        return self

    def append_values( self, range_name: str, values: List[List[Any]]) -> Self:
        """
        Appends values to a spreadsheet logical table using A1 notation.
        
        Args:
            range_name: A1 notation targeting the table or boundary.
            values: A 2D list matrix to append at the bottom of the table.
        """
        self.value_append_requests.append({
            "range": range_name,
            "values": values
        })
        return self

    def clear_values( self, range_name: str) -> Self:
        """
        Clears values from a given range using A1 notation.
        
        Args:
            range_name: A1 notation target (e.g. "Sheet1!A1:C10").
        """
        self.value_clear_requests.append(range_name)
        return self

    def _hex_to_rgb(self, hex_color: str) -> dict:
        """Helper to convert hex to Sheets RGB dict."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c + c for c in hex_color)
        r = int(hex_color[0:2], 16) / 255.0  # type: ignore
        g = int(hex_color[2:4], 16) / 255.0  # type: ignore
        b = int(hex_color[4:6], 16) / 255.0  # type: ignore
        return {"red": r, "green": g, "blue": b}

    def _build_border_dict(self, border_model) -> dict:
        if not border_model:
            return {}
        result = {"style": border_model.style.value}
        if border_model.color_hex:
            result["color"] = self._hex_to_rgb(border_model.color_hex)
        return result

    def format_range( self, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, format: CellFormat) -> Self:
        """
        Format a rectangular bounding box with given CellFormat properties.
        
        Args:
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
            format: The predefined CellFormat block.
        """
        text_format: dict[str, Any] = {}
        if format.bold:
            text_format["bold"] = True
        if format.italic:
            text_format["italic"] = True
        if format.font_size:
            text_format["fontSize"] = format.font_size
        if format.text_color_hex:
            text_format["foregroundColor"] = self._hex_to_rgb(format.text_color_hex)

        cell_format: dict[str, Any] = {}
        if text_format:
            cell_format["textFormat"] = text_format
        if format.background_color_hex:
            cell_format["backgroundColor"] = self._hex_to_rgb(format.background_color_hex)

        fields_to_update = []
        if text_format:
            fields_to_update.append("textFormat")
        if format.background_color_hex:
            fields_to_update.append("backgroundColor")
        if format.borders:
            borders_req = {
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col
                    }
                }
            }
            has_border = False
            if format.borders.top:
                borders_req["updateBorders"]["top"] = self._build_border_dict(format.borders.top)
                has_border = True
            if format.borders.bottom:
                borders_req["updateBorders"]["bottom"] = self._build_border_dict(format.borders.bottom)
                has_border = True
            if format.borders.left:
                borders_req["updateBorders"]["left"] = self._build_border_dict(format.borders.left)
                has_border = True
            if format.borders.right:
                borders_req["updateBorders"]["right"] = self._build_border_dict(format.borders.right)
                has_border = True
            if format.borders.inner_horizontal:
                borders_req["updateBorders"]["innerHorizontal"] = self._build_border_dict(format.borders.inner_horizontal)
                has_border = True
            if format.borders.inner_vertical:
                borders_req["updateBorders"]["innerVertical"] = self._build_border_dict(format.borders.inner_vertical)
                has_border = True

            if has_border:
                self.requests.append(borders_req)

        if not cell_format:
            return self

        self.requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "cell": {
                    "userEnteredFormat": cell_format
                },
                "fields": "userEnteredFormat(" + ",".join(fields_to_update) + ")"
            }
        })
        return self

    def merge_cells( self, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, merge_type: str = "MERGE_ALL") -> Self:
        """
        Merge cells within the specified range.
        
        Args:
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
            merge_type: "MERGE_ALL", "MERGE_COLUMNS", or "MERGE_ROWS".
        """
        self.requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "mergeType": merge_type
            }
        })
        return self

    def unmerge_cells( self, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int) -> Self:
        """
        Unmerges all cells in the specified range.
        
        Args:
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
        """
        self.requests.append({
            "unmergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                }
            }
        })
        return self

    def delete_worksheet( self, sheet_id: int) -> Self:
        """
        Deletes a worksheet by its internal sheet ID.
        
        Args:
            sheet_id: Target worksheet integer ID.
        """
        self.requests.append({
            "deleteSheet": {"sheetId": sheet_id}
        })
        return self

    def rename_worksheet( self, sheet_id: int, new_title: str) -> Self:
        """
        Renames an existing worksheet.
        
        Args:
            sheet_id: Target worksheet integer ID.
            new_title: Target new string name.
        """
        self.requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "title": new_title
                },
                "fields": "title"
            }
        })
        return self

    def auto_resize_columns( self, sheet_id: int, start_col: int, end_col: int) -> Self:
        """
        Auto-resizes the width of the columns based on their content.
        
        Args:
            sheet_id: Target worksheet integer ID.
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
        """
        self.requests.append({
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_col,
                    "endIndex": end_col
                }
            }
        })
        return self

    def insert_rows( self, sheet_id: int, start_index: int, num_rows: int) -> Self:
        """
        Inserts new empty rows before the specified start_index.
        
        Args:
            sheet_id: Target worksheet integer ID.
            start_index: 0-based row index indicating where to insert.
            num_rows: Number of blank rows to create.
        """
        self.requests.append({
            "insertDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_index,
                    "endIndex": start_index + num_rows
                },
                "inheritFromBefore": False
            }
        })
        return self

    def delete_rows( self, sheet_id: int, start_index: int, end_index: int) -> Self:
        """
        Deletes rows entirely between start_index and end_index.
        
        Args:
            sheet_id: Target worksheet integer ID.
            start_index: 0-based starting row index (inclusive).
            end_index: 0-based ending row index (exclusive).
        """
        self.requests.append({
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_index,
                    "endIndex": end_index
                }
            }
        })
        return self

    def sort_range( self, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, sort_column_index: int, ascending: bool = True) -> Self:
        """
        Sorts a rectangular region of cells.
        
        Args:
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
            sort_column_index: 0-based column index representing the key to sort by.
            ascending: Sort order (A-Z).
        """
        self.requests.append({
            "sortRange": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "sortSpecs": [
                    {
                        "dimensionIndex": sort_column_index,
                        "sortOrder": "ASCENDING" if ascending else "DESCENDING"
                    }
                ]
            }
        })
        return self

    def freeze_rows( self, sheet_id: int, num_rows: int) -> Self:
        """
        Freezes the top N rows so they stay visible while scrolling.
        
        Args:
            sheet_id: Target worksheet integer ID.
            num_rows: Number of top rows to freeze.
        """
        self.requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": num_rows
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        })
        return self

    def add_data_validation( self, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, dropdown_values: List[str]) -> Self:
        """
        Adds a dropdown menu to the cells with the provided values.
        
        Args:
            sheet_id: Target worksheet integer ID.
            start_row: 0-based starting row index (inclusive).
            end_row: 0-based ending row index (exclusive).
            start_col: 0-based starting column index (inclusive).
            end_col: 0-based ending column index (exclusive).
            dropdown_values: List of string options allowed.
        """
        condition_values = [{"userEnteredValue": val} for val in dropdown_values]
        self.requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": condition_values
                    },
                    "showCustomUi": True,
                    "strict": True
                }
            }
        })
        return self

    def duplicate_worksheet( self, source_sheet_id: int, new_title: str) -> Self:
        """
        Duplicates an existing worksheet, matching all formats and values.
        
        Args:
            source_sheet_id: Integer sheet ID of the target to copy.
            new_title: Target new string name.
        """
        self.requests.append({
            "duplicateSheet": {
                "sourceSheetId": source_sheet_id,
                "insertSheetIndex": 9999,
                "newSheetName": new_title
            }
        })
        return self
