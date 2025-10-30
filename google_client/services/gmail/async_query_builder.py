from typing import Optional, List

from . import AsyncGmailApiService
from .query_builder import EmailQueryBuilder


class AsyncEmailQueryBuilder(EmailQueryBuilder):
    def __init__(self, api_service_class: AsyncGmailApiService, timezone: str):
        super().__init__(api_service_class, timezone)

    async def execute(self) -> List[str]:
        query_string = " ".join(self._query_parts) if self._query_parts else None
        emails = await self._api_service.list_emails(
            max_results=self._max_results,
            query=query_string,
            include_spam_trash=self._include_spam_trash,
            label_ids=self._label_ids if self._label_ids else None
        )

        return emails

    async def first(self) -> Optional[str]:
        results = await self.limit(1).execute()
        return results[0] if results else None

    async def exists(self) -> bool:
        return (await self.first()) is not None

    async def get_threads(self) -> List[str]:
        query_string = " ".join(self._query_parts) if self._query_parts else None
        threads = await self._api_service.list_threads(
            max_results=self._max_results,
            query=query_string,
            include_spam_trash=self._include_spam_trash,
            label_ids=self._label_ids if self._label_ids else None
        )

        return threads

    def __repr__(self):
        query_string = " ".join(self._query_parts) if self._query_parts else "None"
        return f"EmailQueryBuilder(query='{query_string}', limit={self._max_results})"
