from .base_batch_updater import BaseDocsBatchUpdater

class DocsBatchUpdater(BaseDocsBatchUpdater):
    """
    Synchronous builder and executor for Docs API batchUpdate.
    """
    def __init__(self, service, document_id: str):
        super().__init__(document_id)
        self._service = service

    def execute(self) -> dict:
        """
        Executes all accumulated requests in a single API call.
        Returns the batchUpdate response.
        """
        if not self._requests:
            return {}

        body = {"requests": self._requests}
        response = self._service.documents().batchUpdate(
            documentId=self._document_id,
            body=body
        ).execute()
        
        # Clear requests after successful execution
        self._requests = []
        return response
