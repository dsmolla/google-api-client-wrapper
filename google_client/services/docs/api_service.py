from typing import Optional, Dict, Any, List

from google.auth.credentials import Credentials
from googleapiclient.discovery import build


class DocsApiService:
    """
    Service layer for Google Docs API operations.
    """

    def __init__(self, credentials: Credentials, timezone: str):
        self._service = build("docs", "v1", credentials=credentials)
        self._timezone = timezone

    def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        Retrieves a specific Google Doc.

        Args:
            document_id: The unique identifier of the document.

        Returns:
            A dictionary containing the document data.
        """
        return self._service.documents().get(documentId=document_id).execute()

    def create_document(self, title: str) -> Dict[str, Any]:
        """
        Creates a new, blank Google Doc.

        Args:
            title: The title of the new document.

        Returns:
            A dictionary containing the created document data.
        """
        body = {
            'title': title
        }
        return self._service.documents().create(body=body).execute()

    def batch_update(self, document_id: str, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applies one or more updates to the document.

        Args:
            document_id: The unique identifier of the document.
            requests: A list of update requests to apply.

        Returns:
            A dictionary with the results of the update.
        """
        body = {
            'requests': requests
        }
        return self._service.documents().batchUpdate(documentId=document_id, body=body).execute()
