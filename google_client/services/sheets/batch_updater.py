from typing import List, Any, Optional
from .types import CellFormat


class SheetsBatchUpdater:
    """
    Builder class for chaining multiple spreadsheet modification requests 
    into a single Google Sheets API batchUpdate call.
    """

    def __init__(self, service, spreadsheet_id: str):
        self._service = service
        self.spreadsheet_id = spreadsheet_id
        self.requests = []

    def add_worksheet(self, title: str, sheet_id: Optional[int] = None, rows: int = 1000, cols: int = 26) -> "SheetsBatchUpdater":
        """
        Add a new worksheet to the spreadsheet.
        """
        props = {
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

    def update_values(self, sheet_id: int, start_row: int, start_col: int, values: List[List[Any]]) -> "SheetsBatchUpdater":
        """
        Update a rectangular block of cells starting from the given coordinates.
        Uses UpdateCellsRequest to support batch grid modifications.
        """
        row_data = []
        for row in values:
            cells = []
            for val in row:
                cells.append(self._convert_value_to_cell_data(val))
            row_data.append({"values": cells})

        self.requests.append({
            "updateCells": {
                "rows": row_data,
                "fields": "userEnteredValue",
                "start": {
                    "sheetId": sheet_id,
                    "rowIndex": start_row,
                    "columnIndex": start_col
                }
            }
        })
        return self

    def append_values(self, sheet_id: int, values: List[List[Any]]) -> "SheetsBatchUpdater":
        """
        Appends values to the end of a spreadsheet logical table.
        """
        row_data = []
        for row in values:
            cells = []
            for val in row:
                cells.append(self._convert_value_to_cell_data(val))
            row_data.append({"values": cells})
            
        self.requests.append({
            "appendCells": {
                "sheetId": sheet_id,
                "rows": row_data,
                "fields": "userEnteredValue"
            }
        })
        return self

    def clear_values(self, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int) -> "SheetsBatchUpdater":
        """
        Clears values from a rectangular region.
        """
        self.requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "cell": {},
                "fields": "userEnteredValue"
            }
        })
        return self

    def _hex_to_rgb(self, hex_color: str) -> dict:
        """Helper to convert hex to Sheets RGB dict."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c + c for c in hex_color)
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return {"red": r, "green": g, "blue": b}

    def _build_border_dict(self, border_model) -> dict:
        if not border_model:
            return {}
        result = {"style": border_model.style.value}
        if border_model.color_hex:
            result["color"] = self._hex_to_rgb(border_model.color_hex)
        return result

    def format_range(self, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, format: CellFormat) -> "SheetsBatchUpdater":
        """
        Format a rectangular bounding box with given CellFormat properties.
        """
        text_format = {}
        if format.bold:
            text_format["bold"] = True
        if format.italic:
            text_format["italic"] = True
        if format.font_size:
            text_format["fontSize"] = format.font_size
        if format.text_color_hex:
            text_format["foregroundColor"] = self._hex_to_rgb(format.text_color_hex)

        cell_format = {}
        if text_format:
            cell_format["textFormat"] = text_format
        if format.background_color_hex:
            cell_format["backgroundColor"] = self._hex_to_rgb(format.background_color_hex)

        fields_to_update = []
        if text_format:
            fields_to_update.append("textFormat")
        if format.background_color_hex:
            fields_to_update.append("backgroundColor")

        # Handle cell borders natively via UpdateBordersRequest
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

    def merge_cells(self, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int, merge_type: str = "MERGE_ALL") -> "SheetsBatchUpdater":
        """
        Merge cells within the specified range.
        merge_type: MERGE_ALL, MERGE_COLUMNS, or MERGE_ROWS.
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

    def unmerge_cells(self, sheet_id: int, start_row: int, end_row: int, start_col: int, end_col: int) -> "SheetsBatchUpdater":
        """
        Unmerges all cells in the specified range.
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

    def delete_worksheet(self, sheet_id: int) -> "SheetsBatchUpdater":
        """
        Deletes a worksheet by its internal sheet ID.
        """
        self.requests.append({
            "deleteSheet": {"sheetId": sheet_id}
        })
        return self

    def rename_worksheet(self, sheet_id: int, new_title: str) -> "SheetsBatchUpdater":
        """
        Renames an existing worksheet.
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

    def auto_resize_columns(self, sheet_id: int, start_col: int, end_col: int) -> "SheetsBatchUpdater":
        """
        Auto-resizes the width of the columns based on their content.
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

    def execute(self) -> dict:
        """
        Fires all accumulating requests natively in a single batchUpdate operation.
        """
        if not self.requests:
            return {}

        body = {"requests": self.requests}
        response = self._service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body=body).execute()
        
        # Clear requests after execution so builder can be reused cleanly
        self.requests = []
        return response
