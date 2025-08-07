import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from ...auth.manager import auth_manager
from ...utils.datetime import convert_datetime_to_readable, convert_datetime_to_local_timezone
from ...utils.log_sanitizer import sanitize_for_logging
from dataclasses import dataclass, field
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import getaddresses, parsedate_to_datetime
import mimetypes
import html
import os
from html2text import html2text
from contextlib import asynccontextmanager
from aiogoogle.excs import HTTPError
import re

logger = logging.getLogger(__name__)

# Constants
MAX_RESULTS_LIMIT = 2500
MAX_SUBJECT_LENGTH = 998  # RFC 2822 practical limit
MAX_BODY_LENGTH = 25000000  # ~25MB Gmail limit
DEFAULT_MAX_RESULTS = 30

# Import exceptions from centralized location
from ...exceptions.gmail import GmailError as AsyncGmailError, GmailPermissionError as AsyncGmailPermissionError, EmailNotFoundError as AsyncEmailNotFoundError


def _sanitize_header_value(value: str) -> str:
    """
    Sanitize a string value for safe use in HTTP headers.
    
    Prevents header injection by removing control characters that could 
    be used to inject additional headers or corrupt the MIME structure.
    
    Args:
        value: The string to sanitize
        
    Returns:
        Sanitized string safe for use in headers
    """
    if not value:
        return ""
        
    # Remove control characters that could cause header injection
    # This includes \r, \n, \0, and other control characters
    sanitized = re.sub(r'[\r\n\x00-\x1f\x7f-\x9f]', '', value)
    
    # Remove any quotes that could break the header structure
    sanitized = sanitized.replace('"', '')
    
    # Limit length to prevent overly long headers
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized.strip()

@asynccontextmanager
async def async_gmail_service():
    """Async context manager for Gmail service connections with error handling."""
    try:
        async with auth_manager.get_async_gmail_service() as (aiogoogle, gmail_service):
            yield aiogoogle, gmail_service
    except FileNotFoundError as e:
        raise AsyncGmailError(f"Credentials file not found: {e}")
    except ValueError as e:
        raise AsyncGmailError(f"Invalid credentials format: {e}")
    except HTTPError as e:
        if e.res.status_code == 403:
            raise AsyncGmailPermissionError(f"Permission denied: {e}")
        elif e.res.status_code == 404:
            raise AsyncEmailNotFoundError(f"Email or label not found: {e}")
        else:
            raise AsyncGmailError(f"Gmail API error: {e}")
    except Exception as e:
        raise AsyncGmailError(f"Unexpected Gmail service error: {e}")

@dataclass
class AsyncEmailAddress:
    """
    Represents an email address with name and email.
    Args:
        email: The email address.
        name: The display name (optional).
    """
    email: str
    name: Optional[str] = None

    def __post_init__(self):
        if not self.email:
            raise ValueError("Email address cannot be empty.")
        if not self._is_valid_email(self.email):
            raise ValueError(f"Invalid email format: {self.email}")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format using regex."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def to_dict(self) -> dict:
        """
        Converts the EmailAddress instance to a dictionary representation.
        Returns:
            A dictionary containing the email address data.
        """
        result = {"email": self.email}
        if self.name:
            result["name"] = self.name
        return result

    def __str__(self):
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email

@dataclass
class AsyncEmailAttachment:
    """
    Represents an email attachment.
    Args:
        filename: The name of the attachment file.
        content_type: The MIME type of the attachment.
        size: The size of the attachment in bytes.
        attachment_id: The unique identifier for the attachment in Gmail.
        message_id: The message id of the message the attachment is attached to.
        data: The attachment data (optional, loaded on demand).
    """
    filename: str
    content_type: str
    size: int
    attachment_id: str
    message_id: str
    data: Optional[bytes] = None

    def __post_init__(self):
        if not self.filename:
            raise ValueError("Attachment filename cannot be empty")
        if not self.attachment_id:
            raise ValueError("Attachment ID cannot be empty")
        if not self.message_id:
            raise ValueError("Message ID cannot be empty")

    def to_dict(self) -> dict:
        """
        Converts the EmailAttachment instance to a dictionary representation.
        Returns:
            A dictionary containing the attachment data.
        """
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "attachment_id": self.attachment_id,
            "message_id": self.message_id,
        }

    async def load_data(self) -> bool:
        """
        Downloads the attachment from the Gmail API and loads it into the data variable.
        Returns:
            True if the attachment was successfully loaded.
        """
        self.data = await self._get_attachment_data()
        return True

    async def download_attachment(self, directory: str) -> bool:
        """
        Downloads the attachment from the Gmail API and saves it into the specified directory with the original filename.
        
        Security: This method includes path traversal protection to prevent malicious filenames 
        from accessing files outside the specified directory. Filenames containing path separators
        or attempting directory traversal (e.g., '../../../etc/passwd') will be rejected.
        
        Args:
            directory: The destination directory for the attachment.

        Returns:
            True if the attachment was successfully downloaded.
            
        Raises:
            ValueError: If filename contains path traversal attempts or invalid path separators.
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        if not os.path.isdir(directory):
            raise ValueError(f"Provided path '{directory}' is not a directory.")

        # Security: Prevent path traversal attacks
        resolved_directory = os.path.realpath(directory)
        file_path = os.path.join(directory, self.filename)
        resolved_file_path = os.path.realpath(file_path)
        
        # Ensure the resolved file path is within the intended directory
        # Use os.path.commonpath to check if they share the same root path
        try:
            common_path = os.path.commonpath([resolved_directory, resolved_file_path])
            if common_path != resolved_directory:
                raise ValueError("Security error: Path traversal detected in filename.")
        except ValueError:
            # os.path.commonpath raises ValueError if paths are on different drives (Windows)
            raise ValueError("Security error: Path traversal detected in filename.")
            
        # Additional check: ensure no path separators in filename itself
        if os.sep in self.filename or (os.altsep and os.altsep in self.filename):
            raise ValueError("Security error: Path separators not allowed in filename.")
        
        sanitized = sanitize_for_logging(attachment_id=self.attachment_id, filename=self.filename, 
                                       message_id=self.message_id)
        logger.info("Downloading attachment %s from message %s to %s",
                    sanitized.get('attachment_id', self.attachment_id), 
                    sanitized.get('message_id', self.message_id), file_path)
        try:
            attachment_data = await self._get_attachment_data()
            with open(file_path, 'wb') as f:
                f.write(attachment_data)
            return True
        except (OSError, IOError, PermissionError) as e:
            logger.error("Failed to write attachment file. Check directory permissions.")
            logger.debug("File write error: %s", str(e)[:100])
            raise
        except Exception as e:
            logger.error("Unexpected error downloading attachment.")
            logger.debug("Download error: %s", str(e)[:100])
            raise

    async def _get_attachment_data(self) -> bytes:
        """
        Retrieves the attachment in bytes from a message.

        Returns:
            The attachment data as bytes.
        """
        logger.info("Retrieving attachment %s from message %s", self.attachment_id, self.message_id)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                attachment = await aiogoogle.as_user(
                    service.users.messages.attachments.get(
                        userId='me',
                        messageId=self.message_id,
                        id=self.attachment_id
                    )
                )
                
                data = attachment['data']
                return base64.urlsafe_b64decode(data + '===')
            except HTTPError as e:
                if e.res.status_code == 403:
                    raise AsyncGmailPermissionError(f"Permission denied accessing attachment: {e}")
                elif e.res.status_code == 404:
                    raise AsyncEmailNotFoundError(f"Attachment not found: {e}")
                else:
                    raise AsyncGmailError(f"Gmail API error downloading attachment: {e}")
            except (ValueError, KeyError) as e:
                logger.error("Invalid attachment data format.")
                logger.debug("Attachment data error: %s", str(e)[:100])
                raise AsyncGmailError(f"Invalid attachment data: {e}")
            except Exception as e:
                logger.error("Unexpected error downloading attachment.")
                logger.debug("Attachment download error: %s", str(e)[:100])
                raise

@dataclass
class AsyncLabel:
    """
    Represents a Gmail label.
    Args:
        id: The unique identifier for the label.
        name: The name of the label.
        type: The type of the label (e.g., system, user).
    """
    id: str
    name: str
    type: str

    def __post_init__(self):
        if not self.id:
            raise ValueError("Label ID cannot be empty")
        if not self.name:
            raise ValueError("Label name cannot be empty")

    @classmethod
    async def list_labels(cls) -> List["AsyncLabel"]:
        """
        Fetches a list of labels from Gmail.
        Returns:
            A list of AsyncLabel objects representing the labels.
        """
        logger.info("Fetching labels from Gmail")
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                labels_response = await aiogoogle.as_user(
                    service.users.labels.list(userId='me')
                )
                labels = labels_response.get('labels', [])
                logger.info("Found %d labels", len(labels))

                labels_list = []
                for label in labels:
                    labels_list.append(cls(
                        id=label.get('id'),
                        name=label.get('name'),
                        type=label.get('type')
                    ))

                return labels_list
            except Exception as e:
                logger.error("Failed to fetch labels: %s", e)
                raise

    @classmethod
    async def create_label(cls, name: str) -> "AsyncLabel":
        """
        Creates a new label in Gmail.
        Args:
            name: The name of the label to create.

        Returns:
            An AsyncLabel object representing the created label.
        """
        logger.info("Creating label with name: %s", name)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                label = await aiogoogle.as_user(
                    service.users.labels.create(
                        userId='me',
                        json={'name': name, 'type': 'user'}
                    )
                )
                return cls(
                    id=label.get('id'),
                    name=label.get('name'),
                    type=label.get('type', 'user')
                )
            except Exception as e:
                logger.error("Error creating label: %s", e)
                raise

    @classmethod
    async def get_label(cls, label_id: str) -> "AsyncLabel":
        """
        Retrieves a specific label by its ID.
        Args:
            label_id: The unique identifier of the label to retrieve.

        Returns:
            An AsyncLabel object representing the label.
        """
        logger.info("Retrieving label with ID: %s", label_id)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                label = await aiogoogle.as_user(
                    service.users.labels.get(userId='me', id=label_id)
                )
                return cls(
                    id=label.get('id'),
                    name=label.get('name'),
                    type=label.get('type')
                )
            except Exception as e:
                logger.error("Error retrieving label: %s", e)
                raise

    async def delete_label(self) -> bool:
        """
        Deletes this label.

        Returns:
            True if the label was successfully deleted, False otherwise.
        """
        logger.info("Deleting label with ID: %s", self.id)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                await aiogoogle.as_user(
                    service.users.labels.delete(userId='me', id=self.id)
                )
                logger.info("Label deleted successfully")
                return True
            except Exception as e:
                logger.error("Error deleting label: %s", e)
                return False

    async def update_label(self, new_name: str) -> "AsyncLabel":
        """
        Updates the name of this label.
        Args:
            new_name: The new name for the label.

        Returns:
            The updated AsyncLabel object.
        """
        logger.info("Updating label %s to new name: %s", self.id, new_name)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                updated_label = await aiogoogle.as_user(
                    service.users.labels.patch(
                        userId='me',
                        id=self.id,
                        json={'name': new_name}
                    )
                )
                self.name = updated_label.get('name')
                return self
            except Exception as e:
                logger.error("Error updating label: %s", e)
                raise

    def __repr__(self):
        return f"AsyncLabel(id={self.id}, name={self.name}, type={self.type})"

@dataclass
class AsyncEmailMessage:
    """
    Represents a Gmail message with various attributes.
    Args:
        message_id: Unique identifier for the message.
        thread_id: The thread ID this message belongs to.
        subject: The subject line of the email.
        sender: The sender's email address information.
        recipients: List of recipient email addresses (To field).
        cc_recipients: List of CC recipient email addresses.
        bcc_recipients: List of BCC recipient email addresses.
        date_time: When the message was sent or received.
        body_text: Plain text body of the email.
        body_html: HTML body of the email.
        attachments: List of attachments in the email.
        label_ids: List of Gmail labels applied to the message.
        is_read: Whether the message has been read.
        is_starred: Whether the message is starred.
        is_important: Whether the message is marked as important.
        snippet: A short snippet of the message content.
        reply_to_id: The ID of the message to use when replying to this message.
    """
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    reply_to_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[AsyncEmailAddress] = None
    recipients: List[AsyncEmailAddress] = field(default_factory=list)
    cc_recipients: List[AsyncEmailAddress] = field(default_factory=list)
    bcc_recipients: List[AsyncEmailAddress] = field(default_factory=list)
    date_time: Optional[datetime] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    attachments: List[AsyncEmailAttachment] = field(default_factory=list)
    label_ids: List[str] = field(default_factory=list)
    is_read: bool = False
    is_starred: bool = False
    is_important: bool = False
    snippet: Optional[str] = None

    def __post_init__(self):
        self._validate_text_field(self.subject, MAX_SUBJECT_LENGTH, "subject")
        self._validate_text_field(self.body_text, MAX_BODY_LENGTH, "body_text")
        self._validate_text_field(self.body_html, MAX_BODY_LENGTH, "body_html")

    def _validate_text_field(self, value: Optional[str], max_length: int, field_name: str) -> None:
        """Validates text field length and content."""
        if value and len(value) > max_length:
            raise ValueError(f"Email {field_name} cannot exceed {max_length} characters")

    @staticmethod
    def _extract_body(payload: dict) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts plain text and HTML body from Gmail message payload.
        Returns:
            A tuple of (plain_text, html_text)
        """
        body_text = None
        body_html = None

        def decode_body(data: str) -> str:
            """Decode base64url encoded body data."""
            try:
                return base64.urlsafe_b64decode(data + '===').decode('utf-8')
            except:
                return ""

        def extract_from_parts(parts: List[dict]):
            nonlocal body_text, body_html
            for part in parts:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain' and part.get('body', {}).get('data'):
                    body_text = decode_body(part['body']['data'])
                elif mime_type == 'text/html' and part.get('body', {}).get('data'):
                    body_html = decode_body(part['body']['data'])
                elif part.get('parts'):
                    extract_from_parts(part['parts'])

        # Handle different payload structures
        if payload.get('parts'):
            extract_from_parts(payload['parts'])
        elif payload.get('body', {}).get('data'):
            mime_type = payload.get('mimeType', '')
            if mime_type == 'text/plain':
                body_text = decode_body(payload['body']['data'])
            elif mime_type == 'text/html':
                body_html = decode_body(payload['body']['data'])

        return body_text, body_html

    @staticmethod
    def _extract_attachments(message_id: str, payload: dict) -> List[AsyncEmailAttachment]:
        """
        Extracts attachment information from Gmail message payload.
        Returns:
            A list of AsyncEmailAttachment objects.
        """
        attachments = []

        def extract_from_parts(parts: List[dict]):
            for part in parts:
                if part.get('filename') and part.get('body', {}).get('attachmentId'):
                    try:
                        attachment = AsyncEmailAttachment(
                            filename=part['filename'],
                            content_type=part.get('mimeType', 'application/octet-stream'),
                            size=part.get('body', {}).get('size', 0),
                            attachment_id=part['body']['attachmentId'],
                            message_id=message_id
                        )
                        attachments.append(attachment)
                    except ValueError as e:
                        logger.warning("Skipping invalid attachment: %s", e)
                elif part.get('parts'):
                    extract_from_parts(part['parts'])

        if payload.get('parts'):
            extract_from_parts(payload['parts'])

        return attachments

    @staticmethod
    def _from_gmail_message(gmail_message: dict) -> "AsyncEmailMessage":
        """
        Creates an AsyncEmailMessage instance from a Gmail API response.
        Args:
            gmail_message: A dictionary containing message data from Gmail API.

        Returns:
            An AsyncEmailMessage instance populated with the data from the dictionary.
        """
        headers = {}
        payload = gmail_message.get('payload', {})

        # Extract headers
        for header in payload.get('headers', []):
            headers[header['name'].lower()] = header['value']

        # Parse email addresses
        def parse_email_addresses(header_value: str) -> List[AsyncEmailAddress]:
            if not header_value:
                return []

            addresses = []
            for name, email in getaddresses([header_value]):
                if email and AsyncEmailAddress._is_valid_email(email):
                    try:
                        addresses.append(AsyncEmailAddress(email=email, name=name if name else None))
                    except ValueError as e:
                        logger.warning("Skipping invalid email address: %s", e)
            return addresses

        sender = None
        if headers.get('from'):
            sender_list = parse_email_addresses(headers['from'])
            sender = sender_list[0] if sender_list else None

        recipients = parse_email_addresses(headers.get('to', ''))
        cc_recipients = parse_email_addresses(headers.get('cc', ''))
        bcc_recipients = parse_email_addresses(headers.get('bcc', ''))

        # Extract body
        body_text, body_html = AsyncEmailMessage._extract_body(payload)

        # Extract attachments
        message_id = gmail_message.get('id')
        attachments = AsyncEmailMessage._extract_attachments(message_id, payload)

        # Parse date
        date_received = None
        if headers.get('date'):
            try:
                # Parse RFC 2822 date format
                date_received = parsedate_to_datetime(headers['date'])
                date_received = convert_datetime_to_local_timezone(date_received)
            except:
                logger.warning("Failed to parse date: %s", headers.get('date'))

        # Extract labels
        labels = gmail_message.get('labelIds', [])

        # Determine read status, starred, important
        is_read = 'UNREAD' not in labels
        is_starred = 'STARRED' in labels
        is_important = 'IMPORTANT' in labels

        return AsyncEmailMessage(
            message_id=gmail_message.get('id'),
            thread_id=gmail_message.get('threadId'),
            subject=headers.get('subject', "").strip(),
            sender=sender,
            recipients=recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            date_time=date_received,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            label_ids=labels,
            is_read=is_read,
            is_starred=is_starred,
            is_important=is_important,
            snippet=html.unescape(gmail_message.get('snippet')).strip(),
            reply_to_id=headers.get('message-id')
        )

    @staticmethod
    def _create_message(
            to: List[str],
            subject: Optional[str] = None,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            cc: Optional[List[str]] = None,
            bcc: Optional[List[str]] = None,
            attachments: Optional[List[str]] = None,
            reply_to_message_id: Optional[str] = None
    ) -> str:
        """
        Creates a MIMEText email message.
        
        Security: Attachment filenames are sanitized to prevent header injection attacks.
        Filenames containing control characters (CRLF, etc.) that could inject additional 
        headers are automatically cleaned.
        
        Args:
            to: List of recipient email addresses.
            subject: The subject line of the email.
            body_text: Plain text body of the email (optional).
            body_html: HTML body of the email (optional).
            cc: List of CC recipient email addresses (optional).
            bcc: List of BCC recipient email addresses (optional).
            attachments: List of file paths to attach (optional).
            reply_to_message_id: ID of message this is replying to (optional).

        Returns:
            A base64 encoded string representing the email message.
        """
        if not to:
            raise ValueError("At least one recipient is required.")

        # Validate inputs
        if subject and len(subject) > MAX_SUBJECT_LENGTH:
            raise ValueError(f"Subject cannot exceed {MAX_SUBJECT_LENGTH} characters")
        if body_text and len(body_text) > MAX_BODY_LENGTH:
            raise ValueError(f"Body text cannot exceed {MAX_BODY_LENGTH} characters")
        if body_html and len(body_html) > MAX_BODY_LENGTH:
            raise ValueError(f"Body HTML cannot exceed {MAX_BODY_LENGTH} characters")

        if body_html and body_text:
            message = MIMEMultipart('alternative')
            message.attach(MIMEText(body_text, 'plain'))
            message.attach(MIMEText(body_html, 'html'))
        elif body_html:
            message = MIMEText(body_html, 'html')
        else:
            message = MIMEText(body_text or '', 'plain')

        message['to'] = ', '.join(to)
        message['subject'] = subject

        if cc:
            message['cc'] = ', '.join(cc)
        if bcc:
            message['bcc'] = ', '.join(bcc)

        # Add attachments
        if attachments:
            # Convert to multipart if needed
            if not isinstance(message, MIMEMultipart):
                original_message = message
                message = MIMEMultipart()
                message.attach(original_message)
                message['to'] = ', '.join(to)
                message['subject'] = subject
                if cc:
                    message['cc'] = ', '.join(cc)
                if bcc:
                    message['bcc'] = ', '.join(bcc)

            for file_path in attachments:
                if os.path.isfile(file_path):
                    content_type, encoding = mimetypes.guess_type(file_path)
                    if content_type is None or encoding is not None:
                        content_type = 'application/octet-stream'

                    main_type, sub_type = content_type.split('/', 1)

                    with open(file_path, 'rb') as fp:
                        attachment = MIMEBase(main_type, sub_type)
                        attachment.set_payload(fp.read())
                        encoders.encode_base64(attachment)
                        # Sanitize filename to prevent header injection
                        safe_filename = _sanitize_header_value(os.path.basename(file_path))
                        attachment.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{safe_filename}"'
                        )
                        message.attach(attachment)

        # Add reply headers if this is a reply
        if reply_to_message_id:
            message['In-Reply-To'] = reply_to_message_id
            message['References'] = reply_to_message_id

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        return raw_message

    @classmethod
    def query(cls) -> "AsyncEmailQueryBuilder":
        """
        Create a new AsyncEmailQueryBuilder for building complex email queries with a fluent API.
        
        Returns:
            AsyncEmailQueryBuilder instance for method chaining
            
        Example:
            emails = await (AsyncEmailMessage.query()
                .limit(50)
                .from_sender("sender@example.com")
                .search("meeting")
                .with_attachments()
                .execute())
        """
        from .async_query_builder import AsyncEmailQueryBuilder
        return AsyncEmailQueryBuilder(cls)

    @classmethod
    async def list_emails(
            cls,
            max_results: Optional[int] = DEFAULT_MAX_RESULTS,
            query: Optional[str] = None,
            include_spam_trash: bool = False,
            label_ids: Optional[List[str]] = None
    ) -> List["AsyncEmailMessage"]:
        """
        Fetches a list of messages from Gmail with optional filtering.

        Args:
            max_results: Maximum number of messages to retrieve. Defaults to 30.
            query: Gmail search query string (same syntax as Gmail search).
            include_spam_trash: Whether to include messages from spam and trash.
            label_ids: List of label IDs to filter by.

        Returns:
            A list of AsyncEmailMessage objects representing the messages found.
            If no messages are found, an empty list is returned.
        """
        # Input validation
        if max_results and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

        sanitized = sanitize_for_logging(query=query, max_results=max_results, 
                                        include_spam_trash=include_spam_trash, label_ids=label_ids)
        logger.info("Fetching messages with max_results=%s, query=%s, include_spam_trash=%s, label_ids=%s",
                    sanitized['max_results'], sanitized['query'], sanitized['include_spam_trash'], sanitized['label_ids'])

        async with async_gmail_service() as (aiogoogle, service):
            # Get list of message IDs
            request_params = {
                'userId': 'me',
                'maxResults': max_results,
                'includeSpamTrash': include_spam_trash
            }

            if query:
                request_params['q'] = query
            if label_ids:
                request_params['labelIds'] = label_ids

            try:
                result = await aiogoogle.as_user(
                    service.users.messages.list(**request_params)
                )
                messages = result.get('messages', [])

                logger.info("Found %d message IDs", len(messages))

                # Fetch full message details concurrently
                tasks = [cls.get_email(message['id']) for message in messages]
                email_messages = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out exceptions and log them
                valid_messages = []
                for msg in email_messages:
                    if isinstance(msg, Exception):
                        logger.warning("Failed to fetch message: %s", msg)
                    else:
                        valid_messages.append(msg)

                logger.info("Successfully fetched %d complete messages", len(valid_messages))
                return valid_messages

            except Exception as e:
                logger.error("An error occurred while fetching messages: %s", e)
                raise

    @classmethod
    async def get_email(cls, message_id: str) -> "AsyncEmailMessage":
        """
        Retrieves a specific message from Gmail using its unique identifier.

        Args:
            message_id: The unique identifier of the message to be retrieved.

        Returns:
            An AsyncEmailMessage object representing the message with the specified ID.
        """
        logger.info("Retrieving message with ID: %s", message_id)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                gmail_message = await aiogoogle.as_user(
                    service.users.messages.get(
                        userId='me',
                        id=message_id,
                        format='full'
                    )
                )
                logger.info("Message retrieved successfully")
                return cls._from_gmail_message(gmail_message)
            except Exception as e:
                logger.error("Error retrieving message: %s", e)
                raise

    @classmethod
    async def send_email(
            cls,
            to: List[str],
            subject: Optional[str] = None,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            cc: Optional[List[str]] = None,
            bcc: Optional[List[str]] = None,
            attachments: Optional[List[str]] = None,
            reply_to_message_id: Optional[str] = None,
            thread_id: Optional[str] = None
    ) -> "AsyncEmailMessage":
        """
        Sends a new email message.

        Args:
            to: List of recipient email addresses.
            subject: The subject line of the email.
            body_text: Plain text body of the email (optional).
            body_html: HTML body of the email (optional).
            cc: List of CC recipient email addresses (optional).
            bcc: List of BCC recipient email addresses (optional).
            attachments: List of file paths to attach (optional).
            reply_to_message_id: ID of message this is replying to (optional).
            thread_id: ID of the thread to which this message belongs (optional).

        Returns:
            An AsyncEmailMessage object representing the message sent.
        """
        sanitized = sanitize_for_logging(subject=subject, to=to)
        logger.info("Sending message with subject=%s, to=%s", sanitized['subject'], sanitized['to'])

        # Create message
        raw_message = cls._create_message(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
            reply_to_message_id=reply_to_message_id
        )

        async with async_gmail_service() as (aiogoogle, service):
            try:
                send_result = await aiogoogle.as_user(
                    service.users.messages.send(
                        userId='me',
                        json={'raw': raw_message, 'threadId': thread_id}
                    )
                )

                logger.info("Message sent successfully with ID: %s", send_result.get('id'))
                return await cls.get_email(send_result['id'])

            except Exception as e:
                logger.error("Error sending message: %s", e)
                raise

    @classmethod
    async def batch_get_emails(cls, message_ids: List[str]) -> List["AsyncEmailMessage"]:
        """
        Retrieves multiple emails concurrently.
        
        Args:
            message_ids: List of message IDs to retrieve
            
        Returns:
            List of AsyncEmailMessage objects
        """
        logger.info("Batch retrieving %d messages", len(message_ids))
        
        tasks = [cls.get_email(message_id) for message_id in message_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        valid_messages = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Failed to fetch message: %s", result)
            else:
                valid_messages.append(result)
                
        return valid_messages

    @classmethod
    async def batch_send_emails(cls, email_data_list: List[Dict[str, Any]]) -> List["AsyncEmailMessage"]:
        """
        Sends multiple emails concurrently.
        
        Args:
            email_data_list: List of dictionaries containing email parameters
            
        Returns:
            List of sent AsyncEmailMessage objects
        """
        logger.info("Batch sending %d emails", len(email_data_list))
        
        tasks = [cls.send_email(**email_data) for email_data in email_data_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        valid_messages = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Failed to send email: %s", result)
            else:
                valid_messages.append(result)
                
        return valid_messages

    async def reply(
            self,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            attachments: Optional[List[str]] = None
    ) -> "AsyncEmailMessage":
        """
        Sends a reply to the current email message.
        Args:
            body_text: Plain text body of the email.
            body_html: HTML body of the email.
            attachments: List of file paths to attach (optional).
        Returns:
            An AsyncEmailMessage object representing the message sent.
        """
        if self.is_from('me'):
            to = self.get_recipient_emails()
        else:
            to = [self.sender.email]

        logger.info("Replying to message %s", self.message_id)
        return await AsyncEmailMessage.send_email(
            to=to,
            subject=self.subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            reply_to_message_id=self.reply_to_id,
            thread_id=self.thread_id
        )

    async def mark_as_read(self) -> bool:
        """
        Marks a message as read by removing the UNREAD label.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Marking message as read: %s", self.message_id)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                await aiogoogle.as_user(
                    service.users.messages.modify(
                        userId='me',
                        id=self.message_id,
                        json={'removeLabelIds': ['UNREAD']}
                    )
                )
                self.is_read = True
                logger.info("Message marked as read successfully")
                return True
            except Exception as e:
                logger.error("Error marking message as read: %s", e)
                return False

    async def mark_as_unread(self) -> bool:
        """
        Marks a message as unread by adding the UNREAD label.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Marking message as unread: %s", self.message_id)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                await aiogoogle.as_user(
                    service.users.messages.modify(
                        userId='me',
                        id=self.message_id,
                        json={'addLabelIds': ['UNREAD']}
                    )
                )
                self.is_read = False
                logger.info("Message marked as unread successfully")
                return True
            except Exception as e:
                logger.error("Error marking message as unread: %s", e)
                return False

    async def add_label(self, label_ids: List[str]) -> bool:
        """
        Adds labels to a message.

        Args:
            label_ids: List of label IDs to add.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Adding labels %s to message: %s", label_ids, self.message_id)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                await aiogoogle.as_user(
                    service.users.messages.modify(
                        userId='me',
                        id=self.message_id,
                        json={'addLabelIds': label_ids}
                    )
                )
                # Update local state
                for label_id in label_ids:
                    if label_id not in self.label_ids:
                        self.label_ids.append(label_id)
                logger.info("Labels added successfully")
                return True
            except Exception as e:
                logger.error("Error adding labels: %s", e)
                return False

    async def remove_label(self, label_ids: List[str]) -> bool:
        """
        Removes labels from a message.

        Args:
            label_ids: List of label IDs to remove.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Removing labels %s from message: %s", label_ids, self.message_id)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                await aiogoogle.as_user(
                    service.users.messages.modify(
                        userId='me',
                        id=self.message_id,
                        json={'removeLabelIds': label_ids}
                    )
                )
                # Update local state
                for label_id in label_ids:
                    if label_id in self.label_ids:
                        self.label_ids.remove(label_id)
                logger.info("Labels removed successfully")
                return True
            except Exception as e:
                logger.error("Error removing labels: %s", e)
                return False

    async def delete_email(self, permanent: bool = False) -> bool:
        """
        Deletes a message (moves to trash or permanently deletes).

        Args:
            permanent: If True, permanently deletes the message. If False, moves to trash.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Deleting message: %s, permanent=%s", self.message_id, permanent)
        
        async with async_gmail_service() as (aiogoogle, service):
            try:
                if permanent:
                    await aiogoogle.as_user(
                        service.users.messages.delete(userId='me', id=self.message_id)
                    )
                    logger.info("Message permanently deleted")
                else:
                    await aiogoogle.as_user(
                        service.users.messages.trash(userId='me', id=self.message_id)
                    )
                    logger.info("Message moved to trash")
                return True
            except Exception as e:
                logger.error("Error deleting message: %s", e)
                return False

    def get_plain_text_content(self) -> str:
        """
        Retrieves the plain text content of the email message, converting HTML if necessary.
        Returns:
            The plain text content if available, empty string otherwise.
        """
        if self.body_text:
            return self.body_text.strip()
        elif self.body_html:
            return html2text(self.body_html)
        return ""

    def has_attachments(self) -> bool:
        """
        Checks if the message has attachments.
        Returns:
            True if the message has attachments, False otherwise.
        """
        return len(self.attachments) > 0

    def get_recipient_emails(self) -> List[str]:
        """
        Retrieves a list of recipient emails (To).
        Returns:
            A list of recipient email addresses.
        """
        return [recipient.email for recipient in self.recipients]

    def get_all_recipient_emails(self) -> List[str]:
        """
        Retrieves a list of all recipient email addresses (To, CC, BCC).
        Returns:
            A list of email addresses.
        """
        emails = []
        for recipient in self.recipients + self.cc_recipients + self.bcc_recipients:
            emails.append(recipient.email)
        return emails

    def is_from(self, email: str) -> bool:
        """
        Checks if the message is from a specific email address.
        Use "me" to check if the message is from the authenticated user.
        Args:
            email: The email address to check.

        Returns:
            True if the message is from the specified email, False otherwise.
        """
        if email.lower() == "me":
            # Special case for checking if the message is from the authenticated user
            return 'SENT' in self.label_ids

        return self.sender and self.sender.email.lower() == email.lower()

    def has_label(self, label: str) -> bool:
        """
        Checks if the message has a specific label.
        Args:
            label: The label to check for.

        Returns:
            True if the message has the label, False otherwise.
        """
        return label in self.label_ids

    def __repr__(self):
        return (
            f"Subject: {self.subject!r}\n"
            f"From: {self.sender}\n"
            f"To: {', '.join(str(r) for r in self.recipients)}\n"
            f"Date: {convert_datetime_to_readable(self.date_time) if self.date_time else 'Unknown'}\n"
            f"Snippet: {self.snippet}\n"
            f"Labels: {', '.join(self.label_ids)}\n"
        )