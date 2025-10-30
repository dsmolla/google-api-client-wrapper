import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import aiofiles
from google.auth.credentials import Credentials
from googleapiclient.discovery import build

from . import utils
from .types import EmailMessage, EmailAttachment, Label, EmailThread


class AsyncGmailApiService:

    def __init__(self, credentials: Credentials, timezone: str):
        self._executor = ThreadPoolExecutor()
        self._credentials = credentials
        self._timezone = timezone

    def __del__(self):
        """Cleanup ThreadPoolExecutor on deletion."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

    def _service(self):
        return build("gmail", "v1", credentials=self._credentials)

    def query(self):
        from .async_query_builder import AsyncEmailQueryBuilder
        return AsyncEmailQueryBuilder(self, self._timezone)

    async def list_emails(
            self,
            max_results: Optional[int] = 100,
            query: Optional[str] = None,
            include_spam_trash: bool = False,
            label_ids: Optional[List[str]] = None
    ) -> List[str]:

        if max_results < 1:
            raise ValueError(f"max_results must be at least 1")

        request_params = {
            'userId': 'me',
            'maxResults': max_results,
            'includeSpamTrash': include_spam_trash
        }
        if query:
            request_params['q'] = query
        if label_ids:
            request_params['labelIds'] = label_ids

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().messages().list(**request_params).execute()
        )

        message_ids = [message['id'] for message in result.get('messages', [])]

        while result.get('nextPageToken') and len(message_ids) < max_results:
            request_params['maxResults'] = max_results - len(message_ids)
            result = await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().messages().list(
                    **request_params,
                    pageToken=result['nextPageToken']
                ).execute()
            )

            message_ids.extend([message['id'] for message in result.get('messages', [])])

        return message_ids

    async def get_email(self, message_id: str) -> EmailMessage:
        loop = asyncio.get_event_loop()
        gmail_message = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().messages().get(userId='me', id=message_id, format='full').execute()
        )

        return utils.from_gmail_message(gmail_message, timezone=self._timezone)

    async def send_email(
            self,
            to: List[str],
            subject: Optional[str] = None,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            cc: Optional[List[str]] = None,
            bcc: Optional[List[str]] = None,
            attachment_paths: Optional[List[str]] = None,
            reply_to_message_id: Optional[str] = None,
            references: Optional[str] = None,
            thread_id: Optional[str] = None
    ) -> EmailMessage:

        raw_message = utils.create_message(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachment_paths=attachment_paths,
            references=references,
            reply_to_message_id=reply_to_message_id
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().messages().send(
                userId='me',
                body={'raw': raw_message, 'threadId': thread_id}
            ).execute()
        )

        return await self.get_email(result['id'])

    async def create_draft(
            self,
            to: List[str],
            subject: Optional[str] = None,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            cc: Optional[List[str]] = None,
            bcc: Optional[List[str]] = None,
            attachment_paths: Optional[List[str]] = None,
            reply_to_message_id: Optional[str] = None,
            references: Optional[str] = None,
            thread_id: Optional[str] = None
    ) -> EmailMessage:

        raw_message = utils.create_message(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachment_paths=attachment_paths,
            references=references,
            reply_to_message_id=reply_to_message_id
        )

        draft_body = {
            'message': {
                'raw': raw_message
            }
        }

        if thread_id:
            draft_body['message']['threadId'] = thread_id

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().drafts().create(
                userId='me',
                body=draft_body
            ).execute()
        )

        return await self.get_email(result['message']['id'])

    async def batch_get_emails(self, message_ids: List[str]) -> List["EmailMessage"]:
        tasks = []
        for message_id in message_ids:
            task = asyncio.create_task(self.get_email(message_id))
            tasks.append(task)

        emails = await asyncio.gather(*tasks, return_exceptions=True)
        return emails

    async def batch_send_emails(self, email_data_list: List[Dict[str, Any]]) -> List["EmailMessage"]:
        tasks = []
        for email_data in email_data_list:
            task = asyncio.create_task(self.send_email(**email_data))
            tasks.append(task)

        emails = await asyncio.gather(*tasks, return_exceptions=True)
        return emails

    async def reply(
            self,
            original_email: Union[EmailMessage, str],
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            attachment_paths: Optional[List[str]] = None,
    ) -> EmailMessage:
        if isinstance(original_email, str):
            original_email = await self.get_email(original_email)

        if original_email.is_from('me'):
            to = original_email.get_recipient_emails()
        else:
            to = [original_email.sender.email]

        enhanced_references = utils.build_references_header(original_email)
        email = await self.send_email(
            to=to,
            subject=original_email.subject,
            body_text=body_text,
            body_html=body_html,
            attachment_paths=attachment_paths,
            reply_to_message_id=original_email.reply_to_id,
            references=enhanced_references,
            thread_id=original_email.thread_id
        )
        return email

    async def forward(
            self,
            original_email: Union[EmailMessage, str],
            to: List[str],
            include_attachments: bool = True
    ) -> EmailMessage:

        if isinstance(original_email, str):
            original_email = await self.get_email(original_email)

        subject = f"Fwd: {original_email.subject}" if original_email.subject else "Fwd:"

        forwarded_body_text = None
        if original_email.body_text:
            forwarded_body_text = utils.prepare_forward_body_text(original_email)

        forwarded_body_html = None
        if original_email.body_html:
            forwarded_body_html = utils.prepare_forward_body_html(original_email)

        attachment_data_list = []
        if include_attachments and original_email.attachments:
            for attachment in original_email.attachments:
                attachment_bytes = self.get_attachment_payload(attachment)
                attachment_data_list.append((attachment.filename, attachment.mime_type, attachment_bytes))

        raw_message = utils.create_message(
            to=to,
            subject=subject,
            body_text=forwarded_body_text,
            body_html=forwarded_body_html,
            attachment_data_list=attachment_data_list if attachment_data_list else None
        )

        loop = asyncio.get_event_loop()
        email = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
        )

        return await self.get_email(email['id'])

    async def mark_as_read(self, email: Union[EmailMessage, str]) -> bool:
        try:
            if isinstance(email, str):
                message_id = email
            else:
                message_id = email.message_id

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
            )
            email.is_read = True
            return True
        except Exception:
            return False

    async def mark_as_unread(self, email: Union[EmailMessage, str]) -> bool:
        try:
            if isinstance(email, str):
                message_id = email
            else:
                message_id = email.message_id

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'addLabelIds': ['UNREAD']}
                ).execute()
            )
            email.is_read = False
            return True
        except Exception:
            return False

    async def add_label(self, email: Union[EmailMessage, str], labels: List[str]) -> bool:
        try:
            if isinstance(email, str):
                message_id = email
            else:
                message_id = email.message_id

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'addLabelIds': labels}
                ).execute()
            )
            return True
        except Exception:
            return False

    async def remove_label(self, email: Union[EmailMessage, str], labels: List[str]) -> bool:
        try:
            if isinstance(email, str):
                message_id = email
            else:
                message_id = email.message_id

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'removeLabelIds': labels}
                ).execute()
            )
            for label in labels:
                try:
                    email.labels.remove(label)
                except ValueError:
                    continue
            return True
        except Exception:
            return False

    async def delete_email(self, email: Union[EmailMessage, str], permanent: bool = False) -> bool:
        try:
            if isinstance(email, str):
                message_id = email
            else:
                message_id = email.message_id

            loop = asyncio.get_event_loop()
            if permanent:
                await loop.run_in_executor(
                    self._executor,
                    lambda: self._service().users().messages().delete(userId='me', id=message_id).execute()
                )
            else:
                await loop.run_in_executor(
                    self._executor,
                    lambda: self._service().users().messages().trash(userId='me', id=message_id).execute()
                )
            return True
        except Exception:
            return False

    async def get_attachment_payload(self, attachment: Union[EmailAttachment, dict]) -> bytes:
        if isinstance(attachment, dict):
            if not all(k in attachment for k in ('attachment_id', 'message_id')):
                raise ValueError("Attachment dictionary must contain 'attachment_id' and 'message_id' keys.")
            message_id = attachment['message_id']
            attachment_id = attachment['attachment_id']
        else:
            message_id = attachment.message_id
            attachment_id = attachment.attachment_id

        loop = asyncio.get_event_loop()
        payload = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
        )

        data = payload['data']
        data = base64.urlsafe_b64decode(data + '===')

        return data

    async def download_attachment(
            self,
            attachment: Union[EmailAttachment, dict],
            download_folder: str = str(Path.home() / "Downloads" / "GmailAttachments")
    ) -> str:
        download_folder = Path(download_folder)
        download_folder.mkdir(parents=True, exist_ok=True)

        if isinstance(attachment, EmailAttachment):
            filename = attachment.filename
        else:
            if not all(k in attachment for k in ('filename', 'attachment_id', 'message_id')):
                raise ValueError(
                    "Attachment dictionary must contain 'filename', 'attachment_id', and 'message_id' keys."
                )
            filename = attachment['filename']

        file_path = str(download_folder.joinpath(filename))
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(await self.get_attachment_payload(attachment))

        return file_path

    async def download_all_attachments(
            self,
            email: Union[EmailMessage, str],
            download_folder: str = str(Path.home() / "Downloads" / "GmailAttachments")
    ) -> List[str | Exception]:
        if isinstance(email, str):
            email = await self.get_email(email)

        tasks = []
        for attachment in email.attachments:
            task = asyncio.create_task(self.download_attachment(attachment, download_folder))
            tasks.append(task)

        downloaded_paths = await asyncio.gather(*tasks, return_exceptions=True)
        return downloaded_paths

    async def create_label(self, name: str) -> "Label":
        loop = asyncio.get_event_loop()
        label = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().labels().create(
                userId='me',
                body={'name': name, 'type': 'user'}
            ).execute()
        )
        return Label(
            id=label['id'],
            name=label['name'],
            type=label['type']
        )

    async def list_labels(self) -> List["Label"]:
        loop = asyncio.get_event_loop()
        labels = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().labels().list(userId='me').execute()
        )
        labels = labels.get('labels', [])

        labels_list = []
        for label in labels:
            labels_list.append(
                Label(
                    id=label['id'],
                    name=label['name'],
                    type=label['type']
                )
            )

        return labels_list

    async def delete_label(self, label: Union[Label, str]) -> bool:
        try:
            if isinstance(label, Label):
                label = label.id

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().labels().delete(userId='me', id=label).execute()
            )
            return True
        except Exception:
            return False

    async def update_label(self, label: Union[Label, str], new_name: str) -> "Label":
        try:
            if isinstance(label, Label):
                label = label.id

            loop = asyncio.get_event_loop()
            updated_label = await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().labels().patch(
                    userId='me',
                    id=label,
                    body={'name': new_name}
                ).execute()
            )
            label.name = updated_label.get('name')
            return updated_label
        except Exception:
            raise

    async def list_threads(
            self,
            max_results: Optional[int] = 100,
            query: Optional[str] = None,
            include_spam_trash: bool = False,
            label_ids: Optional[List[str]] = None
    ) -> List[str]:

        if max_results < 1:
            raise ValueError(f"max_results must be at least 1")

        request_params = {
            'userId': 'me',
            'maxResults': max_results,
            'includeSpamTrash': include_spam_trash
        }

        if query:
            request_params['q'] = query
        if label_ids:
            request_params['labelIds'] = label_ids

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().threads().list(**request_params).execute()
        )
        thread_ids = [thread['id'] for thread in result.get('threads', [])]
        while result.get('nextPageToken') and len(thread_ids) < max_results:
            request_params['maxResults'] = max_results - len(thread_ids)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().threads().list(
                    **request_params,
                    pageToken=result['nextPageToken']
                ).execute()
            )
            thread_ids.extend([thread['id'] for thread in result.get('messages', [])])

        return thread_ids

    async def get_thread(self, thread_id: str) -> EmailThread:
        loop = asyncio.get_event_loop()
        thread = await loop.run_in_executor(
            self._executor,
            lambda: self._service().users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
        )
        return utils.from_gmail_thread(thread, self._timezone)

    async def batch_get_thread(self, thread_ids: List[str]) -> List[EmailThread]:
        tasks = []
        for thread_id in thread_ids:
            task = asyncio.create_task(self.get_thread(thread_id))
            tasks.append(task)

        threads = await asyncio.gather(*tasks, return_exceptions=True)
        return threads

    async def delete_thread(self, thread: Union[EmailThread, str], permanent: bool = False) -> bool:
        try:
            if isinstance(thread, EmailThread):
                thread = thread.thread_id

            if permanent:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor,
                    lambda: self._service().users().threads().delete(userId='me', id=thread).execute()
                )
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor,
                    lambda: self._service().users().threads().trash(userId='me', id=thread).execute()
                )
            return True
        except Exception:
            return False

    async def modify_thread_labels(
            self,
            thread: Union[EmailThread, str],
            add_labels: Optional[List[str]] = None,
            remove_labels: Optional[List[str]] = None
    ) -> bool:

        try:
            if not add_labels and not remove_labels:
                return True

            if isinstance(thread, EmailThread):
                thread = thread.thread_id

            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().threads().modify(
                    userId='me',
                    id=thread,
                    body=body
                ).execute()
            )

            return True
        except Exception:
            return False

    async def untrash_thread(self, thread: Union[EmailThread, str]) -> bool:
        try:
            if isinstance(thread, EmailThread):
                thread = thread.thread_id

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                lambda: self._service().users().threads().untrash(userId='me', id=thread).execute()
            )
            return True
        except Exception:
            return False
