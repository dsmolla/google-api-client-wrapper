import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base_batch_updater import BaseDocsBatchUpdater

class AsyncDocsBatchUpdater(BaseDocsBatchUpdater):
    """
    Asynchronous builder and executor for Docs API batchUpdate.
    """
    def __init__(self, service, executor: ThreadPoolExecutor, document_id: str):
        super().__init__(document_id)
        self._service = service
        self._executor = executor

    async def execute(self) -> dict:
        if not self._requests:
            return {}

        body = {"requests": self._requests}
        loop = asyncio.get_event_loop()
        
        response = await loop.run_in_executor(
            self._executor,
            lambda: self._service.documents().batchUpdate(
                documentId=self._document_id,
                body=body
            ).execute()
        )
        
        self._requests = []
        return response
