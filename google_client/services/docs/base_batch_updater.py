from typing import List, Optional, Any

class BaseDocsBatchUpdater:
    """
    Base builder for creating Google Docs batch update requests.
    Implementations (sync/async) will handle the actual execution.
    """
    def __init__(self, document_id: str):
        self._document_id = document_id
        self._requests: List[dict] = []

    def insert_text(self, text: str, index: int = 1) -> 'BaseDocsBatchUpdater':
        """
        Inserts text at the specified index in the document.
        
        Args:
            text: The literal text string to insert.
            index: The 1-based UTF-16 code unit index where the text will be inserted.
                   Index 1 represents the start of the document skipping the invisible start token.
        """
        self._requests.append({
            "insertText": {
                "location": {
                    "index": index
                },
                "text": text
            }
        })
        return self

    def delete_text(self, start_index: int, end_index: int) -> 'BaseDocsBatchUpdater':
        """
        Deletes text between start_index and end_index.
        
        Args:
            start_index: The starting half-open index (inclusive).
            end_index: The ending half-open index (exclusive). Text up to this index is removed.
        """
        self._requests.append({
            "deleteContentRange": {
                "range": {
                    "startIndex": start_index,
                    "endIndex": end_index
                }
            }
        })
        return self

    def replace_all_text(self, contains_text: str, replace_text: str, match_case: bool = True) -> 'BaseDocsBatchUpdater':
        """
        Replaces all instances of `contains_text` with `replace_text`.
        
        Args:
            contains_text: The substring to search for.
            replace_text: The text to inject in place of the matched substring.
            match_case: Whether to enforce case sensitivity.
        """
        self._requests.append({
            "replaceAllText": {
                "containsText": {
                    "text": contains_text,
                    "matchCase": match_case
                },
                "replaceText": replace_text
            }
        })
        return self

    def update_text_style(self, start_index: int, end_index: int, 
                          bold: Optional[bool] = None, 
                          italic: Optional[bool] = None, 
                          font_family: Optional[str] = None, 
                          font_size: Optional[int] = None) -> 'BaseDocsBatchUpdater':
        """
        Updates the stylistic properties of text within a specific range.
        
        Args:
            start_index: The starting index (inclusive) of the text to style.
            end_index: The ending index (exclusive) of the text to style.
            bold: Set to True to bold the text, False to unbold execution.
            italic: Set to True to italicize the text.
            font_family: String name of the Google Font to apply (e.g., "Arial", "Inter").
            font_size: The font size measured in points (pt).
        """
        text_style: dict[str, Any] = {}
        fields = []
        if bold is not None:
            text_style["bold"] = bold
            fields.append("bold")
        if italic is not None:
            text_style["italic"] = italic
            fields.append("italic")
        if font_family is not None:
            text_style["weightedFontFamily"] = {"fontFamily": font_family}
            fields.append("weightedFontFamily")
        if font_size is not None:
            text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
            fields.append("fontSize")
            
        if not fields:
            return self

        self._requests.append({
            "updateTextStyle": {
                "range": {
                    "startIndex": start_index,
                    "endIndex": end_index
                },
                "textStyle": text_style,
                "fields": ",".join(fields)
            }
        })
        return self

    def update_paragraph_alignment(self, start_index: int, end_index: int, alignment: str) -> 'BaseDocsBatchUpdater':
        """
        Updates the alignment of paragraphs overlapping the specified range.
        
        Args:
            start_index: The starting index (inclusive) of the paragraphs to align.
            end_index: The ending index (exclusive) of the paragraphs to align.
            alignment: The alignment type (e.g., "START", "CENTER", "END", "JUSTIFIED").
        """
        self._requests.append({
            "updateParagraphStyle": {
                "range": {
                    "startIndex": start_index,
                    "endIndex": end_index
                },
                "paragraphStyle": {
                    "alignment": alignment
                },
                "fields": "alignment"
            }
        })
        return self

    def update_heading_style(self, start_index: int, end_index: int, heading_id: str) -> 'BaseDocsBatchUpdater':
        """
        Changes the paragraph style to a designated heading size.
        
        Args:
            start_index: The starting index (inclusive) of the paragraph to style.
            end_index: The ending index (exclusive) of the paragraph to style.
            heading_id: Must be one of "NORMAL_TEXT", "TITLE", "SUBTITLE", "HEADING_1", etc.
        """
        self._requests.append({
            "updateParagraphStyle": {
                "range": {
                    "startIndex": start_index,
                    "endIndex": end_index
                },
                "paragraphStyle": {
                    "namedStyleType": heading_id
                },
                "fields": "namedStyleType"
            }
        })
        return self

    def insert_page_break(self, index: int) -> 'BaseDocsBatchUpdater':
        """
        Forces a page break at the specific index.
        
        Args:
            index: The 1-based index where the page break is inserted, pushing subsequent elements to a new page.
        """
        self._requests.append({
            "insertPageBreak": {
                "location": {
                    "index": index
                }
            }
        })
        return self

    def insert_table(self, rows: int, columns: int, index: int) -> 'BaseDocsBatchUpdater':
        """
        Dynamically generates a grid table.
        
        Args:
            rows: Total number of horizontal rows.
            columns: Total number of vertical columns.
            index: The 1-based index where the table structure should inject itself into the document.
        """
        self._requests.append({
            "insertTable": {
                "rows": rows,
                "columns": columns,
                "location": {
                    "index": index
                }
            }
        })
        return self

    def get_requests(self) -> List[dict]:
        """
        Returns the accumulated requests.
        """
        return self._requests
