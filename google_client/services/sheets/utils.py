from typing import Dict, Any, List
from .types import Spreadsheet, Worksheet

def convert_api_spreadsheet_to_spreadsheet(data: Dict[str, Any]) -> Spreadsheet:
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

def parse_values_to_dicts(values: List[List[Any]]) -> List[dict]:
    """
    Reads a 2D array and automatically maps the first row as headers for the following rows.
    Returns a list of dictionaries, perfect for AI agents parsing JSON.
    """
    if not values or len(values) < 2:
        return []
        
    headers = values[0]
    data = []
    
    for row in values[1:]:
        row_dict = {}
        for i, header in enumerate(headers):
            row_dict[header] = row[i] if i < len(row) else ""
        data.append(row_dict)
        
    return data
