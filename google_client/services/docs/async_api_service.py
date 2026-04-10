import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from google.auth.credentials import Credentials
from googleapiclient.discovery import build

from . import utils
from .types import Document
from .async_batch_updater import AsyncDocsBatchUpdater


class AsyncDocsApiService:
    """
    Async service layer for Docs API operations.
    """

    def __init__(self, credentials: Credentials, timezone: str = 'UTC'):
        self._executor = ThreadPoolExecutor()
        self._credentials = credentials
        self.timezone = timezone

    def __del__(self):
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

    def _service(self):
        return build("docs", "v1", credentials=self._credentials)

    def batch_updater(self, document_id: str) -> AsyncDocsBatchUpdater:
        """
        Returns an asynchronous builder to chain multiple update requests.
        
        Args:
            document_id: The unique string identifier of the document.
        """
        return AsyncDocsBatchUpdater(self._service(), self._executor, document_id)

    async def create_document(self, title: str) -> Document:
        """
        Creates a new, blank Google Document.
        
        Args:
            title: The title string of the new document.
        """
        body = {'title': title}
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().documents().create(body=body).execute()
        )
        return utils.convert_api_document_to_document(result)

    async def get_document(self, document_id: str) -> Document:
        """
        Retrieves a specific Google Document (metadata only by default).
        
        Args:
            document_id: The unique string identifier of the document.
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().documents().get(documentId=document_id).execute()
        )
        return utils.convert_api_document_to_document(result)

    async def batch_update(self, document_id: str, requests: List[dict]) -> dict:
        """
        Executes a custom batchUpdate mapping directly to raw JSON requests.
        
        Args:
            document_id: The unique string identifier of the document.
            requests: A list of dict payloads representing Google Docs API requests.
        """
        body = {'requests': requests}
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self._service().documents().batchUpdate(
                documentId=document_id, body=body).execute()
        )

    async def insert_text(self, document_id: str, text: str, index: int = 1) -> bool:
        """
        Inserts text at the specified index in the document asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
            text: The literal text string to inject.
            index: The 1-based UTF-16 code unit index where the text will be inserted.
                   Index 1 represents the start of the document block.
        """
        try:
            await self.batch_updater(document_id).insert_text(text, index).execute()
            return True
        except Exception:
            return False

    async def delete_text(self, document_id: str, start_index: int, end_index: int) -> bool:
        """
        Deletes text between start_index and end_index asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
            start_index: The starting half-open index (inclusive).
            end_index: The ending half-open index (exclusive). Text up to this index is removed.
        """
        try:
            await self.batch_updater(document_id).delete_text(start_index, end_index).execute()
            return True
        except Exception:
            return False

    async def replace_all_text(self, document_id: str, contains_text: str, replace_text: str, match_case: bool = True) -> bool:
        """
        Replaces all instances of a specific substring asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
            contains_text: The exact substring to locate and replace.
            replace_text: The new text string to inject.
            match_case: If True, only replaces exact capitalization matches.
        """
        try:
            await self.batch_updater(document_id).replace_all_text(contains_text, replace_text, match_case).execute()
            return True
        except Exception:
            return False

    async def get_document_text(self, document_id: str) -> str:
        """
        Returns the flattened plaintext content of the document, resolving tables asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
        """
        loop = asyncio.get_event_loop()
        doc = await loop.run_in_executor(
            self._executor,
            lambda: self._service().documents().get(documentId=document_id).execute()
        )
        return utils.extract_text_from_document(doc)

    async def get_document_links(self, document_id: str) -> list:
        """
        Returns a list of URLs and their anchor texts embedded within the document asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
        """
        loop = asyncio.get_event_loop()
        doc = await loop.run_in_executor(
            self._executor,
            lambda: self._service().documents().get(documentId=document_id).execute()
        )
        return utils.extract_links_from_document(doc)

    async def update_text_style(self, document_id: str, start_index: int, end_index: int, 
                                bold: Optional[bool] = None, italic: Optional[bool] = None, 
                                font_family: Optional[str] = None, font_size: Optional[int] = None) -> bool:
        """
        Updates the stylistic properties of text within a specific range asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
            start_index: The starting index (inclusive).
            end_index: The ending index (exclusive).
            bold: Set to True to bold the text, False to unbold alignment.
            italic: Set to True to italicize the text.
            font_family: String name of the Google Font to apply.
            font_size: The font size in points (e.g. 12).
        """
        try:
            await self.batch_updater(document_id).update_text_style(start_index, end_index, bold, italic, font_family, font_size).execute()
            return True
        except Exception:
            return False

    async def update_paragraph_alignment(self, document_id: str, start_index: int, end_index: int, alignment: str) -> bool:
        """
        Updates the alignment layout of paragraphs overlapping the specified range asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
            start_index: The starting index (inclusive).
            end_index: The ending index (exclusive).
            alignment: The alignment type ("START", "CENTER", "END", "JUSTIFIED").
        """
        try:
            await self.batch_updater(document_id).update_paragraph_alignment(start_index, end_index, alignment).execute()
            return True
        except Exception:
            return False

    async def update_heading_style(self, document_id: str, start_index: int, end_index: int, heading_id: str) -> bool:
        """
        Changes the targeted paragraph style to a predefined heading size asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
            start_index: The starting index (inclusive).
            end_index: The ending index (exclusive).
            heading_id: A valid Docs heading type ("NORMAL_TEXT", "HEADING_1", etc.).
        """
        try:
            await self.batch_updater(document_id).update_heading_style(start_index, end_index, heading_id).execute()
            return True
        except Exception:
            return False

    async def insert_page_break(self, document_id: str, index: int) -> bool:
        """
        Forces a page break at the specific index asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
            index: The 1-based index where the page break is inserted.
        """
        try:
            await self.batch_updater(document_id).insert_page_break(index).execute()
            return True
        except Exception:
            return False

    async def insert_table(self, document_id: str, rows: int, columns: int, index: int) -> bool:
        """
        Dynamically generates a grid table asynchronously.
        
        Args:
            document_id: The unique string identifier of the document.
            rows: Total number of horizontal rows.
            columns: Total number of vertical columns.
            index: The 1-based index where the table structure should inject itself into the document.
        """
        try:
            await self.batch_updater(document_id).insert_table(rows, columns, index).execute()
            return True
        except Exception:
            return False

    async def insert_table_with_data(self, document_id: str, index: int, data: List[List[str]]) -> bool:
        """
        Creates a table and fills it with data asynchronously, automatically abstracting away the complex
        JSON structural index mapping and backwards text insertions.
        
        Args:
            document_id: The unique string identifier of the document.
            index: The starting index where the new table should be inserted.
            data: A 2D list array (List[List[str]]) mapping directly to the table layout.
        """
        if not data or not data[0]:
            return False
            
        rows = len(data)
        cols = max(len(row) for row in data)
        
        # Step 1: Insert empty table
        if not await self.insert_table(document_id, rows, cols, index):
            return False
            
        # Step 2: Fetch updated document map
        try:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(
                self._executor,
                lambda: self._service().documents().get(documentId=document_id).execute()
            )
        except Exception:
            return False
            
        content = doc.get("body", {}).get("content", [])
        target_table = None
        
        for el in content:
            if "table" in el:
                start = el.get("startIndex", 0)
                if abs(start - index) <= 2:
                    target_table = el["table"]
                    break
                    
        if not target_table:
            return False
            
        # Step 3: Insert backwards based on mapped indices
        updater = self.batch_updater(document_id)
        
        for r in range(rows - 1, -1, -1):
            row_data = data[r]
            for c in range(cols - 1, -1, -1):
                if c >= len(row_data):
                    continue
                cell_text = str(row_data[c])
                if not cell_text:
                    continue
                    
                cell = target_table.get("tableRows", [])[r].get("tableCells", [])[c]
                cell_start = cell.get("content", [])[0].get("startIndex", 0)
                
                if cell_start > 0:
                    updater.insert_text(cell_text, index=cell_start)
                    
        try:
            await updater.execute()
            return True
        except Exception:
            return False
