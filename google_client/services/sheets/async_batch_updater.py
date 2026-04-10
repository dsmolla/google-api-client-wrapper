import asyncio
from .base_batch_updater import BaseSheetsBatchUpdater

class AsyncSheetsBatchUpdater(BaseSheetsBatchUpdater):
    """
    Builder class for chaining multiple spreadsheet modification requests 
    into a single batchUpdate operation asynchronously.
    """
    def __init__(self, service, executor, spreadsheet_id: str):
        super().__init__(spreadsheet_id)
        self._service = service
        self._executor = executor

    async def execute(self) -> dict:
        response = {}
        loop = asyncio.get_event_loop()
        if self.requests:
            body = {"requests": self.requests}
            response = await loop.run_in_executor(
                self._executor,
                lambda: self._service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id, body=body).execute()
            )
            self.requests = []
            
        if self.value_update_requests:
            body = {
                "valueInputOption": "USER_ENTERED",
                "data": self.value_update_requests
            }
            res = await loop.run_in_executor(
                self._executor,
                lambda: self._service.spreadsheets().values().batchUpdate(
                    spreadsheetId=self.spreadsheet_id, body=body).execute()
            )
            if not response: response = res
            self.value_update_requests = []
            
        for req in self.value_append_requests:
            def run_req(r=req):
                body = {"values": r["values"]}
                return self._service.spreadsheets().values().append(
                    spreadsheetId=self.spreadsheet_id, range=r["range"],
                    valueInputOption="USER_ENTERED", body=body).execute()
            
            await loop.run_in_executor(self._executor, run_req)
        self.value_append_requests = []
            
        if self.value_clear_requests:
            body = {"ranges": self.value_clear_requests}
            await loop.run_in_executor(
                self._executor,
                lambda: self._service.spreadsheets().values().batchClear(
                    spreadsheetId=self.spreadsheet_id, body=body).execute()
            )
            self.value_clear_requests = []
            
        return response
