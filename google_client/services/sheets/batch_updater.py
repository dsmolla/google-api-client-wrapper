from .base_batch_updater import BaseSheetsBatchUpdater

class SheetsBatchUpdater(BaseSheetsBatchUpdater):
    """
    Builder class for chaining multiple spreadsheet modification requests 
    into a single Google Sheets API batchUpdate call.
    """

    def __init__(self, service, spreadsheet_id: str):
        super().__init__(spreadsheet_id)
        self._service = service

    def execute(self) -> dict:
        """
        Fires all accumulating requests using the appropriate API endpoints.
        """
        response = {}
        if self.requests:
            body = {"requests": self.requests}
            response = self._service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id, body=body).execute()
            self.requests = []
            
        if self.value_update_requests:
            body = {
                "valueInputOption": "USER_ENTERED",
                "data": self.value_update_requests
            }
            res = self._service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id, body=body).execute()
            if not response: response = res
            self.value_update_requests = []
            
        for req in self.value_append_requests:
            body = {"values": req["values"]}
            self._service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id, range=req["range"],
                valueInputOption="USER_ENTERED", body=body).execute()
        self.value_append_requests = []
            
        if self.value_clear_requests:
            body = {"ranges": self.value_clear_requests}
            self._service.spreadsheets().values().batchClear(
                spreadsheetId=self.spreadsheet_id, body=body).execute()
            self.value_clear_requests = []
            
        return response
