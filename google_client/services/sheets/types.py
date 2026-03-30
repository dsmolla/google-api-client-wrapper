from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

class Worksheet(BaseModel):
    """
    Represents an individual tab/sheet within a workbook.
    """
    sheet_id: int = Field(description="The unique ID of the sheet")
    title: str = Field(description="The name of the sheet")
    index: int = Field(description="The index position of the sheet")
    row_count: int = Field(description="Number of rows in the grid")
    column_count: int = Field(description="Number of columns in the grid")
    hidden: bool = Field(False, description="Whether the sheet is hidden")

    def is_hidden(self) -> bool:
        """
        Check if the worksheet is hidden.
        """
        return self.hidden


class Spreadsheet(BaseModel):
    """
    Represents an entire Google Sheets document (workbook).
    """
    spreadsheet_id: str = Field(description="The ID of the spreadsheet")
    title: str = Field(description="The title of the spreadsheet")
    url: str = Field(description="The URL to access the spreadsheet")
    worksheets: List[Worksheet] = Field(default_factory=list, description="List of worksheets in this document")

    def get_worksheet_by_title(self, title: str) -> Optional[Worksheet]:
        """
        Retrieves a worksheet by its exact title.
        """
        for ws in self.worksheets:
            if ws.title == title:
                return ws
        return None

    def get_worksheet_by_id(self, sheet_id: int) -> Optional[Worksheet]:
        """
        Retrieves a worksheet by its unique sheet ID.
        """
        for ws in self.worksheets:
            if ws.sheet_id == sheet_id:
                return ws
        return None

    def to_dict(self) -> dict:
        return {
            "spreadsheet_id": self.spreadsheet_id,
            "title": self.title,
            "url": self.url,
            "worksheets": [ws.model_dump() for ws in self.worksheets]
        }


class CellRange(BaseModel):
    """
    Represents a block of fetched data from a spreadsheet.
    """
    range_name: str = Field(description="The A1 notation of the range from which data was fetched")
    values: List[List[Any]] = Field(default_factory=list, description="The 2D array of raw values")

    def get_row(self, index: int) -> List[Any]:
        """
        Get a specific row by its zero-based index.
        """
        if 0 <= index < len(self.values):
            return self.values[index]
        return []

    def get_column(self, index: int) -> List[Any]:
        """
        Get a specific column by its zero-based index.
        """
        col = []
        for row in self.values:
            if index < len(row):
                col.append(row[index])
            else:
                col.append(None)
        return col

    def to_dict_list(self, header_row_index: int = 0) -> List[dict]:
        """
        Converts the 2D array to a list of dictionaries based on a header row.
        Args:
            header_row_index: The row index containing the header keys.
        """
        if header_row_index >= len(self.values) or not self.values:
            return []

        headers = [str(h) for h in self.values[header_row_index]]
        result = []
        for i in range(header_row_index + 1, len(self.values)):
            row = self.values[i]
            row_dict = {}
            for j, header in enumerate(headers):
                if j < len(row):
                    row_dict[header] = row[j]
                else:
                    row_dict[header] = None
            result.append(row_dict)
        return result


class BorderStyle(str, Enum):
    """Supported border styles in Google Sheets."""
    NONE = "NONE"
    DOTTED = "DOTTED"
    DASHED = "DASHED"
    SOLID = "SOLID"
    SOLID_MEDIUM = "SOLID_MEDIUM"
    SOLID_THICK = "SOLID_THICK"
    DOUBLE = "DOUBLE"


class Border(BaseModel):
    """Represents a single border."""
    style: BorderStyle = Field(default=BorderStyle.SOLID)
    color_hex: Optional[str] = Field(None, description="Hex color for the border (e.g. #000000)")


class CellBorders(BaseModel):
    """Represents all borders of a cell or range."""
    top: Optional[Border] = None
    bottom: Optional[Border] = None
    left: Optional[Border] = None
    right: Optional[Border] = None
    inner_horizontal: Optional[Border] = None
    inner_vertical: Optional[Border] = None


class CellFormat(BaseModel):
    """
    Represents styling for cells.
    Used for formatting specific ranges.
    """
    bold: bool = False
    italic: bool = False
    font_size: Optional[int] = None
    text_color_hex: Optional[str] = None
    background_color_hex: Optional[str] = None
    borders: Optional[CellBorders] = None
